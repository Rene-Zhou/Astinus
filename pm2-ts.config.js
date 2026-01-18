module.exports = {
  apps: [
    {
      name: "astinus-backend-ts",
      cwd: "src/backend-ts",
      script: "node",
      args: ["node_modules/.bin/tsx", "watch", "src/index.ts"],
      env: {
        NODE_ENV: "development",
        PORT: "8000",
      },
      autorestart: true,
      watch: true,
      max_memory_restart: "1G",
      restart_delay: 2000,
      out_file: "logs/backend-ts.log",
      error_file: "logs/backend-ts-error.log",
    },
  ],
};
