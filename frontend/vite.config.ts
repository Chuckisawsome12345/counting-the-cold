import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Local dev: the FastAPI backend on :8000 serves /api.
    proxy: { '/api': 'http://localhost:8000' },
  },
  build: {
    rolldownOptions: {
      output: {
        // The map and chart libraries are most of the bundle; separate files load in parallel and cache across deploys.
        codeSplitting: {
          groups: [
            { name: 'leaflet', test: /node_modules[\\/](leaflet|react-leaflet|@react-leaflet)[\\/]/ },
            { name: 'charts', test: /node_modules[\\/](recharts|d3-[^\\/]+|victory-vendor|es-toolkit|@reduxjs|redux|reselect|immer)[\\/]/ },
            { name: 'react', test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/ },
          ],
        },
      },
    },
  },
})
