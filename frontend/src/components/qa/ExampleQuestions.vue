<template>
  <div class="example-questions">
    <p v-if="title" class="example-title">{{ title }}</p>
    <div class="example-list">
      <el-button
        v-for="q in questions"
        :key="q"
        class="example-item"
        size="small"
        plain
        @click="emit('pick', q)"
      >
        {{ q }}
      </el-button>
    </div>
  </div>
</template>

<script>
// 冷启动 8 条示例问句（覆盖八大类问句形态）：首页与问答页共用同一份常量
// 具名引入：import { EXAMPLE_QUESTIONS } from '@/components/qa/ExampleQuestions.vue'
export const EXAMPLE_QUESTIONS = [
  '遵义会议是什么时候召开的？',
  '中共一大在哪里召开？',
  '古田会议的主要内容是什么？',
  '遵义会议有什么历史意义？',
  '秋收起义是谁领导的？',
  '哪些人参加了中共一大？',
  '《论持久战》的作者是谁？',
  '土地革命战争时期有哪些重大事件？',
]
</script>

<script setup>
// 点击即发送 / 直达问答页
defineProps({
  title: { type: String, default: '试试这样问：' },
  questions: { type: Array, default: () => EXAMPLE_QUESTIONS },
})
const emit = defineEmits(['pick'])
</script>

<style scoped>
.example-title {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.example-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.example-item {
  max-width: 100%;
}
</style>
