<template>
  <span class="type-badge" :class="size" :style="{ backgroundColor: color }">{{ text }}</span>
</template>

<script setup>
import { computed } from 'vue'
import { labelZh, labelColor } from '@/utils/ontology'

// 实体类型徽标：颜色与中文名只取自 ontology.js（全站唯一来源）
const props = defineProps({
  type: { type: String, required: true },
  size: { type: String, default: 'small' }, // small | default
})
const color = computed(() => labelColor(props.type))
const text = computed(() => labelZh(props.type))
</script>

<style scoped>
.type-badge {
  display: inline-block;
  padding: 0 6px;
  line-height: 18px;
  font-size: 12px;
  color: #fff;
  border-radius: 4px;
  vertical-align: middle;
  white-space: nowrap;
}
.type-badge.default {
  padding: 0 10px;
  line-height: 24px;
  font-size: 13px;
}
</style>
