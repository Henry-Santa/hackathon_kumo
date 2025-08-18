import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Remove proxy for production deployment
  },
  preview: {
    port: 5173,
    host: '0.0.0.0',
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      'healthcheck.railway.app', // Allow Railway healthchecks
      '.railway.app', // Allow all Railway domains
    ],
  },
});


