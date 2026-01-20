# Astinus Architecture Documentation

This document defines the technical architecture, directory structure, and engineering standards for the Astinus project.

## 1. System Overview

Astinus follows a **Client-Server** architecture with an embedded data layer, enabling easy distribution as a desktop application or hosted service.

- **Frontend (Client)**: React 19 + Vite + TypeScript + TailwindCSS. Handles user input, rendering, and state display via REST API and WebSocket.
- **Backend (Server)**: Node.js + Hono. Lightweight, edge-ready web framework hosting the Game Engine and AI Agents.
- **AI Layer**: Vercel AI SDK provides LLM abstraction with structured outputs and streaming support.
- **Data Layer**: LanceDB (embedded vector search) and SQLite (via Drizzle ORM) run directly within the application process.

## 2. Directory Structure

```text
Astinus/
├── src/
│   ├── backend/              # Node.js/Hono Application
│   │   ├── src/
│   │   │   ├── agents/       # AI Agent Definitions
│   │   │   │   ├── gm/       # GM Agent (Orchestrator)
│   │   │   │   └── npc/      # NPC Agent
│   │   │   ├── api/          # Hono Routes
│   │   │   │   ├── v1/       # REST API (game, settings)
│   │   │   │   └── websocket.ts
│   │   │   ├── db/           # Database Layer
│   │   │   │   ├── schema.ts # Drizzle ORM Schemas
│   │   │   │   └── index.ts  # SQLite Connection
│   │   │   ├── lib/          # Core Libraries
│   │   │   │   ├── llm-factory.ts  # Multi-provider LLM setup
│   │   │   │   ├── lance.ts        # LanceDB Wrapper
│   │   │   │   └── embeddings.ts   # Transformers.js embeddings
│   │   │   ├── services/     # Business Logic
│   │   │   │   ├── world.ts  # World Pack Loader (Zod)
│   │   │   │   ├── dice.ts   # 2d6 Mechanics
│   │   │   │   ├── lore.ts   # Hybrid search service
│   │   │   │   ├── config.ts # Configuration management
│   │   │   │   └── location-context.ts
│   │   │   ├── schemas/      # Zod validation schemas
│   │   │   └── index.ts      # Server Entrypoint
│   │   ├── tests/            # Vitest tests
│   │   └── package.json
│   │
│   └── web/                  # React 19 Frontend
│       ├── src/
│       │   ├── api/          # API Client (REST + WebSocket)
│       │   ├── components/   # React Components
│       │   ├── stores/       # Zustand state management
│       │   ├── hooks/        # Custom React hooks
│       │   ├── locales/      # i18n bundles (cn/en)
│       │   └── utils/        # Utilities
│       └── package.json
│
├── data/
│   ├── packs/                # World Packs (JSON)
│   ├── saves/                # SQLite game saves
│   └── lancedb/              # Vector store data
├── config/                   # Configuration (settings.yaml)
├── docs/                     # Documentation
└── pm2.config.js             # Development process management
```

## 3. Data & Model Layers

### 3.1 Schemas (Zod)

All data validation uses **Zod**, which provides both runtime validation and static TypeScript types.

- **GameState**: The central source of truth for game sessions
- **WorldPack**: Defines the structure of `data/packs/*.json`
- **ConfigSchema**: Settings validation for LLM providers

### 3.2 Database (Drizzle ORM)

- **SQLite**: Used for relational data (game state, player data)
- **Drizzle**: Provides type-safe SQL queries with automatic TypeScript inference

### 3.3 Embedded Vector Search (LanceDB)

- **LanceDB**: Embedded vector database, runs in-process with file-based storage
- **Embeddings**: Uses **Transformers.js** with **Qwen3-Embedding-0.6B-ONNX** for multilingual support
- **Hybrid Search**: Combines vector similarity with keyword matching for Lore retrieval

## 4. Frontend Architecture (React 19)

### 4.1 UI Design

- **Mobile-First**: Bottom panels for mobile, three-column layout for desktop
- **GamePhase Enum**: Controls UI interactivity (locks input during `narrating` or `processing`)
- **Zustand + Immer**: Immutable state management

