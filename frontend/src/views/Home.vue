<template>
  <div class="home">
    <!-- 一、大屏主视觉轮播：党史地标实景高清图（本地打包，保证断网可演示）
         + Ken Burns 缓动 + 红色渐变遮罩 + 文字入场动画 -->
    <section class="hero-carousel">
      <el-carousel
        ref="carouselRef"
        height="clamp(420px, 52vh, 560px)"
        :interval="7000"
        arrow="hover"
        indicator-position="none"
        motion-blur
        @change="onSlideChange"
      >
        <el-carousel-item v-for="(s, i) in SLIDES" :key="s.img">
          <div class="slide">
            <!-- 图层：Ken Burns 由 .is-active 触发，非当前帧不跑动画，避免后台空转 -->
            <img
              class="slide-img"
              :src="s.img"
              :alt="s.alt"
              :loading="i === 0 ? 'eager' : 'lazy'"
              :fetchpriority="i === 0 ? 'high' : 'low'"
            />
            <div class="slide-mask" aria-hidden="true"></div>
            <div class="slide-inner">
              <span class="slide-tag">{{ s.tag }}</span>
              <h2 class="slide-title">{{ s.title }}</h2>
              <p class="slide-desc">{{ s.desc }}</p>
              <div class="slide-actions">
                <el-button type="primary" size="large" @click="router.push(s.to)">{{ s.action }}</el-button>
                <el-button v-if="s.subTo" size="large" class="slide-ghost" @click="router.push(s.subTo)">
                  {{ s.subAction }}
                </el-button>
              </div>
            </div>
            <!-- CC BY-SA 图片须署名，就近标注在对应画面上 -->
            <span class="slide-credit">{{ s.credit }}</span>
          </div>
        </el-carousel-item>
      </el-carousel>

      <!-- 自定义指示器：横条 + 地标名，比默认圆点更贴"大屏"观感 -->
      <div class="slide-dots">
        <button
          v-for="(s, i) in SLIDES"
          :key="s.img"
          type="button"
          class="slide-dot"
          :class="{ active: i === activeSlide }"
          @click="carouselRef && carouselRef.setActiveItem(i)"
        >
          <i class="dot-bar"></i><span>{{ s.place }}</span>
        </button>
      </div>
    </section>

    <div class="page">
      <!-- 二、问答入口：首页最核心的行动点 -->
      <section class="card ask-card">
        <h2 class="ask-title">你想了解哪一段党史？</h2>
        <p class="ask-sub">答案由知识图谱事实生成，逐条标注来源，未收录的问题回落权威原文段落</p>
        <div class="ask-search">
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

      <!-- 三、规模数据带：让来访者一眼看到知识底座的体量 -->
      <section class="stat-strip">
        <div v-for="s in stats" :key="s.label" class="stat-item">
          <div class="stat-num">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </section>

      <!-- 四、今日推荐 + 历史上的今天（FR-G01） -->
      <el-row :gutter="16" class="home-body">
        <el-col :xs="24" :md="10">
          <div class="card daily-card" v-loading="loading">
            <h2 class="section-title">
              今日推荐
              <span class="section-extra">每日 0 点更新，全站一致</span>
            </h2>
            <template v-if="recommend">
              <div class="rec-head">
                <span class="rec-name">{{ recommend.name }}</span>
                <TypeBadge :type="recommend.type" />
              </div>
              <p class="rec-intro">{{ recommend.intro || '暂无简介' }}</p>
              <div class="rec-actions">
                <el-button type="primary" size="small" @click="openEntity(recommend.name)">查看词条</el-button>
                <el-button size="small" @click="router.push({ name: 'graph', query: { kw: recommend.name } })">
                  在图谱中查看
                </el-button>
              </div>
              <!-- 由今日推荐延伸出可直接点击的问句，把"看一眼"变成"问一句" -->
              <div class="rec-ask">
                <p class="rec-ask-title">就它继续提问</p>
                <button v-for="q in recommendQuestions" :key="q" class="rec-ask-item" type="button" @click="ask(q)">
                  {{ q }}
                </button>
              </div>
            </template>
            <EmptyState v-else-if="!loading" icon="Reading" text="今日推荐暂未生成，先去问一个问题吧"
              action-text="去问答" @action="router.push('/qa')" />
          </div>
        </el-col>

        <!-- 无匹配时该栏整体隐藏，不出现空态（FRS FR-G01 唯一例外） -->
        <el-col v-if="todayEvents.length" :xs="24" :md="14">
          <div class="card today-card">
            <h2 class="section-title">
              历史上的今天
              <span class="section-extra">{{ todayLabel }}</span>
            </h2>
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

      <!-- 五、功能入口卡片 -->
      <section class="feature-section">
        <h2 class="block-title">四大学习入口</h2>
        <el-row :gutter="16">
          <el-col v-for="f in FEATURES" :key="f.to" :xs="12" :md="6">
            <div class="feature-card" @click="router.push(f.to)">
              <div class="feature-icon" :style="{ background: f.color }">
                <el-icon :size="22"><component :is="f.icon" /></el-icon>
              </div>
              <h3>{{ f.title }}</h3>
              <p>{{ f.desc }}</p>
            </div>
          </el-col>
        </el-row>
      </section>

      <!-- 六、七个历史时期快捷入口：通史浏览的起点 -->
      <section class="period-section">
        <h2 class="block-title">
          按历史时期浏览
          <el-button link type="primary" @click="router.push('/timeline')">查看完整时间轴 →</el-button>
        </h2>
        <div class="period-grid">
          <div
            v-for="(p, i) in PERIODS"
            :key="p.name"
            class="period-card"
            @click="router.push({ name: 'timeline', query: { period: p.name } })"
          >
            <span class="period-order">{{ String(i + 1).padStart(2, '0') }}</span>
            <span class="period-name">{{ p.name }}</span>
            <span class="period-years">{{ p.start_year }} – {{ p.end_year }}</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Search, Share, Tickets, Clock } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import TypeBadge from '@/components/common/TypeBadge.vue'
