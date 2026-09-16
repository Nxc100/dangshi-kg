<template>
  <div class="chat-bubble" :class="role">
    <el-avatar v-if="role === 'system'" :size="32" class="bubble-avatar system-avatar">
      <el-icon><ChatDotRound /></el-icon>
    </el-avatar>
    <div class="bubble-wrap">
      <p v-if="hint" class="bubble-hint">{{ hint }}</p>
      <div class="bubble-body">
        <div v-if="loading" class="bubble-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>{{ loadingText }}</span>
        </div>
        <slot v-else />
      </div>
    </div>
    <el-avatar v-if="role === 'user'" :size="32" :src="avatar" class="bubble-avatar" />
  </div>
</template>

<script setup>
// 问答气泡容器：用户右 / 系统左，支持加载态与气泡上方浅色提示（如"已按…为你查询"）
defineProps({
  role: { type: String, default: 'system' }, // user | system
  loading: { type: Boolean, default: false },
  loadingText: { type: String, default: '正在查询知识图谱…' },
  hint: { type: String, default: '' },
  avatar: { type: String, default: '' },
})
</script>

<style scoped>
.chat-bubble {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  align-items: flex-start;
}
.chat-bubble.user {
  flex-direction: row;
  justify-content: flex-end;
}
.bubble-avatar {
  flex-shrink: 0;
}
.system-avatar {
  background: var(--color-primary);
  color: #fff;
}
.bubble-wrap {
  max-width: 78%;
}
.chat-bubble.user .bubble-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.bubble-hint {
  margin: 0 0 4px;
  font-size: 12px;
  color: var(--color-text-light);
}
.bubble-body {
  padding: 12px 14px;
  border-radius: var(--radius);
  background: var(--color-card);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  line-height: 1.8;
  word-break: break-word;
}
.chat-bubble.user .bubble-body {
  background: var(--color-primary);
  color: #fff;
}
.bubble-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-secondary);
}
</style>
