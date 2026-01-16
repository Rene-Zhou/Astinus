# API - Interface Layer

**Scope:** FastAPI Routers, WebSocket endpoint, and Request/Response models.

## OVERVIEW

The API layer serves as the entry point for all client interactions, bridging the React frontend with the multi-agent backend. It focuses on request validation, session management, and real-time narrative streaming.

## WHERE TO LOOK

| Task | Location | Role |
|------|----------|------|
| **Game Actions** | `src/backend/api/v1/game.py` | REST endpoints for state and character management. |
| **WebSocket Hub** | `src/backend/api/websockets.py` | Real-time streaming (typewriter effect) and status. |
| **Settings** | `src/backend/api/v1/settings.py` | Provider and Agent configuration endpoints. |
| **Router Registry** | `src/backend/main.py` | Main app initialization and router mounting. |

## CONVENTIONS

- **Thin Routers**: Routers MUST be kept lean. Their sole responsibility is to validate input, call the appropriate service (usually `GMAgent`), and format the output.
- **Pydantic Validation**: All API surface areas use Pydantic for strict type checking and auto-documentation (Swagger).
- **Async/Await**: Every endpoint and WebSocket operation is asynchronous to handle long-running LLM tasks without blocking.
- **Session Mapping**: WebSocket connections are mapped to unique `session_id`s for targeted narrative delivery.

## ANTI-PATTERNS

- **Fat Controllers**: Moving game logic, dice rolling, or lore retrieval into the router modules.
- **Direct Resource Access**: Accessing `vector_store` or `SQLite` directly from endpoints; use services instead.
- **Unstructured JSON**: Returning raw dictionaries instead of defined Pydantic response models.
- **Meta-data Exposure**: Leaking internal agent names or hidden world flags to the player interface.
