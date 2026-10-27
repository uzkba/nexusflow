import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    dedupe: ['react', 'react-dom', 'react-router-dom'],
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom'],
  },
  server: {
    host: true, 
    proxy: {
      '/api': {
        // Aponta para o nome do serviço do FastAPI no docker-compose
        target: 'http://backend:8000', 
        changeOrigin: true,
        secure: false,
      }
    }
  }
})