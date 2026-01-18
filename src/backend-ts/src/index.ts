import { Hono } from "hono";
import { cors } from "hono/cors";
import { logger } from "hono/logger";
import { createNodeWebSocket } from "@hono/node-ws";
import { serve } from "@hono/node-server";

import { gameRouter } from "./api/v1/game";
import { settingsRouter } from "./api/v1/settings";
import { createWebSocketHandler } from "./api/websocket";
import { getEmbeddingService } from "./lib/embeddings";
import { getVectorStoreService } from "./lib/lance";
import { WorldPackLoader } from "./services/world";
import { LoreService } from "./services/lore";
import { ConfigService } from "./services/config";
import { GMAgent } from "./agents/gm";

export interface AppContext {
  gmAgent: GMAgent | null;
  worldPackLoader: WorldPackLoader | null;
  vectorStore: Awaited<ReturnType<typeof getVectorStoreService>> | null;
  loreService: LoreService | null;
}

const appContext: AppContext = {
  gmAgent: null,
  worldPackLoader: null,
  vectorStore: null,
  loreService: null,
};

export function getAppContext(): AppContext {
  return appContext;
}

const app = new Hono();

app.use("*", logger());

app.use(
  "*",
  cors({
    origin: "*",
    allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowHeaders: ["Content-Type", "Authorization"],
    credentials: true,
  })
);

app.get("/", (c) => {
  return c.json({
    name: "Astinus TTRPG Engine",
    version: "0.1.0",
    status: "running",
    runtime: "Node.js + Hono",
    docs: "/docs",
  });
});

app.get("/health", (c) => {
  const statusInfo = {
    status: appContext.gmAgent ? "healthy" : "unhealthy",
    version: "0.1.0",
    agents: {
      gm_agent: appContext.gmAgent !== null,
      npc_agent: appContext.gmAgent !== null,
    },
    services: {
      world_pack_loader: appContext.worldPackLoader !== null,
      vector_store: appContext.vectorStore !== null,
      lore_service: appContext.loreService !== null,
    },
  };

  if (!appContext.gmAgent) {
    return c.json(statusInfo, 503);
  }

  return c.json(statusInfo);
});

app.route("/api/v1", gameRouter);
app.route("/api/v1/settings", settingsRouter);

const { injectWebSocket, upgradeWebSocket } = createNodeWebSocket({ app });
const wsHandler = createWebSocketHandler(upgradeWebSocket, () => appContext);

app.get("/ws/game/:sessionId", wsHandler);

async function initializeServices(): Promise<void> {
  console.log("🚀 Starting Astinus backend (TypeScript)...");

  try {
    console.log("⚙️ Loading configuration...");
    const configPath = ConfigService.getInstance().getConfigPath();
    console.log(`   Reading from: ${configPath}`);
    await ConfigService.getInstance().load();
    console.log("✅ Configuration loaded successfully");
  } catch (error) {
    console.error("⚠️ Failed to load configuration:", error);
    console.error("   Using default/fallback settings where possible, but LLM features may fail.");
  }

  try {
    console.log("📦 Initializing embedding service...");

    // Check if HF token is available
    if (!process.env.HF_TOKEN) {
      console.warn("⚠️  HF_TOKEN not set - embedding service will be disabled");
      console.warn("⚠️  Set HF_TOKEN environment variable to enable HuggingFace model downloads");
      console.warn("⚠️  Or run without vector store features");
    }

    await getEmbeddingService((progress) => {
      if (progress.status === "progress" && progress.file) {
        const pct = progress.progress?.toFixed(1) || "0";
        console.log(`   Downloading ${progress.file}: ${pct}%`);
      }
    });
    console.log("✅ Embedding service ready");
  } catch (error) {
    console.error("⚠️ Embedding service failed:", error);
    console.warn("⚠️  Continuing without embedding service...");
    console.warn("⚠️  Set HF_TOKEN environment variable to enable HuggingFace features");
  }

  try {
    console.log("📦 Initializing vector store...");
    appContext.vectorStore = await getVectorStoreService();
    console.log("✅ Vector store ready");
  } catch (error) {
    console.error("⚠️ Vector store failed:", error);
  }

  try {
    console.log("📦 Initializing world pack loader...");
    appContext.worldPackLoader = new WorldPackLoader("../../data/packs");
    const packs = await appContext.worldPackLoader.listAvailable();
    console.log(`✅ World pack loader ready (packs: ${packs.join(", ")})`);
  } catch (error) {
    console.error("⚠️ World pack loader failed:", error);
  }

  if (appContext.worldPackLoader && appContext.vectorStore) {
    try {
      appContext.loreService = new LoreService(
        appContext.worldPackLoader,
        appContext.vectorStore
      );
      console.log("✅ Lore service ready");
    } catch (error) {
      console.error("⚠️ Lore service failed:", error);
    }
  }

  console.log("✅ Astinus backend started successfully");
  console.log("📝 API available at http://localhost:3000");
}

const PORT = parseInt(process.env.PORT || "3000", 10);

initializeServices()
  .then(() => {
    const server = serve(
      {
        fetch: app.fetch,
        port: PORT,
      },
      (info) => {
        console.log(`🌐 Server listening on http://localhost:${info.port}`);
      }
    );

    injectWebSocket(server);
  })
  .catch((error) => {
    console.error("❌ Failed to start server:", error);
    process.exit(1);
  });

export { app };
