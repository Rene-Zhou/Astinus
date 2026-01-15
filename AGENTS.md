# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-15 15:55:00
**Commit:** e2d5152
**Branch:** main
**Stack:** Python 3.13+ (FastAPI, LangChain) + React 19 (Vite, Tailwind, Zustand)

## OVERVIEW

AI-driven TTRPG engine with multi-agent architecture (Star topology: GM Agent orchestrating Rule/NPC/Lore agents). Uses ChromaDB for vector search, SQLite for persistence, and WebSocket for real-time streaming.

## STRUCTURE

```
./
├── src/
│   ├── backend/              # FastAPI server + AI agents
│   │   ├── agents/           # GM, Rule, NPC, Lore, Director agents
│   │   ├── api/              # REST endpoints + WebSocket
│   │   ├── core/             # Pydantic schemas, settings, i18n, prompt loader
│   │   ├── models/           # Data models (game state, world packs, persistence)
│   │   └── services/         # Game logic (dice, world loader, narrative, vector store)
│   └── web/                 # React frontend
│       ├── src/
│       │   ├── components/     # React UI components
│       │   ├── stores/        # Zustand state management
│       │   ├── hooks/         # Custom React hooks
│       │   ├── api/           # Frontend API clients + WebSocket
│       │   └── utils/        # Frontend utilities
│       └── dist/             # Production build
├── tests/                   # Backend tests (pytest) + Frontend tests (Vitest)
├── data/                    # SQLite saves, ChromaDB vector store
├── config/                  # settings.yaml (secrets - use settings.example.yaml)
├── locale/                  # i18n bundles (cn/en)
└── docs/                    # Architecture, API types, plans
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| **Add AI Agent** | `src/backend/agents/` | Use Jinja2 templates in `prompts/*.yaml` - NEVER hardcode |
| **Modify Agent Logic** | `src/backend/agents/gm.py` | Central ReAct orchestrator (1240 lines - refactor candidate) |
| **New API Endpoint** | `src/backend/api/v1/` | Router pattern, add to `main.py` |
| **React Component** | `src/web/src/components/` | TailwindCSS, i18n for text |
| **State Management** | `src/web/src/stores/` | Zustand stores with Immer |
| **Game Logic** | `src/backend/services/` | Dice, world loader, narrative manager |
| **Data Models** | `src/backend/models/` | Pydantic domain models, SQLAlchemy for persistence |
| **Type Sharing** | `docs/API_TYPES.ts` | Manual sync (no auto-gen) |

## CODE MAP

| Symbol | Type | Location | Refs | Role |
|---------|-------|-----------|-------|------|
| `GMAgent` | Class | `src/backend/agents/gm.py` | High | Central ReAct orchestrator, context slicing |
| `GameState` | Class | `src/backend/models/game_state.py` | High | Single source of truth |
| `WorldPackLoader` | Class | `src/backend/services/world.py` | Medium | Loads/validates world packs |
| `NarrativeManager` | Class | `src/backend/services/narrative.py` | Medium | Narrative graph, scene transitions |
| `DicePool` | Class | `src/backend/services/dice.py` | Medium | 2d6 mechanics, bonus/penalty dice |
| `gameStore` | Store | `src/web/src/stores/gameStore.ts` | High | Frontend game state, WebSocket |
| `PromptLoader` | Class | `src/backend/core/prompt_loader.py` | High | Jinja2 prompt template manager |
| `I18nService` | Class | `src/backend/core/i18n.py` | High | Centralized localization |

## CONVENTIONS

### Python (Backend)
- **Linter/Formatter**: Ruff (line-length=100, double quotes)
- **Type Check**: MyPy (python_version="3.13")
- **Prompts**: Jinja2 templates in `agents/prompts/*.yaml` — NEVER hardcode
- **Settings**: YAML-based (`config/settings.yaml`), loaded via `pydantic-settings`
- **Async**: All database and LLM calls must be async
- **Services**: Singleton pattern with `get_*()` functions

### TypeScript (Frontend)
- **Strict Mode**: `strict: true`
- **No Unused**: `noUnusedLocals`, `noUnusedParameters` enforced
- **Testing**: Vitest + React Testing Library
- **i18n**: Use `useTranslation()` hook, never hardcode strings
- **State**: Zustand + Immer for immutable updates
- **Styling**: TailwindCSS utility classes only (no inline styles)

### Git
- Branch: `feature/<name>` or `fix/<name>`
- PR required for merge
- Commit: Conventional Commits (not enforced, but recommended)

## ANTI-PATTERNS (THIS PROJECT)

| Rule | Reason |
|------|--------|
| **NO hardcoded strings** | Use i18n bundles (`locale/*.json`) or `LocalizedString` objects |
| **NO AI dice rolls** | Only player rolls (transparency) |
| **NO agent name leaks** | Never expose "Rule Agent", "Lore Agent" in output |
| **NO NPC real names** | Use descriptions until player learns them |
| **NO prompt hardcoding** | All prompts in `agents/prompts/*.yaml` |
| **NO context bloat** | Use context slices (GM prepares for sub-agents) |
| **NO TUI frontend work** | `src/frontend/` is deprecated; all work in `src/web/` |
| **NO ID exposure** | Internal IDs (e.g., `village_well`) never shown to player |
| **NO full history** | Never send entire game history to sub-agents |

## UNIQUE STYLES

- **Star Topology**: GM Agent as central hub, context slicing for sub-agents
- **ReAct Loop**: GM iterates max 3-5 times, can `CALL_AGENT` or `RESPOND`
- **Two-Phase Narrative**: GM connects NPC dialogue/actions exactly as generated (maintains consistency)
- **Director Agent**: Hidden agent tracking narrative beats, pacing, and tension
- **Dice State Resumption**: GM saves ReAct state during dice checks, resumes with result
- **Manual Type Sync**: `docs/API_TYPES.ts` must match Pydantic models manually
- **PM2 for Dev**: Unusual but preferred - uses PM2 to run both backend and frontend

## COMMANDS

```bash
# Backend
uv sync                             # Install deps
uv run pytest                        # Run tests
uv run ruff check                    # Lint
uv run ruff format                   # Format
uv run mypy                          # Type check
uv run uvicorn src.backend.main:app --reload  # Dev server (or use PM2)

# Frontend
cd src/web
npm install
npm run dev                          # Dev server (or use PM2)
npm run build                        # Production
npm test                             # Vitest
npm run lint                         # ESLint

# PM2 (recommended for development)
pm2 start pm2.config.js             # Start both servers
pm2 status                          # Check status
pm2 logs                            # View logs
pm2 stop all                        # Stop all
```

## NOTES

- **TUI Deprecated**: `src/frontend/` is deprecated; all frontend work in `src/web/`
- **Dual Entry**: Root `main.py` is stub ("Hello from astinus!"); real entry is `src/backend/main.py`
- **Manual Type Sync**: `docs/API_TYPES.ts` must match Python Pydantic models manually
- **PM2 Dev**: `pm2.config.js` manages both dev servers (unusual but preferred here)
- **Large Files**: `gm.py` (1240 lines) is refactoring candidate - extreme nesting (328 lines at 4+ levels)
- **No CI**: No GitHub Actions workflows - CI/CD is manual
- **No Docker**: No docker-compose.yaml - environment setup via `uv` + `npm`
- **Build Artifacts**: `src/astinus.egg-info` should be gitignored but is tracked
