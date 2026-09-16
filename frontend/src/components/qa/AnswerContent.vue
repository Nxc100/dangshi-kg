<template>
  <div class="answer-content">
    <p class="answer-text">
      <template v-for="(seg, i) in segments" :key="i">
        <router-link
          v-if="seg.entity"
          class="entity-link"
          :style="{ color: labelColor(seg.entity.type), borderColor: labelColor(seg.entity.type) }"
          :to="{ name: 'entity', params: { name: seg.entity.name } }"
          >{{ seg.text }}</router-link
        >
        <span v-else>{{ seg.text }}</span>
      </template>
    </p>

    <div class="answer-actions">
      <el-button link type="primary" size="small" @click="showSource = !showSource">
        <el-icon><Share /></el-icon>{{ showSource ? '收起知识来源' : '查看知识来源' }}
      </el-button>
      <el-button link size="small" :type="favorited ? 'warning' : 'default'" @click="emit('favorite')">
        <el-icon><component :is="favorited ? 'StarFilled' : 'Star'" /></el-icon>{{ favorited ? '已收藏' : '收藏' }}
      </el-button>
    </div>

    <div v-if="showSource" class="answer-source">
      <KgGraph :nodes="subgraph.nodes" :links="subgraph.links" height="300px" :show-legend="false"
        empty-text="本次回答未涉及关联子图" @node-dblclick="openEntity" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import KgGraph from '@/components/graph/KgGraph.vue'
import { labelColor } from '@/utils/ontology'

// 答案正文：文本中的实体渲染为带类型色可点击链接（跳百科）；底部固定"查看知识来源"与"收藏"
const props = defineProps({
  text: { type: String, default: '' },
  entities: { type: Array, default: () => [] }, // [{id,name,type}]
  subgraph: { type: Object, default: () => ({ nodes: [], links: [] }) },
  favorited: { type: Boolean, default: false },
})
const emit = defineEmits(['favorite'])

const router = useRouter()
const showSource = ref(false)

// 按实体名（长名优先）切分答案文本，命中处渲染为实体链接
const segments = computed(() => {
  const text = props.text || ''
  const names = props.entities
    .filter((e) => e && e.name)
    .slice()
    .sort((a, b) => b.name.length - a.name.length)
  if (!text || !names.length) return [{ text, entity: null }]

  const out = []
  let buffer = ''
  let i = 0
  while (i < text.length) {
    const hit = names.find((e) => text.startsWith(e.name, i))
    if (hit) {
      if (buffer) {
        out.push({ text: buffer, entity: null })
        buffer = ''
      }
      out.push({ text: hit.name, entity: hit })
      i += hit.name.length
    } else {
      buffer += text[i]
      i += 1
    }
  }
  if (buffer) out.push({ text: buffer, entity: null })
  return out
})

function openEntity(node) {
  router.push({ name: 'entity', params: { name: node.name } })
}
</script>

<style scoped>
.answer-text {
  margin: 0;
  line-height: 1.9;
}
.entity-link {
  border-bottom: 1px dashed;
  padding-bottom: 1px;
}
.answer-actions {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--color-border);
  display: flex;
  gap: 12px;
}
.answer-source {
  margin-top: 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
}
</style>