import ExampleQuestions from '@/components/qa/ExampleQuestions.vue'
import { getDaily } from '@/api/daily'
import { questionError } from '@/utils/validators'
import { LABELS, PERIODS, RELATIONS } from '@/utils/ontology'
import request from '@/utils/request'
import nanhuImg from '@/assets/carousel/nanhu.jpg'
import yidaImg from '@/assets/carousel/yidahuizhi.jpg'
import jinggangImg from '@/assets/carousel/jinggangshan.jpg'
import zunyiImg from '@/assets/carousel/zunyi.jpg'

// 首页（F8 每日学习 + 问答入口）：轮播主视觉 / 问答入口 / 规模数据 /
// 今日推荐 / 历史上的今天 / 功能入口 / 时期导航
// 接口异常时降级显示固定引导语与示例问句，不白屏（FR-G01）
const router = useRouter()

// 主视觉四帧：一帧讲平台主张，三帧沿党史脉络导流到具体内容。
// 图片为 Wikimedia Commons 自由许可的党史地标实景，已下载进 assets 本地打包——
// 开发规范第 0 节要求「零外部依赖、断网单机可完整演示」，不得热链外部图床。
const SLIDES = [
  {
    img: nanhuImg,
    place: '嘉兴南湖',
    alt: '嘉兴南湖红船',
    credit: '图：嘉兴南湖红船 / Wikimedia Commons · CC BY-SA 4.0',
    tag: '溯源',
    title: '让每一个答案\n都能回到它的出处',
    desc: '基于 Neo4j 知识图谱的党史问答：答案由图谱事实经模板生成，零编造；图谱未收录的问题回落权威原文段落，并标注章节出处。',
    action: '立即提问',
    to: '/qa',
    subAction: '看知识图谱',
    subTo: '/graph',
  },
  {
    img: yidaImg,
    place: '中共一大会址',
    alt: '上海中共一大会址',
    credit: '图：中共一大会址 / Wikimedia Commons · CC BY-SA 4.0',
    tag: '1921',
    title: '开天辟地\n中国共产党诞生',
    desc: '1921 年 7 月，中国共产党第一次全国代表大会在上海召开，最后一天会议转移到浙江嘉兴南湖的游船上举行。',
    action: '了解中共一大',
    to: '/entity/中国共产党第一次全国代表大会',
    subAction: '建党初期与大革命时期',
    subTo: '/timeline?period=建党初期与大革命时期',
  },
  {
    img: jinggangImg,
    place: '井冈山',
    alt: '井冈山黄洋界',
    credit: '图：井冈山黄洋界 / Wikimedia Commons · CC BY-SA 4.0',
    tag: '1927',
    title: '星火燎原\n工农武装割据',
    desc: '南昌起义、秋收起义之后，党在井冈山创建第一个农村革命根据地，开辟出农村包围城市、武装夺取政权的道路。',
    action: '浏览土地革命战争时期',
    to: '/timeline?period=土地革命战争时期',
    subAction: '了解秋收起义',
    subTo: '/entity/秋收起义',
  },
  {
    img: zunyiImg,
    place: '遵义会议会址',
    alt: '遵义会议会址',
    credit: '图：遵义会议会址 / Wikimedia Commons · CC BY-SA 4.0',
    tag: '1935',
    title: '生死攸关\n伟大的历史转折',
    desc: '1935 年 1 月，遵义会议在长征途中召开，确立了毛泽东在党中央和红军的领导地位，是党的历史上一个生死攸关的转折点。',
    action: '了解遵义会议',
    to: '/entity/遵义会议',
    subAction: '在图谱中查看',
    subTo: '/graph?kw=遵义会议',
  },
]

