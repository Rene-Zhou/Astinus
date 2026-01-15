# API - REST Endpoints + WebSocket

**Scope:** FastAPI endpoints and real-time communication

## OVERVIEW

REST API for game operations, settings, and WebSocket for streaming narrative. Endpoints follow a modular router pattern, with core logic delegated to services.

## STRUCTURE

```
api/
├── v1/                    # Router modules
│   ├── game.py           # Game state, actions (Complexity Hotspot)
│   └── settings.py       # LLM Provider & Agent settings
└── websockets.py         # Real-time streaming (Star Topology hub)
```

## WHERE TO LOOK

| Task | File |
|------|------|
| Game Session/Actions | `v1/game.py` |
| LLM/Agent Config | `v1/settings.py` |
| Real-time Streaming | `websockets.py` |
| Router Registration | `src/backend/main.py` |

## CONVENTIONS

- **Router Pattern**: Each module exports an `APIRouter`, included in `main.py`.
- **Pydantic**: Strict use of Pydantic models for all Request/Response bodies.
- **Service-Only**: NO direct database or vector store access in endpoints.
- **Async**: All endpoints and WebSocket handlers must be `async`.

## NOTES

- **Complexity Hotspot**: `v1/game.py` (~630 lines) acts as a fat controller.
  - `start_new_game`: ~210 lines handling world loading, NPC agent registration, and state initialization. Refactoring candidate.
- **WebSocket Streaming**: 
  - Supports typewriter effect with chunked content delivery.
  - Handles two-way game flow: `DICE_CHECK` requests from server -> `DICE_RESULT` from client.
  - Broadcasts phase changes (e.g., `processing` -> `narrating` -> `waiting_input`).
- **Error Handling**: Standardized via FastAPI `HTTPException` returning JSON details.
