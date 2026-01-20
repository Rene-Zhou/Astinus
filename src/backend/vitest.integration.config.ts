import { defineConfig } from "vitest/config";

/**
 * 集成测试配置
 *
 * 用于运行需要真实服务（如向量数据库、嵌入模型）的测试
 * 不使用全局 mock
 */
export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    include: ["tests/services/**/*.test.ts"],
    exclude: ["node_modules", "dist"],
    // 不使用 setupFiles，避免全局 mock
    // setupFiles: ['./tests/setup.ts'],
    testTimeout: 300000, // 5 分钟超时，因为需要下载模型
    hookTimeout: 300000,
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      include: ["src/**/*.ts"],
      exclude: ["src/**/*.test.ts", "src/index.ts"],
    },
  },
  resolve: {
    alias: {
      "@": "/src",
    },
  },
});
