<template>
  <div class="kg-graph" :style="{ height }">
    <div v-if="!hasData" class="graph-empty">
      <el-icon :size="32"><Share /></el-icon>
      <p>{{ emptyText }}</p>
    </div>
    <template v-else>
      <div ref="containerRef" class="graph-canvas"></div>

      <!-- 图例：按画布中实际出现的实体类型生成，色值取自 ontology.js。
           只做展示不做筛选——类型筛选由图谱页 GraphToolbar 统一负责（规范 1.1），避免两套过滤机制 -->
      <div v-if="showLegend" class="graph-legend">
        <span v-for="t in categories" :key="t" class="legend-item">
          <i class="legend-dot" :style="{ background: labelColor(t) }"></i>{{ labelZh(t) }}
        </span>
      </div>

      <!-- 孤立节点：画布仅显示自身，另给出提示（FR-G03 异常与提示）。
           问答溯源子图的属性类意图本就只有一个节点，属正常结果，故由调用方按需开启。 -->
      <p v-if="showIsolatedHint && isolated" class="graph-isolated-hint">{{ emptyText }}</p>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Graph } from '@antv/g6'
import { labelColor, labelZh } from '@/utils/ontology'

// 知识图谱可视化封装（图谱页 2 跳 / 百科局部 1 跳 / 问答溯源三处复用，唯一实现）
// 渲染引擎：AntV G6 v5（专业图可视化引擎，d3-force 布局 + 邻接聚焦 + 标签分级显示）
// 节点七色与关系中文名一律取自 ontology.js，禁止在此另写一份映射
const props = defineProps({
  nodes: { type: Array, default: () => [] },
  links: { type: Array, default: () => [] },
  height: { type: String, default: '480px' },
  showLegend: { type: Boolean, default: true },
  emptyText: { type: String, default: '暂无关联知识' },
  centerId: { type: String, default: '' },
  // 仅图谱页开启：孤立节点（仅自身、无边）时在画布上给出提示
  showIsolatedHint: { type: Boolean, default: false },
})
const emit = defineEmits(['node-click', 'node-dblclick'])

// 标签超过该长度即截断：事件实体名是编年条目的整句原文，全量上屏会糊成一片
const LABEL_MAX = 12
// 画布节点数超过该值时，只给「中心节点 + 高度数节点」显示常驻标签，其余 hover 才显示
const LABEL_DENSE_THRESHOLD = 25

const containerRef = ref(null)
let graph = null
let resizeObserver = null

const hasData = computed(() => props.nodes && props.nodes.length > 0)
const isolated = computed(() => props.nodes.length === 1 && props.links.length === 0)
const categories = computed(() => {
  const types = []
  props.nodes.forEach((n) => {
    if (n.type && !types.includes(n.type)) types.push(n.type)
  })
  return types
})

function truncate(text) {
  const s = String(text || '')
  return s.length > LABEL_MAX ? `${s.slice(0, LABEL_MAX)}…` : s
}

function degreeMap() {
  const deg = {}
  props.links.forEach((l) => {
    deg[l.source] = (deg[l.source] || 0) + 1
    deg[l.target] = (deg[l.target] || 0) + 1
  })
  return deg
}

// G6 不接受 Vue 响应式对象，这里产出纯对象快照
function buildData() {
  const deg = degreeMap()
  const visible = props.nodes
  const ids = new Set(visible.map((n) => n.id))
  const dense = visible.length > LABEL_DENSE_THRESHOLD
  // 稠密时的常驻标签阈值：取度数前 20% 的节点，至少 2 度
  const degrees = visible.map((n) => deg[n.id] || 0).sort((a, b) => b - a)
  const cut = Math.max(degrees[Math.floor(degrees.length * 0.2)] || 0, 2)

  return {
    nodes: visible.map((n) => {
      const d = deg[n.id] || 0
      const isCenter = n.id === props.centerId
      return {
        id: n.id,
        data: {
          name: n.name,
          type: n.type,
          typeZh: labelZh(n.type),
          degree: d,
          isCenter,
          // 常驻标签：中心节点、稀疏图全部、稠密图里的高度数节点
          keepLabel: isCenter || !dense || d >= cut,
        },
      }
    }),
    edges: props.links
      .filter((l) => ids.has(l.source) && ids.has(l.target))
      .map((l, i) => ({
        id: `${l.source}->${l.target}-${l.relation}-${i}`,
        source: l.source,
        target: l.target,
        data: { relation: l.relation, label: l.label || l.relation },
      })),
  }
}

