module.exports = {
  apps: [
    {
      name: "astinus-backend-ts",
      cwd: "src/backend-ts",
      script: "npm",
      args: ["run", "dev"],
      env: {
        NODE_ENV: "development",
        PORT: "3000",
      },
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      restart_delay: 2000,
      out_file: "logs/backend-ts.log",
      error_file: "logs/backend-ts-error.log",
    },
  ],
};
