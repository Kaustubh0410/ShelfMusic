import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api to the backend container so the frontend
// can call the API without hardcoding the backend host. In production the
// built static files are served by nginx, which proxies /api (see nginx.conf).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://backend:8000",
        changeOrigin: true,
      },
    },
  },
});
