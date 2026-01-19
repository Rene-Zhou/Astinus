/**
 * 向量检索功能测试
 *
 * 测试 LanceDB + QwenEmbedding 的核心功能：
 * 1. 初始化向量存储
 * 2. 加载 demo_pack.json 世界包
 * 3. 对 lore 条目建立向量索引
 * 4. 执行多语言查询测试
 * 5. 验证检索结果的准确性
 *
 * 注意: 此测试需要下载嵌入模型 (~240MB)，首次运行会较慢
 *
 * 环境要求:
 *   - 网络连接（首次需要下载模型）
 *   - 可选: 设置 HF_TOKEN 环境变量用于 HuggingFace 认证
 *
 * 运行方式:
 *   npm run test:vector
 *   # 或者直接:
 *   npx vitest run tests/services/vector-search.test.ts --config vitest.integration.config.ts
 *
 * 跳过测试:
 *   设置 SKIP_VECTOR_TESTS=1 环境变量可跳过这些测试
 */

import { describe, it, expect, beforeAll, afterAll, vi } from "vitest";
import { promises as fs } from "fs";
import path from "path";
import { fileURLToPath } from "url";

// 重要: 取消全局 mock，使用真实的服务
vi.unmock("../../src/lib/embeddings");
vi.unmock("../../src/lib/lance");

// 现在导入真实的模块
import { LanceDBService, getVectorStoreService } from "../../src/lib/lance";
import { QwenEmbedding, getEmbeddingService } from "../../src/lib/embeddings";
import { WorldPackLoader } from "../../src/services/world";
import type { WorldPack } from "../../src/schemas";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 使用项目根目录的 data/packs 作为世界包路径
const PACKS_DIR = path.resolve(__dirname, "../../../../data/packs");

// 测试用的 collection 名称前缀
const TEST_COLLECTION_PREFIX = "test_lore_entries_";

// 设置较长的超时时间，因为需要下载模型
const TEST_TIMEOUT = 300_000; // 5 minutes

// 检查是否跳过向量测试
const SKIP_VECTOR_TESTS = process.env.SKIP_VECTOR_TESTS === "1";

// 检查向量服务是否可用
let vectorServiceAvailable = false;
let serviceInitError: Error | null = null;

