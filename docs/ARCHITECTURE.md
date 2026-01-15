# Astinus Architecture Documentation

This document defines the technical architecture, directory structure, and engineering standards for the Astinus project. It bridges the gap between the domain logic in `GUIDE.md` and the development standards in `CLAUDE.md`.

## 1. System Overview

Astinus follows a **Client-Server** architecture, even when running locally. This separation ensures scalability and allows the frontend to be decoupled from the heavy AI processing logic.

- **Frontend (Client)**: A React Web Application built with **React 19** + Vite + TypeScript + TailwindCSS. It handles user input, rendering, and state display via REST API and WebSocket.
- **Backend (Server)**: A `FastAPI` application that hosts the Game Engine, Agents, and Database.
- **AI Layer**: `LangChain` orchestrates the interaction between the Backend and LLMs using a multi-agent star topology.

> **Note**: The original Textual TUI frontend (`src/frontend/`) has been deprecated in favor of the React Web frontend.

## 2. Directory Structure

The project follows a strict separation of concerns:

```text
Astinus/
├── src/
│   ├── backend/              # FastAPI Application & Game Logic
│   │   ├── agents/           # LangChain Agent Implementations
│   │   │   ├── gm.py         # GM Agent (Central Orchestrator)
│   │   │   ├── npc.py        # NPC Agent (Soul/Body split)
│   │   │   ├── rule.py       # Rule Agent (2d6 Mechanics)
│   │   │   ├── lore.py       # Lore Agent (RAG)
│   │   │   └── director.py   # Director Agent (Pacing & Tension)
│   │   ├── api/              # API Routers
│   │   │   ├── v1/
│   │   │   └── websockets.py # Real-time game stream
│   │   ├── core/             # Config, Logging, DB setup, Prompt Loader
│   │   ├── models/           # Pydantic Domain Models
│   │   │   ├── game_state.py # Central source of truth
│   │   │   ├── character.py  # Trait-based Player Character
│   │   │   └── world_pack.py # World modularity & NPC templates
│   │   ├── services/         # Business Logic Layer
│   │   │   ├── dice.py       # 2d6 Pool & Mechanics
│   │   │   ├── world.py      # World Pack Loader with Migration
│   │   │   ├── narrative.py  # Narrative Graph & Transitions
│   │   │   ├── location_context.py # Hierarchical context aggregation
│   │   │   ├── game_logger.py# Dual-stream logging (Debug + JSONL)
│   │   │   └── vector_store.py # ChromaDB Service
│   │   └── main.py           # App Entrypoint
│   │
│   ├── web/                  # React 19 Frontend
│   │   ├── src/
│   │   │   ├── api/          # API Client (REST + WebSocket)
│   │   │   ├── components/   # React Components (Chat, StatBlock, Dice)
│   │   │   ├── stores/       # Zustand state management with Immer
│   │   │   ├── hooks/        # Custom React hooks
│   │   │   └── utils/        # i18n and utilities
│   │
│   └── shared/               # Manual Type Sync (docs/API_TYPES.ts)
│
├── data/                     # Data Storage (SQLite, ChromaDB, Packs)
├── locale/                   # i18n bundles (cn/en)
├── docs/                     # Architecture, API types, plans
├── config/                   # Configuration (settings.yaml)
├── pm2.config.js             # Development process management
└── pyproject.toml            # Dependencies (uv)
```

## 3. Data & Model Layers

### 3.1 Pydantic Domain Models
The backend uses Pydantic V2 for strict type validation and documentation.
- **GameState**: The central source of truth. It stores message history, current phase, story flags, and active NPCs.
- **PlayerCharacter**: Pure trait-based design. No numerical stats (like Strength/HP). Uses `traits` (with dual aspects) and `tags` (status conditions).
- **NPCData**: Split-layer design. **Soul** contains narrative personality for the LLM; **Body** contains structured game state (location, inventory, relationships).
- **LocalizedString**: Core utility for i18n, ensuring all narrative text supports `cn` and `en`.

### 3.2 Service Layer
- **WorldPackLoader**: Handles loading and validating modular world packs. Includes self-migration logic for older pack formats.
- **NarrativeManager**: Manages the narrative graph, scene transitions, and global story flags.
- **LocationContextService**: Aggregates hierarchical context (Region > Location) and generates atmosphere strings for agents.
- **VectorStoreService**: ChromaDB wrapper for RAG. Manages collections for Lore, NPC Memories, and Conversation History.
- **GameLogger**: Dual-stream logging. `game_debug.log` for human-readable debugging; `llm_raw.jsonl` for raw AI input/output analysis.

### 3.3 Persistence
- **SQLite**: Stores deterministic game state (GameState, Player, NPC Body). Ensures save-game portability.
- **ChromaDB**: Local persistent storage for semantic search. Uses `all-MiniLM-L6-v2` for embeddings.

## 4. Frontend Architecture (React 19)

