# BACKEND SERVICES KNOWLEDGE BASE

## OVERVIEW
Service layer for game logic, data persistence, and world content orchestration.

## WHERE TO LOOK
| Service | File | Role |
|---------|------|------|
| `WorldPackLoader` | `world.py` | Loads/validates JSON world packs with self-migration. |
| `NarrativeManager` | `narrative.py` | Manages scene transitions and narrative graph. |
| `LocationContextService` | `location_context.py` | Aggregates hierarchical context and atmosphere strings. |
| `DicePool` | `dice.py` | 2d6 mechanics with bonus/penalty dice (roll N take 2). |
| `GameLogger` | `game_logger.py` | Dual-stream logging (debug log + raw LLM JSONL). |
| `DatabaseService` | `database.py` | Async SQLite persistence for sessions and saves. |
| `VectorStoreService` | `vector_store.py` | ChromaDB semantic search for lore and memories. |

## CONVENTIONS
- **Singleton Access**: Core services managing shared resources (DB, Vector Store, World Loader, Logger) use `get_*()` functions for access.
- **Instantiable Helpers**: Logic-heavy services like `LocationContextService` and `NarrativeManager` can be instantiated as needed, usually passing the loader/graph in `__init__`.
- **i18n-first**: All service-generated strings must support localized output via `lang` parameter.
- **Async Required**: Database (`DatabaseService`) and Vector Store operations must be awaited.
- **Pydantic Driven**: Use `BaseModel` for complex data transfer between services and agents.

## ANTI-PATTERNS
- **NO direct instantiation of Core Services**: Never call `WorldPackLoader()` or `DatabaseService()` directly; use the singleton accessor.
- **NO raw prompt strings**: Build atmosphere/guidance strings via `LocationContextService`.
- **NO absolute paths**: Always use `Path` objects relative to project root for data/pack access.

## NOTES
- `WorldPackLoader` automatically handles schema migration for older world pack formats.
- `GameLogger` provides a unified formatter for both app logs and uvicorn/fastapi logs.
- `DicePool` ensures results never exceed 12 (natural) by keeping exactly 2 dice from the pool.
