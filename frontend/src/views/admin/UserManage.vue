<template>
  <div class="user-manage">
    <div class="card">
      <div class="toolbar">
        <el-input v-model="query.kw" placeholder="按用户名 / 昵称检索" clearable class="kw-input" @keyup.enter="search" />
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
      </div>

      <div v-loading="loading">
        <ErrorRetry v-if="error" :message="error" :loading="loading" @retry="load" />
        <EmptyState v-else-if="!list.length && !loading" icon="User" text="没有匹配的用户"
          action-text="清空筛选" @action="resetQuery" />

        <el-table v-else :data="list" size="default">
          <el-table-column prop="username" label="用户名" min-width="140" />
          <el-table-column prop="nickname" label="昵称" min-width="140" />
          <el-table-column label="角色" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.role === 'admin' ? 'danger' : 'info'" effect="plain">
                {{ row.role === 'admin' ? '管理员' : '普通用户' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-switch
                :model-value="Number(row.status) === 1"
                :disabled="isSelf(row) || busyId === row.user_id"
                active-text="启用"
                inactive-text="禁用"
                inline-prompt
                @change="(v) => toggleStatus(row, v)"
              />
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="注册时间" min-width="160" />
          <el-table-column label="操作" width="230">
            <template #default="{ row }">
              <el-button link type="primary" size="small" :disabled="isSelf(row)" @click="resetPassword(row)">
                重置密码
              </el-button>
              <el-button link type="warning" size="small" :disabled="isSelf(row)" @click="toggleRole(row)">
                {{ row.role === 'admin' ? '取消管理员' : '设为管理员' }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="total > query.size" class="pager">
          <el-pagination layout="total, prev, pager, next" :current-page="query.page" :page-size="query.size"
            :total="total" @current-change="onPageChange" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ErrorRetry from '@/components/common/ErrorRetry.vue'
import { listUsers, resetUserPassword, setUserRole, setUserStatus } from '@/api/adminUser'
import { useUserStore } from '@/store/user'

// 用户管理（FR-A05）：禁用 / 启用、重置密码（随机密码仅显示一次）、授予 / 取消管理员；不能操作自己
const userStore = useUserStore()
const list = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const busyId = ref(null)
const query = reactive({ kw: '', page: 1, size: 10 })

function isSelf(row) {
  return Number(row.user_id) === Number(userStore.user_id)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await listUsers({ ...query })
    list.value = data.list || []
    total.value = data.total || 0
  } catch (err) {
    list.value = []
    error.value = (err && err.msg) || '用户列表加载失败，请稍后重试'
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
  search()
}

function onPageChange(p) {
  query.page = p
  load()
}

async function toggleStatus(row, next) {
  const target = next ? 1 : 0
  try {
    await ElMessageBox.confirm(
      target === 0
        ? `禁用「${row.username}」后，该用户下一次请求即被拒绝。`
        : `确定启用「${row.username}」吗？`,
      target === 0 ? '禁用确认' : '启用确认',
      { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  busyId.value = row.user_id
  try {
    await setUserStatus(row.user_id, target)
    ElMessage.success(target === 1 ? '已启用' : '已禁用')
    load()
  } catch (err) {
    ElMessage.error((err && err.msg) || '操作失败，请重试')
  } finally {
    busyId.value = null
  }
}

async function resetPassword(row) {
  try {
    await ElMessageBox.confirm(
      `将为「${row.username}」生成一个随机密码，且仅显示一次，请及时复制发送给用户。`,
      '重置密码',
      { type: 'warning', confirmButtonText: '重置', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    const data = await resetUserPassword(row.user_id)
    // 随机密码仅显示一次，关闭后不可再查
    ElNotification({
      title: `已重置「${row.username}」的密码`,
      message: `新密码：${data.password}（仅显示一次，请复制发送给用户）`,
      type: 'success',
      duration: 0,
    })
  } catch (err) {
    ElMessage.error((err && err.msg) || '重置失败，请重试')
  }
}

async function toggleRole(row) {
  const next = row.role === 'admin' ? 'user' : 'admin'
  try {
    await ElMessageBox.confirm(
      next === 'admin'
        ? `确定将「${row.username}」设为管理员吗？该用户将获得后台全部权限。`
        : `确定取消「${row.username}」的管理员权限吗？`,
      '角色变更',
      { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  try {
    await setUserRole(row.user_id, next)
    ElMessage.success('角色已更新')
    load()
  } catch (err) {
    ElMessage.error((err && err.msg) || '操作失败，请重试')
  }
}

onMounted(load)
</script>

<style scoped>
.kw-input {
  width: 240px;
}
</style>
