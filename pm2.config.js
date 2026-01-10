/* PM2 process configuration for Astinus backend and React frontend (dev) */
module.exports = {
  apps: [
    {
      name: "astinus-backend",
      cwd: ".",
      script: "uv",
      args: [
        "run",
        "uvicorn",
        "src.backend.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--log-level",
        "info",
      ],
      env: {
        PYTHONUNBUFFERED: "1",
        UVICORN_WORKERS: "1",
      },
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      restart_delay: 2000,
      out_file: "logs/backend.log",
      error_file: "logs/backend.log",
    },
    {
      name: "astinus-frontend",
      cwd: "src/web",
      script: "npm",
      args: ["run", "dev", "--", "--host", "--port", "5173"],
      env: {
        NODE_ENV: "development",
        PORT: "5173",
      },
      autorestart: true,
      watch: false,
      max_memory_restart: "512M",
      restart_delay: 2000,
      out_file: "logs/frontend.log",
      error_file: "logs/frontend.log",
    },
  ],
};