### 4.1 UI Design
- **Mobile-First**: Uses bottom panels for mobile devices and a three-column layout for desktop.
- **GamePhase Enum**: Directly controls UI interactivity (e.g., locking input during `narrating` or `processing`).
- **Zustand + Immer**: Manages complex state updates immutably.

### 4.2 Real-time Interaction
- **WebSocket Flow**:
  1. Client sends `player_input`.
  2. Server sends `status` (which agent is acting).
  3. Server streams `content` (typewriter effect).
  4. If check needed: Server sends `dice_check` -> Client shows roller -> Client sends `dice_result` -> Server resumes.
  5. Server sends `complete` with updated metadata (HP, Location).

## 5. Multi-Agent Architecture

### 5.1 Star Topology
The **GM Agent** acts as the central orchestrator. It is the only agent that interacts with the `GameState`.

### 5.2 ReAct Loop
The GM Agent operates in a ReAct (Reasoning + Acting) loop:
1. **Analyze**: Understand player intent.
2. **Call Agent**: GM prepares a **Context Slice** for a sub-agent (Rule, NPC, or Lore).
3. **Synthesize**: Integrate sub-agent output into the narrative.
4. **Iterate**: Repeat 3-5 times if needed before responding.

### 5.3 Specialized Agents
- **Rule Agent**: Calculates deterministic outcomes (2d6 pool). Does not "guess" rules.
- **NPC Agent**: Handles character-specific dialogue using the NPC's "Soul".
- **Lore Agent**: Performs RAG against World Pack lore entries.
- **Director Agent**: A hidden agent that tracks narrative beats, pacing, and tension to guide the GM's tone.

### 5.4 Context Slicing & Narrative Consistency
- **Information Leakage Prevention**: GM only sends relevant data to sub-agents (e.g., NPC Agent only knows what that specific NPC knows).
- **Two-Phase Narrative**: GM connects NPC dialogue or Rule results exactly as generated to maintain consistency.
- **Dice State Resumption**: GM saves its ReAct state during a `DICE_CHECK`, allowing the loop to resume once the result is received.

### 5.5 Implementation Example: ReAct Context Slice
```python
# From gm.py - GM preparing context for NPC Agent
npc_context = {
    "npc_id": target_npc_id,
    "location_id": self.game_state.current_location,
    "history": self.game_state.get_recent_messages(5),
    "world_pack_id": self.game_state.world_pack_id,
    "player_traits": [t.name.cn for t in self.game_state.player.traits],
}
response = await self.npc_agent.run(npc_context)
```

## 6. Game Mechanics (2d6 System)

Astinus has migrated from a d20 system to a **2d6-based pool system**.

### 6.1 Dice Pool Logic
- **Standard**: Roll 2d6, take both.
- **Bonus Dice (+N)**: Roll 2+N dice, keep the **highest** 2.
- **Penalty Dice (-N)**: Roll 2+N dice, keep the **lowest** 2.
- **Natural Max**: The natural roll (before modifiers) is always capped at 12.

### 6.2 Outcomes
- **12+**: Critical Success
- **10-11**: Success
- **7-9**: Partial Success (Success at a cost)
- **6-**: Failure (GM moves)

### 6.3 Implementation Example: Dice Pool
```python
# From dice.py
def roll(self) -> DiceResult:
    net_bonus = self.bonus_dice - self.penalty_dice
    dice_count = 2 + abs(net_bonus)
    all_rolls = [random.randint(1, 6) for _ in range(dice_count)]
    sorted_rolls = sorted(all_rolls, reverse=True)

    if net_bonus >= 0:
        kept_rolls = sorted_rolls[:2] # Bonus: Highest 2
    else:
        kept_rolls = sorted_rolls[-2:] # Penalty: Lowest 2
    
    total = sum(kept_rolls) + self.modifier
    return DiceResult(total=total, ...)
```

## 7. Development & Operations

- **PM2 for Development**: `pm2.config.js` manages both the FastAPI backend and Vite frontend development servers.
- **Manual Type Sync**: TypeScript types in `src/web/src/api/types.ts` and `docs/API_TYPES.ts` must be manually kept in sync with Pydantic models.
- **CI/CD & Docker**: Currently, there are no GitHub Actions or Docker configurations. Environment setup relies on `uv` (Python) and `npm` (Node.js).

## 8. Technical Debt

The following files are identified as refactoring candidates due to complexity:
- `src/backend/agents/gm.py`: 1240 lines, extreme nesting (328 lines at level 4+).
- `src/backend/api/v1/game.py`: 631 lines, contains a 215-line fat controller function.
- `src/backend/agents/npc.py`: 636 lines.

## 9. Internationalization (i18n)

- All user-facing strings are stored in `locale/*.json`.
- World packs and Lore entries use the `LocalizedString` schema (`{cn: "...", en: "..."}`).
- Tiered Discovery: Lore entries support `basic` vs `detailed` visibility to control the flow of information.
