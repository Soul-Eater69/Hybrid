/**
 * Vite Configuration
 * ==================
 *
 * Configuration for the Vite build tool.
 *
 * HOW IT WORKS:
 *   - Vite is a modern build tool for frontend development
 *   - It provides fast HMR (Hot Module Replacement) in development
 *   - Builds optimized bundles for production
 *
 * PROXY CONFIGURATION:
 *   The proxy setting forwards API requests to the FastAPI backend
 *   during development, avoiding CORS issues.
 *
 *   Frontend (localhost:5173) --> Proxy --> Backend (localhost:8000)
 */

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API requests to FastAPI backend
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
