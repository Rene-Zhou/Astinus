# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-16
**Branch:** main
**Stack:** Python 3.13+ (FastAPI, LangChain) + React 19 (Vite, Tailwind, Zustand)

## OVERVIEW

AI-driven TTRPG engine with multi-agent architecture (Star topology). GM Agent orchestrates Rule/NPC/Lore agents via ReAct loop. Uses ChromaDB for vector search, SQLite for persistence, and WebSocket for real-time streaming.

## STRUCTURE

```
./
├── src/
│   ├── backend/              # FastAPI server + AI agents (Real Entry: main.py)
│   │   ├── agents/           # [CORE] GM, Rule, NPC, Lore (See AGENTS.md)
│   │   ├── models/           # [DATA] Pydantic models (See AGENTS.md)
│   │   └── services/         # [LOGIC] Dice, World, Vector (See AGENTS.md)
│   └── web/                 # React frontend (See AGENTS.md)
├── data/                    # SQLite saves, ChromaDB vector store
├── config/                  # settings.yaml (secrets)
├── locale/                  # i18n bundles (cn/en)
├── pm2.config.js           # Dev process manager (Backend + Frontend)
└── Makefile                # Unified build/test commands
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| **Dev Start** | `pm2.config.js` | `pm2 start pm2.config.js` runs both |
| **Agent Logic** | `src/backend/agents/` | Logic lives here, prompts in `prompts/*.yaml` |
| **API Routes** | `src/backend/api/v1/` | FastAPI routers |
| **Frontend** | `src/web/src/` | React 19 + Tailwind |
| **Type Definitions** | `docs/API_TYPES.ts` | **MANUAL SYNC REQUIRED** with Pydantic |
| **Config** | `config/settings.yaml` | Use `settings.example.yaml` as template |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `GMAgent` | Class | `src/backend/agents/gm.py` | Central Orchestrator (Star Topology Hub) |
| `GameState` | Class | `src/backend/models/game_state.py` | Single Source of Truth |
| `gameStore` | Store | `src/web/src/stores/gameStore.ts` | Frontend State (Zustand) |
| `main.py` | File | `src/backend/main.py` | Real Backend Entry Point |

## CONVENTIONS

### General
- **Architecture**: Star Topology (GM -> Sub-agents).
- **Process**: PM2 for local dev orchestration.
- **CI/CD**: None. Manual `make check` required before commit.

### Python (Backend)
- **Async**: All IO (DB, LLM) must be `async`.
- **Prompts**: Jinja2 templates in `agents/prompts/*.yaml` (No hardcoding).
- **Services**: Singleton pattern (`get_service()`).

### TypeScript (Frontend)
- **Styling**: TailwindCSS only. No inline styles.
- **State**: Zustand + Immer.
- **i18n**: `useTranslation` hook.

## ANTI-PATTERNS (THIS PROJECT)

| Rule | Reason |
|------|--------|
| **NO automated type sync** | `docs/API_TYPES.ts` must be updated MANUALLY. |
| **NO hardcoded prompts** | Use `src/backend/agents/prompts/`. |
| **NO root main.py usage** | It is a stub. Use `src/backend/main.py`. |
| **NO TUI work** | `src/frontend/` is deprecated. Use `src/web/`. |
| **NO Agent Name Leaks** | Players see "Narrator", not "Rule Agent". |
| **NO AI Dice Rolls** | Only players roll dice (for transparency). |

## COMMANDS

```bash
make install        # Install backend deps (uv)
make install-web    # Install frontend deps (npm)
make check          # Run ALL checks (lint, test, type)
make run-dev        # Start dev servers (PM2)
```

## NOTES
- **Dual Entry**: `main.py` (root) is a dummy. Real app is `src/backend/main.py`.
- **Large File**: `gm.py` (>1200 lines) is a known complexity hotspot.
- **Git**: `src/astinus.egg-info` is tracked (unusual but required).
