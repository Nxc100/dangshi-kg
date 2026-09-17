<template>
  <div class="page qa-page">
    <div class="qa-head">
      <h1 class="page-title">智能问答</h1>
      <LlmToggle />
    </div>

    <div ref="listRef" class="qa-list card">
      <div v-if="!messages.length" class="qa-welcome">
        <p class="welcome-text">你好，我是党史学习助手。答案均来自知识图谱与权威资料，可查看来源。</p>
        <ExampleQuestions @pick="send" />
      </div>

      <template v-for="msg in messages" :key="msg.id">
        <ChatBubble v-if="msg.role === 'user'" role="user" :avatar="userStore.avatar_url">
          {{ msg.text }}
        </ChatBubble>

        <ChatBubble v-else role="system" :loading="msg.loading" :loading-text="loadingText" :hint="msg.hint">
          <template v-if="!msg.loading">
            <template v-if="msg.data.answer_source === 'llm' && msg.data.llm">
              <LlmAnswer :llm="msg.data.llm" :passages="msg.data.fallback_passages" />
              <!-- 规范 1.1：气泡底部固定两个操作，AI 生成回答同样可收藏 -->
              <div class="llm-actions">
                <el-button link :type="msg.favorited ? 'primary' : 'default'" size="small"
                  :icon="msg.favorited ? StarFilled : Star" @click="toggleFavorite(msg)">
                  {{ msg.favorited ? '已收藏' : '收藏' }}
                </el-button>
              </div>
            </template>

            <!-- 兜底且无段落时，引导语由 FallbackPassages 统一呈现，此处不重复渲染 answer_text -->
            <AnswerContent
              v-else-if="msg.data.answer_text && !msg.data.clarify && !isGuideOnly(msg.data)"
              :text="msg.data.answer_text"
              :entities="msg.data.entities"
              :subgraph="msg.data.subgraph"
              :favorited="msg.favorited"
              @favorite="toggleFavorite(msg)"
            />

            <template v-if="msg.data.clarify">
              <p class="clarify-text">{{ msg.data.clarify.text }}</p>
              <CandidateChips tip="" :items="msg.data.clarify.examples" @pick="send" />
            </template>

            <CandidateChips
              v-if="msg.data.candidates && msg.data.candidates.length"
              tip="你是不是想问："
              :items="msg.data.candidates"
              @pick="(c) => send(c.name)"
            />

            <FallbackPassages
              v-if="msg.data.fallback && msg.data.answer_source !== 'llm'"
              :passages="msg.data.fallback_passages"
              @ask="send"
            />
          </template>
        </ChatBubble>
      </template>
    </div>

    <div class="qa-input card">
      <el-input
        v-model="draft"
        type="textarea"
        :rows="2"
        resize="none"
        maxlength="100"
        show-word-limit
        placeholder="请输入党史问题，回车发送（Shift + 回车换行）"
        @keydown.enter.exact.prevent="send(draft)"
      />
      <div class="input-actions">
        <span class="input-tip">{{ inputError }}</span>
        <el-button type="primary" :loading="sending" :icon="Promotion" @click="send(draft)">发送</el-button>
      </div>
    </div>

    <LoginGuide v-model="loginGuide" text="登录后可收藏问答，随时回看" />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Promotion, Star, StarFilled } from '@element-plus/icons-vue'
import ChatBubble from '@/components/qa/ChatBubble.vue'
import AnswerContent from '@/components/qa/AnswerContent.vue'
import CandidateChips from '@/components/qa/CandidateChips.vue'
import FallbackPassages from '@/components/qa/FallbackPassages.vue'
import LlmAnswer from '@/components/qa/LlmAnswer.vue'
import LlmToggle from '@/components/qa/LlmToggle.vue'
import ExampleQuestions from '@/components/qa/ExampleQuestions.vue'
import LoginGuide from '@/components/common/LoginGuide.vue'
import { askQuestion } from '@/api/qa'
import { addFavorite, removeFavorite } from '@/api/user'
import { useUserStore } from '@/store/user'
import { useLlmPrefStore } from '@/store/llmPref'
import { questionError } from '@/utils/validators'

// 问答页（F1 / F9 / FR-L01~L03）：气泡流 + 溯源子图 + 候选 / 澄清 / 兜底 / AI 生成分支
const route = useRoute()
const userStore = useUserStore()
const llmPref = useLlmPrefStore()

const draft = ref('')
const messages = ref([])
const sending = ref(false)
const loginGuide = ref(false)
const listRef = ref(null)

let msgSeq = 0
const nextId = () => {
  msgSeq += 1
  return msgSeq
}

const inputError = computed(() => (draft.value ? questionError(draft.value) : ''))
const loadingText = computed(() => (llmPref.useLlm ? 'AI 生成中…' : '正在查询知识图谱…'))

// 兜底且检索不到段落时，后端把引导语放在 answer_text，兜底区也会展示同一句引导语；
// 此时只由 FallbackPassages 呈现，避免同一句话在气泡里出现两次
function isGuideOnly(data) {
  return data.fallback && data.answer_source !== 'llm' && !(data.fallback_passages || []).length
}

