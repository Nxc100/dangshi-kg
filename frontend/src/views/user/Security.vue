<template>
  <div class="security">
    <h2 class="sub-title">账号安全</h2>

    <el-alert v-if="mustChange" type="warning" :closable="false" show-icon class="alert"
      title="请先修改初始密码" description="为保证账号安全，修改密码后方可使用系统其他功能。" />

    <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" class="security-form">
      <el-form-item label="原密码" prop="old_password" :error="errors.old_password">
        <el-input v-model="form.old_password" type="password" placeholder="请输入原密码" show-password />
      </el-form-item>
      <el-form-item label="新密码" prop="new_password" :error="errors.new_password">
        <el-input v-model="form.new_password" type="password" placeholder="8–20 位，需含字母与数字" show-password />
      </el-form-item>
      <el-form-item label="确认新密码" prop="confirm_password">
        <el-input v-model="form.confirm_password" type="password" placeholder="请再次输入新密码" show-password />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="submitting" @click="submit">修改密码</el-button>
      </el-form-item>
    </el-form>

    <p class="tip text-light">修改成功后需要重新登录；密码全程加盐哈希存储，系统不保存明文。</p>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { changePassword } from '@/api/user'
import { useUserStore } from '@/store/user'
import { confirmPasswordRules, passwordRules, pickFieldErrors } from '@/utils/validators'

// 修改密码（FR-U03）：成功后强制重新登录；must_change_pwd=1 时本页是唯一可达页
const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const submitting = ref(false)
const form = reactive({ old_password: '', new_password: '', confirm_password: '' })
const errors = reactive({ old_password: '', new_password: '' })

const mustChange = computed(() => Number(userStore.must_change_pwd) === 1)

const rules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    ...passwordRules,
    {
      validator: (_r, value, cb) =>
        value && value === form.old_password ? cb(new Error('新密码不能与原密码相同')) : cb(),
      trigger: 'blur',
    },
  ],
  confirm_password: confirmPasswordRules(() => form.new_password),
}

async function submit() {
  errors.old_password = ''
  errors.new_password = ''
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await changePassword({ ...form })
    ElMessage.success('密码已修改，请重新登录')
    userStore.logout()
    router.replace({ name: 'login' })
  } catch (err) {
    Object.assign(errors, pickFieldErrors(err, ['old_password', 'new_password', 'confirm_password']))
    if (!err.errors) ElMessage.error((err && err.msg) || '修改失败，请重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.sub-title {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
}
.alert {
  margin-bottom: 16px;
}
.security-form {
  max-width: 460px;
}
.tip {
  font-size: 12px;
}
</style>
