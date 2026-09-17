<template>
  <div class="page timeline-page">
    <h1 class="page-title">党史大事记时间轴</h1>

    <div class="card">
      <div class="toolbar">
        <el-input v-model="yearInput" placeholder="输入年份定位，如 1935" class="year-input" clearable
          @keyup.enter="locateYear">
          <template #append><el-button :icon="Position" @click="locateYear">定位</el-button></template>
        </el-input>
        <span class="text-light">共 {{ periods.length }} 个历史时期</span>
      </div>

      <el-tabs v-model="activePeriod" @tab-change="onTabChange">
        <el-tab-pane v-for="p in periods" :key="p.name" :label="p.name" :name="p.name" />
      </el-tabs>

      <div v-loading="loading" class="timeline-body">
        <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="() => loadPeriod(activePeriod)" />
        <EmptyState v-else-if="!events.length && !loading" icon="Clock" text="该时期暂无事件数据" />
        <el-timeline v-else>
          <el-timeline-item
            v-for="(e, i) in events"
            :key="e.name"
            :timestamp="e.time_text"
            placement="top"
            :color="labelColor(e.type)"
            :hollow="false"
          >
            <div :ref="(el) => setItemRef(el, i)" class="event-item" @click="openEntity(e.name)">
              <div class="event-name">{{ e.name }}<TypeBadge :type="e.type" class="event-badge" /></div>
              <p v-if="e.brief" class="event-brief">{{ e.brief }}</p>
            </div>
          </el-timeline-item>
        </el-timeline>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Position } from '@element-plus/icons-vue'
import TypeBadge from '@/components/common/TypeBadge.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import { getTimeline } from '@/api/timeline'
import { labelColor } from '@/utils/ontology'
import { YEAR_ERROR, isValidYear } from '@/utils/validators'

// 时间轴页（F3）：七个时期页签（按 order）+ time_sort 升序事件卡 + 年份定位
const route = useRoute()
const router = useRouter()
const periods = ref([])
const activePeriod = ref('')
const events = ref([])
const loading = ref(false)
const error = ref('')
const yearInput = ref('')
const itemRefs = ref([])

function setItemRef(el, i) {
  if (el) itemRefs.value[i] = el
}

async function loadPeriod(period) {
  loading.value = true
  error.value = ''
  itemRefs.value = []
  try {
    const data = await getTimeline(period)
    if (data.periods && data.periods.length) {
      periods.value = [...data.periods].sort((a, b) => a.order - b.order)
    }
    activePeriod.value = data.period || period || (periods.value[0] && periods.value[0].name) || ''
    events.value = data.events || []
  } catch {
    events.value = []
    error.value = '时间轴加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function onTabChange(name) {
  loadPeriod(name)
}

// 年份定位：按 start_year ≤ year ≤ end_year 切换时期页签，滚动到该年首条；该年无条目则定位到其后最近一条
async function locateYear() {
  const value = yearInput.value.trim()
  if (!isValidYear(value)) {
    ElMessage.warning(YEAR_ERROR)
    return
  }
  const year = Number(value)
  const target = periods.value.find(
    (p) => year >= p.start_year && (!p.end_year || year <= p.end_year),
  )
  if (!target) {
    ElMessage.warning('未找到该年份所属的历史时期')
    return
  }
  if (target.name !== activePeriod.value) {
    await loadPeriod(target.name)
  }
  await nextTick()
  const index = events.value.findIndex((e) => Number(String(e.time_sort || '').slice(0, 4)) >= year)
  if (index < 0) {
    ElMessage.info('该年份之后暂无事件条目')
    return
  }
  const el = itemRefs.value[index]
  if (el && el.scrollIntoView) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function openEntity(name) {
  router.push({ name: 'entity', params: { name } })
}

// 支持 /timeline?period=xxx 深链（首页时期卡片、站内互链直达指定时期）；
// 参数非法时回落为默认时期，不报错
onMounted(() => {
  const q = route.query.period
  loadPeriod(typeof q === 'string' && q.trim() ? q.trim() : undefined)
})
</script>

<style scoped>
.year-input {
  width: 260px;
}
.timeline-body {
  min-height: 240px;
  padding-top: 8px;
}
.event-item {
  cursor: pointer;
  padding: 6px 10px;
  border-radius: var(--radius);
}
.event-item:hover {
  background: var(--color-bg-gray);
}
.event-name {
  font-weight: 600;
}
.event-badge {
  margin-left: 6px;
}
.event-brief {
  margin: 4px 0 0;
  color: var(--color-text-secondary);
  line-height: 1.7;
}
</style>
