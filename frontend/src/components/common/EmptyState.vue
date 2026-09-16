<template>
  <div class="empty-state">
    <el-icon class="empty-icon" :size="48"><component :is="icon" /></el-icon>
    <p class="empty-text">{{ text }}</p>
    <el-button v-if="actionText" type="primary" plain size="small" @click="$emit('action')">{{ actionText }}</el-button>
  </div>
</template>

<script setup>
// 空状态：Icon + 引导文案 + 操作按钮（开发规范 1.2）
defineProps({
  icon: { type: String, default: 'Box' },
  text: { type: String, default: '暂无数据' },
  actionText: { type: String, default: '' },
})
defineEmits(['action'])
</script>

<style scoped>
.empty-state {
  padding: 40px 16px;
  text-align: center;
  color: var(--color-text-light);
}
.empty-icon {
  color: var(--color-border);
}
.empty-text {
  margin: 12px 0 16px;
}
</style>