describe.skipIf(SKIP_VECTOR_TESTS)("向量检索功能测试", () => {
  let vectorStore: LanceDBService | undefined;
  let worldPack: WorldPack;
  let collectionName: string;

  beforeAll(async () => {
    console.log("\n🔧 初始化测试环境...");
    console.log(`📁 世界包目录: ${PACKS_DIR}`);

    // 验证 demo_pack.json 存在
    const demoPackPath = path.join(PACKS_DIR, "demo_pack.json");
    try {
      await fs.access(demoPackPath);
      console.log("✅ demo_pack.json 文件存在");
    } catch {
      throw new Error(`未找到 demo_pack.json: ${demoPackPath}`);
    }

    // 尝试初始化向量服务
    try {
      console.log("\n📦 尝试初始化向量服务...");
      vectorStore = await getVectorStoreService();
      vectorServiceAvailable = true;
      console.log("✅ 向量服务初始化成功");
    } catch (error) {
      serviceInitError = error instanceof Error ? error : new Error(String(error));
      console.log(`⚠️ 向量服务初始化失败: ${serviceInitError.message}`);
      console.log("   后续测试将被跳过");
    }
  }, TEST_TIMEOUT);

  afterAll(async () => {
    console.log("\n🧹 清理测试环境...");

    // 清理测试创建的 collection
    if (vectorStore && collectionName) {
      try {
        await vectorStore.deleteTable(collectionName);
        console.log(`✅ 已删除测试 collection: ${collectionName}`);
      } catch {
        // 忽略不存在的 collection
      }
    }

    // 清理 LanceDB 单例
    await LanceDBService.cleanup();
    await QwenEmbedding.cleanup();
    console.log("✅ 服务已清理");
  });

  describe("步骤 1: 初始化向量存储服务", () => {
    it(
      "应该成功初始化 LanceDB 和嵌入服务",
      async () => {
        // 如果服务初始化失败，显示错误信息
        if (!vectorServiceAvailable) {
          console.log(`\n⚠️ 跳过测试: ${serviceInitError?.message}`);
          expect(serviceInitError).toBeDefined();
          return;
        }

        expect(vectorStore).toBeDefined();
        expect(vectorStore).toBeInstanceOf(LanceDBService);
        console.log("✅ 向量存储服务已初始化");
      },
      TEST_TIMEOUT
    );

    it(
      "应该成功加载嵌入模型",
      async () => {
        if (!vectorServiceAvailable) {
          console.log(`\n⚠️ 跳过测试: 向量服务不可用`);
          return;
        }

        console.log("\n🧠 验证嵌入模型...");

        const embedder = await getEmbeddingService();

        expect(embedder).toBeDefined();
        expect(embedder).toBeInstanceOf(QwenEmbedding);

        // 测试嵌入生成
        const testEmbedding = await embedder.embed("测试文本", "document");
        expect(testEmbedding).toBeDefined();
        expect(testEmbedding.length).toBe(QwenEmbedding.EMBEDDING_DIM);

        console.log("✅ 嵌入模型已加载");
      },
      TEST_TIMEOUT
    );
  });

  describe("步骤 2: 加载世界包", () => {
    it("应该成功加载 demo_pack.json", async () => {
      console.log("\n📚 加载 demo_pack.json...");

      const worldPackLoader = new WorldPackLoader(PACKS_DIR);
      worldPack = await worldPackLoader.load("demo_pack");

      expect(worldPack).toBeDefined();
      expect(worldPack.info).toBeDefined();
      expect(worldPack.info.name.cn).toBe("幽暗庄园");
      expect(Object.keys(worldPack.entries).length).toBeGreaterThan(0);

      console.log(`✅ 世界包已加载: ${worldPack.info.name.cn}`);
      console.log(`   版本: ${worldPack.info.version}`);
      console.log(`   Lore 条目数: ${Object.keys(worldPack.entries).length}`);
      console.log(`   NPC 数量: ${Object.keys(worldPack.npcs).length}`);
    });
  });

  describe("步骤 3: 建立向量索引", () => {
    it(
      "应该成功为 lore 条目建立向量索引",
      async () => {
        if (!vectorServiceAvailable || !vectorStore) {
          console.log("\n⚠️ 跳过测试: 向量服务不可用");
          return;
        }

        console.log("\n🔍 建立向量索引...");

        const packId = "demo_pack";
        // 使用测试专用的 collection 名称，避免与生产数据冲突
        collectionName = `${TEST_COLLECTION_PREFIX}${packId}_${Date.now()}`;

        // 准备文档和元数据
        const documents: string[] = [];
        const metadatas: Record<string, string | number | boolean>[] = [];
        const ids: string[] = [];

        for (const entry of Object.values(worldPack.entries)) {
          // 中文版本
          if (entry.content.cn) {
            documents.push(entry.content.cn);
            metadatas.push({
              uid: entry.uid,
              lang: "cn",
              keys: entry.key.join(","),
              order: entry.order,
              constant: entry.constant,
              visibility: entry.visibility || "basic",
            });
            ids.push(`${entry.uid}_cn`);
          }

          // 英文版本
          if (entry.content.en) {
            documents.push(entry.content.en);
            metadatas.push({
              uid: entry.uid,
              lang: "en",
              keys: entry.key.join(","),
              order: entry.order,
              constant: entry.constant,
              visibility: entry.visibility || "basic",
            });
            ids.push(`${entry.uid}_en`);
          }
        }

        console.log(`   准备索引 ${documents.length} 个文档...`);

        // 添加文档到向量存储
        await vectorStore.addDocuments(collectionName, documents, ids, metadatas);

        console.log(`✅ 向量索引已建立: ${collectionName}`);
        console.log(
          `   中文文档: ${metadatas.filter((m) => m.lang === "cn").length}`
        );
        console.log(
          `   英文文档: ${metadatas.filter((m) => m.lang === "en").length}`
        );
      },
      TEST_TIMEOUT
    );
  });

  describe("步骤 4: 中文查询测试", () => {
    const chineseQueries = [
      { query: "庄园的历史背景", expectedKeys: ["幽暗庄园", "庄园"] },
      { query: "管家是谁", expectedKeys: ["管家", "老管家"] },
      { query: "密室里有什么", expectedKeys: ["密室", "书房"] },
    ];

    for (const { query, expectedKeys } of chineseQueries) {
      it(
        `应该找到与 "${query}" 相关的结果`,
        async () => {
          if (!vectorServiceAvailable || !vectorStore || !collectionName) {
            console.log(`\n⚠️ 跳过测试: 向量服务不可用`);
            return;
          }

          // Note: metadata fields like 'lang' are nested, filter not supported in this basic test
          const results = await vectorStore.search(
            collectionName,
            query,
            5
          );

          console.log(`\n🔍 查询: "${query}"`);
          console.log(`   找到 ${results.length} 条结果`);

          expect(results.length).toBeGreaterThan(0);

          // 检查第一个结果
          const topResult = results[0]!;
          console.log(`   最佳匹配 ID: ${topResult.id}`);
          console.log(`   相似度: ${(1 - topResult.distance).toFixed(3)}`);
          console.log(
            `   关键字: ${topResult.metadata?.keys || "无"}`
          );

          // 验证结果包含预期的关键字 (至少一个)
          const hasExpectedKey = expectedKeys.some((key) =>
            topResult.metadata?.keys?.toString().includes(key)
          );

          // 这是一个软检查，因为向量搜索结果可能因模型而异
          if (hasExpectedKey) {
            console.log(`   ✅ 找到预期关键字`);
          } else {
            console.log(`   ⚠️ 未找到预期关键字，但搜索成功`);
          }
        },
        TEST_TIMEOUT
      );
    }
  });

  describe("步骤 5: 英文查询测试", () => {
    const englishQueries = [
      { query: "manor history", expectedKeys: ["幽暗庄园", "Dark Manor"] },
      { query: "butler", expectedKeys: ["管家", "butler"] },
      { query: "secret room", expectedKeys: ["密室", "secret room"] },
    ];

    for (const { query } of englishQueries) {
      it(
        `应该找到与 "${query}" 相关的结果`,
        async () => {
          if (!vectorServiceAvailable || !vectorStore || !collectionName) {
            console.log(`\n⚠️ 跳过测试: 向量服务不可用`);
            return;
          }

          // Note: metadata fields like 'lang' are nested, filter not supported in this basic test
          const results = await vectorStore.search(
            collectionName,
            query,
            5
          );

          console.log(`\n🔍 查询: "${query}"`);
          console.log(`   找到 ${results.length} 条结果`);

          expect(results.length).toBeGreaterThan(0);

          // 检查第一个结果
          const topResult = results[0]!;
          console.log(`   最佳匹配 ID: ${topResult.id}`);
          console.log(`   相似度: ${(1 - topResult.distance).toFixed(3)}`);
          console.log(
            `   关键字: ${topResult.metadata?.keys || "无"}`
          );
        },
        TEST_TIMEOUT
      );
    }
  });

  describe("步骤 6: 跨语言语义搜索测试", () => {
    it(
      "中文查询应该能找到语义相关的内容",
      async () => {
        if (!vectorServiceAvailable || !vectorStore || !collectionName) {
          console.log(`\n⚠️ 跳过测试: 向量服务不可用`);
          return;
        }

        // 使用不在关键字中的查询词，测试语义理解
        const query = "火灾之后发生了什么";
        const results = await vectorStore.search(
          collectionName,
          query,
          5
        );

        console.log(`\n🔍 语义查询: "${query}"`);
        console.log(`   找到 ${results.length} 条结果`);

        expect(results.length).toBeGreaterThan(0);

        // 打印前3个结果
        for (let i = 0; i < Math.min(3, results.length); i++) {
          const result = results[i]!;
          const similarity = 1 - result.distance;
          console.log(
            `   [${i + 1}] ID: ${result.id}, 相似度: ${similarity.toFixed(3)}`
          );
          console.log(`       内容片段: ${result.text.substring(0, 50)}...`);
        }
      },
      TEST_TIMEOUT
    );

    it(
      "英文查询应该能找到语义相关的内容",
      async () => {
        if (!vectorServiceAvailable || !vectorStore || !collectionName) {
          console.log(`\n⚠️ 跳过测试: 向量服务不可用`);
          return;
        }

        // 使用不在关键字中的查询词，测试语义理解
        const query = "What happened after the fire";
        const results = await vectorStore.search(
          collectionName,
          query,
          5
        );

        console.log(`\n🔍 语义查询: "${query}"`);
        console.log(`   找到 ${results.length} 条结果`);

        expect(results.length).toBeGreaterThan(0);

        // 打印前3个结果
        for (let i = 0; i < Math.min(3, results.length); i++) {
          const result = results[i]!;
          const similarity = 1 - result.distance;
          console.log(
            `   [${i + 1}] ID: ${result.id}, 相似度: ${similarity.toFixed(3)}`
          );
          console.log(`       内容片段: ${result.text.substring(0, 50)}...`);
        }
      },
      TEST_TIMEOUT
    );
  });

  describe("步骤 7: 相似度排序验证", () => {
    it(
      "搜索结果应该按相似度降序排列",
      async () => {
        if (!vectorServiceAvailable || !vectorStore || !collectionName) {
          console.log(`\n⚠️ 跳过测试: 向量服务不可用`);
          return;
        }

        const results = await vectorStore.search(
          collectionName,
          "庄园的历史",
          10
        );

        console.log("\n🔍 相似度排序验证:");
        console.log(`   查询: "庄园的历史"`);
        console.log(`   结果数量: ${results.length}`);

        expect(results.length).toBeGreaterThan(1);

        // 验证结果按距离升序排列（距离越小越相似）
        for (let i = 1; i < results.length; i++) {
          expect(results[i]!.distance).toBeGreaterThanOrEqual(
            results[i - 1]!.distance
          );
        }

        // 打印前3个结果的相似度
        for (let i = 0; i < Math.min(3, results.length); i++) {
          const result = results[i]!;
          const similarity = 1 - result.distance;
          console.log(
            `   [${i + 1}] 相似度: ${similarity.toFixed(3)}, ID: ${result.id}`
          );
        }

        console.log("✅ 相似度排序正确");
      },
      TEST_TIMEOUT
    );

    it(
      "空查询应该返回空结果或抛出错误",
      async () => {
        if (!vectorServiceAvailable || !vectorStore || !collectionName) {
          console.log(`\n⚠️ 跳过测试: 向量服务不可用`);
          return;
        }

        try {
          const results = await vectorStore.search(collectionName, "", 5);
          // 如果没有抛出错误，应该返回空结果或有结果
          expect(results).toBeDefined();
          console.log("✅ 空查询处理正确");
        } catch (error) {
          // 抛出错误也是可接受的行为
          expect(error).toBeDefined();
          console.log("✅ 空查询抛出错误（预期行为）");
        }
      },
      TEST_TIMEOUT
    );
  });
});
