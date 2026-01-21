import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// 从环境变量读取后端端口，默认 8000
const backendPort = process.env.VITE_BACKEND_PORT || "8000";
const backendUrl = `http://localhost:${backendPort}`;

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: backendUrl,
        changeOrigin: true,
      },
      "/ws": {
        target: backendUrl,
        ws: true,
        changeOrigin: true,
        rewrite: (path) => path,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    css: true,
    setupFiles: ["./src/setupTests.ts"],
    coverage: {
      reporter: ["text", "json", "html"],
    },
  },
});
