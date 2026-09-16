<template>
  <el-container class="admin-layout">
    <el-aside :width="collapsed ? '64px' : '220px'" class="admin-aside">
      <div class="admin-brand" @click="collapsed = !collapsed">
        <el-icon :size="20"><Menu /></el-icon>
        <span v-show="!collapsed">后台管理</span>
      </div>
      <el-menu :default-active="route.path" router :collapse="collapsed" :collapse-transition="false" class="admin-menu">
        <el-menu-item index="/admin/overview"><el-icon><DataBoard /></el-icon><template #title>总览</template></el-menu-item>
        <el-menu-item index="/admin/entities"><el-icon><Collection /></el-icon><template #title>知识管理 - 实体</template></el-menu-item>
        <el-menu-item index="/admin/triples"><el-icon><Share /></el-icon><template #title>知识管理 - 关系</template></el-menu-item>
        <el-menu-item index="/admin/oplog"><el-icon><Tickets /></el-icon><template #title>操作日志</template></el-menu-item>
        <el-menu-item index="/admin/users"><el-icon><User /></el-icon><template #title>用户管理</template></el-menu-item>
        <el-menu-item index="/admin/qalog"><el-icon><ChatLineSquare /></el-icon><template #title>问答日志</template></el-menu-item>
        <el-menu-item index="/admin/stats"><el-icon><TrendCharts /></el-icon><template #title>热点统计</template></el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ path: '/admin/overview' }">后台管理</el-breadcrumb-item>
          <el-breadcrumb-item>{{ route.meta.title }}</el-breadcrumb-item>
        </el-breadcrumb>
        <div class="admin-header-right">
          <el-avatar :size="28" :src="avatarSrc" />
          <span class="nickname">{{ userStore.nickname || userStore.username }}</span>
          <el-button link @click="router.push('/')">返回前台</el-button>
          <el-button link type="danger" @click="logout">退出登录</el-button>
        </div>
      </el-header>
      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'
import defaultAvatar from '@/assets/default_avatar.svg'

// 后台布局：左侧深色折叠菜单 + 顶部面包屑 / 头像昵称 / 返回前台 / 退出登录；路由 /admin/* 需 admin
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const collapsed = ref(false)
const avatarSrc = computed(() => userStore.avatar_url || defaultAvatar)

function logout() {
  userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/')
}
</script>

<style scoped>
.admin-layout {
  min-height: 100vh;
  background: var(--admin-body-bg);
}
.admin-aside {
  background: var(--admin-menu-bg);
  transition: width 0.2s;
  overflow-x: hidden;
}
.admin-brand {
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.admin-menu {
  border-right: none;
  --el-menu-bg-color: var(--admin-menu-bg);
  --el-menu-text-color: var(--admin-menu-text);
  --el-menu-hover-bg-color: var(--admin-menu-hover);
  --el-menu-active-color: #ffffff;
}
.admin-menu :deep(.el-menu-item.is-active) {
  background: var(--admin-menu-active);
}
.admin-header {
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--admin-header-bg);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.admin-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.nickname {
  color: var(--color-text-secondary);
}
.admin-main {
  padding: 16px;
}
</style>
