<template>
  <div class="relation-groups">
    <div v-for="(group, i) in groups" :key="i" class="relation-group">
      <div class="group-title">
        {{ group.title }}
        <span class="group-count">{{ group.items.length }}</span>
      </div>
      <div class="group-items">
        <el-tag
          v-for="item in group.items"
          :key="item.name"
          class="group-tag"
          :color="labelColor(item.type)"
          effect="dark"
          @click="emit('open', item)"
        >
          {{ item.name }}
        </el-tag>
      </div>
    </div>
    <p v-if="!groups.length" class="text-light">暂无关联知识。</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { labelColor, labelZh, relationZh } from '@/utils/ontology'

// 关联实体分组标签区：按"关系 × 邻居类型"分组（如会议页"出席人物 / 形成文献 / 召开地点"），标签可点击跳转
// 分组标题由 ontology 的关系中文名与邻居类型中文名组合，禁止页面内另写一份映射
const props = defineProps({
  // [{relation, label, direction, neighbor_type, items:[{name,type}]}]
  relations: { type: Array, default: () => [] },
})
const emit = defineEmits(['open'])

const groups = computed(() =>
  props.relations
    .filter((r) => r.items && r.items.length)
    .map((r) => ({
      title: `${r.label || relationZh(r.relation)}·${labelZh(r.neighbor_type)}${r.direction === 'in' ? '（被指向）' : ''}`,
      items: r.items,
    })),
)
</script>

<style scoped>
.relation-group {
  margin-bottom: 14px;
}
.group-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}
.group-count {
  margin-left: 4px;
  font-weight: 400;
  color: var(--color-text-light);
}
.group-items {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.group-tag {
  cursor: pointer;
  border: none;
  color: #fff;
}
</style>
