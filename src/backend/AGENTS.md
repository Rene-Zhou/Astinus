# BACKEND - Hono + AI Agents

**Generated:** 2026-01-20
**Stack:** Node.js 20+ | Hono | Vercel AI SDK | Drizzle ORM | LanceDB | Vitest

## OVERVIEW

AI-driven game server implementing Star Topology multi-agent architecture. Hono handles REST/WebSocket, Vercel AI SDK powers the ReAct loop, LanceDB provides semantic retrieval.

## STRUCTURE

```
src/backend/
├── src/
│   ├── agents/           # AI agents (See agents/AGENTS.md)
│   ├── api/              # Hono routes
│   │   ├── v1/           # REST endpoints (game.ts, settings.ts)
│   │   └── websocket.ts  # Real-time streaming handler
│   ├── db/               # Drizzle ORM
│   │   ├── schema.ts     # Table definitions
│   │   └── index.ts      # DB connection
│   ├── lib/              # Core utilities
│   │   ├── llm-factory.ts    # Model instantiation
│   │   ├── embeddings.ts     # Local Transformers.js embeddings
│   │   └── lance.ts          # LanceDB wrapper
│   ├── schemas/          # Zod config schemas
│   ├── schemas.ts        # [CORE] All game type schemas
│   └── services/         # Business logic
│       ├── world.ts      # WorldPackLoader (Zod validation + indexing)
│       ├── lore.ts       # Hybrid search (keyword + vector)
│       ├── dice.ts       # 2d6 mechanics
│       ├── location-context.ts  # Scene context builder
│       └── config.ts     # YAML config loader
├── tests/
│   ├── mocks/            # Typed factory functions
│   ├── utils/            # createTestApp for DI
│   └── api/              # Contract tests
└── index.ts              # Entry point
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| **Add API Route** | `api/v1/` | Export from router, mount in index.ts |
| **Modify Game Logic** | `services/` | Dice, Lore, World loading |
| **Change AI Behavior** | `agents/gm/` | System prompt, tool definitions |
| **Add Schema** | `schemas.ts` | Zod + `z.infer<>` for types |
| **Vector Operations** | `lib/lance.ts` | Table creation, search, upsert |
| **WebSocket Protocol** | `api/websocket.ts` | Phase transitions, streaming |

## CONVENTIONS

- **Zod-First**: Define schema in `schemas.ts`, infer type. Never hand-write interfaces for game data.
- **Service Singletons**: Services initialized once in `initializeServices()`, injected via context.
- **Async Initialization**: Heavy services (embeddings, vector store) use lazy init with progress callbacks.
- **Error Handling**: Services return `{ success, data?, error? }` pattern. Never throw for expected failures.

## ANTI-PATTERNS

| Rule | Reason |
|------|--------|
| **NO console.log in production** | Use structured logging or PM2 logs |
| **NO blocking init** | Embedding model loads async with progress callback |
| **NO raw SQL** | Use Drizzle ORM queries only |
| **NO direct LLM calls** | Use `llm-factory.ts` for model instantiation |

## COMMANDS

```bash
npm run dev      # tsx watch (hot reload)
npm run build    # tsc to dist/
npm test         # vitest
npm run lint     # eslint
```

## NOTES

- **Port**: 8000 (configured in pm2.config.js)
- **DB Path**: `../../data/astinus.db` (relative to src/backend)
- **Vector Path**: `../../data/vector_store/` (LanceDB tables)
- **Config**: `../../config/settings.yaml` (API keys, model selection)
