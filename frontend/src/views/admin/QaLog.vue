<template>
  <div class="qa-log">
    <div class="card">
      <div class="toolbar">
        <el-input v-model="query.kw" placeholder="按问句关键词检索" clearable class="kw-input" @keyup.enter="search" />
        <el-select v-model="query.fallback" placeholder="全部结果" clearable class="s-select">
          <el-option label="图谱命中" value="0" />
          <el-option label="兜底" value="1" />
        </el-select>
        <el-select v-model="query.source" placeholder="全部来源" clearable class="s-select">
          <el-option v-for="s in SOURCES" :key="s.value" :label="s.label" :value="s.value" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期"
          end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="onDateChange" />
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="Download" :loading="exporting" @click="exportCsv">导出 CSV</el-button>
      </div>

      <div v-loading="loading">
        <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="load" />
        <EmptyState v-else-if="!list.length && !loading" icon="ChatLineSquare" text="暂无问答日志"
          action-text="清空筛选" @action="resetQuery" />

        <el-table v-else :data="list" size="default">
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="expand-box">
                <p><strong>答案：</strong>{{ row.answer || '（无）' }}</p>
                <p v-if="row.llm_detail"><strong>AI 生成详情：</strong></p>
                <pre v-if="row.llm_detail" class="detail-pre">{{ pretty(row.llm_detail) }}</pre>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="时间" min-width="160" />
          <el-table-column prop="user_name" label="用户" width="110" />
          <el-table-column prop="question" label="问句" min-width="220" show-overflow-tooltip />
          <el-table-column prop="intent" label="意图" width="90" />
          <el-table-column prop="matched_entity" label="命中实体" min-width="140" show-overflow-tooltip />
          <el-table-column label="兜底" width="80">
            <template #default="{ row }">
              <el-tag size="small" :type="Number(row.fallback) === 1 ? 'warning' : 'success'" effect="plain">
                {{ Number(row.fallback) === 1 ? '是' : '否' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="回答来源" width="110">
            <template #default="{ row }">{{ SOURCE_ZH[row.answer_source] || row.answer_source }}</template>
          </el-table-column>
          <el-table-column label="时延" width="90">
            <template #default="{ row }">
              {{ row.llm_latency_ms != null ? `${row.llm_latency_ms} ms` : '—' }}
            </template>
          </el-table-column>
        </el-table>

        <div v-if="total > query.size" class="pager">
          <el-pagination layout="total, prev, pager, next" :current-page="query.page" :page-size="query.size"
            :total="total" @current-change="onPageChange" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Search } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import { exportQaLogs, getQaLogs } from '@/api/adminLog'

// 问答日志（FR-A06 / FR-L04）：筛选 + llm 记录展开 + 按当前筛选导出 CSV（utf-8-sig，Excel 无乱码）
const SOURCES = [
  { value: 'kg', label: '知识图谱' },
  { value: 'passage', label: '权威段落' },
  { value: 'llm', label: 'AI 生成' },
]
const SOURCE_ZH = { kg: '知识图谱', passage: '权威段落', llm: 'AI 生成' }

const list = ref([])
const total = ref(0)
const loading = ref(false)
const exporting = ref(false)
const error = ref('')
const dateRange = ref([])
const query = reactive({ kw: '', fallback: '', source: '', from: '', to: '', page: 1, size: 10 })

function pretty(text) {
  try {
    return JSON.stringify(typeof text === 'string' ? JSON.parse(text) : text, null, 2)
  } catch {
    return text
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await getQaLogs({ ...query })
    list.value = data.list || []
    total.value = data.total || 0
  } catch (err) {
    list.value = []
    error.value = (err && err.msg) || '问答日志加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function onDateChange(value) {
  query.from = value && value[0] ? value[0] : ''
  query.to = value && value[1] ? value[1] : ''
}

function search() {
  query.page = 1
  load()
}

function resetQuery() {
  Object.assign(query, { kw: '', fallback: '', source: '', from: '', to: '', page: 1 })
  dateRange.value = []
  load()
}

function onPageChange(p) {
  query.page = p
  load()
}

// 导出与当前筛选条件一致
async function exportCsv() {
  exporting.value = true
  try {
    const blob = await exportQaLogs({ ...query, page: undefined, size: undefined })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `qa_logs_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    ElMessage.success('已导出')
  } catch (err) {
    ElMessage.error((err && err.msg) || '导出失败，请重试')
  } finally {
    exporting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.kw-input {
  width: 200px;
}
.s-select {
  width: 130px;
}
.expand-box {
  padding: 8px 16px;
  line-height: 1.8;
}
.expand-box p {
  margin: 0 0 6px;
}
.detail-pre {
  max-height: 260px;
  overflow: auto;
  margin: 0;
  padding: 8px;
  font-size: 12px;
  background: var(--color-bg-gray);
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
