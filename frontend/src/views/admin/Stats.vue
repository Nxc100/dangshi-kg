<template>
  <div class="admin-stats" v-loading="loading">
    <div class="stats-head">
      <h2 class="sub-title">热点统计看板</h2>
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </div>

    <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="load" />

    <template v-else>
      <el-row :gutter="16">
        <el-col :xs="24" :md="12"><BarChart title="高频问句 Top10" :data="data.top_questions" /></el-col>
        <el-col :xs="24" :md="12"><BarChart title="高频实体 Top10" :data="data.top_entities" /></el-col>
      </el-row>

      <el-row :gutter="16" class="row-gap">
        <el-col :xs="24" :md="12"><PieChart title="意图类型分布" :data="data.intent_dist" /></el-col>
        <el-col :xs="24" :md="12"><LineChart title="近 30 天问答量趋势" :data="data.trend_30d" /></el-col>
      </el-row>

      <el-row :gutter="16" class="row-gap">
        <el-col :xs="24" :md="8">
          <div class="card rate-card">
            <div class="rate-title">兜底率</div>
            <div class="rate-value">{{ fallbackPercent }}</div>
            <div class="rate-sub text-light">问答总量 {{ data.total || 0 }} 条</div>
          </div>
        </el-col>
        <el-col :xs="24" :md="16">
          <PieChart title="图谱命中 / 兜底占比" :data="fallbackPie" doughnut height="240px"
            :colors="FALLBACK_PIE_COLORS" />
        </el-col>
      </el-row>

      <div class="card row-gap">
        <h3 class="llm-title">AI 增强模块（近 30 天）</h3>
        <el-row :gutter="16">
          <el-col v-for="m in llmMetrics" :key="m.label" :xs="8">
            <div class="llm-metric">
              <div class="llm-value">{{ m.value }}</div>
              <div class="llm-label">{{ m.label }}</div>
            </div>
          </el-col>
        </el-row>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import BarChart from '@/components/charts/BarChart.vue'
import PieChart from '@/components/charts/PieChart.vue'
import LineChart from '@/components/charts/LineChart.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import { getStatsOverview } from '@/api/stats'
import { FALLBACK_PIE_COLORS } from '@/utils/chartTheme'

// 热点统计看板（FR-A07 / FR-L04）：五图 + LLM 三指标卡
// 所有数值均为后端 stats_service 聚合结果，前端只做展示与百分号格式化，不自行计算统计量
const data = reactive({
  top_questions: [],
  top_entities: [],
  intent_dist: [],
  trend_30d: [],
  fallback_rate: 0,
  fallback_count: 0,
  total: 0,
  llm: { calls: 0, success_rate: 0, avg_latency_ms: 0 },
})
const loading = ref(false)
const error = ref('')

const fallbackPercent = computed(() => `${(Number(data.fallback_rate || 0) * 100).toFixed(1)}%`)

// 环形图两项直接取后端下发的兜底数与总数（stats_service 聚合），前端不做推算
const fallbackPie = computed(() => {
  const total = Number(data.total || 0)
  const fallback = Number(data.fallback_count || 0)
  if (!total) return []
  return [
    { name: '图谱命中', value: total - fallback },
    { name: '兜底', value: fallback },
  ]
})

const llmMetrics = computed(() => [
  { label: '调用次数', value: data.llm ? data.llm.calls || 0 : 0 },
  { label: '生成成功率', value: `${((data.llm ? data.llm.success_rate : 0) * 100).toFixed(1)}%` },
  { label: '平均时延', value: `${data.llm ? Math.round(data.llm.avg_latency_ms || 0) : 0} ms` },
])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await getStatsOverview()
    Object.assign(data, result)
    if (!result.llm) data.llm = { calls: 0, success_rate: 0, avg_latency_ms: 0 }
  } catch (err) {
    error.value = (err && err.msg) || '统计数据加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.stats-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.sub-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
.row-gap {
  margin-top: 16px;
}
.rate-card {
  text-align: center;
  padding: 24px 16px;
}
.rate-title {
  font-size: 14px;
  color: var(--color-text-secondary);
}
.rate-value {
  margin: 8px 0 4px;
  font-size: 34px;
  font-weight: 700;
  color: var(--color-primary);
}
.rate-sub {
  font-size: 12px;
}
.llm-title {
  margin: 0 0 12px;
  font-size: 15px;
}
.llm-metric {
  text-align: center;
}
.llm-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-gold);
}
.llm-label {
  font-size: 13px;
  color: var(--color-text-light);
}
</style>
