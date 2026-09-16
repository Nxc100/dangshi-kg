import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

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
      '/api': { target: 'http://127.0.0.1:5000', changeOrigin: true },
      '/static': { target: 'http://127.0.0.1:5000', changeOrigin: true },
    },
  },
  build: {
    chunkSizeWarningLimit: 1500,
  },
})
