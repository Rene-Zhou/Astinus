# API - REST Endpoints + WebSocket

**Scope:** FastAPI endpoints and real-time communication

## OVERVIEW

REST API for game operations, settings, and WebSocket for streaming narrative. Endpoints organized by router pattern in `v1/`.

## STRUCTURE

```
api/
├── v1/                    # Router modules
│   ├── __pycache__/
│   ├── game.py           # Game state, actions
│   ├── settings.py       # Runtime settings
│   └── websockets.py     # Real-time streaming
├── __pycache__/
└── (main router integration)
```

## WHERE TO LOOK

| Task | File |
|------|------|
| Game actions | `v1/game.py` |
| Settings API | `v1/settings.py` |
| WebSocket streaming | `v1/websockets.py` |
| Router registration | `src/backend/main.py` |

## CONVENTIONS

- Router pattern: each `v1/*.py` is a router, included in main.py
- Use `APIRouter(prefix="/v1", tags=["..."])`
- WebSocket: `websockets.py` for streaming narrative

## NOTES

- WebSocket used for typewriter effect streaming
- All endpoints return Pydantic models
