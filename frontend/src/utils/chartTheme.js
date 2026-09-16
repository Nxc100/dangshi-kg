// 图表与画布配色常量（唯一来源）
//
// 注意：这里的颜色**不是实体类型语义色**。七类实体的类型色是本体的一部分，只能来自
// `@/utils/ontology.js` 的 LABEL_COLOR（由 backend/common/ontology.py 生成），任何页面
// 与组件都不得在此重新定义。本文件只收敛与本体无关的通用视觉常量：
//   - 统计图表的分类调色板与主色（柱状 / 折线 / 饼图）
//   - 兜底率环形图的双色
//   - 力导向图的连线与边标签等中性色
// 与 CSS 变量的分工：能用 CSS 表达的（文字、背景、边框）一律走 styles/variables.css；
// ECharts 的 option 只能接收字面量，故在此集中定义，避免散落各组件。

// 图表主色，与 --color-primary 保持一致
export const CHART_PRIMARY = '#C7000B'

// 分类调色板：用于饼图 / 多系列图的扇区着色（非实体类型语义）
export const CHART_PALETTE = [
  '#C7000B', '#E67E22', '#2E86C1', '#8E44AD',
  '#27AE60', '#B7950B', '#7F8C8D', '#C9A227',
]

// 后台总览四个数字卡的图标底色
export const OVERVIEW_CARD_COLORS = ['#C7000B', '#E67E22', '#2E86C1', '#27AE60']

// 兜底率环形图：命中图谱 / 走兜底
export const FALLBACK_PIE_COLORS = ['#27AE60', '#E6A23C']

// 力导向图中性色：边线与边标签（与 --color-text-light / --color-border 同色系）
export const GRAPH_EDGE_COLOR = '#C0C4CC'
export const GRAPH_EDGE_LABEL_COLOR = '#909399'
