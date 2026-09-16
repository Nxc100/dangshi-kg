<template>
  <div class="entity-manage">
    <div class="card">
      <div class="toolbar">
        <el-input v-model="query.kw" placeholder="按名称关键词检索" clearable class="kw-input" @keyup.enter="search" />
        <el-select v-model="query.type" placeholder="全部类型" clearable class="type-select">
          <el-option v-for="t in LABELS" :key="t" :label="labelZh(t)" :value="t" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="Plus" @click="openCreate">新增实体</el-button>
      </div>

      <div v-loading="loading">
        <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="load" />
        <EmptyState v-else-if="!list.length && !loading" icon="Collection" text="没有匹配的实体"
          action-text="清空筛选" @action="resetQuery" />

        <el-table v-else :data="list" size="default">
          <el-table-column prop="name" label="名称" min-width="180" />
          <el-table-column label="类型" width="110">
            <template #default="{ row }"><TypeBadge :type="row.type" /></template>
          </el-table-column>
          <el-table-column prop="degree" label="关系数" width="90" />
          <el-table-column label="核心池" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="Number(row.checked) === 1 ? 'success' : 'info'" effect="plain">
                {{ Number(row.checked) === 1 ? '已校验' : '未校验' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="updated_at" label="更新时间" min-width="160" />
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
              <el-button link type="danger" size="small" @click="confirmDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="total > query.size" class="pager">
          <el-pagination layout="total, prev, pager, next" :current-page="query.page" :page-size="query.size"
            :total="total" @current-change="onPageChange" />
        </div>
      </div>
    </div>

    <EntityForm v-model="formVisible" :entity="editing" :submitting="submitting" :errors="formErrors"
      @submit="onSubmit" />
    <ConfirmByName v-model="confirmVisible" :name="deleting ? deleting.name : ''"
      :degree="deleting ? deleting.degree : 0" :submitting="submitting" :error="confirmError"
      @confirm="doDelete" />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import TypeBadge from '@/components/common/TypeBadge.vue'
import EntityForm from '@/components/admin/EntityForm.vue'
import ConfirmByName from '@/components/admin/ConfirmByName.vue'
import { createEntity, deleteEntity, listEntities, updateEntity } from '@/api/adminKg'
import { getEntity } from '@/api/entity'
import { LABELS, labelZh } from '@/utils/ontology'

// 实体管理（FR-A02）：检索 / 分页 / 动态表单新增编辑 / 级联删除强确认；写操作后台留痕、前台即时生效
const HIGH_DEGREE = 20

const list = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const query = reactive({ kw: '', type: '', page: 1, size: 10 })

const formVisible = ref(false)
const editing = ref(null)
const submitting = ref(false)
const formErrors = ref({})

const confirmVisible = ref(false)
const confirmError = ref('')
const deleting = ref(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await listEntities({ ...query })
    list.value = data.list || []
    total.value = data.total || 0
  } catch (err) {
    list.value = []
    error.value = (err && err.msg) || '实体列表加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function search() {
  query.page = 1
  load()
}

function resetQuery() {
  query.kw = ''
  query.type = ''
  search()
}

function onPageChange(p) {
  query.page = p
  load()
}

function openCreate() {
  editing.value = null
  formErrors.value = {}
  formVisible.value = true
}

async function openEdit(row) {
  formErrors.value = {}
  try {
    // 百科接口把 intro / source / alias 从 props 中单独拆出，回填时须合并，否则必填项为空
    const detail = await getEntity(row.name)
    const entity = detail.entity || {}
    const props = { ...(entity.props || {}), name: entity.name || row.name }
    if (detail.intro) props.intro = detail.intro
    if (detail.source) props.source = detail.source
    if (entity.alias && entity.alias.length) props.alias = entity.alias.join('/')
    editing.value = { type: row.type, name: row.name, props, checked: entity.checked ?? row.checked }
  } catch {
    editing.value = { type: row.type, name: row.name, props: { name: row.name }, checked: row.checked }
  }
  formVisible.value = true
}

async function onSubmit(payload) {
  submitting.value = true
  formErrors.value = {}
  try {
    if (editing.value) {
      await updateEntity(payload)
      ElMessage.success('实体已更新')
    } else {
      await createEntity(payload)
      ElMessage.success('实体已新增')
    }
    formVisible.value = false
    load()
  } catch (err) {
    formErrors.value = (err && err.errors) || {}
    // 新增重名：提示并可直接前往编辑
    if (err && err.code === 422 && err.data && err.data.exists_type) {
      try {
        await ElMessageBox.confirm(err.msg || '实体已存在，是否前往编辑？', '实体已存在', {
          type: 'warning',
          confirmButtonText: '前往编辑',
          cancelButtonText: '取消',
        })
        formVisible.value = false
        openEdit({ name: payload.name, type: err.data.exists_type, checked: 0 })
      } catch {
        // 用户取消
      }
    } else if (!err.errors) {
      ElMessage.error((err && err.msg) || '保存失败，请重试')
    }
  } finally {
    submitting.value = false
  }
}

// 规范 6.7：级联删除提示中的关系数必须实时查询，不得使用列表页缓存值
// 删除前实时查询关系数（规范 6.7：不得用列表页缓存值）。
// kw 是包含匹配，同名前缀的实体可能排在前面，故取满页再按主名精确定位。
async function fetchDegree(row) {
  const data = await listEntities({ kw: row.name, type: row.type, page: 1, size: 50 })
  const hit = (data.list || []).find((item) => item.name === row.name)
  if (!hit) throw new Error('实体不存在')
  return Number(hit.degree || 0)
}

async function confirmDelete(row) {
  let degree = Number(row.degree || 0)
  let stale = false
  try {
    degree = await fetchDegree(row)
  } catch {
    stale = true // 实时查询失败时回退到列表值，并在文案中说明
  }
  deleting.value = { ...row, degree, stale }
  // 高连接度实体：输入名称强确认；其余实体：普通二次确认，明确显示级联删除关系数
  if (degree >= HIGH_DEGREE) {
    confirmError.value = ''
    confirmVisible.value = true
    return
  }
  const suffix = stale ? '（关系数取自列表缓存，实时查询失败）' : ''
  try {
    await ElMessageBox.confirm(
      `删除「${row.name}」将级联删除该实体的 ${degree} 条关系${suffix}，操作不可撤销。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  doDelete()
}

async function doDelete(confirmName) {
  submitting.value = true
  confirmError.value = ''
  try {
    const payload = { type: deleting.value.type, name: deleting.value.name }
    if (confirmName) payload.confirm_name = confirmName
    await deleteEntity(payload)
    ElMessage.success('实体已删除')
    confirmVisible.value = false
    if (list.value.length === 1 && query.page > 1) query.page -= 1
    load()
  } catch (err) {
    confirmError.value = (err && err.msg) || '删除失败，请重试'
    if (!confirmVisible.value) ElMessage.error(confirmError.value)
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.kw-input {
  width: 220px;
}
.type-select {
  width: 150px;
}
</style>
