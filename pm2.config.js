/* PM2 process configuration for Astinus backend and React frontend (dev) */

// === 端口配置 (只需修改这里) ===
const BACKEND_PORT = 8000;
const FRONTEND_PORT = 5173;

module.exports = {
  apps: [
    {
      name: "astinus-backend",
      cwd: "src/backend",
      script: "npx",
      args: ["tsx", "watch", "src/index.ts"],
      env: {
        NODE_ENV: "development",
        PORT: String(BACKEND_PORT),
      },
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      restart_delay: 2000,
      out_file: "../../logs/backend.log",
      error_file: "../../logs/backend.log",
    },
    {
      name: "astinus-frontend",
      cwd: "src/web",
      script: "npm",
      args: ["run", "dev", "--", "--host", "--port", String(FRONTEND_PORT)],
      env: {
        NODE_ENV: "development",
        PORT: String(FRONTEND_PORT),
        // Vite 会自动读取 VITE_ 前缀的环境变量
        VITE_BACKEND_PORT: String(BACKEND_PORT),
      },
      autorestart: true,
      watch: false,
      max_memory_restart: "512M",
      restart_delay: 2000,
      out_file: "../../logs/frontend.log",
      error_file: "../../logs/frontend.log",
    },
  ],
};
