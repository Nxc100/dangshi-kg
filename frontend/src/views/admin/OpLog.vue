<template>
  <div class="op-log">
    <div class="card">
      <div class="toolbar">
        <el-select v-model="query.action" placeholder="全部动作" clearable class="s-select">
          <el-option v-for="a in ACTIONS" :key="a.value" :label="a.label" :value="a.value" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          @change="onDateChange"
        />
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <span class="text-light">操作日志只可查询，不可删除（审计属性）</span>
      </div>

      <div v-loading="loading">
        <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="load" />
        <EmptyState v-else-if="!list.length && !loading" icon="Tickets" text="暂无操作日志"
          action-text="清空筛选" @action="resetQuery" />

        <el-table v-else :data="list" size="default">
          <el-table-column prop="created_at" label="时间" min-width="160" />
          <el-table-column prop="admin_name" label="操作人" width="120" />
          <el-table-column label="动作" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="ACTION_TYPE[row.action] || 'info'" effect="plain">
                {{ ACTION_ZH[row.action] || row.action }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="对象" min-width="200">
            <template #default="{ row }">
              <span class="obj-kind">{{ row.object_type === 'entity' ? '实体' : '关系' }}</span>
              <span v-if="row.object_label" class="obj-label">{{ objectLabel(row) }}</span>
              {{ row.object_name }}
            </template>
          </el-table-column>
          <el-table-column label="变更摘要" min-width="220">
            <template #default="{ row }">
              <el-popover v-if="row.summary" placement="left" width="420" trigger="click">
                <template #reference><el-button link type="primary" size="small">查看</el-button></template>
                <pre class="summary-pre">{{ pretty(row.summary) }}</pre>
              </el-popover>
              <span v-else class="text-light">—</span>
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
import { Search } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import { getOpLog } from '@/api/adminKg'
import { labelZh, relationZh } from '@/utils/ontology'

// 知识操作日志（FR-A04）：只读，按动作与日期范围筛选；与知识写操作 1:1 对应
const ACTIONS = [
  { value: 'add', label: '新增' },
  { value: 'edit', label: '编辑' },
  { value: 'delete', label: '删除' },
]
const ACTION_ZH = { add: '新增', edit: '编辑', delete: '删除' }
const ACTION_TYPE = { add: 'success', edit: 'warning', delete: 'danger' }

const list = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const dateRange = ref([])
const query = reactive({ action: '', from: '', to: '', page: 1, size: 10 })

function objectLabel(row) {
  return row.object_type === 'entity' ? labelZh(row.object_label) : relationZh(row.object_label)
}

function pretty(text) {
  try {
    return JSON.stringify(JSON.parse(text), null, 2)
  } catch {
    return text
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await getOpLog({ ...query })
    list.value = data.list || []
    total.value = data.total || 0
  } catch (err) {
    list.value = []
    error.value = (err && err.msg) || '操作日志加载失败，请稍后重试'
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
  query.action = ''
  query.from = ''
  query.to = ''
  dateRange.value = []
  search()
}

function onPageChange(p) {
  query.page = p
  load()
}

onMounted(load)
</script>

<style scoped>
.s-select {
  width: 150px;
}
.obj-kind {
  margin-right: 6px;
  font-size: 12px;
  color: var(--color-text-light);
}
.obj-label {
  margin-right: 6px;
  color: var(--color-text-secondary);
}
.summary-pre {
  max-height: 320px;
  overflow: auto;
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
