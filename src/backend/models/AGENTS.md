# MODELS KNOWLEDGE BASE

**Location:** `src/backend/models/`
**Status:** Core Domain Layer (Single Source of Truth)

## OVERVIEW

This directory defines the structural foundation of Astinus. It uses **Pydantic V2** for runtime validation/serialization and **SQLAlchemy 2.0** for SQLite persistence.

> [!CAUTION]
> **CRITICAL: MANUAL TYPE SYNC REQUIRED**
> Any change to these models **MUST** be manually reflected in `docs/API_TYPES.ts`. Failure to do so will break frontend type safety.

## WHERE TO LOOK

| Component | File | Role |
|-----------|------|------|
| **GameState** | `game_state.py` | Global truth owned by GM Agent; tracks phases & turn count. |
| **WorldPack** | `world_pack.py` | Static lore, NPC templates (Soul/Body), and location definitions. |
| **Player** | `character.py` | PC state including Traits (dual-aspect) and Fate Points. |
| **I18n** | `i18n.py` | `LocalizedString` utility for mandatory dual-language support. |
| **Persistence**| `persistence.py` | SQLAlchemy ORM mappings with JSON-to-SQLite serialization. |
| **Traits** | `trait.py` | Logic-less definitions for narrative character qualities. |

## CONVENTIONS

- **I18n-First**: All user-facing narrative text must use `LocalizedString` (cn/en).
- **Pydantic V2**: Use strict typing and `Field` for documentation/defaults.
- **Star Topology**: Only the GM Agent updates the global `GameState`. Sub-agents receive immutable context "slices".
- **Snake_Case IDs**: Use snake_case for all internal identifiers (IDs for locations, items, etc.).
- **Audit Log**: `GameState.messages` is the append-only source of narrative history.

## ANTI-PATTERNS

- **NO Numerical Stats**: Do not use "HP" or "Strength"; use **Traits** and **Tags**.
- **NO Logic in Models**: Models are data containers; move logic to `services/`.
- **NO Sub-Agent Write**: Sub-agents must never modify the global `GameState` directly.
- **NO Direct DB Access**: Use `persistence.py` models only through service layers.

## NOTES

- **Soul vs Body**: NPCs separate narrative personality (Soul) from game state (Body).
- **Fate Points**: Capped at 5; managed via Rule Agent logic.
- **Trait Duality**: Every Trait must have both a positive and a negative narrative aspect.
