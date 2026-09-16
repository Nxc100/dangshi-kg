<template>
  <div class="triple-manage">
    <div class="card">
      <div class="toolbar">
        <el-input v-model="query.head" placeholder="头实体" clearable class="s-input" @keyup.enter="search" />
        <el-select v-model="query.rel" placeholder="全部关系" clearable class="s-select">
          <el-option v-for="r in RELATIONS" :key="r" :label="`${relationZh(r)}（${r}）`" :value="r" />
        </el-select>
        <el-input v-model="query.tail" placeholder="尾实体" clearable class="s-input" @keyup.enter="search" />
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="Plus" @click="formVisible = true">新增关系</el-button>
      </div>

      <div v-loading="loading">
        <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="load" />
        <EmptyState v-else-if="!list.length && !loading" icon="Share" text="没有匹配的关系"
          action-text="清空筛选" @action="resetQuery" />

        <el-table v-else :data="list" size="default">
          <el-table-column label="头实体" min-width="160">
            <template #default="{ row }">
              {{ row.head }}<TypeBadge :type="row.head_type" class="cell-badge" />
            </template>
          </el-table-column>
          <el-table-column label="关系" width="150">
            <template #default="{ row }">
              <el-tag size="small" effect="plain">{{ row.label || relationZh(row.rel) }}</el-tag>
              <span v-if="row.props && row.props.position" class="rel-prop">{{ row.props.position }}</span>
            </template>
          </el-table-column>
          <el-table-column label="尾实体" min-width="160">
            <template #default="{ row }">
              {{ row.tail }}<TypeBadge :type="row.tail_type" class="cell-badge" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90">
            <template #default="{ row }">
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

    <TripleForm v-model="formVisible" :submitting="submitting" :errors="formErrors" @submit="onSubmit" />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import TypeBadge from '@/components/common/TypeBadge.vue'
import TripleForm from '@/components/admin/TripleForm.vue'
import { createTriple, deleteTriple, listTriples } from '@/api/adminKg'
import { RELATIONS, relationZh } from '@/utils/ontology'

// 关系管理（FR-A03）：三级联动新增（头尾类型约束）+ 删除；新增 / 删除后前台百科标签、图谱边、问答三处同步
const list = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const query = reactive({ head: '', tail: '', rel: '', page: 1, size: 10 })

const formVisible = ref(false)
const submitting = ref(false)
const formErrors = ref({})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await listTriples({ ...query })
    list.value = data.list || []
    total.value = data.total || 0
  } catch (err) {
    list.value = []
    error.value = (err && err.msg) || '关系列表加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

function search() {
  query.page = 1
  load()
}

function resetQuery() {
  query.head = ''
  query.tail = ''
  query.rel = ''
  search()
}

function onPageChange(p) {
  query.page = p
  load()
}

async function onSubmit(payload) {
  submitting.value = true
  formErrors.value = {}
  try {
    await createTriple(payload)
    ElMessage.success('关系已新增')
    formVisible.value = false
    load()
  } catch (err) {
    formErrors.value = (err && err.errors) || {}
    if (!err.errors) ElMessage.error((err && err.msg) || '保存失败，请重试')
  } finally {
    submitting.value = false
  }
}

async function confirmDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除关系「${row.head} —${row.label || relationZh(row.rel)}→ ${row.tail}」吗？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await deleteTriple({
      head: row.head,
      head_type: row.head_type,
      rel: row.rel,
      tail: row.tail,
      tail_type: row.tail_type,
    })
    ElMessage.success('关系已删除')
    if (list.value.length === 1 && query.page > 1) query.page -= 1
    load()
  } catch (err) {
    ElMessage.error((err && err.msg) || '删除失败，请重试')
  }
}

onMounted(load)
</script>

<style scoped>
.s-input {
  width: 160px;
}
.s-select {
  width: 180px;
}
.cell-badge {
  margin-left: 6px;
}
.rel-prop {
  margin-left: 6px;
  font-size: 12px;
  color: var(--color-text-light);
}
</style>