// 力导向参数按规模自适应：节点越多斥力越大、边越长，避免小图散开、大图挤成球。
// alphaDecay / alphaMin 取较大值使布局快速收敛并停止——持续 tick 会让画布一直重绘，
// 既耗 CPU 也让页面永不静止（答辩演示时表现为图谱一直在抖）。
function layoutOf(nodeCount) {
  const scale = Math.min(Math.max(nodeCount, 5), 100)
  return {
    type: 'd3-force',
    // 斥力随规模增长但设上限，否则「时期」这类超级节点（一个节点连几十个事件）会把
    // 星形簇甩得极远，fitView 后整图被压缩得很小
    manyBody: { strength: -50 - scale * 3 },
    link: { distance: 70 + scale * 0.5, strength: 0.9 },
    collide: { radius: 30, strength: 0.9 },
    // 向心力偏强：让整体向画布中心聚拢，提高画布利用率
    center: { strength: 0.16 },
    alphaDecay: 0.06,
    alphaMin: 0.02,
  }
}

function nodeSize(d) {
  if (d.data.isCenter) return 48
  return Math.min(22 + d.data.degree * 2.4, 40)
}

function buildOptions() {
  const data = buildData()
  return {
    container: containerRef.value,
    autoResize: false, // 由 ResizeObserver 统一驱动，避免与父容器动画竞争
    // 关闭元素过渡动画：布局收敛后画布应完全静止。持续重绘既耗 CPU，
    // 也会让"图谱一直在抖"成为答辩现场的观感问题
    animation: false,
    data,
    layout: layoutOf(data.nodes.length),
    padding: 24,
    node: {
      type: 'circle',
      style: {
        size: (d) => nodeSize(d),
        fill: (d) => labelColor(d.data.type),
        stroke: (d) => (d.data.isCenter ? '#C7000B' : '#FFFFFF'),
        lineWidth: (d) => (d.data.isCenter ? 3 : 1.5),
        shadowColor: 'rgba(0,0,0,0.18)',
        shadowBlur: (d) => (d.data.isCenter ? 12 : 4),
        cursor: 'pointer',
        // 标签分级显示：常驻标签者上屏，其余留给 hover 态
        labelText: (d) => (d.data.keepLabel ? truncate(d.data.name) : ''),
        labelPlacement: 'bottom',
        labelFontSize: 12,
        labelFill: '#303133',
        labelBackground: true,
        labelBackgroundFill: 'rgba(255,255,255,0.82)',
        labelBackgroundRadius: 4,
        labelBackgroundPadding: [2, 5],
      },
      state: {
        // hover / 选中时补全完整名称与类型，解决「稠密图看不清是谁」
        active: {
          lineWidth: 3,
          stroke: '#C7000B',
          labelText: (d) => `${d.data.name}（${d.data.typeZh}）`,
          labelFontSize: 13,
          labelFontWeight: 600,
          labelBackgroundFill: '#FFFFFF',
          shadowBlur: 16,
        },
        selected: {
          lineWidth: 3,
          stroke: '#C7000B',
          labelText: (d) => `${d.data.name}（${d.data.typeZh}）`,
          labelFontWeight: 600,
        },
        // 非邻接节点淡出，突出当前焦点的一跳关系
        inactive: { fillOpacity: 0.25, strokeOpacity: 0.25, labelOpacity: 0.15 },
      },
    },
    edge: {
      type: 'line',
      style: {
        stroke: '#C0C4CC',
        lineWidth: 1.2,
        endArrow: true,
        endArrowType: 'vee',
        endArrowSize: 8,
        // 边的中文关系名默认不上屏（密集时不可读），hover 高亮时才显示
        labelText: '',
        labelFontSize: 11,
        labelFill: '#909399',
        labelBackground: true,
        labelBackgroundFill: 'rgba(255,255,255,0.9)',
        labelBackgroundPadding: [1, 4],
      },
      state: {
        active: {
          stroke: '#C7000B',
          lineWidth: 2.2,
          labelText: (d) => d.data.label,
          labelFill: '#C7000B',
          labelFontWeight: 600,
        },
        inactive: { strokeOpacity: 0.12, labelOpacity: 0 },
      },
    },
    behaviors: [
      'drag-canvas',
      'zoom-canvas',
      { type: 'drag-element-force', fixed: true }, // 拖动节点后钉住，便于人工理顺布局
      { type: 'hover-activate', degree: 1, state: 'active', inactiveState: 'inactive' },
      { type: 'click-select', degree: 1, state: 'selected', unselectedState: 'inactive', multiple: false },
    ],
    plugins: [
      {
        type: 'tooltip',
        trigger: 'hover',
        enable: (e) => e.targetType === 'node' || e.targetType === 'edge',
        getContent: (_e, items) => {
          const it = items && items[0]
          if (!it) return ''
          const d = it.data || {}
          if (d.label && !d.name) return `<div class="kg-tip"><b>${d.label}</b></div>`
          return `<div class="kg-tip"><b>${d.name || ''}</b><span>${d.typeZh || ''}　关联 ${d.degree || 0}</span></div>`
        },
      },
    ],
  }
}

