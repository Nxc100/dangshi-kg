<template>
  <div class="question-card card">
    <div class="question-head">
      <span class="question-index">第 {{ index + 1 }} 题</span>
      <TypeBadge v-if="question.entity" :type="question.entity.type" />
    </div>
    <p class="question-text">{{ question.question }}</p>

    <div class="option-list">
      <button
        v-for="opt in question.options"
        :key="opt.key"
        class="option-item"
        :class="optionClass(opt.key)"
        :disabled="answered"
        @click="choose(opt.key)"
      >
        <span class="option-key">{{ opt.key }}</span>
        <span class="option-text">{{ opt.text }}</span>
        <el-icon v-if="answered && opt.key === question.answer_key" class="option-icon"><Select /></el-icon>
        <el-icon v-else-if="answered && opt.key === chosen" class="option-icon"><CloseBold /></el-icon>
      </button>
    </div>

    <div v-if="answered" class="explanation">
      <p class="explanation-text">
        <strong>{{ correct ? '回答正确' : '回答错误' }}：</strong>{{ question.explanation }}
      </p>
      <router-link
        v-if="question.entity"
        class="review-link"
        :to="{ name: 'entity', params: { name: question.entity.name } }"
      >
        去百科页复习「{{ question.entity.name }}」
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import TypeBadge from '@/components/common/TypeBadge.vue'

// 单题卡：点选即判分，选项标绿（对）/ 标红（错，同时标出正确项），下方展开解析（即图谱事实）+ 百科复习链接
const props = defineProps({
  question: { type: Object, required: true }, // {id, question, options, answer_key, explanation, entity, template}
  index: { type: Number, default: 0 },
  chosen: { type: String, default: '' },
})
const emit = defineEmits(['choose'])

const answered = computed(() => !!props.chosen)
const correct = computed(() => props.chosen === props.question.answer_key)

function choose(key) {
  if (answered.value) return
  emit('choose', { id: props.question.id, key })
}

function optionClass(key) {
  if (!answered.value) return ''
  if (key === props.question.answer_key) return 'is-correct'
  if (key === props.chosen) return 'is-wrong'
  return 'is-muted'
}
</script>

<style scoped>
.question-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.question-index {
  font-size: 12px;
  color: var(--color-text-light);
}
.question-text {
  margin: 0 0 12px;
  font-size: 15px;
  line-height: 1.8;
}
.option-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.option-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 12px;
  font: inherit;
  text-align: left;
  color: var(--color-text);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  cursor: pointer;
}
.option-item:not(:disabled):hover {
  border-color: var(--color-primary);
}
.option-item:disabled {
  cursor: default;
}
.option-key {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  line-height: 22px;
  text-align: center;
  border-radius: 50%;
  background: var(--color-bg-gray);
  font-size: 12px;
}
.option-text {
  flex: 1;
}
.option-item.is-correct {
  border-color: var(--color-success);
  background: rgba(103, 194, 58, 0.12);
}
.option-item.is-wrong {
  border-color: var(--color-danger);
  background: rgba(245, 108, 108, 0.12);
}
.option-item.is-muted {
  opacity: 0.6;
}
.option-icon {
  flex-shrink: 0;
}
.explanation {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--color-border);
  line-height: 1.8;
}
.explanation-text {
  margin: 0 0 4px;
  color: var(--color-text-secondary);
}
.review-link {
  font-size: 13px;
}
</style>
