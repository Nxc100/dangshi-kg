<template>
  <el-descriptions v-if="rows.length" :column="column" border size="default" class="property-table">
    <el-descriptions-item v-for="row in rows" :key="row.name" :label="row.zh">
      <span class="prop-value">{{ row.value }}</span>
    </el-descriptions-item>
  </el-descriptions>
  <p v-else class="text-light">该词条暂无结构化属性。</p>
</template>

<script setup>
import { computed } from 'vue'
import { PROPS } from '@/utils/ontology'

// 百科属性表：仅渲染非空字段，字段中文名取自 ontology；时间字段展示 time_text（后端只下发展示值）
// 简介与来源在页面中单独成段，属性表内不重复展示
const HIDDEN = ['name', 'alias', 'intro', 'source', 'time_sort', 'time_precision']

const props = defineProps({
  type: { type: String, required: true },
  values: { type: Object, default: () => ({}) },
  column: { type: Number, default: 2 },
})

const rows = computed(() =>
  (PROPS[props.type] || [])
    .filter((p) => !HIDDEN.includes(p.name))
    .filter((p) => {
      const v = props.values[p.name]
      return v !== undefined && v !== null && v !== ''
    })
    .map((p) => ({ name: p.name, zh: p.zh, value: props.values[p.name] })),
)
</script>

<style scoped>
.prop-value {
  word-break: break-word;
}
</style>
