<template>
  <div class="llm-answer">
    <div class="llm-badge">
      <el-icon><MagicStick /></el-icon>
      <strong>AI 生成，仅供参考</strong>
    </div>

    <p class="llm-text">{{ llm.text }}</p>

    <el-collapse v-if="passages.length" class="llm-collapse">
      <el-collapse-item name="src" title="查看所引权威资料原文">
        <div v-for="(p, i) in passages" :key="i" class="cited-item" :class="{ cited: isCited(i + 1) }">
          <p class="cited-text"><span class="cited-index">[{{ i + 1 }}]</span>{{ p.text }}</p>
          <div class="cited-meta">
            <span>出处：{{ p.chapter || '权威资料' }}</span>
            <a v-if="p.source" :href="p.source" target="_blank" rel="noopener">查看原文</a>
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup>
// AI 生成回答（FR-L02）：固定徽标 + 正文（含 [n] 编号引用）+ 所引权威资料原文折叠区；
// 编号与正文引用一一对应，被引用段落高亮
const props = defineProps({
  llm: { type: Object, required: true }, // {text, cited:[1,2], latency_ms}
  passages: { type: Array, default: () => [] },
})

function isCited(index) {
  return Array.isArray(props.llm.cited) && props.llm.cited.includes(index)
}
</script>

<style scoped>
.llm-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--color-gold);
  background: rgba(201, 162, 39, 0.12);
  border-radius: 4px;
}
.llm-text {
  margin: 0;
  line-height: 1.9;
}
.llm-collapse {
  margin-top: 8px;
  border-top: 1px dashed var(--color-border);
}
.cited-item {
  padding: 8px 10px;
  border-radius: 4px;
  margin-bottom: 6px;
  background: var(--color-bg);
}
.cited-item.cited {
  background: var(--color-primary-lighter);
}
.cited-text {
  margin: 0 0 4px;
  line-height: 1.8;
}
.cited-index {
  margin-right: 4px;
  font-weight: 600;
  color: var(--color-primary);
}
.cited-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-light);
}
</style>
