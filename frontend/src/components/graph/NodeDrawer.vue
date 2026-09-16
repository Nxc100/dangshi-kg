<template>
  <el-drawer
    :model-value="modelValue"
    :title="node ? node.name : '节点详情'"
    direction="rtl"
    size="360px"
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <div v-if="node" v-loading="loading" class="node-drawer">
      <div class="node-head">
        <TypeBadge :type="node.type" size="default" />
      </div>

      <el-descriptions v-if="visibleProps.length" :column="1" border size="small" class="node-props">
        <el-descriptions-item v-for="p in visibleProps" :key="p.name" :label="p.zh">
          <span class="prop-value">{{ p.value }}</span>
        </el-descriptions-item>
      </el-descriptions>
      <p v-else class="text-light">该节点暂无可展示的属性摘要。</p>

      <div class="node-actions">
        <el-button type="primary" plain :loading="expanding" @click="emit('expand', node)">展开邻居</el-button>
        <el-button @click="emit('open-entity', node)">查看词条</el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed } from 'vue'
import TypeBadge from '@/components/common/TypeBadge.vue'
import { PROPS } from '@/utils/ontology'

// 图谱节点属性摘要抽屉（单击节点打开）：属性摘要 + "展开邻居" + 进入百科页
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  node: { type: Object, default: null },
  detail: { type: Object, default: null }, // 百科聚合结果 {entity:{props}}
  loading: { type: Boolean, default: false },
  expanding: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'expand', 'open-entity'])

// 仅展示非空字段，字段中文名取自 ontology
const visibleProps = computed(() => {
  if (!props.node || !props.detail || !props.detail.entity) return []
  const values = props.detail.entity.props || {}
  return (PROPS[props.node.type] || [])
    .filter((p) => values[p.name] !== undefined && values[p.name] !== null && values[p.name] !== '')
    .map((p) => ({ name: p.name, zh: p.zh, value: String(values[p.name]).slice(0, 120) }))
})
</script>

<style scoped>
.node-drawer {
  min-height: 120px;
}
.node-head {
  margin-bottom: 12px;
}
.node-props {
  margin-bottom: 16px;
}
.prop-value {
  word-break: break-all;
}
.node-actions {
  display: flex;
  gap: 8px;
}
</style>
