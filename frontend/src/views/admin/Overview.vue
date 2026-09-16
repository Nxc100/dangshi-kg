<template>
  <div class="admin-overview" v-loading="loading">
    <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="load" />

    <el-row v-else :gutter="16">
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

    <div class="card tip-card">
      <h3 class="tip-title">运营提示</h3>
      <p class="text-secondary">
        知识管理中的每次写操作都会留痕到操作日志；后台修改即时生效，前台问答、百科与图谱下一次请求即为最新值。
      </p>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import { getOverview } from '@/api/adminKg'
import { OVERVIEW_CARD_COLORS } from '@/utils/chartTheme'

// 后台总览（FR-A01）：四个概览数字卡，数值与各管理页一致（全部来自后端聚合）
const cards = [
  { key: 'entity_count', label: '实体总数', icon: 'Collection', color: OVERVIEW_CARD_COLORS[0] },
  { key: 'relation_count', label: '关系总数', icon: 'Share', color: OVERVIEW_CARD_COLORS[1] },
  { key: 'user_count', label: '注册用户数', icon: 'User', color: OVERVIEW_CARD_COLORS[2] },
  { key: 'today_qa_count', label: '今日问答量', icon: 'ChatLineSquare', color: OVERVIEW_CARD_COLORS[3] },
]

const data = reactive({ entity_count: 0, relation_count: 0, user_count: 0, today_qa_count: 0 })
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    Object.assign(data, await getOverview())
  } catch (err) {
    error.value = (err && err.msg) || '总览数据加载失败，请稍后重试'
  } finally {
    loading.value = false
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
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
}
.stat-label {
  font-size: 13px;
  color: var(--color-text-light);
}
.tip-card {
  margin-top: 16px;
}
.tip-title {
  margin: 0 0 8px;
  font-size: 15px;
}
</style>
