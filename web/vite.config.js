import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev:   base='/'      → localhost:3000/
// Build: base='/app/'  → FastAPI servíruje z /app/
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'build' ? '/app/' : '/',
  server: {
    port: 3000,
    proxy: {
      '/api': { target: 'http://localhost:8002', changeOrigin: true },
      '/ws':  { target: 'ws://localhost:8002',  changeOrigin: true, ws: true },
    },
  },
  build: {
    outDir: '../web_dist',
    emptyOutDir: true,
  },
}))
