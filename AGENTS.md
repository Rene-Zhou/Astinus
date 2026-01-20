# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-19
**Branch:** main
**Stack:** TypeScript (Node.js + Hono + Vercel AI SDK) + React 19 (Vite, Tailwind, Zustand)

## OVERVIEW

AI-driven TTRPG engine with multi-agent architecture (Star topology). GM Agent orchestrates NPC/Lore agents via Vercel AI SDK tool loops. Uses LanceDB for vector search, SQLite (Drizzle ORM) for persistence, and WebSocket for real-time streaming.

## STRUCTURE

```
./
├── src/
│   ├── backend/              # Hono server + AI agents (Entry: src/index.ts)
│   │   ├── src/
│   │   │   ├── agents/       # [CORE] GM, NPC agents
│   │   │   ├── api/          # [ROUTES] Hono API routes
│   │   │   ├── db/           # [DATA] Drizzle ORM schemas
│   │   │   ├── lib/          # [LIB] LLM factory, embeddings, LanceDB
│   │   │   ├── schemas/      # [VALIDATION] Zod schemas
│   │   │   └── services/     # [LOGIC] Dice, World, Lore, Config
│   │   └── tests/            # Vitest tests
│   └── web/                  # React frontend
├── data/                     # SQLite saves, LanceDB vector store
├── config/                   # settings.yaml (secrets)
├── pm2.config.js            # Dev process manager (Backend + Frontend)
└── Makefile                 # Unified build/test commands
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| **Dev Start** | `pm2.config.js` | `pm2 start pm2.config.js` runs both |
| **Agent Logic** | `src/backend/src/agents/` | GM and NPC agents |
| **API Routes** | `src/backend/src/api/` | Hono routers |
| **Frontend** | `src/web/src/` | React 19 + Tailwind |
| **DB Schema** | `src/backend/src/db/schema.ts` | Drizzle ORM definitions |
| **Config** | `config/settings.yaml` | Use `settings.example.yaml` as template |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `GMAgent` | Module | `src/backend/src/agents/gm/index.ts` | Central Orchestrator (Star Topology Hub) |
| `NPCAgent` | Module | `src/backend/src/agents/npc/index.ts` | NPC dialogue and roleplay |
| `gameStore` | Store | `src/web/src/stores/gameStore.ts` | Frontend State (Zustand) |
| `index.ts` | File | `src/backend/src/index.ts` | Backend Entry Point |

## CONVENTIONS

### General
- **Architecture**: Star Topology (GM -> Sub-agents).
- **Process**: PM2 for local dev orchestration.
- **CI/CD**: GitHub Actions. Run `make check` before commit.

### TypeScript (Backend)
- **Framework**: Hono (lightweight, edge-ready).
- **AI SDK**: Vercel AI SDK with structured outputs.
- **ORM**: Drizzle with SQLite.
- **Vector DB**: LanceDB (embedded).
- **Validation**: Zod schemas.

### TypeScript (Frontend)
- **Styling**: TailwindCSS only. No inline styles.
- **State**: Zustand + Immer.
- **i18n**: `useTranslation` hook.

## ANTI-PATTERNS (THIS PROJECT)

| Rule | Reason |
|------|--------|
| **NO TUI work** | `src/frontend/` is deprecated. Use `src/web/`. |
| **NO Agent Name Leaks** | Players see "Narrator", not "Rule Agent". |
| **NO AI Dice Rolls** | Only players roll dice (for transparency). |

## COMMANDS

```bash
make install         # Install all deps (backend + web)
make install-backend # Install backend deps (npm)
make install-web     # Install frontend deps (npm)
make check           # Run ALL checks (lint, type-check, test)
make run-dev         # Start dev servers (PM2)
make build           # Build all (backend + web)
```

## NOTES
- **Monorepo**: Two npm packages under `src/` (backend + web).
- **Entry Point**: `src/backend/src/index.ts` is the backend entry.
