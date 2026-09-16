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

// 柱状图（高频问句 Top10 / 高频实体 Top10）：只渲染后端聚合值，前端不做任何计算
const props = defineProps({
  data: { type: Array, default: () => [] }, // [{name, value}]
  title: { type: String, default: '' },
  height: { type: String, default: '300px' },
  horizontal: { type: Boolean, default: true },
})

const chartRef = ref(null)
let chart = null

function option() {
  const names = props.data.map((d) => d.name)
  const values = props.data.map((d) => d.value)
  const cat = { type: 'category', data: props.horizontal ? [...names].reverse() : names, axisLabel: { fontSize: 11 } }
  const val = { type: 'value', minInterval: 1 }
  return {
    grid: { left: props.horizontal ? 130 : 40, right: 24, top: 16, bottom: 30 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: props.horizontal ? val : cat,
    yAxis: props.horizontal ? cat : val,
    series: [
      {
        type: 'bar',
        barMaxWidth: 18,
        itemStyle: { color: CHART_PRIMARY, borderRadius: 3 },
        data: props.horizontal ? [...values].reverse() : values,
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
