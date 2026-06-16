import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  // 打包输出到 项目根目录/dist
  server: {
    // 代理配置：将 /api 开头的请求转发到后端
    proxy: {
      '/api': {
        target: 'http://localhost:8000', // 后端 FastAPI 服务地址
        changeOrigin: true, // 跨域时修改 Origin 头
        // rewrite: (path) => path.replace(/^\/api/, ''), // 若后端接口不带 /api 则开启，你的后端带 /api 所以注释
      }
    }
  }
})