async function render() {
  await nextTick()
  if (!containerRef.value) return
  destroyGraph()
  graph = new Graph(buildOptions())
  graph.on('node:click', (e) => {
    const node = findNode(e.target?.id)
    if (node) emit('node-click', node)
  })
  graph.on('node:dblclick', (e) => {
    const node = findNode(e.target?.id)
    if (node) emit('node-dblclick', node)
  })
  // d3-force 是异步迭代的：render() 返回时布局往往还在收敛，此时 fitView 会按半成品的
  // 包围盒缩放，表现为图偏在一角、画布大片留白。故在布局结束后再做一次适配。
  graph.on('afterlayout', fitLater)
  await graph.render()
  fitLater()
}

let fitTimer = null
function fitLater() {
  clearTimeout(fitTimer)
  fitTimer = setTimeout(() => {
    if (!graph || graph.destroyed) return
    graph.fitView({ when: 'always', direction: 'both' }, { duration: 300 }).catch(() => {
      /* 画布尺寸为 0（父容器隐藏）时 fitView 会失败，忽略即可 */
    })
  }, 260)
}

// 对外仍下发原始节点对象（含 id/name/type），保持与调用方既有约定一致
function findNode(id) {
  return props.nodes.find((n) => n.id === id) || null
}

function destroyGraph() {
  clearTimeout(fitTimer)
  if (graph) {
    graph.destroy()
    graph = null
  }
}

// ---- 暴露给 GraphToolbar 的视图操作（接口与原实现保持一致） ----
function zoomBy(delta) {
  if (!graph) return
  const next = Math.min(Math.max(graph.getZoom() * delta, 0.2), 4)
  graph.zoomTo(next, { duration: 200 })
}

function resetView() {
  render()
}

function resize() {
  if (!graph || !containerRef.value) return
  const { clientWidth, clientHeight } = containerRef.value
  if (clientWidth && clientHeight) graph.setSize(clientWidth, clientHeight)
}

defineExpose({ zoomBy, resetView, resize, fitView: () => graph && graph.fitView() })

onMounted(() => {
  if (hasData.value) render()
  if (containerRef.value && window.ResizeObserver) {
    resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(containerRef.value)
  }
})

watch(
  () => [props.nodes, props.links, props.centerId],
  () => {
    if (hasData.value) render()
    else destroyGraph()
  },
  { deep: true },
)

onBeforeUnmount(() => {
  if (resizeObserver) resizeObserver.disconnect()
  destroyGraph()
})
</script>

<style scoped>
.kg-graph {
  position: relative;
  width: 100%;
  background: radial-gradient(circle at 50% 40%, #ffffff 0%, #fbfbfc 60%, #f5f6f8 100%);
  border-radius: var(--radius);
  overflow: hidden;
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
/* 图例浮于画布左下角，不占画布高度 */
.graph-legend {
  position: absolute;
  left: 12px;
  bottom: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-width: calc(100% - 24px);
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--color-text-secondary);
  font-size: 12px;
}
.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
/* 孤立节点提示浮于画布上方，不占布局空间；置顶避让底部图例 */
.graph-isolated-hint {
  position: absolute;
  left: 50%;
  top: 12px;
  transform: translateX(-50%);
  margin: 0;
  padding: 4px 12px;
  border-radius: var(--radius);
  background: var(--color-bg-gray);
  color: var(--color-text-light);
  font-size: 13px;
  pointer-events: none;
}
</style>

<style>
/* G6 tooltip 为插件注入的全局节点，不能用 scoped */
.kg-tip {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 13px;
  line-height: 1.6;
  max-width: 280px;
}
.kg-tip span {
  color: #909399;
  font-size: 12px;
}
</style>
