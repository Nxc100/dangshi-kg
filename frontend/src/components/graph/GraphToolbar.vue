<template>
  <div class="graph-toolbar">
    <div class="filter-area">
      <span class="filter-label">类型筛选</span>
      <el-checkbox-group :model-value="modelValue" size="small" @change="(v) => emit('update:modelValue', v)">
        <el-checkbox v-for="t in types" :key="t" :value="t" :label="t">
          <span class="dot" :style="{ backgroundColor: labelColor(t) }"></span>{{ labelZh(t) }}
        </el-checkbox>
      </el-checkbox-group>
    </div>
    <div class="action-area">
      <el-button-group size="small">
        <el-button :icon="ZoomIn" @click="emit('zoom-in')" />
        <el-button :icon="ZoomOut" @click="emit('zoom-out')" />
        <el-button :icon="RefreshLeft" @click="emit('reset')">重置视图</el-button>
      </el-button-group>
    </div>
  </div>
</template>

<script setup>
import { RefreshLeft, ZoomIn, ZoomOut } from '@element-plus/icons-vue'
import { labelColor, labelZh } from '@/utils/ontology'

// 图谱工具栏：按实体类型勾选筛选 / 缩放 / 重置视图（颜色与中文名取自 ontology.js）
defineProps({
  modelValue: { type: Array, default: () => [] }, // 选中的实体类型
  types: { type: Array, default: () => [] }, // 当前画布出现的类型
})
const emit = defineEmits(['update:modelValue', 'zoom-in', 'zoom-out', 'reset'])
</script>

<style scoped>
.graph-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--color-bg-gray);
  border-radius: var(--radius);
  margin-bottom: 12px;
}
.filter-area {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.filter-label {
  font-size: 13px;
  color: var(--color-text-secondary);
}
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: middle;
}
</style>
