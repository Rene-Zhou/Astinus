# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-14 12:16:31
**Branch:** (see git branch)
**Stack:** Python 3.13+ (FastAPI, LangChain) + React 19 (Vite, Tailwind, Zustand)

## OVERVIEW

AI-driven TTRPG engine with multi-agent architecture (GM Agent orchestrating Rule/NPC/Lore agents). Star topology centered on GM, using ChromaDB for vector search and SQLite for persistence.

## STRUCTURE

```
./
├── src/
│   ├── backend/          # FastAPI server + AI agents
│   │   ├── agents/       # GM, Rule, NPC, Lore agents (STAR topology center)
│   │   ├── api/          # REST endpoints + WebSocket
│   │   ├── core/         # Pydantic schemas, settings, i18n
│   │   ├── models/       # Data models, SQLAlchemy entities
│   │   └── services/     # Game logic, dice, world packs
│   └── web/              # React frontend
│       ├── src/
│       │   ├── components/  # React UI components
│       │   ├── stores/      # Zustand state management
│       │   ├── hooks/       # Custom React hooks
│       │   └── api/         # Frontend API clients
│       └── dist/         # Production build
├── tests/                # Backend tests (pytest)
├── data/                 # SQLite saves, ChromaDB vector store
├── docs/                 # Architecture, API types, plans
└── config/               # settings.yaml (secrets)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add AI Agent | `src/backend/agents/` | Use Jinja2 templates in `prompts/` |
| New API Endpoint | `src/backend/api/v1/` | Router pattern, add to main.py |
| React Component | `src/web/src/components/` | TailwindCSS, i18n for text |
| State Management | `src/web/src/stores/` | Zustand stores |
| Game Logic | `src/backend/services/` | Dice, rolls, rules |
| Type Sharing | `docs/API_TYPES.ts` | Manual sync (no auto-gen) |

## CONVENTIONS

### Python (Backend)
- **Linter/Formatter**: Ruff (line-length=100, double quotes)
- **Type Check**: MyPy (python_version="3.13")
- **Prompts**: Jinja2 templates in `agents/prompts/*.yaml` — NEVER hardcode
- **Settings**: YAML-based (`config/settings.yaml`), loaded via `pydantic-settings`

### TypeScript (Frontend)
- **Strict Mode**: `strict: true`
- **No Unused**: `noUnusedLocals`, `noUnusedParameters` enforced
- **Testing**: Vitest + React Testing Library
- **i18n**: Use `useTranslation()` hook, never hardcode strings

### Git
- Branch: `feature/<name>` or `fix/<name>`
- PR required for merge

## ANTI-PATTERNS (THIS PROJECT)

| Rule | Reason |
|------|--------|
| **NO hardcoded strings** | Use i18n bundles or world packs |
| **NO AI dice rolls** | Only player rolls (transparency) |
| **NO agent name leaks** | Never expose "Rule Agent", "Lore Agent" in output |
| **NO NPC real names** | Use descriptions until player learns them |
| **NO prompt hardcoding** | All prompts in `agents/prompts/*.yaml` |
| **NO context bloat** | Use context slices, not full history |
| **NO TUI frontend work** | `src/frontend/` is deprecated |

## COMMANDS

```bash
# Backend
uv sync              # Install deps
uv run pytest        # Run tests
uv run ruff check    # Lint
uv run ruff format   # Format
uv run mypy          # Type check
uv run uvicorn src.backend.main:app --reload  # Dev server

# Frontend
cd src/web
npm install
npm run dev          # Dev server
npm run build        # Production
npm test             # Vitest
npm run lint         # ESLint
```

## NOTES

- **TUI Deprecated**: `src/frontend/` is deprecated; all frontend work in `src/web/`
- **Dual Entry**: Root `main.py` is stub; real entry is `src/backend/main.py`
- **Manual Type Sync**: `docs/API_TYPES.ts` must match Python Pydantic models manually
- **PM2 Dev**: `pm2.config.js` manages both dev servers (unusual but used here)