const FEATURES = [
  { title: '智能问答', desc: '自然语言提问，答案可溯源', to: '/qa', icon: ChatDotRound, color: '#C7000B' },
  { title: '知识图谱', desc: '实体关系网络可视化探索', to: '/graph', icon: Share, color: '#8E44AD' },
  { title: '大事记时间轴', desc: '七个时期通史浏览', to: '/timeline', icon: Clock, color: '#2E86C1' },
  { title: '知识测验', desc: '自动出题，即时判分解析', to: '/quiz', icon: Tickets, color: '#C9A227' },
]

const carouselRef = ref(null)
const activeSlide = ref(0)
function onSlideChange(index) {
  activeSlide.value = index
}

const question = ref('')
const recommend = ref(null)
const todayEvents = ref([])
const loading = ref(false)
const scale = ref({ entities: null, paragraphs: null })

const todayLabel = computed(() => {
  const d = new Date()
  return `${d.getMonth() + 1} 月 ${d.getDate()} 日`
})

// 按实体类型给出该类型「支持的问法」，与问答管道的槽位约束一致，
// 避免生成「谁参加了毛泽东」这类必然触发澄清的问句
const QUESTION_TEMPLATES = {
  Meeting: (n) => [`${n}是什么时候召开的？`, `${n}在哪里召开？`, `哪些人参加了${n}？`],
  Event: (n) => [`${n}是什么时候发生的？`, `${n}是谁领导的？`, `${n}有什么历史意义？`],
  Person: (n) => [`${n}写了哪些著作？`, `${n}领导过哪些事件？`, `${n}担任过什么职务？`],
  Document: (n) => [`《${n}》的作者是谁？`, `${n}的主要内容是什么？`],
  Organization: (n) => [`${n}是什么时候成立的？`, `${n}由什么改编而来？`],
  Location: (n) => [`介绍一下${n}`],
  Period: (n) => [`${n}有哪些重大事件？`],
}

const recommendQuestions = computed(() => {
  const r = recommend.value
  if (!r) return []
  const build = QUESTION_TEMPLATES[r.type]
  return build ? build(r.name).slice(0, 3) : [`介绍一下${r.name}`]
})

// 规模数据：实体数与语料段数取自既有的 /api/health（游客可用，开发规范 8.1 不另起路径），
// 取不到时显示占位符而非隐藏，保持版面稳定
const stats = computed(() => [
  { label: '图谱实体', value: scale.value.entities ?? '—' },
  { label: '权威语料段', value: scale.value.paragraphs ?? '—' },
  { label: '实体类型', value: LABELS.length },
  { label: '关系类型', value: RELATIONS.length },
  { label: '历史时期', value: PERIODS.length },
])

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

