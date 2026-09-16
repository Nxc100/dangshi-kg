<template>
  <div class="candidate-chips">
    <p class="chips-tip">{{ tip }}</p>
    <div class="chips-list">
      <el-button
        v-for="item in items"
        :key="item.name || item"
        size="small"
        plain
        type="primary"
        @click="emit('pick', item)"
      >
        {{ item.name || item }}
        <TypeBadge v-if="item.type" :type="item.type" class="chip-badge" />
      </el-button>
    </div>
  </div>
</template>

<script setup>
import TypeBadge from '@/components/common/TypeBadge.vue'

// "你是不是想问"候选按钮组 / 槽位不符时的问法示例按钮组；点击即以该内容重发
defineProps({
  tip: { type: String, default: '你是不是想问：' },
  items: { type: Array, default: () => [] }, // [{name,type}] 或 ['示例问句']
})
const emit = defineEmits(['pick'])
</script>

<style scoped>
.chips-tip {
  margin: 0 0 8px;
  color: var(--color-text-secondary);
}
.chips-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip-badge {
  margin-left: 4px;
}
</style>
