<template>
  <div class="history">
    <div class="history-head">
      <h2 class="sub-title">提问历史</h2>
      <el-button v-if="list.length" type="danger" link :icon="Delete" @click="clearAll">清空历史</el-button>
    </div>

    <div v-loading="loading">
      <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="load" />
      <EmptyState v-else-if="!list.length && !loading" icon="ChatDotRound" text="暂无提问，去问一个？"
        action-text="去提问" @action="router.push('/qa')" />

      <div v-for="item in list" :key="item.id" class="history-item">
        <div class="item-main">
          <p class="item-question">
            {{ item.question }}
            <el-tag v-if="item.fallback" size="small" type="warning" effect="plain">兜底</el-tag>
          </p>
          <p class="item-answer">{{ summary(item.answer) }}</p>
          <span class="item-time">{{ item.created_at }}</span>
        </div>
        <div class="item-actions">
          <el-button link type="primary" size="small" @click="reAsk(item.question)">重新提问</el-button>
          <el-button link type="danger" size="small" @click="remove(item)">删除</el-button>
        </div>
      </div>

      <div v-if="total > size" class="pager">
        <el-pagination
          layout="prev, pager, next"
          :current-page="page"
          :page-size="size"
          :total="total"
          @current-change="onPageChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import { clearHistory, deleteHistory, getHistory } from '@/api/user'

// 提问历史（FR-U04）：倒序分页 + 一键重问 + 删除 / 清空（逻辑删除，不影响管理员日志与统计计数）
const router = useRouter()
const list = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)
const loading = ref(false)
const error = ref('')

function summary(text) {
  const s = String(text || '')
  return s.length > 40 ? `${s.slice(0, 40)}…` : s || '（无答案文本）'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await getHistory({ page: page.value, size: size.value })
    list.value = data.list || []
    total.value = data.total || 0
  } catch {
    list.value = []
    error.value = '历史加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function onPageChange(p) {
  page.value = p
  load()
}

function reAsk(question) {
  router.push({ name: 'qa', query: { q: question } })
}

async function remove(item) {
  try {
    await ElMessageBox.confirm('确定删除这条提问记录吗？', '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteHistory(item.id)
    ElMessage.success('已删除')
    if (list.value.length === 1 && page.value > 1) page.value -= 1
    load()
  } catch (err) {
    ElMessage.error((err && err.msg) || '删除失败，请重试')
  }
}

async function clearAll() {
  try {
    await ElMessageBox.confirm('确定清空全部提问历史吗？该操作仅影响你的个人视图。', '清空确认', {
      type: 'warning',
      confirmButtonText: '清空',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await clearHistory()
    ElMessage.success('已清空')
    page.value = 1
    load()
  } catch (err) {
    ElMessage.error((err && err.msg) || '清空失败，请重试')
  }
}

onMounted(load)
</script>

<style scoped>
.history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sub-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
}
.history-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border);
}
.item-question {
  margin: 0 0 4px;
  font-weight: 600;
}
.item-answer {
  margin: 0 0 4px;
  color: var(--color-text-secondary);
  font-size: 13px;
}
.item-time {
  font-size: 12px;
  color: var(--color-text-light);
}
.item-actions {
  flex-shrink: 0;
}
</style>
