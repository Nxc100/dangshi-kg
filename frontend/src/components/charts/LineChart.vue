<template>
  <div class="chart-card card">
    <div class="chart-title">{{ title }}</div>
    <div v-if="!data.length" class="chart-empty">暂无数据</div>
    <div v-else ref="chartRef" :style="{ height }"></div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { CHART_PRIMARY } from '@/utils/chartTheme'

// 折线图（近 30 天问答量趋势）：无记录日期由后端补零，前端原样渲染
const props = defineProps({
  data: { type: Array, default: () => [] }, // [{date, value}]
  title: { type: String, default: '' },
  height: { type: String, default: '300px' },
})

const chartRef = ref(null)
let chart = null

function option() {
  return {
    grid: { left: 44, right: 24, top: 20, bottom: 40 },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: props.data.map((d) => d.date),
      axisLabel: { fontSize: 11, formatter: (v) => String(v).slice(5) },
    },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        type: 'line',
        smooth: true,
        showSymbol: false,
        itemStyle: { color: CHART_PRIMARY },
        areaStyle: { color: 'rgba(199, 0, 11, 0.08)' },
        data: props.data.map((d) => d.value),
      },
    ],
  }
}

function resize() {
  if (chart) chart.resize()
}

async function render() {
  await nextTick()
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
    window.addEventListener('resize', resize)
  }
  chart.setOption(option(), true)
}

function dispose() {
  if (chart) {
    window.removeEventListener('resize', resize)
    chart.dispose()
    chart = null
  }
}

onMounted(render)
watch(() => props.data, () => (props.data.length ? render() : dispose()), { deep: true })
onBeforeUnmount(dispose)
</script>

<style scoped>
.chart-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--color-text);
}
.chart-empty {
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-light);
}
</style>
