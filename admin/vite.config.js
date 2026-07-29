import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发时把 /api 代理到本机 FastAPI 后端（8000），避免跨域；
// 生产部署时由 nginx 反向代理 /api 到后端，前端无需改动。
// base 用相对路径 './'，保证在 CloudStudio / 子目录 / 任意静态托管下资源不 404。
export default defineConfig({
  plugins: [vue()],
  base: './',
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      // 后端 /static 静态资源（上传的封面图等）同样代理到 8000，开发时 admin 才能预览本地图
      '/static': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
