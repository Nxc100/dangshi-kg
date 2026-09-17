import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'

const SITE_TITLE = '党史学习智能问答系统'

// 前台挂根路径 /，个人中心 /user/*（需登录），后台 /admin/*（需 admin）；三类角色同一工程，路由层级区分
const routes = [
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      { path: '', name: 'home', component: () => import('@/views/Home.vue'), meta: { title: '首页' } },
      { path: 'qa', name: 'qa', component: () => import('@/views/Qa.vue'), meta: { title: '智能问答' } },
      { path: 'graph', name: 'graph', component: () => import('@/views/Graph.vue'), meta: { title: '知识图谱' } },
      { path: 'timeline', name: 'timeline', component: () => import('@/views/Timeline.vue'), meta: { title: '大事记时间轴' } },
      { path: 'entity/:name', name: 'entity', component: () => import('@/views/Entity.vue'), props: true, meta: { title: '词条' } },
      { path: 'entity-not-found', name: 'entityNotFound', component: () => import('@/views/EntityNotFound.vue'), meta: { title: '未找到词条' } },
      { path: 'quiz', name: 'quiz', component: () => import('@/views/Quiz.vue'), meta: { title: '知识测验' } },
      { path: 'login', name: 'login', component: () => import('@/views/Login.vue'), meta: { title: '登录 / 注册' } },
      {
        path: 'user',
        component: () => import('@/layouts/UserCenterLayout.vue'),
        meta: { requiresAuth: true },
        redirect: '/user/profile',
        children: [
          { path: 'profile', name: 'userProfile', component: () => import('@/views/user/Profile.vue'), meta: { title: '我的资料' } },
          { path: 'security', name: 'userSecurity', component: () => import('@/views/user/Security.vue'), meta: { title: '账号安全' } },
          { path: 'history', name: 'userHistory', component: () => import('@/views/user/History.vue'), meta: { title: '提问历史' } },
          { path: 'favorites', name: 'userFavorites', component: () => import('@/views/user/Favorites.vue'), meta: { title: '收藏夹' } },
          { path: 'quiz-records', name: 'userQuizRecords', component: () => import('@/views/user/QuizRecords.vue'), meta: { title: '测验记录' } },
        ],
      },
    ],
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    redirect: '/admin/overview',
    children: [
      { path: 'overview', name: 'adminOverview', component: () => import('@/views/admin/Overview.vue'), meta: { title: '总览' } },
      { path: 'entities', name: 'adminEntities', component: () => import('@/views/admin/EntityManage.vue'), meta: { title: '知识管理 - 实体' } },
      { path: 'triples', name: 'adminTriples', component: () => import('@/views/admin/TripleManage.vue'), meta: { title: '知识管理 - 关系' } },
      { path: 'oplog', name: 'adminOpLog', component: () => import('@/views/admin/OpLog.vue'), meta: { title: '操作日志' } },
      { path: 'users', name: 'adminUsers', component: () => import('@/views/admin/UserManage.vue'), meta: { title: '用户管理' } },
      { path: 'qalog', name: 'adminQaLog', component: () => import('@/views/admin/QaLog.vue'), meta: { title: '问答日志' } },
      { path: 'stats', name: 'adminStats', component: () => import('@/views/admin/Stats.vue'), meta: { title: '热点统计' } },
      { path: 'llm', name: 'adminLlm', component: () => import('@/views/admin/LlmConfig.vue'), meta: { title: 'AI 增强' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

// 守卫优先级：must_change_pwd（最高）> requiresAuth > requiresAdmin；/login 与词条 404 页不受守卫拦截
router.beforeEach((to) => {
  const userStore = useUserStore()

  if (userStore.isLogin && Number(userStore.must_change_pwd) === 1) {
    if (to.name === 'userSecurity' || to.name === 'login') return true
    ElMessage.warning('请先修改初始密码')
    return { name: 'userSecurity' }
  }

  if (to.name === 'login' || to.name === 'entityNotFound') return true

  if (to.matched.some((r) => r.meta.requiresAuth) && !userStore.isLogin) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.matched.some((r) => r.meta.requiresAdmin) && !userStore.isAdmin) {
    ElMessage.error('无权限访问')
    return { name: 'home' }
  }

  return true
})

router.afterEach((to) => {
  document.title = to.meta && to.meta.title ? `${to.meta.title} - ${SITE_TITLE}` : SITE_TITLE
})

export default router
