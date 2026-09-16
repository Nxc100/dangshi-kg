<template>
  <div class="page home">
    <section class="hero card">
      <h1 class="hero-title">党史学习智能问答</h1>
      <p class="hero-sub">知识来自权威公开出版物与官方网站，答案可溯源、零编造</p>
      <div class="hero-search">
        <el-input
          v-model="question"
          size="large"
          placeholder="请输入你想了解的党史问题，如：遵义会议在哪里召开？"
          maxlength="100"
          show-word-limit
          clearable
          @keyup.enter="ask(question)"
        >
          <template #append>
            <el-button type="primary" :icon="Search" @click="ask(question)">提问</el-button>
          </template>
        </el-input>
      </div>
      <ExampleQuestions @pick="ask" />
    </section>

    <el-row :gutter="16" class="home-body">
      <el-col :xs="24" :md="10">
        <div class="card daily-card" v-loading="loading">
          <h2 class="section-title">今日推荐</h2>
          <template v-if="recommend">
            <div class="rec-head">
              <span class="rec-name">{{ recommend.name }}</span>
              <TypeBadge :type="recommend.type" />
            </div>
            <p class="rec-intro clamp-2">{{ recommend.intro || '暂无简介' }}</p>
            <el-button type="primary" plain size="small" @click="openEntity(recommend.name)">查看详情</el-button>
          </template>
          <EmptyState v-else-if="!loading" icon="Reading" text="今日推荐暂未生成，先去问一个问题吧"
            action-text="去问答" @action="router.push('/qa')" />
        </div>
      </el-col>

      <!-- 无匹配时该栏整体隐藏，不出现空态（FRS FR-G01 唯一例外） -->
      <el-col v-if="todayEvents.length" :xs="24" :md="14">
        <div class="card">
          <h2 class="section-title">历史上的今天</h2>
          <div v-for="e in todayEvents" :key="e.name" class="event-card" @click="openEntity(e.name)">
            <div class="event-time">{{ e.time_text }}</div>
            <div class="event-main">
              <div class="event-name">{{ e.name }}<TypeBadge :type="e.type" class="event-badge" /></div>
              <p class="event-brief clamp-2">{{ e.brief }}</p>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import TypeBadge from '@/components/common/TypeBadge.vue'
import ExampleQuestions from '@/components/qa/ExampleQuestions.vue'
import { getDaily } from '@/api/daily'
import { questionError } from '@/utils/validators'

// 首页（F8 每日学习 + 问答入口）：今日推荐 / 历史上的今天 / 8 条示例问句
// 接口异常时降级显示固定引导语与示例问句，不白屏
const router = useRouter()
const question = ref('')
const recommend = ref(null)
const todayEvents = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await getDaily()
    recommend.value = data.recommend || null
    todayEvents.value = data.today_events || []
  } catch {
    recommend.value = null
    todayEvents.value = []
  } finally {
    loading.value = false
  }
}

function ask(q) {
  const text = String(q || '').trim()
  // 前端拦截空白 / 纯符号 / 超长，就地提示，不跳到问答页再报错（规范 1.3）
  const error = questionError(text)
  if (error) {
    ElMessage.warning(error)
    return
  }
  router.push({ name: 'qa', query: { q: text } })
}

function openEntity(name) {
  router.push({ name: 'entity', params: { name } })
}

onMounted(load)
</script>

<style scoped>
.hero {
  text-align: center;
  padding: 32px 20px 24px;
  margin-bottom: 16px;
  background: linear-gradient(180deg, #fff 0%, var(--color-primary-lighter) 100%);
}
.hero-title {
  margin: 0 0 6px;
  font-size: 26px;
  color: var(--color-primary);
}
.hero-sub {
  margin: 0 0 18px;
  color: var(--color-text-secondary);
}
.hero-search {
  max-width: 680px;
  margin: 0 auto 14px;
}
.section-title {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 600;
}
.daily-card {
  min-height: 180px;
}
.rec-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.rec-name {
  font-size: 18px;
  font-weight: 600;
}
.rec-intro {
  margin: 0 0 12px;
  color: var(--color-text-secondary);
  line-height: 1.8;
}
.event-card {
  display: flex;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
}
.event-card:last-child {
  border-bottom: none;
}
.event-time {
  flex-shrink: 0;
  width: 110px;
  color: var(--color-primary);
  font-size: 13px;
}
.event-name {
  font-weight: 600;
}
.event-badge {
  margin-left: 6px;
}
.event-brief {
  margin: 4px 0 0;
  color: var(--color-text-light);
  font-size: 13px;
}
</style>
