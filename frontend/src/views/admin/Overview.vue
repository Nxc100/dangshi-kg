<template>
  <div class="admin-overview" v-loading="loading">
    <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="load" />

    <template v-else>
      <el-row :gutter="16">
        <el-col v-for="card in cards" :key="card.key" :xs="12" :md="6">
          <div class="stat-card card">
            <div class="stat-icon" :style="{ backgroundColor: card.color }">
              <el-icon :size="20"><component :is="card.icon" /></el-icon>
            </div>
            <div class="stat-body">
              <div class="stat-value">{{ data[card.key] ?? '—' }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 快捷入口：把最常用的管理动作放在总览首屏，减少一次菜单点击 -->
      <div class="quick-row">
        <button v-for="q in QUICK_LINKS" :key="q.to" class="quick-card" type="button" @click="router.push(q.to)">
          <el-icon :size="18" :style="{ color: q.color }"><component :is="q.icon" /></el-icon>
          <span class="quick-title">{{ q.title }}</span>
          <span class="quick-desc">{{ q.desc }}</span>
        </button>
      </div>

      <el-row :gutter="16" class="panel-row">
        <!-- 最近知识变更：与操作日志页同源（GET /api/admin/oplog），只取前 6 条 -->
        <el-col :xs="24" :md="12">
          <div class="card panel">
            <h3 class="panel-title">
              最近知识变更
              <el-button link type="primary" @click="router.push('/admin/oplog')">全部日志 →</el-button>
            </h3>
            <ul v-if="oplogs.length" class="panel-list">
              <li v-for="o in oplogs" :key="o.id">
                <el-tag :type="ACTION_TAG[o.action] || 'info'" size="small" effect="plain">
                  {{ ACTION_ZH[o.action] || o.action }}
                </el-tag>
                <span class="panel-main" :title="o.object_name">{{ o.object_name }}</span>
                <span class="panel-time">{{ o.created_at }}</span>
              </li>
            </ul>
            <p v-else class="panel-empty">暂无知识变更记录</p>
          </div>
        </el-col>

        <!-- 最近问答：与问答日志页同源（GET /api/admin/logs），只取前 6 条 -->
        <el-col :xs="24" :md="12">
          <div class="card panel">
            <h3 class="panel-title">
              最近问答
              <el-button link type="primary" @click="router.push('/admin/qalog')">全部记录 →</el-button>
            </h3>
            <ul v-if="qalogs.length" class="panel-list">
              <li v-for="q in qalogs" :key="q.id">
                <el-tag :type="q.fallback ? 'warning' : 'success'" size="small" effect="plain">
                  {{ q.fallback ? '兜底' : '命中' }}
                </el-tag>
                <span class="panel-main" :title="q.question">{{ q.question }}</span>
                <span class="panel-time">{{ q.created_at }}</span>
              </li>
            </ul>
            <p v-else class="panel-empty">暂无问答记录</p>
          </div>
        </el-col>
      </el-row>

      <div class="card tip-card">
        <h3 class="tip-title">运营提示</h3>
        <p class="text-secondary">
          知识管理中的每次写操作都会留痕到操作日志；后台修改即时生效，前台问答、百科与图谱下一次请求即为最新值。
          新增实体默认为「未校验」，不参与测验出题与每日推荐，人工核对后在编辑表单勾选「已校验」方可进入核心池。
        </p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import { getOpLog, getOverview } from '@/api/adminKg'
import { getQaLogs } from '@/api/adminLog'
import { OVERVIEW_CARD_COLORS } from '@/utils/chartTheme'

// 后台总览（FR-A01）：四个概览数字卡 + 快捷入口 + 最近变更/最近问答
// 数值与各管理页一致（全部来自后端聚合，前端不自行计算）
const router = useRouter()

const cards = [
  { key: 'entity_count', label: '实体总数', icon: 'Collection', color: OVERVIEW_CARD_COLORS[0] },
  { key: 'relation_count', label: '关系总数', icon: 'Share', color: OVERVIEW_CARD_COLORS[1] },
  { key: 'user_count', label: '注册用户数', icon: 'User', color: OVERVIEW_CARD_COLORS[2] },
  { key: 'today_qa_count', label: '今日问答量', icon: 'ChatLineSquare', color: OVERVIEW_CARD_COLORS[3] },
]

const QUICK_LINKS = [
  { title: '实体管理', desc: '新增 / 编辑 / 删除词条', to: '/admin/entities', icon: 'Collection', color: '#C7000B' },
  { title: '关系管理', desc: '维护三元组关系', to: '/admin/triples', icon: 'Share', color: '#8E44AD' },
  { title: '用户管理', desc: '禁用 / 重置 / 授权', to: '/admin/users', icon: 'User', color: '#2E86C1' },
  { title: '热点统计', desc: '问答热点与兜底率', to: '/admin/stats', icon: 'TrendCharts', color: '#C9A227' },
]

const ACTION_ZH = { add: '新增', edit: '编辑', delete: '删除' }
const ACTION_TAG = { add: 'success', edit: 'warning', delete: 'danger' }

const data = reactive({ entity_count: 0, relation_count: 0, user_count: 0, today_qa_count: 0 })
const oplogs = ref([])
const qalogs = ref([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    Object.assign(data, await getOverview())
  } catch (err) {
    error.value = (err && err.msg) || '总览数据加载失败，请稍后重试'
    return
  } finally {
    loading.value = false
  }
  loadPanels()
}

// 两个面板是总览的补充信息：失败时各自留空态，不影响数字卡与页面主体
async function loadPanels() {
  try {
    const res = await getOpLog({ page: 1, size: 6 })
    oplogs.value = res.list || []
  } catch {
    oplogs.value = []
  }
  try {
    const res = await getQaLogs({ page: 1, size: 6 })
    qalogs.value = res.list || []
  } catch {
    qalogs.value = []
  }
}

onMounted(load)
</script>

<style scoped>
.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
}
.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.3;
}
.stat-label {
  font-size: 13px;
  color: var(--color-text-light);
}

/* 快捷入口 */
.quick-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-top: 16px;
}
.quick-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 14px 16px;
  background: var(--color-card);
  border: none;
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  text-align: left;
  transition: transform var(--transition), box-shadow var(--transition);
}
.quick-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}
.quick-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}
.quick-desc {
  font-size: 12px;
  color: var(--color-text-light);
}

/* 最近变更 / 最近问答 */
.panel-row {
  margin-top: 16px;
}
.panel {
  height: 100%;
}
.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0 0 8px;
  font-size: 15px;
}
.panel-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.panel-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 0;
  border-bottom: 1px dashed var(--color-border);
}
.panel-list li:last-child {
  border-bottom: none;
}
.panel-main {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}
.panel-time {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--color-text-light);
}
.panel-empty {
  margin: 16px 0;
  text-align: center;
  color: var(--color-text-light);
  font-size: 13px;
}
.tip-card {
  margin-top: 16px;
}
.tip-title {
  margin: 0 0 8px;
  font-size: 15px;
}

@media (max-width: 992px) {
  .quick-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
