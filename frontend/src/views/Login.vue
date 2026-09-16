<template>
  <div class="page login-page">
    <div class="card login-card">
      <div class="login-head">
        <img :src="logo" class="login-logo" alt="logo" />
        <h1 class="login-title">党史学习智能问答系统</h1>
      </div>

      <el-tabs v-model="tab" stretch>
        <el-tab-pane label="登录" name="login">
          <el-form ref="loginRef" :model="loginForm" :rules="loginRules" label-position="top" @keyup.enter="doLogin">
            <el-form-item label="用户名" prop="username" :error="loginErrors.username">
              <el-input v-model="loginForm.username" placeholder="请输入用户名" clearable />
            </el-form-item>
            <el-form-item label="密码" prop="password" :error="loginErrors.password">
              <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" show-password />
            </el-form-item>
            <el-button type="primary" class="submit-btn" :loading="submitting" @click="doLogin">登录</el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-form ref="registerRef" :model="registerForm" :rules="registerRules" label-position="top">
            <el-form-item label="用户名" prop="username" :error="usernameTaken || registerErrors.username">
              <el-input v-model="registerForm.username" placeholder="3–20 位字母、数字或下划线" clearable
                @blur="checkName" />
            </el-form-item>
            <el-form-item label="密码" prop="password" :error="registerErrors.password">
              <el-input v-model="registerForm.password" type="password" placeholder="8–20 位，需含字母与数字"
                show-password />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirm_password">
              <el-input v-model="registerForm.confirm_password" type="password" placeholder="请再次输入密码"
                show-password />
            </el-form-item>
            <el-button type="primary" class="submit-btn" :loading="submitting" @click="doRegister">
              注册并登录
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { checkUsername, login, register } from '@/api/auth'
import { useUserStore } from '@/store/user'
import { confirmPasswordRules, passwordRules, pickFieldErrors, usernameRules } from '@/utils/validators'
import logo from '@/assets/logo.svg'

// 登录 / 注册页（FR-G07 / FR-G08）：注册成功后自动登录并按 redirect 回跳；三角色共用同一登录页
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const tab = ref('login')
const submitting = ref(false)
const usernameTaken = ref('')

const loginRef = ref(null)
const registerRef = ref(null)
const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', password: '', confirm_password: '' })
const loginErrors = reactive({ username: '', password: '' })
const registerErrors = reactive({ username: '', password: '' })

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}
const registerRules = {
  username: usernameRules,
  password: passwordRules,
  confirm_password: confirmPasswordRules(() => registerForm.password),
}

function clearErrors(target) {
  Object.keys(target).forEach((k) => (target[k] = ''))
}

// 用户名失焦唯一性预检，重名即时红字提示
async function checkName() {
  usernameTaken.value = ''
  const name = registerForm.username.trim()
  if (!name) return
  try {
    const data = await checkUsername(name)
    if (data && data.available === false) usernameTaken.value = '该用户名已被占用'
  } catch {
    // 预检失败不阻断注册，后端会复校
  }
}

function afterAuth(data) {
  userStore.login(data)
  const redirect = route.query.redirect
  if (data.user && Number(data.user.must_change_pwd) === 1) {
    ElMessage.warning('请先修改初始密码')
    router.replace('/user/security')
    return
  }
  router.replace(redirect ? String(redirect) : '/')
}

async function doLogin() {
  clearErrors(loginErrors)
  const valid = await loginRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const data = await login({ username: loginForm.username.trim(), password: loginForm.password })
    ElMessage.success('登录成功')
    afterAuth(data)
  } catch (err) {
    Object.assign(loginErrors, pickFieldErrors(err, ['username', 'password']))
    if (!err.errors) ElMessage.error((err && err.msg) || '用户名或密码错误')
  } finally {
    submitting.value = false
  }
}

async function doRegister() {
  clearErrors(registerErrors)
  const valid = await registerRef.value.validate().catch(() => false)
  if (!valid || usernameTaken.value) return
  submitting.value = true
  try {
    const data = await register({
      username: registerForm.username.trim(),
      password: registerForm.password,
      confirm_password: registerForm.confirm_password,
    })
    ElMessage.success('注册成功')
    afterAuth(data)
  } catch (err) {
    Object.assign(registerErrors, pickFieldErrors(err, ['username', 'password', 'confirm_password']))
    if (!err.errors) ElMessage.error((err && err.msg) || '注册失败，请重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.login-card {
  max-width: 420px;
  margin: 48px auto;
  padding: 28px 28px 20px;
}
.login-head {
  text-align: center;
  margin-bottom: 12px;
}
.login-logo {
  width: 44px;
  height: 44px;
}
.login-title {
  margin: 8px 0 0;
  font-size: 18px;
  color: var(--color-primary);
}
.submit-btn {
  width: 100%;
  margin-top: 4px;
}
</style>
