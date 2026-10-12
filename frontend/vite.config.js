import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In Docker the backend is reachable as http://backend:8000;
// outside Docker it is http://localhost:8000.
const apiTarget = process.env.API_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: { '/api': apiTarget },
  },
})
