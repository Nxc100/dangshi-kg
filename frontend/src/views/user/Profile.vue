<template>
  <div class="profile" v-loading="loading">
    <h2 class="sub-title">我的资料</h2>

    <div class="profile-body">
      <AvatarUpload v-model="avatarUrl" @uploaded="onAvatarUploaded" />

      <el-descriptions :column="1" border class="profile-desc">
        <el-descriptions-item label="用户名">
          <span>{{ profile.username }}</span>
          <el-tag v-if="profile.role === 'admin'" size="small" type="danger" class="role-tag">管理员</el-tag>
        </el-descriptions-item>

        <el-descriptions-item label="昵称">
          <template v-if="!editing">
            <span>{{ profile.nickname || profile.username }}</span>
            <el-button link type="primary" :icon="Edit" class="edit-btn" @click="startEdit">编辑</el-button>
          </template>
          <div v-else class="nickname-edit">
            <el-input v-model="nickname" maxlength="16" show-word-limit placeholder="1–16 个字符" class="nickname-input" />
            <el-button type="primary" size="small" :loading="saving" @click="saveNickname">保存</el-button>
            <el-button size="small" @click="editing = false">取消</el-button>
          </div>
          <p v-if="nicknameError" class="field-error">{{ nicknameError }}</p>
        </el-descriptions-item>

        <el-descriptions-item label="注册时间">{{ profile.created_at || '—' }}</el-descriptions-item>
      </el-descriptions>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Edit } from '@element-plus/icons-vue'
import AvatarUpload from '@/components/common/AvatarUpload.vue'
import { getProfile, updateProfile } from '@/api/user'
import { useUserStore } from '@/store/user'
import { isValidNickname, normalizeNickname, pickFieldErrors } from '@/utils/validators'

// 我的资料（FR-U01 / FR-U02）：头像上传 + 昵称行内编辑 + 用户名只读 + 注册时间
const userStore = useUserStore()

const profile = reactive({ username: '', nickname: '', role: '', created_at: '' })
const avatarUrl = ref('')
const nickname = ref('')
const nicknameError = ref('')
const editing = ref(false)
const loading = ref(false)
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await getProfile()
    Object.assign(profile, data)
    avatarUrl.value = data.avatar_url || ''
    nickname.value = data.nickname || data.username
    userStore.setUser(data)
  } catch {
    ElMessage.error('资料加载失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function startEdit() {
  nickname.value = profile.nickname || profile.username
  nicknameError.value = ''
  editing.value = true
}

async function saveNickname() {
  const value = normalizeNickname(nickname.value)
  if (!isValidNickname(value)) {
    nicknameError.value = '昵称为 1–16 个字符'
    return
  }
  saving.value = true
  nicknameError.value = ''
  try {
    const data = await updateProfile({ nickname: value })
    Object.assign(profile, data)
    userStore.setUser(data) // 以接口返回值更新全站显示（导航栏即时同步）
    editing.value = false
    ElMessage.success('昵称已更新')
  } catch (err) {
    const errors = pickFieldErrors(err, ['nickname'])
    nicknameError.value = errors.nickname || (err && err.msg) || '保存失败，请重试'
  } finally {
    saving.value = false
  }
}

function onAvatarUploaded(url) {
  userStore.setUser({ avatar_url: url })
}

onMounted(load)
</script>

<style scoped>
.sub-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
}
.profile-body {
  display: flex;
  gap: 28px;
  flex-wrap: wrap;
  align-items: flex-start;
}
.profile-desc {
  flex: 1;
  min-width: 280px;
}
.role-tag {
  margin-left: 8px;
}
.edit-btn {
  margin-left: 10px;
}
.nickname-edit {
  display: flex;
  gap: 8px;
  align-items: center;
}
.nickname-input {
  max-width: 240px;
}
.field-error {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-danger);
}
</style>
