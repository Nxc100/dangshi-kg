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
import { CHART_PALETTE } from '@/utils/chartTheme'

// 饼图 / 环形图（意图类型分布、兜底率）：只渲染后端聚合值
const props = defineProps({
  data: { type: Array, default: () => [] }, // [{name, value}]
  title: { type: String, default: '' },
  height: { type: String, default: '300px' },
  doughnut: { type: Boolean, default: false },
  colors: { type: Array, default: () => CHART_PALETTE },
})

const chartRef = ref(null)
let chart = null

function option() {
  return {
    tooltip: { trigger: 'item', formatter: '{b}：{c}（{d}%）' },
    legend: { type: 'scroll', bottom: 0, icon: 'circle', textStyle: { fontSize: 11 } },
    color: props.colors,
    series: [
      {
        type: 'pie',
        radius: props.doughnut ? ['48%', '68%'] : '62%',
        center: ['50%', '45%'],
        label: { formatter: '{b} {d}%', fontSize: 11 },
        data: props.data,
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
