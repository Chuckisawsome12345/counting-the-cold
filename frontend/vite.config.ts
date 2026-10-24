import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Local dev: the FastAPI backend on :8000 serves /api.
    proxy: { '/api': 'http://localhost:8000' },
  },
})
