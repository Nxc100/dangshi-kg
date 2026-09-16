<template>
  <div class="score-panel card">
    <div class="score-head">
      <div class="score-value">
        <span class="score-num">{{ score }}</span>
        <span class="score-total">/ {{ total }}</span>
      </div>
      <div class="score-meta">
        <p>用时 {{ durationText }}</p>
        <p class="text-light">{{ comment }}</p>
      </div>
    </div>

    <div class="review-list">
      <div v-for="(item, i) in review" :key="i" class="review-item" :class="{ wrong: !item.correct }">
        <span class="review-index">{{ i + 1 }}</span>
        <span class="review-text">{{ item.question }}</span>
        <el-tag size="small" :type="item.correct ? 'success' : 'danger'" effect="plain">
          {{ item.correct ? '正确' : '错误' }}
        </el-tag>
      </div>
    </div>

    <div class="score-actions">
      <el-button type="primary" :loading="saving" :disabled="saved" @click="emit('save')">
        {{ saved ? '成绩已保存' : '保存成绩' }}
      </el-button>
      <el-button @click="emit('restart')">再来一组</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

// 成绩页：得分 / 用时 / 逐题回顾 + "保存成绩"（游客触发登录引导，成绩暂存前端不丢失）/ "再来一组"
const props = defineProps({
  score: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  durationSec: { type: Number, default: 0 },
  review: { type: Array, default: () => [] }, // [{question, correct}]
  saving: { type: Boolean, default: false },
  saved: { type: Boolean, default: false },
})
const emit = defineEmits(['save', 'restart'])

const durationText = computed(() => {
  const s = Math.max(0, Math.round(props.durationSec))
  return s < 60 ? `${s} 秒` : `${Math.floor(s / 60)} 分 ${s % 60} 秒`
})

const comment = computed(() => {
  if (!props.total) return ''
  const rate = props.score / props.total
  if (rate === 1) return '全部答对，党史知识掌握扎实。'
  if (rate >= 0.6) return '答得不错，错题可前往百科页复习。'
  return '再接再厉，建议结合时间轴与百科页系统学习。'
})
</script>

<style scoped>
.score-head {
  display: flex;
  align-items: center;
  gap: 20px;
  padding-bottom: 12px;
  border-bottom: 1px dashed var(--color-border);
}
.score-value {
  color: var(--color-primary);
}
.score-num {
  font-size: 40px;
  font-weight: 700;
}
.score-total {
  font-size: 16px;
  margin-left: 4px;
}
.score-meta p {
  margin: 0 0 4px;
}
.review-list {
  margin: 12px 0;
}
.review-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--color-border);
}
.review-item.wrong .review-text {
  color: var(--color-danger);
}
.review-index {
  flex-shrink: 0;
  width: 20px;
  color: var(--color-text-light);
  font-size: 12px;
}
.review-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.score-actions {
  display: flex;
  gap: 8px;
}
</style>