### 4.2 Real-time Interaction (WebSocket)

```
1. Client sends `player_action`
2. Server sends `status` (which agent is acting)
3. Server streams `content` (typewriter effect)
4. If check needed: Server sends `dice_check` → Client shows roller → Client sends `dice_result`
5. Server sends `complete` with updated metadata
```

## 5. Multi-Agent Architecture

### 5.1 Star Topology

The **GM Agent** acts as the central orchestrator. It is the only agent that directly manages game state.

```
        ┌───────────────┐
        │  GM Agent     │
        │ (Orchestrator)│
        └──────┬────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
    ▼          ▼          ▼
┌───────┐  ┌───────┐  ┌───────┐
│  NPC  │  │ Lore  │  │ Dice  │
│ Agent │  │ Tool  │  │ Tool  │
└───────┘  └───────┘  └───────┘
```

### 5.2 Tool Loop (Vercel AI SDK)

The GM Agent operates in a tool-calling loop:

1. **Analyze**: Understand player intent
2. **Call Tool/Agent**: Invoke Lore search, NPC dialogue, or Dice check
3. **Synthesize**: Integrate outputs into coherent narrative
4. **Stream**: Send response to client

### 5.3 Specialized Components

| Component | Type | Purpose |
|-----------|------|---------|
| GM Agent | Agent | Central orchestrator, narrative generation |
| NPC Agent | Agent | Character-specific dialogue and personality |
| Lore Tool | Tool | RAG-based world knowledge retrieval |
| Dice Tool | Tool | 2d6 pool mechanics calculation |

### 5.4 Context Slicing

GM Agent provides only relevant context to sub-agents:
- NPC Agent only receives information that specific NPC would know
- Lore Tool queries are scoped to relevant world pack data

## 6. Game Mechanics (2d6 System)

### 6.1 Dice Pool Logic

- **Standard**: Roll 2d6, sum both
- **Bonus Dice (+N)**: Roll 2+N dice, keep **highest** 2
- **Penalty Dice (-N)**: Roll 2+N dice, keep **lowest** 2

### 6.2 Outcomes

| Roll | Result |
|------|--------|
| 12+ | Critical Success |
| 10-11 | Success |
| 7-9 | Partial Success (success at a cost) |
| 6- | Failure (GM moves) |

## 7. API Contract

### REST Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v1/game/new` | Start new game session |
| POST | `/api/v1/game/action` | Process player action |
| POST | `/api/v1/game/dice-result` | Submit dice roll result |
| GET | `/api/v1/game/state/:sessionId` | Get game state |
| GET | `/api/v1/world-packs` | List available world packs |
| GET | `/api/v1/settings` | Get settings |
| PUT | `/api/v1/settings` | Update settings |

### WebSocket

- **Endpoint**: `WS /ws/game/:sessionId`
- **Client → Server**: `player_action`, `dice_result`, `ping`
- **Server → Client**: `status`, `content`, `complete`, `error`, `phase`, `dice_check`

## 8. Technology Stack

### Backend

| Component | Technology |
|-----------|------------|
| Runtime | Node.js 20+ |
| Framework | Hono |
| AI SDK | Vercel AI SDK |
| ORM | Drizzle + SQLite |
| Vector DB | LanceDB |
| Embeddings | Transformers.js (Qwen3-Embedding-0.6B) |
| Validation | Zod |

### Frontend

| Component | Technology |
|-----------|------------|
| Framework | React 19 |
| Build Tool | Vite |
| Styling | TailwindCSS |
| State | Zustand + Immer |
| Routing | React Router v7 |
| Testing | Vitest |

## 9. Development & Operations

### Commands

```bash
make install      # Install all dependencies
make check        # Run lint + type-check + test
make run-dev      # Start dev servers (PM2)
make build        # Build all
```

### Process Management

`pm2.config.js` manages both backend (tsx watch) and frontend (vite dev) servers.

## 10. Internationalization (i18n)

- Frontend strings: `src/web/src/locales/{cn,en}.json`
- World packs use `LocalizedString` schema: `{ cn: "...", en: "..." }`
- Lore entries support tiered discovery (`basic` vs `detailed` visibility)
