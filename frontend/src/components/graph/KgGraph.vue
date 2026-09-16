<template>
  <div class="kg-graph" :style="{ height }">
    <div v-if="!hasData" class="graph-empty">
      <el-icon :size="32"><Share /></el-icon>
      <p>{{ emptyText }}</p>
    </div>
    <div v-else ref="chartRef" class="graph-canvas"></div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { labelColor, labelZh } from '@/utils/ontology'
import { GRAPH_EDGE_COLOR, GRAPH_EDGE_LABEL_COLOR } from '@/utils/chartTheme'

// ECharts 力导向图封装（图谱页 2 跳 / 百科局部 1 跳 / 问答溯源三处复用，唯一实现）
// 节点七色与关系中文名一律取自 ontology.js；边 label 使用后端下发的 link.label（中文关系名）
const props = defineProps({
  nodes: { type: Array, default: () => [] },
  links: { type: Array, default: () => [] },
  height: { type: String, default: '480px' },
  showLegend: { type: Boolean, default: true },
  emptyText: { type: String, default: '暂无关联知识' },
  centerId: { type: String, default: '' },
})
const emit = defineEmits(['node-click', 'node-dblclick'])

const chartRef = ref(null)
let chart = null

const hasData = computed(() => props.nodes && props.nodes.length > 0)

// 图例按画布中实际出现的实体类型生成
const categories = computed(() => {
  const types = []
  props.nodes.forEach((n) => {
    if (n.type && !types.includes(n.type)) types.push(n.type)
  })
  return types
})

function buildOption() {
  const cats = categories.value
  const degree = {}
  props.links.forEach((l) => {
    degree[l.source] = (degree[l.source] || 0) + 1
    degree[l.target] = (degree[l.target] || 0) + 1
  })
  const option = {
    tooltip: {
      formatter: (params) =>
        params.dataType === 'edge'
          ? params.data.label || params.data.relation
          : `${params.data.name}<br/>${labelZh(params.data.type)}`,
    },
    animationDuration: 600,
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        top: 10,
        bottom: props.showLegend ? 40 : 10,
        categories: cats.map((t) => ({ name: labelZh(t), itemStyle: { color: labelColor(t) } })),
        force: { repulsion: 320, edgeLength: [80, 160], gravity: 0.06 },
        label: { show: true, position: 'right', fontSize: 12 },
        edgeLabel: { show: true, formatter: (p) => p.data.label || '', fontSize: 10, color: GRAPH_EDGE_LABEL_COLOR },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 7,
        lineStyle: { color: GRAPH_EDGE_COLOR, width: 1.2, curveness: 0.08, opacity: 0.9 },
        emphasis: { focus: 'adjacency', lineStyle: { width: 2.4 } },
        data: props.nodes.map((n) => ({
          id: n.id,
          name: n.name,
          type: n.type,
          category: Math.max(cats.indexOf(n.type), 0),
          symbolSize: n.id === props.centerId ? 52 : Math.min(24 + (degree[n.id] || 0) * 3, 44),
          itemStyle: { color: labelColor(n.type) },
        })),
        links: props.links.map((l) => ({
          source: l.source,
          target: l.target,
          relation: l.relation,
          label: l.label,
        })),
      },
    ],
  }
  if (props.showLegend) {
    option.legend = [{ data: cats.map((t) => labelZh(t)), bottom: 4, icon: 'circle' }]
  }
  return option
}

function resize() {
  if (chart) chart.resize()
}

async function init() {
  await nextTick()
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
    chart.on('click', (params) => {
      if (params.dataType === 'node') emit('node-click', params.data)
    })
    chart.on('dblclick', (params) => {
      if (params.dataType === 'node') emit('node-dblclick', params.data)
    })
    window.addEventListener('resize', resize)
  }
  chart.setOption(buildOption(), true)
}

function dispose() {
  if (chart) {
    window.removeEventListener('resize', resize)
    chart.dispose()
    chart = null
  }
}

// 缩放 / 重置视图由 GraphToolbar 通过模板 ref 调用
function zoomBy(delta) {
  if (!chart) return
  const series = chart.getOption().series[0]
  const current = series.zoom || 1
  chart.setOption({ series: [{ zoom: Math.min(Math.max(current * delta, 0.3), 4) }] })
}

function resetView() {
  if (!chart) return
  chart.setOption(buildOption(), true)
}

defineExpose({ zoomBy, resetView, resize })

onMounted(() => {
  if (hasData.value) init()
})

watch(
  () => [props.nodes, props.links],
  () => {
    if (hasData.value) init()
    else dispose()
  },
  { deep: true },
)

onBeforeUnmount(dispose)
</script>

<style scoped>
.kg-graph {
  position: relative;
  width: 100%;
  background: var(--color-card);
  border-radius: var(--radius);
}
.graph-canvas {
  width: 100%;
  height: 100%;
}
.graph-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--color-text-light);
}
.graph-empty p {
  margin: 0;
}
</style>