async function loadScale() {
  try {
    const data = await request.get('/health')
    scale.value = {
      entities: data.dictionary_entities || null,
      paragraphs: data.corpus_paragraphs || null,
    }
  } catch {
    /* 规模数据是锦上添花，拿不到就保持占位符 */
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

// 串行：/daily 成功才去取规模数据。后端不可用时只会弹一次全局提示，
// 而不是让 request 拦截器连着弹两条同样的「服务暂时不可用」
onMounted(async () => {
  await load()
  if (recommend.value || todayEvents.value.length) loadScale()
})
</script>

<style scoped>
/* ---------- 大屏主视觉轮播 ---------- */
.hero-carousel {
  position: relative;
  background: #2A0708;
}
.slide {
  position: relative;
  height: 100%;
  overflow: hidden;
  display: flex;
  align-items: center;
}
.slide-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transform: scale(1.06);
  will-change: transform;
}
/* Ken Burns：仅当前帧缓慢推近平移，切走即复位，避免非可见帧持续合成 */
:deep(.el-carousel__item.is-active) .slide-img {
  animation: kenburns 9s ease-out both;
}
@keyframes kenburns {
  from { transform: scale(1.06) translate3d(0, 0, 0); }
  to { transform: scale(1.16) translate3d(-1.2%, -1.6%, 0); }
}
/* 红色渐变遮罩：既压暗照片保证文字可读，又把实景纳入全站庄重红基调 */
.slide-mask {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(90, 8, 12, 0.88) 0%, rgba(110, 10, 14, 0.62) 34%, rgba(60, 6, 9, 0.20) 64%, rgba(40, 4, 6, 0.42) 100%),
    linear-gradient(180deg, rgba(30, 3, 5, 0.42) 0%, transparent 34%, rgba(30, 3, 5, 0.58) 100%);
}
.slide-inner {
  position: relative;
  max-width: var(--page-max);
  width: 100%;
  margin: 0 auto;
  padding: 0 20px;
  color: #fff;
}
/* 文字入场：切到当前帧才播放，逐级延迟形成层次 */
:deep(.el-carousel__item.is-active) .slide-tag { animation: rise 0.6s 0.05s both; }
:deep(.el-carousel__item.is-active) .slide-title { animation: rise 0.7s 0.15s both; }
:deep(.el-carousel__item.is-active) .slide-desc { animation: rise 0.7s 0.28s both; }
:deep(.el-carousel__item.is-active) .slide-actions { animation: rise 0.7s 0.4s both; }
@keyframes rise {
  from { opacity: 0; transform: translateY(18px); }
  to { opacity: 1; transform: translateY(0); }
}
.slide-tag {
  display: inline-block;
  padding: 4px 14px;
  border: 1px solid var(--color-gold);
  border-radius: 999px;
  color: var(--color-gold);
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 2px;
  margin-bottom: 18px;
  backdrop-filter: blur(2px);
}
.slide-title {
  margin: 0 0 14px;
  font-size: 42px;
  line-height: 1.34;
  letter-spacing: 2px;
  white-space: pre-line; /* 标题用 
 手工断行，保证断句符合中文语感 */
  text-shadow: 0 2px 16px rgba(0, 0, 0, 0.45);
}
.slide-desc {
  margin: 0 0 26px;
  max-width: 560px;
  font-size: 15px;
  line-height: 2;
  color: rgba(255, 255, 255, 0.9);
  text-shadow: 0 1px 10px rgba(0, 0, 0, 0.45);
}
.slide-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.slide-ghost {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.7);
  color: #fff;
  backdrop-filter: blur(4px);
}
.slide-ghost:hover {
  background: rgba(255, 255, 255, 0.22);
  border-color: #fff;
  color: #fff;
}
.slide-credit {
  position: absolute;
  right: 16px;
  bottom: 12px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.55);
  letter-spacing: 0.3px;
}

/* 自定义指示器：横条 + 地标名 */
.slide-dots {
  position: absolute;
  left: 50%;
  bottom: 22px;
  transform: translateX(-50%);
  z-index: 3;
  display: flex;
  gap: 18px;
  max-width: var(--page-max);
  width: 100%;
  padding: 0 20px;
}
.slide-dot {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 0;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  font-size: 12px;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: color var(--transition);
}
.dot-bar {
  display: block;
  width: 62px;
  height: 3px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.34);
  transition: background var(--transition);
}
.slide-dot.active {
  color: #fff;
}
.slide-dot.active .dot-bar {
  background: var(--color-gold);
}

