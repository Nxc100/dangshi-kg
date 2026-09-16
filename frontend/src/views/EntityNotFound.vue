<template>
  <div class="page not-found">
    <div class="card nf-card">
      <el-icon :size="56" class="nf-icon"><DocumentDelete /></el-icon>
      <h1 class="nf-title">未找到该词条</h1>
      <p class="nf-sub">
        <template v-if="missingName">知识库中暂未收录「{{ missingName }}」。</template>
        你可以换个名称搜索，或从下面的热门词条开始了解。
      </p>

      <div class="nf-search">
        <el-autocomplete
          v-model="keyword"
          :fetch-suggestions="suggest"
          placeholder="搜索其他词条"
          clearable
          class="nf-input"
          @select="onSelect"
        >
          <template #default="{ item }">
            <span>{{ item.name }}</span><TypeBadge :type="item.type" class="opt-badge" />
          </template>
        </el-autocomplete>
        <el-button type="primary" @click="go(keyword)">搜索</el-button>
      </div>

      <div class="nf-hot">
        <span class="hot-label">热门词条：</span>
        <el-button v-for="name in HOT" :key="name" link type="primary" size="small" @click="go(name)">
          {{ name }}
        </el-button>
      </div>

      <div class="nf-actions">
        <el-button @click="router.push('/')">返回首页</el-button>
        <el-button type="primary" plain @click="router.push('/qa')">去提问</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import TypeBadge from '@/components/common/TypeBadge.vue'
import { searchEntities } from '@/api/graph'

// 词条 404 页：搜索框 + 热门实体入口（不受路由守卫拦截）
const HOT = ['遵义会议', '中国共产党第一次全国代表大会', '毛泽东', '南昌起义', '《论持久战》']

const route = useRoute()
const router = useRouter()
const keyword = ref('')
const missingName = ref(route.query.name || '')

async function suggest(kw, cb) {
  const text = String(kw || '').trim()
  if (!text) return cb([])
  try {
    const list = await searchEntities(text)
    cb(list.map((i) => ({ ...i, value: i.name })))
  } catch {
    cb([])
  }
}

function go(name) {
  const text = String(name || '').trim()
  if (!text) {
    ElMessage.warning('请输入词条名称')
    return
  }
  router.push({ name: 'entity', params: { name: text } })
}

function onSelect(item) {
  go(item.name)
}
</script>

<style scoped>
.nf-card {
  max-width: 620px;
  margin: 40px auto;
  text-align: center;
  padding: 32px 24px;
}
.nf-icon {
  color: var(--color-text-light);
}
.nf-title {
  margin: 12px 0 6px;
  font-size: 20px;
}
.nf-sub {
  margin: 0 0 18px;
  color: var(--color-text-secondary);
}
.nf-search {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 14px;
}
.nf-input {
  width: 320px;
}
.opt-badge {
  margin-left: 6px;
}
.nf-hot {
  margin-bottom: 18px;
}
.hot-label {
  font-size: 13px;
  color: var(--color-text-light);
}
.nf-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}
</style>
