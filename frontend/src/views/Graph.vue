<template>
  <div class="page graph-page">
    <h1 class="page-title">知识图谱可视化</h1>

    <div class="card">
      <div class="search-bar">
        <el-autocomplete
          v-model="keyword"
          :fetch-suggestions="suggest"
          placeholder="输入实体名称，如：遵义会议"
          clearable
          class="search-input"
          @select="onSelect"
        >
          <template #default="{ item }">
            <span>{{ item.name }}</span><TypeBadge :type="item.type" class="opt-badge" />
          </template>
        </el-autocomplete>
        <el-button type="primary" :icon="Search" :loading="loading" @click="loadByKeyword">查询</el-button>
      </div>

      <el-alert v-if="truncated" type="warning" :closable="false" show-icon class="tip"
        title="节点较多，请使用类型筛选" />

      <GraphToolbar
        v-if="graph.nodes.length"
        v-model="selectedTypes"
        :types="allTypes"
        @zoom-in="graphRef && graphRef.zoomBy(1.25)"
        @zoom-out="graphRef && graphRef.zoomBy(0.8)"
        @reset="resetView"
      />

      <div v-loading="loading">
        <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="loadByKeyword" />
        <EmptyState
          v-else-if="!graph.nodes.length"
          icon="Share"
          text="搜索一个实体，查看它在党史知识网络中的位置"
          action-text="试试「遵义会议」"
          @action="quickSearch('遵义会议')"
        />
        <KgGraph
          v-else
          ref="graphRef"
          :nodes="filtered.nodes"
          :links="filtered.links"
          :center-id="centerId"
          height="560px"
          @node-click="onNodeClick"
          @node-dblclick="openEntity"
        />
      </div>
    </div>

    <NodeDrawer
      v-model="drawerVisible"
      :node="activeNode"
      :detail="activeDetail"
      :loading="detailLoading"
      :expanding="expanding"
      @expand="expandNeighbors"
      @open-entity="openEntity"
    />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import KgGraph from '@/components/graph/KgGraph.vue'
import NodeDrawer from '@/components/graph/NodeDrawer.vue'
import GraphToolbar from '@/components/graph/GraphToolbar.vue'
import TypeBadge from '@/components/common/TypeBadge.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import { getNeighbors, getSubgraph, searchEntities } from '@/api/graph'
import { getEntity } from '@/api/entity'
import { KEYWORD_MAX_LEN, isValidKeyword } from '@/utils/validators'

// 图谱页（F2）：搜索联想 → 2 跳力导向子图 → 单击抽屉 / 展开邻居 → 双击进百科；单画布节点上限 100
const NODE_LIMIT = 100

const router = useRouter()
const keyword = ref('')
const graph = ref({ nodes: [], links: [] })
const centerId = ref('')
const truncated = ref(false)
const loading = ref(false)
const error = ref('')
const selectedTypes = ref([])
const graphRef = ref(null)

const drawerVisible = ref(false)
const activeNode = ref(null)
const activeDetail = ref(null)
const detailLoading = ref(false)
const expanding = ref(false)

const allTypes = computed(() => {
  const types = []
  graph.value.nodes.forEach((n) => {
    if (n.type && !types.includes(n.type)) types.push(n.type)
  })
  return types
})

// 类型筛选：未勾选任何类型视为全选
const filtered = computed(() => {
  const selected = selectedTypes.value
  if (!selected.length) return graph.value
  const nodes = graph.value.nodes.filter((n) => selected.includes(n.type))
  const ids = new Set(nodes.map((n) => n.id))
  return { nodes, links: graph.value.links.filter((l) => ids.has(l.source) && ids.has(l.target)) }
})

async function suggest(kw, cb) {
  const text = String(kw || '').trim()
  if (!text) return cb([])
  // 前端拦截超长搜索词（规范 1.3：非空 ≤ 30 字，后端复校）
  if (!isValidKeyword(text)) {
    ElMessage.warning(`搜索词不能超过 ${KEYWORD_MAX_LEN} 字`)
    return cb([])
  }
  try {
    const list = await searchEntities(text)
    cb(list.map((i) => ({ ...i, value: i.name })))
  } catch {
    cb([])
  }
}

async function load(name) {
  loading.value = true
  error.value = ''
  try {
    const data = await getSubgraph(name, 2, NODE_LIMIT)
    graph.value = { nodes: data.nodes || [], links: data.links || [] }
    centerId.value = data.center ? data.center.id : ''
    truncated.value = !!data.truncated
    selectedTypes.value = []
  } catch (err) {
    graph.value = { nodes: [], links: [] }
    error.value = err && err.code === 404 ? '未找到该词条，请检查名称' : '图谱加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function loadByKeyword() {
  const name = keyword.value.trim()
  if (!name) {
    ElMessage.warning('请输入实体名称')
    return
  }
  load(name)
}

function quickSearch(name) {
  keyword.value = name
  load(name)
}

function onSelect(item) {
  keyword.value = item.name
  load(item.name)
}

async function onNodeClick(node) {
  activeNode.value = node
  activeDetail.value = null
  drawerVisible.value = true
  detailLoading.value = true
  try {
    activeDetail.value = await getEntity(node.name)
  } catch {
    activeDetail.value = null
  } finally {
    detailLoading.value = false
  }
}

// 增量加载 1 跳邻居并合并去重，画布总节点仍受 100 上限约束
async function expandNeighbors(node) {
  expanding.value = true
  try {
    const data = await getNeighbors(node.name)
    const nodeMap = new Map(graph.value.nodes.map((n) => [n.id, n]))
    let reached = false
    ;(data.nodes || []).forEach((n) => {
      if (nodeMap.has(n.id)) return
      if (nodeMap.size >= NODE_LIMIT) {
        reached = true
        return
      }
      nodeMap.set(n.id, n)
    })
    const linkSet = new Set(graph.value.links.map((l) => `${l.source}|${l.target}|${l.relation}`))
    const links = graph.value.links.slice()
    ;(data.links || []).forEach((l) => {
      const key = `${l.source}|${l.target}|${l.relation}`
      if (!linkSet.has(key) && nodeMap.has(l.source) && nodeMap.has(l.target)) {
        linkSet.add(key)
        links.push(l)
      }
    })
    graph.value = { nodes: Array.from(nodeMap.values()), links }
    if (reached) {
      truncated.value = true
      ElMessage.warning('画布节点已达上限 100，请使用类型筛选')
    }
  } catch (err) {
    ElMessage.error((err && err.msg) || '展开邻居失败')
  } finally {
    expanding.value = false
  }
}

function resetView() {
  selectedTypes.value = []
  if (graphRef.value) graphRef.value.resetView()
}

function openEntity(node) {
  drawerVisible.value = false
  router.push({ name: 'entity', params: { name: node.name } })
}
</script>

<style scoped>
.search-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.search-input {
  flex: 1;
  max-width: 420px;
}
.opt-badge {
  margin-left: 6px;
}
.tip {
  margin-bottom: 12px;
}
</style>
