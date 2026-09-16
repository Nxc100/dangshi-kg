<template>
  <div class="page user-center">
    <el-row :gutter="16">
      <el-col :xs="24" :md="5">
        <el-menu :default-active="route.path" router class="side-menu card">
          <el-menu-item index="/user/profile"><el-icon><User /></el-icon><span>我的资料</span></el-menu-item>
          <el-menu-item index="/user/security"><el-icon><Lock /></el-icon><span>账号安全</span></el-menu-item>
          <el-menu-item index="/user/history"><el-icon><ChatDotRound /></el-icon><span>提问历史</span></el-menu-item>
          <el-menu-item index="/user/favorites"><el-icon><Star /></el-icon><span>收藏夹</span></el-menu-item>
          <el-menu-item index="/user/quiz-records"><el-icon><Tickets /></el-icon><span>测验记录</span></el-menu-item>
        </el-menu>
      </el-col>
      <el-col :xs="24" :md="19">
        <div class="card content">
          <router-view />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'

// 个人中心布局：左侧五页签（资料 / 安全 / 历史 / 收藏 / 测验记录），路由 /user/* 需登录
const route = useRoute()
</script>

<style scoped>
.side-menu {
  padding: 0;
  border-right: none;
  overflow: hidden;
}
.content {
  min-height: 480px;
}
@media (max-width: 992px) {
  .side-menu {
    margin-bottom: 12px;
  }
}
</style>
