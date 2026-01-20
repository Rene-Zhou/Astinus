# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-20
**Branch:** migration/Python2TS_2
**Stack:** TypeScript (Hono + Vercel AI SDK + LanceDB) + React 19 (Vite, Tailwind, Zustand)

## OVERVIEW

AI-driven TTRPG engine with multi-agent Star Topology architecture. GM Agent orchestrates NPC/Lore agents via Vercel AI SDK tool loops. LanceDB for vector search, SQLite (Drizzle ORM) for persistence, WebSocket for real-time streaming.

## STRUCTURE

```
./
├── src/
│   ├── backend/              # Hono server + AI agents (See backend/AGENTS.md)
│   │   ├── src/
│   │   │   ├── agents/       # [CORE] GM, NPC agents (See agents/AGENTS.md)
│   │   │   ├── api/          # Hono routes + WebSocket handler
│   │   │   ├── db/           # Drizzle ORM schemas (SQLite)
│   │   │   ├── lib/          # LLM factory, embeddings, LanceDB wrapper
│   │   │   ├── schemas/      # Zod config schemas
│   │   │   └── services/     # Dice, World, Lore, LocationContext
│   │   └── tests/            # Vitest + typed mock factories
│   └── web/                  # React frontend (See web/AGENTS.md)
├── data/                     # SQLite saves, LanceDB vector store
├── config/                   # settings.yaml (API keys, model config)
├── pm2.config.js            # Dev orchestration (Backend:8000 + Frontend:5173)
└── Makefile                 # Unified commands: install, check, run-dev, build
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| **Dev Start** | `make run-dev` | PM2 starts both services |
| **Agent Logic** | `src/backend/src/agents/` | GM orchestrator + NPC sub-agent |
| **API Routes** | `src/backend/src/api/v1/` | REST: game.ts, settings.ts |
| **WebSocket** | `src/backend/src/api/websocket.ts` | Real-time streaming protocol |
| **Frontend State** | `src/web/src/stores/gameStore.ts` | Zustand + Immer |
| **DB Schema** | `src/backend/src/db/schema.ts` | Drizzle ORM definitions |
| **Zod Schemas** | `src/backend/src/schemas.ts` | GameState, NPC, Lore types |
| **Config** | `config/settings.yaml` | Copy from settings.example.yaml |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `GMAgent` | Class | `agents/gm/index.ts` | Star Topology Hub - ReAct loop orchestrator |
| `NPCAgent` | Class | `agents/npc/index.ts` | Character roleplay + memory retrieval |
| `LoreService` | Class | `services/lore.ts` | Hybrid search (keyword + vector) |
| `LanceDBService` | Class | `lib/lance.ts` | Vector store wrapper |
| `gameStore` | Store | `web/src/stores/gameStore.ts` | Frontend state + WS sync |
| `initializeServices` | Func | `index.ts` | Bootstrap embeddings, vector store, agents |

## CONVENTIONS

### Architecture
- **Star Topology**: GM Agent is the ONLY hub. Sub-agents receive context slices, never full state.
- **Information Isolation**: NPCs don't know other NPCs' data. GM controls all context flow.
- **Immersion Rules**: Internal IDs (`village_well`) NEVER appear in narrative. NPCs described by appearance until player learns name.

### Backend
- **Validation**: Zod schemas in `schemas.ts`. All API input/output validated.
- **AI SDK**: Vercel AI SDK with `generateText` + tools for ReAct loop.
- **Streaming**: WebSocket phases: `status` -> `content` -> `complete` / `dice_check`.

### Frontend
- **Styling**: TailwindCSS ONLY. No inline styles.
- **State**: Zustand + Immer. Use selectors to prevent re-renders.
- **i18n**: All text via `useTranslation`. Support `LocalizedString` objects.

### Testing
- **Framework**: Vitest for both packages.
- **Mocks**: Factory functions in `tests/mocks/` (typed, Zod-aligned).
- **Contract Tests**: `frontend-api-contract.test.ts` validates backend/frontend sync.

## ANTI-PATTERNS (THIS PROJECT)

| Rule | Reason |
|------|--------|
| **NO src/frontend work** | Deprecated TUI. Use `src/web/` only. |
| **NO Agent Name Leaks** | Players see "Narrator", never "GM Agent" or "Rule Agent". |
| **NO AI Dice Rolls** | Only players roll dice (transparency). |
| **NO Direct NPC Roleplay by GM** | GM MUST use `call_agent` tool for NPC dialogue. |
| **NO Type Suppression** | Never use `as any`, `@ts-ignore`, `@ts-expect-error`. |
| **NO Hardcoded Strings** | All UI text in i18n bundles. |

## COMMANDS

```bash
make install         # Install all deps (backend + web)
make check           # Lint + type-check + test (ALL)
make run-dev         # Start dev servers via PM2
make build           # Production build
pm2 logs             # View real-time logs
```

## NOTES

- **Monorepo**: Two npm packages under `src/`. No workspace linking - manual type sync.
- **Types**: Backend uses Zod inference. Frontend mirrors in `api/types.ts`.
- **Vector Store**: LanceDB tables: `lore_{packId}`, `npc_memory_{sessionId}`, `gm_history_{sessionId}`.
- **CLAUDE.md**: OUTDATED (references Python/FastAPI). Use this file instead.
