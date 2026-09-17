<template>
  <canvas ref="canvasRef" class="graph-backdrop" aria-hidden="true"></canvas>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { LABEL_COLOR, LABELS } from '@/utils/ontology'

// 知识图谱氛围背景（登录页品牌区装饰）：节点缓慢漂移 + 近距离自动连边，
// 颜色取自 ontology.js 的七类实体色，呼应全站图谱配色。
// 纯装饰，不承载任何数据语义；尊重 prefers-reduced-motion，减少动效时只画静态一帧。
const props = defineProps({
  // 节点数按容器面积推算，保证不同屏幕上的疏密观感一致（默认值仅作下限参考）
  density: { type: Number, default: 13000 },
  minCount: { type: Number, default: 28 },
  maxCount: { type: Number, default: 70 },
  linkDistance: { type: Number, default: 168 },
})

const canvasRef = ref(null)
let ctx = null
let raf = 0
let nodes = []
let width = 0
let height = 0
let dpr = 1
let resizeObserver = null

const COLORS = LABELS.map((l) => LABEL_COLOR[l])

function resize() {
  const el = canvasRef.value
  if (!el || !el.parentElement) return
  const rect = el.parentElement.getBoundingClientRect()
  if (!rect.width || !rect.height) return
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  width = rect.width
  height = rect.height
  // 只设像素缓冲尺寸：显示尺寸已由 CSS 的 absolute inset:0 决定。
  // 若在这里再写 style.width/height，会与 CSS 反复较劲并把 ResizeObserver 带进抖动循环
  el.width = Math.round(width * dpr)
  el.height = Math.round(height * dpr)
  ctx = el.getContext('2d')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
}

function seed() {
  const count = Math.round(
    Math.min(Math.max((width * height) / props.density, props.minCount), props.maxCount),
  )
  nodes = Array.from({ length: count }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    vx: (Math.random() - 0.5) * 0.22,
    vy: (Math.random() - 0.5) * 0.22,
    r: 2 + Math.random() * 3.5,
    color: COLORS[Math.floor(Math.random() * COLORS.length)],
  }))
}

function draw() {
  if (!ctx) return
  ctx.clearRect(0, 0, width, height)

  // 先画边：距离越近越不透明，形成自然的"关系网"观感
  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      const dx = nodes[i].x - nodes[j].x
      const dy = nodes[i].y - nodes[j].y
      const dist = Math.hypot(dx, dy)
      if (dist >= props.linkDistance) continue
      ctx.globalAlpha = (1 - dist / props.linkDistance) * 0.45
      ctx.strokeStyle = '#FFFFFF'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(nodes[i].x, nodes[i].y)
      ctx.lineTo(nodes[j].x, nodes[j].y)
      ctx.stroke()
    }
  }

  // 再画节点：外圈光晕 + 实心点
  nodes.forEach((n) => {
    ctx.globalAlpha = 0.28
    ctx.fillStyle = n.color
    ctx.beginPath()
    ctx.arc(n.x, n.y, n.r * 2.6, 0, Math.PI * 2)
    ctx.fill()

    ctx.globalAlpha = 0.95
    ctx.fillStyle = n.color
    ctx.beginPath()
    ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2)
    ctx.fill()
  })
  ctx.globalAlpha = 1
}

function step() {
  nodes.forEach((n) => {
    n.x += n.vx
    n.y += n.vy
    // 触边反弹，保持节点始终在可视区内
    if (n.x < 0 || n.x > width) n.vx *= -1
    if (n.y < 0 || n.y > height) n.vy *= -1
  })
  draw()
  raf = requestAnimationFrame(step)
}

onMounted(() => {
  resize()
  if (!width || !height) return
  seed()
  const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduced) draw()
  else raf = requestAnimationFrame(step)

  if (window.ResizeObserver && canvasRef.value?.parentElement) {
    // 防抖：容器尺寸连续变化（窗口拖拽）时只在稳定后重建一次，避免高频重算粒子
    let t = 0
    resizeObserver = new ResizeObserver(() => {
      clearTimeout(t)
      t = setTimeout(() => {
        resize()
        seed()
        if (reduced) draw()
      }, 150)
    })
    resizeObserver.observe(canvasRef.value.parentElement)
  }
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  if (resizeObserver) resizeObserver.disconnect()
})
</script>

<style scoped>
.graph-backdrop {
  position: absolute;
  inset: 0;
  display: block;
  pointer-events: none;
}
</style>
