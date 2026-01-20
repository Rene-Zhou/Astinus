# Astinus Backend (TypeScript)

> AI-driven TTRPG engine backend - TypeScript migration from Python/FastAPI

## Stack

- **Runtime**: Node.js 20+ / Bun (recommended)
- **Framework**: Hono (lightweight, edge-ready web framework)
- **AI SDK**: Vercel AI SDK (LLM orchestration with structured outputs)
- **ORM**: Drizzle (type-safe SQL with SQLite)
- **Vector DB**: LanceDB (embedded vector store)
- **Embeddings**: Transformers.js (local ONNX models via Qwen3-Embedding-0.6B)
- **Validation**: Zod (runtime schema validation + type inference)

## Project Structure

```
src/
├── agents/           # AI Agent Definitions
│   ├── gm/           # GM Agent (Orchestrator)
│   ├── npc/          # NPC Agent
│   └── tools/        # Vercel SDK Tools (Lore, Dice)
├── api/              # Hono Routes
├── db/               # Database Layer
│   ├── schema.ts     # Drizzle ORM Schemas
│   └── index.ts      # SQLite Connection
├── lib/              # Core Libraries
│   ├── ai.ts         # Vercel SDK Setup
│   ├── lance.ts      # LanceDB Wrapper
│   └── logger.ts     # Structural Logging
├── services/         # Business Logic
│   ├── world.ts      # World Pack Loader (Zod)
│   └── dice.ts       # 2d6 Mechanics
├── index.ts          # Server Entrypoint
└── types.ts          # Shared Types
```

## Getting Started

### Install Dependencies

```bash
npm install
```

### Development

```bash
# Start dev server with hot reload
npm run dev

# The server will start on http://localhost:3000
# API docs: http://localhost:3000/health
```

### Type Checking & Linting

```bash
# Type checking
npm run typecheck

# Linting
npm run lint

# Format code
npm run format
```

### Database

```bash
# Generate migrations from schema changes
npm run db:generate

# Apply migrations
npm run db:migrate

# Open Drizzle Studio (DB GUI)
npm run db:studio
```

### Build & Production

```bash
# Build TypeScript
npm run build

# Run production build
npm run start
```

## Key Technologies

### Hono Framework

Lightweight web framework (faster than Express):
- **Type-safe routing**: Inferred path params
- **WebSocket support**: Built-in for Bun/Deno
- **Middleware**: CORS, JWT, logging
- **RPC support**: Type-safe client-server communication

**Resources**:
- [Hono Docs](https://hono.dev)
- [Bun + Hono Guide](https://bun.com/docs/guides/ecosystem/hono)

### Vercel AI SDK

Modern LLM orchestration:
- **`generateObject`**: Structured outputs with Zod schemas
- **`streamText`**: Real-time streaming responses
- **`ToolLoopAgent`**: Built-in ReAct agent loops
- **Provider agnostic**: OpenAI, Anthropic, Google Gemini, etc.

**Resources**:
- [AI SDK Docs](https://ai-sdk.dev)
- [GitHub](https://github.com/vercel/ai)

### Drizzle ORM

Type-safe SQL with SQLite:
- **Schema as code**: TypeScript schema definitions
- **Type inference**: Automatic types from schema
- **Migrations**: SQL-first migration system
- **Zod integration**: `createInsertSchema()`, `createSelectSchema()`

**Resources**:
- [Drizzle Docs](https://orm.drizzle.team)
- [SQLite Guide](https://orm.drizzle.team/docs/get-started-sqlite)

### LanceDB

Embedded vector database:
- **File-based storage**: No separate server process
- **Lance format**: Columnar, versioned storage
- **Transformers.js integration**: Local embeddings
- **Vector similarity search**: Cosine, L2, dot product

**Resources**:
- [LanceDB Docs](https://lancedb.github.io/lancedb/)
- [Node.js Guide](https://lancedb.github.io/lancedb/js/)

### Transformers.js

Local ML inference (ONNX):
- **Qwen3-Embedding-0.6B**: Multilingual embeddings (1024-dim)
- **Browser + Node.js**: Runs everywhere
- **WebGPU support**: 100x faster with GPU
- **No Python required**: Pure JavaScript/TypeScript

**Resources**:
- [Transformers.js Docs](https://huggingface.co/docs/transformers.js)
- [Model Hub](https://huggingface.co/onnx-community/Qwen3-Embedding-0.6B-ONNX)

## Migration Notes

This backend is a TypeScript port of the original Python/FastAPI backend (`src/backend/`).

### Key Differences

| Python (v1) | TypeScript (v2) | Reason |
|-------------|-----------------|--------|
| FastAPI | Hono | Lighter, edge-ready |
| LangChain | Vercel AI SDK | Better structured outputs |
| Pydantic | Zod | Runtime validation + TS inference |
| ChromaDB | LanceDB | Embedded, no server process |
| SentenceTransformers | Transformers.js | No Python dependency |
| Jieba | Intl.Segmenter | Native JS API |

### API Contract

The TypeScript backend maintains **API parity** with the Python backend to ensure zero frontend changes.

#### Game Endpoints
- **POST /api/v1/game/new**: Start new game session
- **POST /api/v1/game/action**: Process player action
- **POST /api/v1/game/dice-result**: Submit dice roll result
- **GET /api/v1/game/state/:sessionId**: Get game state

#### World Pack Endpoints
- **GET /api/v1/world-packs**: List available world packs
- **GET /api/v1/world-packs/:packId**: Get world pack info

#### Settings Endpoints
- **GET /api/v1/settings**: Get all settings
- **PUT /api/v1/settings**: Update settings
- **POST /api/v1/settings/test-connection**: Test provider connection

#### WebSocket
- **WS /ws/game/:sessionId**: Real-time bidirectional game communication
  - Client → Server: `player_action`, `dice_result`, `ping`
  - Server → Client: `status`, `content`, `complete`, `error`, `phase`, `dice_check`

## Development Workflow

1. **Define Zod schemas** (`src/types.ts`) matching Pydantic models
2. **Setup Drizzle schema** (`src/db/schema.ts`) matching SQLAlchemy
3. **Port services** (pure logic, no dependencies first)
4. **Build AI agents** using Vercel AI SDK
5. **Implement API routes** with Hono
6. **Test with frontend** (point React app to new backend)

## License

MIT
