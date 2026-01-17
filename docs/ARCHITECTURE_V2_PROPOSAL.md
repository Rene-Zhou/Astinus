# Astinus Architecture V2 (Target Architecture)

This document defines the technical architecture for the **Version 2 (TypeScript)** of the Astinus project.
It replaces the specific implementation details of the original Python-based `ARCHITECTURE.md` while maintaining the core domain logic.

## 1. System Overview

Astinus V2 allows for a **Single-Process** or **Sidecar** deployment model, enabling easy distribution as a desktop application.

- **Frontend**: React 19 + Vite (Unchanged from V1).
- **Backend**: A light **Node.js (Hono)** process that hosts the Game Engine and AI Agents.
- **AI Layer**: **Vercel AI SDK** provides the abstraction over LLMs, replacing LangChain.
- **Data Layer**: **LanceDB** (Embedded Vector Search) and **SQLite** (via Drizzle ORM) run directly within the application process.

## 2. Directory Structure (Target)

The new structure promotes cohesion by grouping features rather than technical layers where possible.

```text
Astinus/
├── src/
│   ├── backend/              # Node.js/Hono Application
│   │   ├── src/
│   │   │   ├── agents/       # AI Agent Definitions
│   │   │   │   ├── gm/       # GM Agent (Orchestrator)
│   │   │   │   │   ├── loops.ts     # ReAct Logic
│   │   │   │   │   └── prompts.ts   # System Prompts
│   │   │   │   ├── npc/      # NPC Agent
│   │   │   │   └── tools/    # Vercel SDK Tools (Lore, Dice)
│   │   │   ├── api/          # Hono Routes
│   │   │   ├── db/           # Database Layer
│   │   │   │   ├── schema.ts # Drizzle ORM Schemas
│   │   │   │   └── index.ts  # SQLite Connection
│   │   │   ├── lib/          # Core Libraries
│   │   │   │   ├── ai.ts     # Vercel SDK Setup
│   │   │   │   ├── lance.ts  # LanceDB Wrapper
│   │   │   │   └── logger.ts # Structural Logging
│   │   │   ├── services/     # Business Logic
│   │   │   │   ├── world.ts  # World Pack Loader (Zod)
│   │   │   │   └── dice.ts   # 2d6 Mechanics
│   │   │   ├── index.ts      # Server Entrypoint
│   │   │   └── types.ts      # Shared Types
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   ├── web/                  # React Frontend (Unchanged)
│   └── shared/               # Shared Types (Zod inferred)
│
├── data/
│   ├── packs/                # World Packs (JSON/YAML)
│   └── save/                 # SQLite & LanceDB Data
├── docs/
└── package.json              # Workspace Root
```

## 3. Data & Model Layers (Zod + Drizzle)

### 3.1 Schemas (Zod)
We replace Pydantic with **Zod**. Zod schemas compile to both runtime validators and static TypeScript types.
- **GameState**: The source of truth object, validated at runtime on load.
- **WorldPack**: Defines the structure of `data/packs/*.json`.

### 3.2 Database (Drizzle ORM)
- **SQLite**: Used for relational data (Game State, simple inventory).
- **Drizzle**: Provides type-safe SQL queries. No code generation step required for queries (unlike Prisma), only for migrations.

### 3.3 Embedded AI Memory (LanceDB)
- **LanceDB**: Replaces chroma-client. It runs in-process and stores vectors in local files.
- **Embeddings**: Uses **Transformers.js** (`@xenova/transformers`) to generate embeddings locally using ONNX models.
  - Model: **Qwen3-Embedding-0.6B-ONNX** for native Chinese support and multilingual capabilities.
  - Removing the need for Python.

## 4. AI & Agent Architecture (Vercel AI SDK)

### 4.1 The SDK Choice
We use **Vercel AI SDK Core** (`ai`).
- **`generateObject`**: The primary primitive. It forces the LLM to output JSON conforming to a Zod schema. This replaces the brittle "Constraint Prompting + JSON Regex Repair" pattern from V1.
- **`streamText`**: Used for the 'typewriter' effect narrative generation.

### 4.2 The GM Agent (Refactored)
The GM Agent logic is simplified:
1. **Input**: Receive `player_input`.
2. **Context Assembly**: `LoreService` queries LanceDB to fill context window.
3. **Decision Step (`generateObject`)**:
   - The LLM decides to `RESPOND`, `CALL_NPC`, or `CHECK_DICE`.
   - Output is a strongly-typed JSON object.
4. **Execution**:
   - if `RESPOND`: Stream text to client.
   - if `CALL_NPC`: Invoke NPC sub-routine.
   - if `CHECK_DICE`: Send pause signal to client.

### 4.3 Tools as First-Class Citizens
Lore looking and Dice rolling are exposed as standard **Tools** that the LLM can invoke function calls on.

## 5. API Contract
The API remains largely compatible with V1 to minimize Frontend changes.

- **POST /api/game/chat**: Main loop entry.
- **WS /api/ws/game**: Real-time stream (Narrative tokens, State updates).

## 6. Packaging Strategy
1. **Node**: `npm run build` -> `dist/index.js`.
2. **Binaries**: Use `pkg` or `Bun` to compile `index.js` + `node_modules` into a single executable `astinus-engine`.
3. **Distribution**: The frontend can optionally bundle this binary or assume a local server (localhost:3000).

## 7. Migration of Mechanics
- **Dice**: The 2d6 logic (`3d6kl2` etc.) is pure logic and will be ported 1:1 to TypeScript.
- **World Loader**: The complex Python `WorldPackLoader` will be rewritten using `fs/promises` and `zod`. This is the most complex component to migrate due to the validation logic.
