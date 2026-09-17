<template>
  <div class="main-layout">
    <header class="main-header">
      <div class="header-inner">
        <router-link to="/" class="brand">
          <img :src="logo" class="brand-logo" alt="logo" />
          <span class="brand-name">党史学习智能问答系统</span>
        </router-link>

        <el-menu mode="horizontal" :default-active="activeMenu" router :ellipsis="false" class="nav-menu">
          <el-menu-item index="/">首页</el-menu-item>
          <el-menu-item index="/qa">智能问答</el-menu-item>
          <el-menu-item index="/graph">知识图谱</el-menu-item>
          <el-menu-item index="/timeline">大事记时间轴</el-menu-item>
          <el-menu-item index="/quiz">知识测验</el-menu-item>
        </el-menu>

        <div class="header-right">
          <el-button v-if="!userStore.isLogin" type="primary" plain size="small" @click="goLogin">登录 / 注册</el-button>
          <el-dropdown v-else trigger="click" @command="onCommand">
            <span class="user-entry">
              <el-avatar :size="32" :src="avatarSrc" />
              <span class="nickname">{{ userStore.nickname || userStore.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="user">个人中心</el-dropdown-item>
                <el-dropdown-item v-if="userStore.isAdmin" command="admin">后台管理</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </header>

    <main class="main-body">
      <router-view />
    </main>

    <SiteFooter />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'
import SiteFooter from '@/components/common/SiteFooter.vue'
import logo from '@/assets/logo.svg'
import defaultAvatar from '@/assets/default_avatar.svg'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const NAV_PATHS = ['/', '/qa', '/graph', '/timeline', '/quiz']
const activeMenu = computed(() => (NAV_PATHS.includes(route.path) ? route.path : ''))
const avatarSrc = computed(() => userStore.avatar_url || defaultAvatar)

function goLogin() {
  router.push({ name: 'login', query: { redirect: route.fullPath } })
}

function onCommand(cmd) {
  if (cmd === 'user') router.push('/user/profile')
  else if (cmd === 'admin') router.push('/admin')
  else if (cmd === 'logout') {
    userStore.logout()
    ElMessage.success('已退出登录')
    router.push('/')
  }
}
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
/* 吸顶导航：正规站点的基本盘——长页面（时间轴、问答流）滚动时导航始终可达 */
.main-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  height: var(--header-height);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: saturate(180%) blur(12px);
  border-bottom: 2px solid var(--color-primary);
  box-shadow: var(--shadow-sm);
}
.header-inner {
  max-width: var(--page-max);
  height: 100%;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  align-items: center;
  gap: 24px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-primary);
  font-weight: 700;
  font-size: 18px;
  white-space: nowrap;
}
.brand-logo {
  width: 32px;
  height: 32px;
}
.nav-menu {
  flex: 1;
  border-bottom: none;
  height: var(--header-height);
}
.header-right {
  display: flex;
  align-items: center;
}
.user-entry {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--color-text);
}
.nickname {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.main-body {
  flex: 1;
  min-width: 0; /* 防止长实体名（整句事件名）把 flex 容器撑出横向滚动条 */
}
.nav-menu :deep(.el-menu-item) {
  font-size: 15px;
}
@media (max-width: 992px) {
  .brand-name {
    display: none;
  }
}
</style>
