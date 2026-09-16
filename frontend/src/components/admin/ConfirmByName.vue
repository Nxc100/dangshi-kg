<template>
  <el-dialog :model-value="modelValue" title="高风险删除确认" width="480px" @update:model-value="close">
    <el-alert type="error" :closable="false" show-icon class="warn">
      <template #title>
        该实体为高连接度实体，将级联删除 <strong>{{ degree }}</strong> 条关系，操作不可撤销
      </template>
    </el-alert>
    <p class="confirm-tip">
      请输入实体名称 <strong>{{ name }}</strong> 以确认删除：
    </p>
    <el-input v-model="input" placeholder="请输入完整实体名称" clearable @keyup.enter="submit" />
    <p v-if="error" class="confirm-error">{{ error }}</p>

    <template #footer>
      <el-button @click="close(false)">取消</el-button>
      <el-button type="danger" :disabled="input.trim() !== name" :loading="submitting" @click="submit">
        确认删除
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'

// 关系数 ≥ 20 的高连接度实体删除：红色强提示 + 输入实体名与目标一致方可提交（后端同样校验 confirm_name）
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  name: { type: String, default: '' },
  degree: { type: Number, default: 0 },
  submitting: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'confirm'])

const input = ref('')

watch(
  () => props.modelValue,
  (open) => {
    if (open) input.value = ''
  },
)

function close(value = false) {
  emit('update:modelValue', value)
}

function submit() {
  if (input.value.trim() !== props.name) return
  emit('confirm', input.value.trim())
}
</script>

<style scoped>
.warn {
  margin-bottom: 12px;
}
.confirm-tip {
  margin: 0 0 8px;
  color: var(--color-text-secondary);
}
.confirm-error {
  margin: 8px 0 0;
  color: var(--color-danger);
  font-size: 13px;
}
</style>
