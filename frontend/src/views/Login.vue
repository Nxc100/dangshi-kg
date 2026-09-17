<template>
  <div class="login-page">
    <!-- 左：品牌区 + 知识图谱氛围背景；右：表单。窄屏下品牌区自动隐藏 -->
    <aside class="login-brand">
      <GraphBackdrop />
      <div class="brand-inner">
        <div class="brand-head">
          <img :src="logo" class="brand-logo" alt="logo" />
          <span class="brand-name">党史学习智能问答系统</span>
        </div>
        <h2 class="brand-slogan">让每一个答案<br />都能回到它的出处</h2>
        <p class="brand-desc">
          基于 Neo4j 知识图谱的党史学习平台。答案由图谱事实经模板生成，
          零编造、可溯源；图谱之外的问题回落权威原文段落，并标注章节出处。
        </p>
        <ul class="brand-points">
          <li v-for="p in BRAND_POINTS" :key="p">{{ p }}</li>
        </ul>
        <div class="brand-stat">
          <span><b>{{ LABELS.length }}</b> 类实体</span>
          <span><b>{{ RELATIONS.length }}</b> 类关系</span>
          <span><b>{{ PERIODS.length }}</b> 个历史时期</span>
        </div>
      </div>
    </aside>

    <div class="login-form-side">
      <div class="login-card">
        <div class="login-head">
          <h1 class="login-title">{{ tab === 'login' ? '欢迎回来' : '创建账号' }}</h1>
          <p class="login-sub">
            {{ tab === 'login' ? '登录后可保存提问历史、收藏词条与测验成绩' : '注册后自动登录，无需重复输入' }}
          </p>
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

        <p class="login-guest">
          暂不登录也可以
          <router-link to="/qa">直接提问</router-link>、
          <router-link to="/graph">浏览图谱</router-link>、
          <router-link to="/quiz">试做测验</router-link>
        </p>
      </div>
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
import GraphBackdrop from '@/components/graph/GraphBackdrop.vue'
import { LABELS, PERIODS, RELATIONS } from '@/utils/ontology'
import logo from '@/assets/logo.svg'

const BRAND_POINTS = [
  '自然语言提问，答案标注来源出处',
  '实体关系网络可视化，支持逐跳探索',
  '七个历史时期贯通 1921—2021 大事记',
  '自动出题即时判分，错题一键复习',
]

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
/* 左右分栏：左品牌区（含图谱氛围背景）+ 右表单区。
   高度扣掉吸顶导航，使整屏沉浸而不出现内层滚动条 */
.login-page {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  min-height: calc(100vh - var(--header-height));
}

/* ---------- 左：品牌区 ---------- */
.login-brand {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  background: var(--gradient-primary);
  color: #fff;
}
.brand-inner {
  position: relative; /* 压在 GraphBackdrop 之上 */
  z-index: 1;
  width: 100%;
  max-width: 520px;
  margin-left: auto;
  padding: 56px 48px;
}
.brand-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 36px;
}
.brand-logo {
  width: 34px;
  height: 34px;
}
.brand-name {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.brand-slogan {
  margin: 0 0 18px;
  font-size: 34px;
  line-height: 1.45;
  letter-spacing: 1px;
}
.brand-desc {
  margin: 0 0 26px;
  font-size: 14px;
  line-height: 2;
  color: rgba(255, 255, 255, 0.85);
}
.brand-points {
  margin: 0 0 32px;
  padding: 0;
  list-style: none;
}
.brand-points li {
  position: relative;
  padding-left: 22px;
  margin-bottom: 10px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
}
.brand-points li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 7px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-gold);
}
.brand-stat {
  display: flex;
  gap: 28px;
  padding-top: 22px;
  border-top: 1px solid rgba(255, 255, 255, 0.18);
}
.brand-stat span {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
}
.brand-stat b {
  display: block;
  font-size: 22px;
  color: var(--color-gold);
  line-height: 1.5;
}

/* ---------- 右：表单区 ---------- */
.login-form-side {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background: var(--color-card);
}
.login-card {
  width: 100%;
  max-width: 380px;
}
.login-head {
  margin-bottom: 18px;
}
.login-title {
  margin: 0 0 6px;
  font-size: 24px;
  color: var(--color-text);
}
.login-sub {
  margin: 0;
  font-size: 13px;
  line-height: 1.8;
  color: var(--color-text-light);
}
.submit-btn {
  width: 100%;
  margin-top: 4px;
}
.login-guest {
  margin: 20px 0 0;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
  font-size: 13px;
  color: var(--color-text-light);
  text-align: center;
}

/* 窄屏：品牌区整体隐藏，表单居中，避免挤成两条窄栏 */
@media (max-width: 992px) {
  .login-page {
    grid-template-columns: 1fr;
  }
  .login-brand {
    display: none;
  }
  .login-form-side {
    justify-content: center;
    padding: 32px 20px;
  }
}
</style>
