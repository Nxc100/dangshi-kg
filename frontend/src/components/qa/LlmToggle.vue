<template>
  <!-- 系统层不可用（llm_available=false）时整体不渲染，界面与原方案一模一样 -->
  <div v-if="llmPref.llm_available" class="llm-toggle">
    <span class="toggle-label">AI 增强回答</span>
    <el-switch :model-value="llmPref.enabled" size="small" @change="onChange" />
    <el-tooltip placement="bottom" :content="TIP">
      <el-icon class="toggle-info"><InfoFilled /></el-icon>
    </el-tooltip>
  </div>
</template>

<script setup>
import { useLlmPrefStore } from '@/store/llmPref'

// AI 增强开关（FR-L01，用户层）：切换即时写入 localStorage，无需刷新，下一次提问即按新状态执行
const TIP = '开启后，知识库未收录的问题将由 AI 基于权威资料生成参考回答，并明确标注；可随时关闭'
const llmPref = useLlmPrefStore()

function onChange(value) {
  llmPref.setEnabled(value)
}
</script>

<style scoped>
.llm-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.toggle-label {
  font-size: 13px;
  color: var(--color-text-secondary);
}
.toggle-info {
  color: var(--color-text-light);
  cursor: help;
}
</style>
