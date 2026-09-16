<template>
  <div class="error-retry">
    <el-icon class="error-icon" :size="40"><WarningFilled /></el-icon>
    <p class="error-text">{{ message }}</p>
    <el-button type="primary" size="small" :loading="loading" @click="$emit('retry')">重试</el-button>
  </div>
</template>

<script setup>
// 错误态：提示 + "重试"按钮（开发规范 1.2）
defineProps({
  message: { type: String, default: '加载失败，请稍后重试' },
  loading: { type: Boolean, default: false },
})
defineEmits(['retry'])
</script>

<style scoped>
.error-retry {
  padding: 40px 16px;
  text-align: center;
  color: var(--color-text-secondary);
}
.error-icon {
  color: var(--color-warning);
}
.error-text {
  margin: 12px 0 16px;
}
</style>
