# Astinus Architecture Documentation

This document defines the technical architecture, directory structure, and engineering standards for the Astinus project. It bridges the gap between the domain logic in `GUIDE.md` and the development standards in `CLAUDE.md`.

## 1. System Overview

Astinus follows a **Client-Server** architecture, even when running locally. This separation ensures scalability and allows the TUI frontend to be decoupled from the heavy AI processing logic.

- **Frontend (Client)**: A Terminal User Interface (TUI) built with `Textual`. It handles user input, rendering, and state display.
- **Backend (Server)**: A `FastAPI` application that hosts the Game Engine, Agents, and Database.
- **AI Layer**: `LangChain` orchestrates the interaction between the Backend and LLMs.

## 2. Directory Structure

The project follows a strict separation of concerns:

```text
Astinus/
├── src/
│   ├── backend/              # FastAPI Application & Game Logic
│   │   ├── agents/           # LangChain Agent Implementations
│   │   │   ├── gm.py         # GM Agent (Orchestrator)
│   │   │   ├── npc.py        # NPC Agent (Persona & Memory)
│   │   │   ├── rule.py       # Rule Agent (Dice & Checks)
│   │   │   └── lore.py       # Lore Agent (RAG)
│   │   ├── api/              # API Routers
│   │   │   ├── v1/
│   │   │   └── websockets.py # Real-time game stream
│   │   ├── core/             # Config, Logging, DB setup
│   │   ├── models/           # Pydantic Models (Schemas)
│   │   │   ├── game_state.py # Matches GUIDE.md GameState
│   │   │   └── character.py  # Matches GUIDE.md NPC definitions
│   │   ├── services/         # Business Logic
│   │   │   ├── dice.py       # RNG & Mechanics
│   │   │   └── world.py      # World Pack Loader
│   │   └── main.py           # App Entrypoint
│   │
│   ├── frontend/             # Textual TUI Application
│   │   ├── app.py            # TUI Entrypoint
│   │   ├── client.py         # HTTP/WebSocket Client
│   │   ├── screens/          # Different views (Game, Character Sheet, Inventory)
│   │   └── widgets/          # Reusable UI components (ChatBox, StatBlock)
│   │
│   └── shared/               # Shared utilities or types (if needed)
│
├── data/                     # Data Storage
│   ├── packs/                # World Packs (YAML)
│   ├── saves/                # SQLite databases for save games
│   └── vector_store/         # ChromaDB persistence directory
│
├── docs/                     # Documentation
├── tests/                    # Pytest suite
├── config/                   # Configuration files (LLM keys, settings)
├── pyproject.toml            # Dependencies (uv)
└── uv.lock
```

## 3. Data Persistence

### 3.1 Structured Data (SQLite)
We use **SQLite** for storing the deterministic game state.
- **Why**: Zero-config, single-file portability for save games.
- **Scope**:
  - `GameState`: Current scene, turn count, active flags.
  - `Player`: Stats, inventory, quest log.
  - `NPC Body`: Location, inventory, relationship tables (as defined in `GUIDE.md`).

### 3.2 Unstructured Data (Vector DB)
We use **ChromaDB** (local mode) for semantic search.
- **Why**: Efficient retrieval for RAG (Retrieval-Augmented Generation).
- **Scope**:
  - `Lore Agent`: Indexing World Packs (`data/packs/**/*.yaml`).
  - `NPC Memory`: Storing episodic memories ("Player helped me kill the wolf").

## 4. Communication Protocols

### 4.1 REST API
Used for stateless or transactional operations.
- `POST /game/load`: Load a save file or start a new game.
- `GET /character/{id}`: Fetch character sheet details.
- `POST /action/command`: Send a discrete player command (e.g., "Equip Sword").

### 4.2 WebSockets
Used for the main game loop to support streaming text and real-time updates.
- **Endpoint**: `/ws/game/{session_id}`
- **Flow**:
  1. Client sends user input (text).
  2. Server processes input via GM Agent.
  3. Server streams back tokens (Typewriter effect).
  4. Server pushes state updates (e.g., HP change) as JSON events interleaved with text.

## 5. AI & Prompt Engineering

### 5.1 Model Configuration
Configuration is managed via `config/settings.yaml` (not committed to git) or Environment Variables.
- **Provider**: OpenAI, Anthropic, or Local (Ollama/vLLM).
- **Model**: Defaults to `gemini-3-flash-preview` for GM/NPCs; smaller models(`gemini-2.5-flash-lite`) for Rule Agent.

### 5.2 Prompt Management
Prompts are **NOT** hardcoded in Python strings.
- Location: `src/backend/agents/prompts/`
- Format: `.yaml` or `.txt` files using Jinja2 templating.
- **Example**:
  ```yaml
  # src/backend/agents/prompts/npc_system.yaml
  role: "You are {{ name }}, {{ description }}."
  context: "Current location: {{ location }}. Interacting with: {{ player_name }}."
  constraints: "Keep responses under 50 words. Speak in {{ speech_style }}."
  ```

## 6. Mechanics Implementation (The "Rule Agent")

The Rule Agent acts as the deterministic engine. It does not "guess" outcomes; it calculates them.

### 6.1 Dice System
Located in `src/backend/services/dice.py`.
- **Standard**: d20 System (D&D-like).
- **Function Signature**:
  ```python
  def check(attribute: int, difficulty: int, advantage: bool = False) -> CheckResult:
      ...
  ```

### 6.2 Workflow
1. **GM Agent** detects a risky action: "I try to jump over the chasm."
2. **GM Agent** calls **Rule Agent**: `AssessDifficulty("jump over chasm")`.
3. **Rule Agent** returns: `Target: Agility, DC: 15`.
4. **GM Agent** requests roll from System.
5. **System** performs roll, updates State, and informs GM of result (Success/Failure).
6. **GM Agent** narrates the outcome.

## 7. Migration Strategy (from `cli-ttrpg`)

1. **Story Packs**: The YAML structure in `cli-ttrpg/story_packs` is largely compatible. We will write a migration script to convert them to the `Astinus` World Pack format (adding Vector embeddings).
2. **Dice Logic**: Port `src/weave/game/dice.py` to `src/backend/services/dice.py`.
3. **Agents**: Refactor `src/weave/agents` to use LangChain's `Runnable` interfaces instead of raw API calls.
