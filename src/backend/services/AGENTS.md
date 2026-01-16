# BACKEND SERVICES KNOWLEDGE BASE

## OVERVIEW
The service layer implements the core business logic of the Astinus engine, handling TTRPG mechanics, world content orchestration, and persistent storage. It acts as the "Engine" that Agents interact with to resolve actions and retrieve world state.

## WHERE TO LOOK
| Service | File | Role |
|---------|------|------|
| `DatabaseService` | `database.py` | **[ASYNC]** SQLite persistence for sessions, messages, and saves. |
| `DicePool` | `dice.py` | 2d6 mechanical engine with bonus/penalty support. |
| `NarrativeManager` | `narrative.py` | Orchestrates scene transitions and the narrative graph. |
| `WorldPackLoader` | `world.py` | Loads, validates, and migrates JSON world packs. |
| `VectorStoreService` | `vector_store.py` | ChromaDB semantic search for lore and memories. |
| `LoreService` | `lore.py` | Hybrid search (keyword + vector) for world lore. |
| `LocationContextService` | `location_context.py` | Aggregates hierarchical context for the GM Agent. |

## CONVENTIONS
- **Singleton Pattern**: Core services managing shared resources (DB, Vector Store, World Loader) MUST be accessed via `get_*()` functions (e.g., `get_database_service()`). This ensures consistent state across the application.
- **Async IO Required**: All Database operations are asynchronous using `aiosqlite`. Any service method performing IO must be `async` and operations MUST be `await`-ed.
- **2d6 Mechanics**:
  - **Base Roll**: 2d6 (sum of two dice).
  - **Bonus Dice**: Roll (2 + N) dice, keep the **highest** 2.
  - **Penalty Dice**: Roll (2 + N) dice, keep the **lowest** 2.
  - **Outcome**: 12+ (Critical), 10-11 (Success), 7-9 (Partial), 6- (Failure).
  - **Natural Cap**: This system ensures the natural total (before modifiers) never exceeds 12.
- **i18n-First**: Services producing human-readable metadata (like `DiceResult.to_display()`) must support `lang` parameters (cn/en).

## ANTI-PATTERNS
- **NO Direct Instantiation**: Never call `DatabaseService()` or `WorldPackLoader()` directly; use the singleton accessor to avoid resource leaks or duplicate engines.
- **NO Sync Database Calls**: Avoid blocking the event loop with synchronous DB operations.
- **NO Raw Prompt Strings**: Services should provide structured data or i18n keys. High-level atmosphere strings should be built via `LocationContextService`.
- **NO Absolute Paths**: Always resolve paths relative to the project root using `Path` objects.

## NOTES
- `WorldPackLoader` handles automatic schema migration for older world pack formats.
- `NarrativeManager` maintains a `NarrativeGraph` that tracks global flags and scene states.
- `VectorStoreService` uses `Qwen3-Embedding-0.6B` for high-quality multilingual semantic search.
- `LoreService` implements hybrid search (jieba for keywords + ChromaDB for vectors).