/* 尊重系统的减少动效设置：关掉 Ken Burns 与入场位移 */
@media (prefers-reduced-motion: reduce) {
  :deep(.el-carousel__item.is-active) .slide-img,
  :deep(.el-carousel__item.is-active) .slide-tag,
  :deep(.el-carousel__item.is-active) .slide-title,
  :deep(.el-carousel__item.is-active) .slide-desc,
  :deep(.el-carousel__item.is-active) .slide-actions {
    animation: none;
  }
}

/* ---------- 问答入口 ---------- */
.ask-card {
  margin-top: 20px;
  text-align: center;
  padding: 28px 20px 20px;
}
.ask-title {
  margin: 0 0 6px;
  font-size: 22px;
  color: var(--color-text);
}
.ask-sub {
  margin: 0 0 18px;
  color: var(--color-text-secondary);
}
.ask-search {
  max-width: 680px;
  margin: 0 auto 14px;
}

/* ---------- 规模数据带 ---------- */
.stat-strip {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1px;
  margin-top: 16px;
  background: var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
}
.stat-item {
  background: var(--color-card);
  padding: 18px 8px;
  text-align: center;
}
.stat-num {
  font-size: 26px;
  font-weight: 700;
  color: var(--color-primary);
  line-height: 1.3;
}
.stat-label {
  margin-top: 2px;
  font-size: 13px;
  color: var(--color-text-light);
}

/* ---------- 今日推荐 / 历史上的今天 ---------- */
.home-body {
  margin-top: 16px;
}
.section-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 600;
}
.section-extra {
  font-size: 13px;
  font-weight: 400;
  color: var(--color-text-light);
}
.daily-card,
.today-card {
  height: 100%;
}
.rec-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.rec-name {
  font-size: 18px;
  font-weight: 600;
  line-height: 1.5;
}
.rec-intro {
  margin: 0 0 14px;
  color: var(--color-text-secondary);
  line-height: 1.9;
}
.rec-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.rec-ask {
  padding-top: 14px;
  border-top: 1px dashed var(--color-border);
}
.rec-ask-title {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--color-text-light);
}
.rec-ask-item {
  display: block;
  width: 100%;
  margin-bottom: 8px;
  padding: 9px 12px;
  text-align: left;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 1.6;
  cursor: pointer;
  transition: all var(--transition);
}
.rec-ask-item:hover {
  background: var(--color-primary-lighter);
  border-color: var(--color-primary-light);
  color: var(--color-primary);
}
.rec-ask-item:last-child {
  margin-bottom: 0;
}
.event-card {
  display: flex;
  gap: 12px;
  padding: 10px 8px;
  border-bottom: 1px solid var(--color-border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: background var(--transition);
}
.event-card:hover {
  background: var(--color-primary-lighter);
}
.event-card:last-child {
  border-bottom: none;
}
.event-time {
  flex-shrink: 0;
  width: 110px;
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 600;
}
.event-main {
  min-width: 0;
}
.event-name {
  font-weight: 600;
  line-height: 1.6;
}
.event-badge {
  margin-left: 6px;
}
.event-brief {
  margin: 4px 0 0;
  color: var(--color-text-light);
  font-size: 13px;
}

/* ---------- 功能入口 / 时期导航 ---------- */
.block-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 28px 0 14px;
  font-size: 18px;
  font-weight: 600;
}
.feature-card {
  height: 100%;
  background: var(--color-card);
  border-radius: var(--radius);
  padding: 20px 16px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: transform var(--transition), box-shadow var(--transition);
}
.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}
.feature-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-bottom: 12px;
}
.feature-card h3 {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
}
.feature-card p {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-text-light);
}
.period-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.period-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  background: var(--color-card);
  border-left: 3px solid var(--color-primary);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: transform var(--transition), box-shadow var(--transition);
}
.period-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}
.period-order {
  font-size: 12px;
  color: var(--color-gold);
  font-weight: 700;
  letter-spacing: 1px;
}
.period-name {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.6;
}
.period-years {
  font-size: 12px;
  color: var(--color-text-light);
}

@media (max-width: 992px) {
  .slide-title {
    font-size: 24px;
  }
  .stat-strip {
    grid-template-columns: repeat(3, 1fr);
  }
  .period-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
