<template>
  <el-dialog :model-value="modelValue" title="需要登录" width="380px" append-to-body @update:model-value="close">
    <p class="guide-text">{{ text }}</p>
    <template #footer>
      <el-button @click="close">稍后再说</el-button>
      <el-button type="primary" @click="goLogin">去登录</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'

// 登录引导弹窗：游客点收藏 / 保存成绩时使用；登录成功后按 redirect 回跳原页
defineProps({
  modelValue: { type: Boolean, default: false },
  text: { type: String, default: '登录后可保存成绩并查看历史错题' },
})
const emit = defineEmits(['update:modelValue'])
const route = useRoute()
const router = useRouter()

function close() {
  emit('update:modelValue', false)
}

function goLogin() {
  close()
  router.push({ name: 'login', query: { redirect: route.fullPath } })
}
</script>

<style scoped>
.guide-text {
  margin: 0;
  line-height: 1.8;
  color: var(--color-text-secondary);
}
</style>
