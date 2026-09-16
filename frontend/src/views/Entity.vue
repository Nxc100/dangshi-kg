<template>
  <div class="page entity-page" v-loading="loading">
    <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="load" />

    <template v-else-if="data">
      <div class="card entity-head">
        <div class="head-main">
          <h1 class="entity-name">{{ data.entity.name }}</h1>
          <TypeBadge :type="data.entity.type" size="default" />
          <el-tag v-for="a in data.entity.alias" :key="a" size="small" class="alias-tag" type="info" effect="plain">
            {{ a }}
          </el-tag>
        </div>
        <el-button :type="favorited ? 'warning' : 'default'" :icon="favorited ? StarFilled : Star"
          :loading="favLoading" @click="toggleFavorite">
          {{ favorited ? '已收藏' : '收藏' }}
        </el-button>
      </div>

      <div class="card">
        <h2 class="section-title">基本信息</h2>
        <PropertyTable :type="data.entity.type" :values="data.entity.props" />
      </div>

      <div v-if="data.intro" class="card">
        <h2 class="section-title">简介</h2>
        <p class="intro-text">{{ data.intro }}</p>
        <p class="intro-source">
          来源：<a v-if="isUrl(data.source)" :href="data.source" target="_blank" rel="noopener">{{ data.source }}</a>
          <span v-else>{{ data.source || '权威公开资料' }}</span>
        </p>
      </div>

      <div class="card">
        <h2 class="section-title">关联知识</h2>
        <RelationGroups :relations="data.relations" @open="openEntity" />
      </div>

      <div class="card">
        <h2 class="section-title">关系图谱</h2>
        <KgGraph
          :nodes="data.subgraph.nodes"
          :links="data.subgraph.links"
          :center-id="centerId"
          height="380px"
          @node-dblclick="openEntity"
        />
        <p class="graph-tip text-light">双击节点可跳转到对应词条</p>
      </div>
    </template>

    <LoginGuide v-model="loginGuide" text="登录后可收藏词条，随时回看" />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Star, StarFilled } from '@element-plus/icons-vue'
import TypeBadge from '@/components/common/TypeBadge.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import LoginGuide from '@/components/common/LoginGuide.vue'
import PropertyTable from '@/components/entity/PropertyTable.vue'
import RelationGroups from '@/components/entity/RelationGroups.vue'
import KgGraph from '@/components/graph/KgGraph.vue'
import { getEntity } from '@/api/entity'
import { addFavorite, removeFavorite } from '@/api/user'
import { useUserStore } from '@/store/user'

// 实体百科页（F4）：各功能统一跳转落点；不存在的词条跳友好 404 页
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const data = ref(null)
const loading = ref(false)
const error = ref('')
const favorited = ref(false)
const favLoading = ref(false)
const loginGuide = ref(false)

// 节点 id 由后端 graph_service.node_id() 唯一生成，前端只从子图取用，不自行拼接（规范 4.3 / 6.5）
const centerId = computed(() => {
  if (!data.value) return ''
  const nodes = (data.value.subgraph && data.value.subgraph.nodes) || []
  const hit = nodes.find((n) => n.name === data.value.entity.name)
  return hit ? hit.id : ''
})

function isUrl(text) {
  return /^https?:\/\//i.test(String(text || ''))
}

async function load() {
  const name = route.params.name
  if (!name) return
  loading.value = true
  error.value = ''
  try {
    const result = await getEntity(name)
    data.value = result
    favorited.value = !!result.favorited
  } catch (err) {
    data.value = null
    if (err && err.code === 404) {
      router.replace({ name: 'entityNotFound', query: { name } })
      return
    }
    error.value = '词条加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function toggleFavorite() {
  if (!userStore.isLogin) {
    loginGuide.value = true
    return
  }
  if (favorited.value) {
    // 规范 1.2：取消收藏属二次确认场景
    try {
      await ElMessageBox.confirm(`确定取消收藏「${data.value.entity.name}」吗？`, '取消收藏', {
        type: 'warning', confirmButtonText: '取消收藏', cancelButtonText: '再想想',
      })
    } catch {
      return
    }
  }
  favLoading.value = true
  try {
    const payload = { fav_type: 'entity', ref_id: data.value.entity.name }
    if (favorited.value) {
      await removeFavorite(payload)
      favorited.value = false
      ElMessage.success('已取消收藏')
    } else {
      await addFavorite(payload)
      favorited.value = true
      ElMessage.success('已收藏')
    }
  } catch (err) {
    ElMessage.error((err && err.msg) || '操作失败，请重试')
  } finally {
    favLoading.value = false
  }
}

function openEntity(item) {
  if (item.name === route.params.name) return
  router.push({ name: 'entity', params: { name: item.name } })
}

watch(() => route.params.name, load, { immediate: true })
</script>

<style scoped>
.entity-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.head-main {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.entity-name {
  margin: 0;
  font-size: 22px;
}
.alias-tag {
  margin-left: 2px;
}
.section-title {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 600;
}
.intro-text {
  margin: 0 0 8px;
  line-height: 1.9;
}
.intro-source {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-light);
  word-break: break-all;
}
.graph-tip {
  margin: 8px 0 0;
  font-size: 12px;
  text-align: center;
}
</style>
