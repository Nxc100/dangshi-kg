<template>
  <div class="page quiz-page">
    <h1 class="page-title">党史知识测验</h1>

    <div v-if="stage === 'setup'" class="card setup-card">
      <p class="setup-tip">题目由知识图谱中已人工校验的核心知识自动生成，答完可查看解析并前往词条复习。</p>
      <el-radio-group v-model="count" size="large">
        <el-radio-button :value="5">5 题</el-radio-button>
        <el-radio-button :value="10">10 题</el-radio-button>
      </el-radio-group>
      <div class="setup-action">
        <el-button type="primary" size="large" :loading="loading" @click="start">开始测验</el-button>
      </div>
      <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="start" />
    </div>

    <template v-else-if="stage === 'doing'">
      <div class="card progress-card">
        <span>已答 {{ answeredCount }} / {{ questions.length }}</span>
        <el-progress :percentage="progress" :stroke-width="10" class="progress-bar" />
      </div>
      <QuestionCard
        v-for="(q, i) in questions"
        :key="q.id"
        :question="q"
        :index="i"
        :chosen="answers[q.id] || ''"
        class="quiz-item"
        @choose="onChoose"
      />
      <div class="card finish-bar">
        <el-button type="primary" :disabled="answeredCount < questions.length" @click="finish">
          {{ answeredCount < questions.length ? `还有 ${questions.length - answeredCount} 题未作答` : '查看成绩' }}
        </el-button>
      </div>
    </template>

    <ScorePanel
      v-else
      :score="score"
      :total="questions.length"
      :duration-sec="durationSec"
      :review="review"
      :saving="saving"
      :saved="saved"
      @save="save"
      @restart="restart"
    />

    <LoginGuide v-model="loginGuide" text="登录后可保存成绩并查看历史错题" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import QuestionCard from '@/components/quiz/QuestionCard.vue'
import ScorePanel from '@/components/quiz/ScorePanel.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import LoginGuide from '@/components/common/LoginGuide.vue'
import { getQuiz, submitQuiz } from '@/api/quiz'
import { useUserStore } from '@/store/user'

// 测验页（F7 / FR-G06 / FR-U06）：游客可试做，成绩暂存前端；"保存成绩"触发登录引导，登录用户写入测验记录
const route = useRoute()
const userStore = useUserStore()

const stage = ref('setup') // setup | doing | score
const count = ref(5)
const questions = ref([])
const answers = ref({})
const loading = ref(false)
const error = ref('')
const saving = ref(false)
const saved = ref(false)
const loginGuide = ref(false)
const durationSec = ref(0)
let startedAt = 0

const answeredCount = computed(() => Object.keys(answers.value).length)
const progress = computed(() =>
  questions.value.length ? Math.round((answeredCount.value / questions.value.length) * 100) : 0,
)
const score = computed(
  () => questions.value.filter((q) => answers.value[q.id] === q.answer_key).length,
)
const review = computed(() =>
  questions.value.map((q) => ({ question: q.question, correct: answers.value[q.id] === q.answer_key })),
)

async function start() {
  loading.value = true
  error.value = ''
  try {
    // "针对错题再练"由 /quiz?entities=a,b 进入，优先以这些实体出题
    const entities = route.query.entities ? String(route.query.entities).split(',').filter(Boolean) : []
    const data = await getQuiz(count.value, entities)
    questions.value = data.questions || []
    if (!questions.value.length) {
      error.value = '题库暂无可用题目，请先导入知识图谱数据'
      return
    }
    answers.value = {}
    saved.value = false
    startedAt = Date.now()
    stage.value = 'doing'
  } catch (err) {
    error.value = (err && err.msg) || '出题失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function onChoose({ id, key }) {
  answers.value = { ...answers.value, [id]: key }
}

function finish() {
  durationSec.value = Math.round((Date.now() - startedAt) / 1000)
  stage.value = 'score'
}

async function save() {
  if (!userStore.isLogin) {
    loginGuide.value = true // 成绩暂存前端，登录回跳后不丢失
    return
  }
  saving.value = true
  try {
    // 后端按 zip(questions, answers) 复算得分并校验长度，answers 必须是与题目等长、同序的数组
    await submitQuiz({
      questions: questions.value,
      answers: questions.value.map((q) => answers.value[q.id] ?? ''),
      duration_sec: durationSec.value,
    })
    saved.value = true
    ElMessage.success('成绩已保存，可在个人中心查看')
  } catch (err) {
    ElMessage.error((err && err.msg) || '保存失败，请重试')
  } finally {
    saving.value = false
  }
}

function restart() {
  stage.value = 'setup'
  questions.value = []
  answers.value = {}
  saved.value = false
}

onMounted(() => {
  if (route.query.entities) start()
})
</script>

<style scoped>
.setup-card {
  text-align: center;
  padding: 32px 20px;
}
.setup-tip {
  margin: 0 0 18px;
  color: var(--color-text-secondary);
}
.setup-action {
  margin-top: 20px;
}
.progress-card {
  display: flex;
  align-items: center;
  gap: 16px;
  color: var(--color-text-secondary);
}
.progress-bar {
  flex: 1;
}
.quiz-item {
  margin-top: 16px;
}
.finish-bar {
  margin-top: 16px;
  text-align: center;
}
</style>
