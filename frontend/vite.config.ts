import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

// Dev 时 Vite proxy 把 /api 转发到后端 FastAPI（默认 http://localhost:8000）。
// 后端已在 CONTRACT.md §8 中配置 CORS 允许 localhost:5173；dev 经 proxy 可绕过同源限制。
// 生产构建产物可直接由后端静态托管，/api 由后端提供。
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
