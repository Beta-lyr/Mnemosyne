import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        ws: true,
      },
      '/uploads': 'http://localhost:8080',
    },
  },
  build: {
    outDir: 'dist',
  },
})
