import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

const backend = 'http://127.0.0.1:5000';

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: 'dist',
  },
  server: {
    proxy: {
      '/ui-api': backend,
      '/api': backend,
      '/admin': backend,
      '/pwa': backend,
      '/apidocs': backend,
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});
