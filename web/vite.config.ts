/// <reference types="vitest" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    css: false,
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'https://diademissa.com.br',
        changeOrigin: true,
        secure: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (_req, req) => {
            console.log(`[proxy] → ${req.method} ${req.url}`)
          })
          proxy.on('proxyRes', (proxyRes, req) => {
            console.log(`[proxy] ← ${proxyRes.statusCode} ${req.method} ${req.url}`)
          })
        },
      },
      '/missa': {
        target: 'https://diademissa.com.br',
        changeOrigin: true,
        secure: true,
        configure: (proxy) => {
          proxy.on('proxyReq', (_req, req) => {
            console.log(`[proxy] → ${req.method} ${req.url}`)
          })
          proxy.on('proxyRes', (proxyRes, req) => {
            console.log(`[proxy] ← ${proxyRes.statusCode} ${req.method} ${req.url}`)
          })
        },
      },
    },
  },
  build: { outDir: 'dist', sourcemap: false },
})
