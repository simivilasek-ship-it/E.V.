import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': { target: 'http://localhost:8002', changeOrigin: true },
      '/ws':  { target: 'ws://localhost:8002',  changeOrigin: true, ws: true },
    },
  },
  base: '/app/',
  build: {
    outDir: '../web_dist',
    emptyOutDir: true,
  },
})
