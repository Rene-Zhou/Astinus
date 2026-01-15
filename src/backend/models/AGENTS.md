# MODELS KNOWLEDGE BASE

**Location:** `src/backend/models/`
**Status:** Core Domain Layer

## OVERVIEW

Pydantic-driven domain models for game state, world modularity, and i18n-aware persistence.

## WHERE TO LOOK

| Component | File | Role |
|-----------|------|------|
| **GameState** | `game_state.py` | Central truth, ReAct loop state, message history |
| **WorldPack** | `world_pack.py` | Lore entries, location graphs, NPC templates |
| **Player** | `character.py` | Trait-based PC with fate points and status tags |
| **NPCData** | `world_pack.py` | Split-layer NPC (Soul for LLM, Body for data) |
| **Traits** | `trait.py` | Dual-aspect (positive/negative) narrative qualities |
| **Persistence** | `persistence.py` | SQLAlchemy ORM with JSON-to-SQLite serialization |
| **Localization** | `i18n.py` | `LocalizedString` utility for multi-language support |

## CONVENTIONS

- **I18n-First**: Use `LocalizedString` for all user-facing narrative text.
- **Pydantic V2**: Strict type validation and `Field` documentation.
- **Star Topology**: GM Agent manages `GameState`; sub-agents receive immutable context slices.
- **Snake_Case IDs**: Use snake_case for all internal identifiers (locations, NPCs, items).
- **Audit Log**: `GameState.messages` is the append-only source of narrative history.
- **JSON Serialization**: Complex objects (traits, memory) are JSON-serialized in DB.

## ANTI-PATTERNS

- **NO Numerical Stats**: Do not add "Strength" or "HP"; use Traits and Tags.
- **NO Logic in Models**: Models define structure; move logic to `services/`.
- **NO Sub-Agent State**: Sub-agents must never write to the global `GameState`.
- **NO Hardcoded Strings**: Never hardcode NPC names or descriptions in code.
- **NO Direct DB Access**: Use `persistence.py` models only for ORM mappings.

## NOTES

- **Soul vs Body**: NPCs separate narrative personality (Soul) from game state (Body).
- **Tiered Discovery**: Lore entries use `visibility` ('basic' vs 'detailed') for pacing.
- **ReAct Resumption**: `GameState` stores pending ReAct state to survive dice roll waits.
- **Region Hierarchy**: Locations roll up to Regions for consistent narrative atmosphere.
- **Fate Points**: Capped at 5; used for narrative influence in Rule Agent logic.
- **Trait Duality**: Every Trait MUST have both a positive and a negative aspect.
