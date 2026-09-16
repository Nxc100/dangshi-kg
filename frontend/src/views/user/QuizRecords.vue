<template>
  <div class="quiz-records">
    <h2 class="sub-title">测验记录</h2>

    <div v-loading="loading">
      <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="load" />
      <EmptyState v-else-if="!list.length && !loading" icon="Tickets" text="还没有测验记录，去测一组？"
        action-text="去测验" @action="router.push('/quiz')" />

      <el-table v-else :data="list" size="default">
        <el-table-column prop="created_at" label="测验时间" min-width="160" />
        <el-table-column label="成绩" width="120">
          <template #default="{ row }">
            <span class="score">{{ row.score }}</span> / {{ row.total }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openDetail(row.id)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="total > size" class="pager">
        <el-pagination layout="prev, pager, next" :current-page="page" :page-size="size" :total="total"
          @current-change="onPageChange" />
      </div>
    </div>

    <el-dialog v-model="detailVisible" title="测验详情" width="680px">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <p class="detail-meta">
            成绩 <strong class="score">{{ detail.score }}</strong> / {{ detail.total }} ·
            用时 {{ detail.detail && detail.detail.duration_sec ? detail.detail.duration_sec : 0 }} 秒 ·
            {{ detail.created_at }}
          </p>
          <div v-for="(q, i) in questions" :key="i" class="detail-item" :class="{ wrong: !q.correct }">
            <p class="detail-question">{{ i + 1 }}. {{ q.question }}</p>
            <p class="detail-answer">
              你的作答：<strong>{{ q.chosen || '未作答' }}</strong>
              <span v-if="!q.correct" class="right-key">正确答案：{{ q.answer_key }}</span>
            </p>
            <router-link v-if="q.entity" class="detail-link"
              :to="{ name: 'entity', params: { name: q.entity.name } }">
              去百科页复习「{{ q.entity.name }}」
            </router-link>
          </div>
        </template>
      </div>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="primary" :disabled="!wrongEntities.length" @click="practiceWrong">针对错题再练</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import { getQuizRecord, getQuizRecords } from '@/api/quiz'

// 测验记录（FR-U06）：列表 + 逐题回顾（错题标红 + 百科复习）+ 针对错题再练
const router = useRouter()
const list = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)
const loading = ref(false)
const error = ref('')

const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)

const questions = computed(() => (detail.value && detail.value.detail && detail.value.detail.questions) || [])
const wrongEntities = computed(() =>
  questions.value.filter((q) => !q.correct && q.entity).map((q) => q.entity.name),
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await getQuizRecords({ page: page.value, size: size.value })
    list.value = data.list || []
    total.value = data.total || 0
  } catch {
    list.value = []
    error.value = '测验记录加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function onPageChange(p) {
  page.value = p
  load()
}

async function openDetail(id) {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await getQuizRecord(id)
  } catch (err) {
    ElMessage.error((err && err.msg) || '详情加载失败')
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

// 以错题涉及的实体重新出题（不足 5 题由后端自动补随机题）
function practiceWrong() {
  detailVisible.value = false
  router.push({ name: 'quiz', query: { entities: wrongEntities.value.join(',') } })
}

onMounted(load)
</script>

<style scoped>
.sub-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
}
.score {
  color: var(--color-primary);
  font-weight: 700;
}
.detail-meta {
  margin: 0 0 12px;
  color: var(--color-text-secondary);
}
.detail-item {
  padding: 10px 12px;
  margin-bottom: 8px;
  border-radius: var(--radius);
  background: var(--color-bg);
}
.detail-item.wrong {
  background: rgba(245, 108, 108, 0.08);
}
.detail-question {
  margin: 0 0 4px;
  line-height: 1.7;
}
.detail-answer {
  margin: 0 0 4px;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.detail-item.wrong .detail-answer strong {
  color: var(--color-danger);
}
.right-key {
  margin-left: 10px;
  color: var(--color-success);
}
.detail-link {
  font-size: 13px;
}
</style>
