/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } },
  },
  build: {
    target: 'es2020',
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          query: ['@tanstack/react-query'],
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    env: { VITE_FEATURE_ROUTING: '1', VITE_FEATURE_HEATMAP: '1' },
    include: ['tests/unit/**/*.test.ts?(x)', 'tests/component/**/*.test.ts?(x)'],
    coverage: {
      provider: 'v8',
      include: ['src/api/**', 'src/state/**', 'src/components/**', 'src/lib/**'],
      reporter: ['text-summary'],
    },
  },
});
