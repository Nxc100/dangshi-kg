<template>
  <el-dialog
    :model-value="modelValue"
    :title="isEdit ? '编辑实体' : '新增实体'"
    width="620px"
    @update:model-value="close"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" label-position="right">
      <!-- 先选类型，表单按 ontology 属性定义动态渲染该类型字段（切换类型即重建字段） -->
      <el-form-item label="实体类型" prop="type" required :error="errors.type">
        <el-select v-model="form.type" :disabled="isEdit" placeholder="请选择实体类型" @change="onTypeChange">
          <el-option v-for="t in LABELS" :key="t" :label="labelZh(t)" :value="t" />
        </el-select>
      </el-form-item>

      <template v-if="form.type">
        <el-form-item
          v-for="p in fields"
          :key="p.name"
          :label="p.zh"
          :prop="`props.${p.name}`"
          :required="p.required"
          :error="errors[p.name]"
        >
          <el-select v-if="p.kind === 'enum'" v-model="form.props[p.name]" clearable :placeholder="`请选择${p.zh}`">
            <el-option v-for="opt in p.enum" :key="opt" :label="opt" :value="opt" />
          </el-select>
          <el-input
            v-else-if="p.kind === 'longtext'"
            v-model="form.props[p.name]"
            type="textarea"
            :rows="3"
            :placeholder="`请输入${p.zh}`"
          />
          <el-input
            v-else-if="p.kind === 'number'"
            v-model="form.props[p.name]"
            :placeholder="`请输入${p.zh}（整数）`"
          />
          <el-input
            v-else
            v-model="form.props[p.name]"
            :placeholder="p.kind === 'time' ? '如：1935 年 1 月 15 日至 17 日' : `请输入${p.zh}`"
          />
          <div v-if="p.kind === 'time'" class="field-tip">时间排序键与精度由后端按原文自动派生</div>
        </el-form-item>

        <el-form-item v-if="isEdit" label="已校验">
          <el-switch v-model="form.checked" :active-value="1" :inactive-value="0" />
          <span class="field-tip">仅已校验（核心池）实体参与测验出题与每日推荐</span>
        </el-form-item>
      </template>
    </el-form>

    <template #footer>
      <el-button @click="close(false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { LABELS, formProps, labelZh } from '@/utils/ontology'

// 实体表单（按类型动态渲染，必填标星）；字段定义、枚举值域、必填项一律取自 ontology.js
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  entity: { type: Object, default: null }, // 编辑时回填 {type, name, props, checked}
  submitting: { type: Boolean, default: false },
  errors: { type: Object, default: () => ({}) }, // 后端 422 的 data.errors
})
const emit = defineEmits(['update:modelValue', 'submit'])

const formRef = ref(null)
const form = reactive({ type: '', props: {}, checked: 0 })

const isEdit = computed(() => !!props.entity)
const fields = computed(() => (form.type ? formProps(form.type) : []))

// 实时校验规则：必填项与整数类型均按 ontology 定义生成，与后端 validate_entity_props 口径一致
const rules = computed(() => {
  const out = { type: [{ required: true, message: '请选择实体类型', trigger: 'change' }] }
  fields.value.forEach((p) => {
    const item = []
    if (p.required) item.push({ required: true, message: `${p.zh}为必填项`, trigger: 'blur' })
    if (p.kind === 'number') {
      item.push({
        validator: (_rule, value, callback) =>
          !value || /^-?\d+$/.test(String(value).trim())
            ? callback()
            : callback(new Error(`${p.zh}必须为整数`)),
        trigger: 'blur',
      })
    }
    if (item.length) out[`props.${p.name}`] = item
  })
  return out
})

function resetProps(type, values = {}) {
  form.props = {}
  formProps(type || '').forEach((p) => {
    form.props[p.name] = values[p.name] !== undefined && values[p.name] !== null ? String(values[p.name]) : ''
  })
}

function onTypeChange(type) {
  resetProps(type)
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    if (props.entity) {
      form.type = props.entity.type
      form.checked = Number(props.entity.checked || 0)
      resetProps(props.entity.type, props.entity.props || {})
      if (props.entity.name) form.props.name = props.entity.name
    } else {
      form.type = ''
      form.checked = 0
      form.props = {}
    }
  },
)

function close(value = false) {
  emit('update:modelValue', value)
}

async function submit() {
  if (formRef.value) {
    const valid = await formRef.value.validate().catch(() => false)
    if (!valid) return
  }
  // 编辑：name 传实体当前名（后端据此 MATCH），新名留在 props.name；新增：name 即表单填写的名称
  const payload = {
    type: form.type,
    name: isEdit.value ? props.entity.name : (form.props.name || '').trim(),
    props: {},
  }
  fields.value.forEach((p) => {
    const v = form.props[p.name]
    if (v !== undefined && v !== null && String(v).trim() !== '') payload.props[p.name] = String(v).trim()
  })
  if (isEdit.value) payload.checked = form.checked
  emit('submit', payload)
}
</script>

<style scoped>
.field-tip {
  font-size: 12px;
  color: var(--color-text-light);
  line-height: 1.6;
}
</style>
