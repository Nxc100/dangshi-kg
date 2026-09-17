<template>
  <el-dialog :model-value="modelValue" title="新增关系" width="620px" @update:model-value="close">
    <el-form :model="form" label-width="110px">
      <!-- 三级联动：头实体联想 → 关系类型仅列出与头类型匹配项 → 尾实体联想仅列出允许类型 -->
      <el-form-item label="头实体" required :error="errors.head">
        <el-autocomplete
          v-model="form.head"
          :fetch-suggestions="searchHead"
          placeholder="输入实体名，需从下拉中选中已有实体"
          clearable
          class="full"
          @select="onHeadSelect"
          @clear="onHeadClear"
        >
          <template #default="{ item }">
            <span>{{ item.name }}</span><TypeBadge :type="item.type" class="opt-badge" />
          </template>
        </el-autocomplete>
        <div class="field-tip">
          已选类型：<span v-if="form.head_type">{{ labelZh(form.head_type) }}</span><span v-else>未选择</span>
        </div>
      </el-form-item>

      <el-form-item label="关系类型" required :error="errors.rel">
        <el-select
          v-model="form.rel"
          :disabled="!form.head_type"
          :placeholder="form.head_type ? '请选择关系类型' : '请先选择头实体'"
          @change="onRelChange"
        >
          <el-option v-for="r in relOptions" :key="r" :label="`${relationZh(r)}（${r}）`" :value="r" />
        </el-select>
      </el-form-item>

      <el-form-item label="尾实体" required :error="errors.tail">
        <el-autocomplete
          v-model="form.tail"
          :fetch-suggestions="searchTail"
          :disabled="!form.rel"
          :placeholder="form.rel ? '输入实体名，需从下拉中选中已有实体' : '请先选择关系类型'"
          clearable
          class="full"
          @select="onTailSelect"
        >
          <template #default="{ item }">
            <span>{{ item.name }}</span><TypeBadge :type="item.type" class="opt-badge" />
          </template>
        </el-autocomplete>
        <div class="field-tip">
          允许的尾实体类型：{{ tailTypes.map(labelZh).join(' / ') || '—' }}
        </div>
      </el-form-item>

      <el-form-item
        v-for="p in relProps"
        :key="p.name"
        :label="p.zh"
        :required="p.required"
        :error="errors[p.name]"
      >
        <el-input v-model="form.props[p.name]" :placeholder="`请输入${p.zh}`" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="close(false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import TypeBadge from '@/components/common/TypeBadge.vue'
import { searchEntities } from '@/api/graph'
import { RELATION_PROPS, allowedRelations, allowedTails, labelZh, relationZh } from '@/utils/ontology'

// 三元组表单：头尾类型约束与关系属性全部取自 ontology.js（与后端复校使用同一份数据）
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  submitting: { type: Boolean, default: false },
  errors: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:modelValue', 'submit'])

const form = reactive({ head: '', head_type: '', rel: '', tail: '', tail_type: '', props: {} })
// 记录下拉中实际选中的实体名，用于识别"选完又手改文本"从而使已选类型失效
const selectedHead = ref('')
const selectedTail = ref('')

const relOptions = computed(() => (form.head_type ? allowedRelations(form.head_type) : []))
const tailTypes = computed(() => (form.head_type && form.rel ? allowedTails(form.head_type, form.rel) : []))
const relProps = computed(() => (form.rel ? RELATION_PROPS[form.rel] || [] : []))

async function suggest(kw, cb, types) {
  const keyword = String(kw || '').trim()
  if (!keyword) return cb([])
  try {
    const list = await searchEntities(keyword)
    const filtered = types && types.length ? list.filter((i) => types.includes(i.type)) : list
    cb(filtered.map((i) => ({ ...i, value: i.name })))
  } catch {
    cb([])
  }
}

const searchHead = (kw, cb) => suggest(kw, cb, null)
const searchTail = (kw, cb) => suggest(kw, cb, tailTypes.value)

function onHeadSelect(item) {
  form.head = item.name
  form.head_type = item.type
  selectedHead.value = item.name
  form.rel = ''
  form.tail = ''
  form.tail_type = ''
  selectedTail.value = ''
  form.props = {}
}

function onHeadClear() {
  form.head_type = ''
  form.rel = ''
  form.tail = ''
  form.tail_type = ''
  selectedHead.value = ''
  selectedTail.value = ''
}

function onRelChange() {
  form.tail = ''
  form.tail_type = ''
  form.props = {}
  ;(RELATION_PROPS[form.rel] || []).forEach((p) => (form.props[p.name] = ''))
}

function onTailSelect(item) {
  form.tail = item.name
  form.tail_type = item.type
  selectedTail.value = item.name
}

// 选中后再手改输入框文本，已选类型即失效：清空类型并断开后续联动，避免带着旧类型提交
watch(
  () => form.head,
  (value) => {
    if (form.head_type && value !== selectedHead.value) onHeadClear()
  },
)

watch(
  () => form.tail,
  (value) => {
    if (form.tail_type && value !== selectedTail.value) form.tail_type = ''
  },
)

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      Object.assign(form, { head: '', head_type: '', rel: '', tail: '', tail_type: '', props: {} })
      selectedHead.value = ''
      selectedTail.value = ''
    }
  },
)

function close(value = false) {
  emit('update:modelValue', value)
}

function submit() {
  const payload = {
    head: form.head.trim(),
    head_type: form.head_type,
    rel: form.rel,
    tail: form.tail.trim(),
    tail_type: form.tail_type,
    props: {},
  }
  ;(RELATION_PROPS[form.rel] || []).forEach((p) => {
    const v = form.props[p.name]
    if (v !== undefined && String(v).trim() !== '') payload.props[p.name] = String(v).trim()
  })
  emit('submit', payload)
}
</script>

<style scoped>
.full {
  width: 100%;
}
.opt-badge {
  margin-left: 6px;
}
.field-tip {
  font-size: 12px;
  color: var(--color-text-light);
  line-height: 1.6;
}
</style>
