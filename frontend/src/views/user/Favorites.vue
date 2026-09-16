<template>
  <div class="favorites">
    <h2 class="sub-title">收藏夹</h2>

    <el-tabs v-model="tab" @tab-change="onTabChange">
      <el-tab-pane label="实体词条" name="entity" />
      <el-tab-pane label="问答记录" name="qa" />
    </el-tabs>

    <div v-loading="loading">
      <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="load" />
      <EmptyState
        v-else-if="!list.length && !loading"
        :icon="tab === 'entity' ? 'Collection' : 'ChatLineSquare'"
        :text="tab === 'entity' ? '还没有收藏词条，去百科页看看？' : '还没有收藏问答，去提一个问题？'"
        :action-text="tab === 'entity' ? '去图谱' : '去提问'"
        @action="router.push(tab === 'entity' ? '/graph' : '/qa')"
      />

      <div v-for="item in list" :key="item.id" class="fav-item">
        <div class="fav-main" @click="open(item)">
          <template v-if="tab === 'entity'">
            <span class="fav-name">{{ item.ref_id }}</span>
            <TypeBadge v-if="item.entity_type" :type="item.entity_type" class="fav-badge" />
            <el-tag v-if="item.deleted" size="small" type="info" effect="plain">词条已删除</el-tag>
          </template>
          <template v-else>
            <p class="fav-question">{{ item.question || `问答记录 #${item.ref_id}` }}</p>
            <p class="fav-answer">{{ summary(item.answer) }}</p>
          </template>
          <span class="fav-time">{{ item.created_at }}</span>
        </div>
        <div class="fav-actions">
          <el-button v-if="tab === 'qa' && item.question" link type="primary" size="small"
            @click="reAsk(item.question)">重新提问</el-button>
          <el-button link type="danger" size="small" @click="cancel(item)">取消收藏</el-button>
        </div>
      </div>

      <div v-if="total > size" class="pager">
        <el-pagination layout="prev, pager, next" :current-page="page" :page-size="size" :total="total"
          @current-change="onPageChange" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import TypeBadge from '@/components/common/TypeBadge.vue'
import { getFavorites, removeFavorite } from '@/api/user'

// 收藏夹（FR-U05）：实体 / 问答两页签，取消收藏，跳转回原页继续学习
const router = useRouter()
const tab = ref('entity')
const list = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)
const loading = ref(false)
const error = ref('')

function summary(text) {
  const s = String(text || '')
  return s.length > 60 ? `${s.slice(0, 60)}…` : s
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await getFavorites({ fav_type: tab.value, page: page.value, size: size.value })
    list.value = data.list || []
    total.value = data.total || 0
  } catch {
    list.value = []
    error.value = '收藏夹加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function onTabChange() {
  page.value = 1
  load()
}

function onPageChange(p) {
  page.value = p
  load()
}

function open(item) {
  if (tab.value !== 'entity' || item.deleted) return
  router.push({ name: 'entity', params: { name: item.ref_id } })
}

function reAsk(question) {
  router.push({ name: 'qa', query: { q: question } })
}

async function cancel(item) {
  try {
    await ElMessageBox.confirm('确定取消收藏吗？', '取消收藏', {
      type: 'warning',
      confirmButtonText: '取消收藏',
      cancelButtonText: '再想想',
    })
  } catch {
    return
  }
  try {
    await removeFavorite({ fav_type: tab.value, ref_id: String(item.ref_id) })
    ElMessage.success('已取消收藏')
    if (list.value.length === 1 && page.value > 1) page.value -= 1
    load()
  } catch (err) {
    ElMessage.error((err && err.msg) || '操作失败，请重试')
  }
}

onMounted(load)
</script>

<style scoped>
.sub-title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 600;
}
.fav-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border);
}
.fav-main {
  flex: 1;
  cursor: pointer;
}
.fav-name {
  font-weight: 600;
}
.fav-badge {
  margin-left: 6px;
}
.fav-question {
  margin: 0 0 4px;
  font-weight: 600;
}
.fav-answer {
  margin: 0 0 4px;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.fav-time {
  font-size: 12px;
  color: var(--color-text-light);
}
.fav-actions {
  flex-shrink: 0;
}
</style>
