import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import http from 'node:http'
import { fileURLToPath, URL } from 'node:url'

// 代理连接策略：Werkzeug 开发服务器对每个响应都无条件回 Connection: close，而 Node 的
// http agent 默认 keepAlive=true。这里让两端行为一致——agent 不保活 + 转发请求显式带
// Connection: close，避免连接池里留下不可复用的陈旧连接。
//
// error 回调必须保留：开发期曾偶发 502「服务暂时不可用」，靠这条日志才拿到真实错误码
// （connect ETIMEDOUT，即建连阶段就超时），据此确认是本机回环连接的偶发抖动——浏览器到
// Vite 这一跳同样会 ERR_CONNECTION_TIMED_OUT——而非接口或代理配置问题。详见开发规范
// 「修复记录 · 2026-09-17」。注意 Vite 自身的 error 处理先于此回调注册并直接回 502，
// 故此处只做记录，不在代理层重试。
const noKeepAlive = new http.Agent({ keepAlive: false })
const apiProxy = {
  target: 'http://127.0.0.1:5000',
  changeOrigin: true,
  agent: noKeepAlive,
  configure: (proxy) => {
    proxy.on('proxyReq', (proxyReq) => {
      if (!proxyReq.headersSent) proxyReq.setHeader('Connection', 'close')
    })
    proxy.on('error', (err, req) => {
      console.log('[proxy error]', req && req.url, err && err.code, err && err.message)
    })
  },
}

// 固定端口 5173（V3 2.5）；strictPort=false：端口被占用时自动顺延，便于本机多项目并行调试
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: false,
    proxy: {
      '/api': apiProxy,
      '/static': apiProxy,
    },
  },
  build: {
    chunkSizeWarningLimit: 1500,
  },
})