// 仅保留最近一轮，作为追问改写上下文（prev_a 截断 200 字）
function lastRound() {
  for (let i = messages.value.length - 1; i >= 0; i -= 1) {
    const m = messages.value[i]
    if (m.role === 'system' && !m.loading && m.data) {
      const answer = m.data.answer_text || (m.data.llm && m.data.llm.text) || ''
      return { prev_q: m.question, prev_a: String(answer).slice(0, 200) }
    }
  }
  return { prev_q: '', prev_a: '' }
}

async function scrollToEnd() {
  await nextTick()
  if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
}

async function send(input) {
  const text = String(input || '').trim()
  const error = questionError(text)
  if (error) {
    ElMessage.warning(error)
    return
  }
  if (sending.value) return

  const round = lastRound()
  messages.value.push({ id: nextId(), role: 'user', text })
  const bubble = {
    id: nextId(), role: 'system', loading: true, question: text, data: null, hint: '', favorited: false,
  }
  messages.value.push(bubble)
  draft.value = ''
  sending.value = true
  scrollToEnd()

  try {
    const data = await askQuestion({
      question: text,
      use_llm: llmPref.useLlm,
      prev_q: round.prev_q,
      prev_a: round.prev_a,
    })
    bubble.data = data
    // 发生追问改写时，以浅色小字展示实际查询的问句（data.question 为改写后问句）
    bubble.hint = data.rewritten_from
      ? `已按「${data.question || text}」为你查询（原问句：${data.rewritten_from}）`
      : ''
  } catch (err) {
    bubble.data = {
      answer_text: err && err.code === 422 ? err.msg : '服务暂时不可用，请稍后重试',
      entities: [],
      subgraph: { nodes: [], links: [] },
      fallback: false,
      candidates: [],
      clarify: null,
      fallback_passages: [],
      answer_source: 'kg',
    }
    draft.value = text // 服务异常时保留输入内容
  } finally {
    bubble.loading = false
    sending.value = false
    scrollToEnd()
  }
}

async function toggleFavorite(msg) {
  if (!userStore.isLogin) {
    loginGuide.value = true
    return
  }
  const refId = msg.data && msg.data.log_id
  if (!refId) {
    ElMessage.warning('该回答暂不支持收藏')
    return
  }
  try {
    if (msg.favorited) {
      // 规范 1.2：取消收藏属二次确认场景
      try {
        await ElMessageBox.confirm('确定取消收藏该回答吗？', '取消收藏', {
          type: 'warning', confirmButtonText: '取消收藏', cancelButtonText: '再想想',
        })
      } catch {
        return
      }
      await removeFavorite({ fav_type: 'qa', ref_id: String(refId) })
      msg.favorited = false
      ElMessage.success('已取消收藏')
    } else {
      await addFavorite({ fav_type: 'qa', ref_id: String(refId) })
      msg.favorited = true
      ElMessage.success('已收藏')
    }
  } catch (err) {
    ElMessage.error((err && err.msg) || '操作失败，请重试')
  }
}

onMounted(async () => {
  if (!llmPref.loaded) await llmPref.fetchConfig()
  const q = route.query.q
  if (q) send(String(q))
})
</script>

<style scoped>
.qa-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
/* 消息区内部滚动（聊天页惯例）。高度扣掉吸顶导航与输入区，
   并设上下限，避免在超宽屏拉得过长、在矮屏挤得过短 */
.qa-list {
  height: calc(100vh - var(--header-height) - 240px);
  min-height: 360px;
  max-height: 680px;
  overflow-y: auto;
  background: linear-gradient(180deg, #fff 0%, #fcfbfa 100%);
  scroll-behavior: smooth;
}
/* 细滚动条，减少聊天区的视觉噪音 */
.qa-list::-webkit-scrollbar {
  width: 8px;
}
.qa-list::-webkit-scrollbar-thumb {
  background: #dcdfe6;
  border-radius: 999px;
}
.qa-list::-webkit-scrollbar-thumb:hover {
  background: #c0c4cc;
}
.qa-welcome {
  padding: 28px 4px 20px;
  text-align: center;
}
.welcome-text {
  margin: 0 auto 16px;
  max-width: 560px;
  line-height: 1.9;
  color: var(--color-text-secondary);
}
.clarify-text {
  margin: 0 0 8px;
  line-height: 1.8;
}
.llm-actions {
  margin-top: 4px;
}
/* 元素已带 .card（内边距、背景、阴影由通用类提供），这里只补聚焦态强调 */
.qa-input {
  margin-top: 12px;
  transition: box-shadow var(--transition);
}
.qa-input:focus-within {
  box-shadow: 0 0 0 3px var(--color-primary-lighter), var(--shadow-sm);
}
.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
}
.input-tip {
  font-size: 12px;
  color: var(--color-danger);
}
</style>
