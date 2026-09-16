import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useUserStore } from '@/store/user'

// 统一返回体 {code, msg, data}：code 0 成功；401 / 403 / 404 / 422 / 500（HTTP 状态码与 code 同步）
const service = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

service.interceptors.request.use((config) => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  return config
})

function buildError(code, msg, data) {
  return { code, msg, data: data || null, errors: (data && data.errors) || null }
}

function handle401() {
  const userStore = useUserStore()
  userStore.logout()
  const current = router.currentRoute.value
  if (current.name !== 'login') {
    ElMessage.warning('登录已过期，请重新登录')
    router.push({ name: 'login', query: { redirect: current.fullPath } })
  }
}

service.interceptors.response.use(
  (response) => {
    // CSV 导出等二进制响应直接返回
    if (response.config.responseType === 'blob') return response.data
    const body = response.data
    if (body && body.code === 0) return body.data
    // 理论上不会出现（后端 HTTP 状态码与 code 同步），兜底按错误处理
    const code = body && body.code !== undefined ? body.code : 500
    return Promise.reject(buildError(code, (body && body.msg) || '请求失败', body && body.data))
  },
  (error) => {
    const resp = error.response
    if (!resp) {
      ElMessage.error('服务暂时不可用，请稍后重试')
      return Promise.reject(buildError(-1, '网络异常，请检查后端服务是否已启动', null))
    }
    const body = resp.data && typeof resp.data === 'object' ? resp.data : {}
    const code = body.code !== undefined ? body.code : resp.status
    const msg = body.msg || '请求失败'
    switch (code) {
      case 401:
        handle401()
        break
      case 403:
        ElMessage.error('无权限访问')
        router.push({ name: 'home' })
        break
      case 404:
      case 422:
        // 页面自行处理：404 走友好页面；422 逐字段显示 data.errors 或 msg
        break
      default:
        ElMessage.error('服务暂时不可用，请稍后重试')
    }
    return Promise.reject(buildError(code, msg, body.data))
  },
)

export default service
