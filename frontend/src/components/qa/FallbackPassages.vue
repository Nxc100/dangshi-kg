<template>
  <div class="fallback-passages">
    <template v-if="passages.length">
      <div class="fallback-header">
        <el-icon><Document /></el-icon>
        <span>以下为权威资料原文节选，供学习参考</span>
      </div>
      <div v-for="(p, i) in passages" :key="i" class="passage-card">
        <p class="passage-text">{{ p.text }}</p>
        <div class="passage-meta">
          <span>出处：{{ p.chapter || '权威资料' }}</span>
          <a v-if="p.source" :href="p.source" target="_blank" rel="noopener">查看原文</a>
        </div>
      </div>
    </template>

    <template v-else>
      <p class="guide-text">{{ guideText }}</p>
      <CandidateChips tip="可以试试这些问题：" :items="examples" @pick="(q) => emit('ask', q)" />
    </template>
  </div>
</template>

<script setup>
import CandidateChips from '@/components/qa/CandidateChips.vue'
import { EXAMPLE_QUESTIONS } from '@/components/qa/ExampleQuestions.vue'

// F9 兜底段落展示：固定顶栏文案 + 段落卡（正文 + 章节出处 + source 链接）；
// 无相关段落时显示引导语 + 3 条示例问句（取自全站唯一的示例问句常量）
defineProps({
  passages: { type: Array, default: () => [] }, // [{text, chapter, source, score}]
  guideText: { type: String, default: '抱歉，暂未找到相关资料。您可以换个问法，或试试下面的示例问题。' },
  examples: { type: Array, default: () => EXAMPLE_QUESTIONS.slice(0, 3) },
})
const emit = defineEmits(['ask'])
</script>

<style scoped>
.fallback-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  margin-bottom: 10px;
  font-size: 13px;
  color: var(--color-primary-dark);
  background: var(--color-primary-lighter);
  border-radius: 4px;
}
.passage-card {
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  margin-bottom: 8px;
  background: var(--color-bg);
}
.passage-text {
  margin: 0 0 6px;
  line-height: 1.8;
}
.passage-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-light);
}
.guide-text {
  margin: 0 0 10px;
  color: var(--color-text-secondary);
}
</style>
