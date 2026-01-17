# Astinus Migration Plan: Python to TypeScript

## 1. Motivation & Goals

The primary goal of this migration is to transform **Astinus** into a truly portable, cross-platform application that is easy to distribute.

- **Unified Technology Stack**: Moving from a hybrid (Python Backend + Node Frontend) to a full Node.js/TypeScript stack.
- **Packaging & Distribution**: Enabling simple packaging (via Electron or single-binary Node builds) for Windows, macOS, and Linux without complex Python environment management.
- **Modern AI Infrastructure**: Leveraging the newest developments in JavaScript AI tooling (Vercel AI SDK, Transformers.js) that offer better type safety and structured output support than their Python counterparts.

## 2. Global Architecture Changes

| Layer | Current (Python) | Future (TypeScript) | Key Benefit |
| :--- | :--- | :--- | :--- |
| **API Server** | FastAPI | **Hono** | Lightweight, Edge-ready, extremely fast. |
| **AI Orchestration** | LangChain / Custom Loop | **Vercel AI SDK (Core)** | Native structured output (`generateObject`), robust streaming. |
| **Database** | SQLite + SQLAlchemy | **SQLite + Drizzle ORM** | Type-safe SQL queries, better migration DX. |
| **Vector Store** | ChromaDB (Python Server) | **LanceDB** (Embedded) | No separate DB process needed; runs in-process. |
| **Embeddings** | SentenceTransformers | **Transformers.js** | Runs ONNX models directly in Node, zero Python dependency. |
| **Models** | Pydantic | **Zod** | Runtime validation + Static type inference in one. |
| **NLP/Tokenization** | Jieba | **Intl.Segmenter** / **nodejieba** | Native browser/Node APIs. |

### 2.1 Communication
The architecture remains **Client-Server**. The Frontend (React/Vite) will continue to communicate with the Backend via REST and WebSockets.
- **Impact on Frontend**: Minimal. API endpoints and WebSocket event payloads will maintain contract parity.

## 3. Detailed Technology Decisions

### 3.1 AI Agent Framework: Vercel AI SDK
Instead of porting the extensive manual ReAct loop from `gm.py`, we will leverage Vercel AI SDK's **`generateObject`**.
- **Current Issue**: The Python `gm.py` spends hundreds of lines manually parsing JSON from LLM responses and fixing errors.
- **New Solution**: `generateObject` forces the LLM to adhere to a Zod schema. The loop becomes significantly cleaner, focusing only on the *logic* of the loop, not the *parsing*.

### 3.2 Vector Search: Transformers.js + LanceDB
To achieve the goal of "easy packaging," we must eliminate heavy dependencies like PyTorch.
- **Transformers.js**: Runs quantized ONNX versions of embedding models (like `all-MiniLM-L6-v2`) directly in V8.
- **LanceDB**: An embedded vector database that runs in-process. It stores data in files, making "save games" or "world packs" easy to manage as simple folders.

## 4. Migration Strategy

The migration will be performed in phases to ensure stability.

### Phase 1: Foundation (Current Step)
- Initialize `src/backend-ts` directory.
- Set up **Hono** server structure.
- Configure ESLint, Prettier, and TypeScript strict mode.
- Establish **Drizzle ORM** schema mirroring the current SQLite structure.

### Phase 2: Core Services
- Port `services/world.py` (WorldPackLoader) using **Zod** for schema validation.
- Port `models/*.py` (Pydantic) to Zod schemas.
- Implement the Dice Roller (`services/dice.py`).

### Phase 3: The AI Engine
- Set up **Transformers.js** for embeddings.
- Implement **LanceDB** implementation for storing Lore and Memories.
- Create the **GMAgent** shell using Vercel AI SDK.

### Phase 4: Key Agent Logic (The "Brain" Transplant)
- Port the **ReAct Loop** logic from `gm.py` to `gm.ts`.
- Port **NPC Agents** (`npc.py`) and their "Soul" prompt construction.
- Implement streaming responses (Server-Sent Events or custom WebSocket stream) to match current typewriter feel.

### Phase 5: API & WebSocket Parity
- Recreate all FastAPI endpoints in Hono.
- Recreate the WebSocket handle logic (`connection_manager`).
- **Verification**: Point the existing React frontend to the new Node backend port (e.g., 3000) and verify full functionality.

### Phase 6: Cleanup & Packaging
- Remove the Python backend.
- (Optional) Wrap the entire stack in **Electron** for a single executable release.

## 5. Directory Mapping

| Python Location | TypeScript Location | Description |
| :--- | :--- | :--- |
| `src/backend/main.py` | `src/backend-ts/src/index.ts` | App Entry Point |
| `src/backend/agents/*.py` | `src/backend-ts/src/agents/*.ts` | Agent Logic |
| `src/backend/models/*.py` | `src/backend-ts/src/schema/*.ts` | Zod Schemas & Types |
| `src/backend/services/*.py` | `src/backend-ts/src/services/*.ts` | Business Logic |
| `src/backend/core/config.py` | `src/backend-ts/src/config.ts` | Environment Config |

## 6. Risk Assessment

1.  **Prompt Compatibility**: Prompts tuned for Python LangChain might perform slightly differently with Vercel AI SDK.
    *   *Mitigation*: We will reuse the exact prompt text files but wrap them in Vercel SDK's `messages` format.
2.  **Embedding Differences**: Transformers.js (ONNX) outputs might vary slightly from PyTorch outputs.
    *   *Mitigation*: Acceptable for game lore semantic search; exact float precision is not required for this use case.

## 7. Next Steps

1.  Create `src/backend-ts` structure.
2.  Install dependencies: `hono`, `zod`, `drizzle-orm`, `ai` (Vercel SDK), `@xenova/transformers`.
3.  Port the `WorldPackLoader` as a proof-of-concept for the new data layer.
