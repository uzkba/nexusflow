/// <reference types="vitest" />
import { defineConfig } from 'vitest/config' 
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
    host: true,        // Permite acesso de fora do contêiner Docker
    port: 5173,        // Força o Vite a rodar exatamente nesta porta
    strictPort: true,  // Derruba o servidor se a 5173 estiver ocupada, em vez de pular para 5174
    proxy: {
      '/api': {
        target: 'http://backend:8000', 
        changeOrigin: true,
        secure: false,
      }
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    exclude: ['node_modules', 'tests/**'], // Ignora a pasta de E2E
  }
})