import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // maplibre-gl spins up a Web Worker via a relative import.meta.url; Vite's dep
  // pre-bundling moves the file and breaks that URL, so leave it unbundled.
  optimizeDeps: {
    exclude: ['maplibre-gl'],
  },
  server: {
    proxy: {
      // FastAPI (api/main.py) runs separately via uvicorn on :8010 during dev
      // (8000 is held by Docker Desktop's backend on this machine).
      '/api': 'http://127.0.0.1:8010',
    },
  },
})
