# Backend Refactoring Feasibility Study: Python -> TypeScript + Vercel AI SDK

## 1. Executive Summary
This document analyzes the feasibility, benefits, and risks of rewriting the current Python + LangChain backend into a TypeScript-based architecture using the Vercel AI SDK.

**Conclusion (Preliminary)**: [Pending final analysis]
**Recommendation**: [Pending]

## 2. Current Architecture Analysis (Python)
### 2.1 Core Components
- **Orchestration**: `GMAgent` (Star Topology) using a custom ReAct loop (`src/backend/agents/gm.py`).
- **Framework**: FastAPI (REST + WebSockets).
- **State**: Pydantic models (`GameState`) + SQLite + ChromaDB.
- **AI Stack**: LangChain Python (Agents, Chains, Prompt Templates).

### 2.2 Key Complexity Points
- **Stateful ReAct Loop**: The `GMAgent` implements a custom state machine that pauses for user input (dice rolls) and resumes.
- **Context Slicing**: Sophisticated logic to partition `GameState` for different sub-agents (`Rule`, `NPC`, `Lore`) to prevent info leakage.
- **Prompt Management**: Custom Jinja2/YAML loader.

## 3. Target Architecture Analysis (TypeScript)
### 3.1 Technology Stack
- **Runtime**: Node.js / Edge Runtime (Next.js).
- **AI Framework**: Vercel AI SDK (Core + UI).
- **Database**: 
  - Relational: Drizzle ORM + SQLite (via `better-sqlite3` or `libsql`).
  - Vector: ChromaDB JS Client.
- **API**: Next.js API Routes / Server Actions.

### 3.2 Vercel AI SDK Capability Mapping
| Python Component | TypeScript Equivalent | Notes |
|------------------|-----------------------|-------|
| `GMAgent` Loop   | `ai` SDK Core (`generateText` + recursive calls) | Vercel AI SDK is lower-level than LangChain, offering more control but less "magic". |
| LangChain Tools  | `ai` SDK `tools` definition | Zod-based schema definition (cleaner than Pydantic v1). |
| `PromptLoader`   | TS Template Literals / Functions | Type-safe prompt construction. |
| ChromaDB Service | `chromadb` (JS Client) | Direct feature parity. |

## 4. Gap Analysis & Risks
### 4.1 Feature Parity
| Feature | Python (LangChain) | TypeScript (Vercel AI SDK) | Gap |
|---------|-------------------|----------------------------|-----|
| **ReAct Agents** | Native `AgentExecutor` or custom loop | `generateText` with `tools` + recursive calling | **Medium**: Requires reimplementing the loop logic manually (which Astinus `GMAgent` already does in Python). Vercel AI SDK doesn't have a pre-built "AgentExecutor" black box, which is actually a *good* thing for control. |
| **Vector Search** | `langchain_community.vectorstores` | Direct `chromadb` JS client | **None**: JS client is mature. |
| **Local LLMs** | `langchain_community.llms.Ollama` | `ollama-ai-provider` | **None**: First-class support in Vercel AI SDK. |
| **Prompt Templates** | Jinja2 (Advanced logic) | JS Template Literals | **Low**: JS template literals are powerful, but complex logic (loops/conditionals inside prompts) might need helper functions or a template engine like `handlebars` or `mustache` if strictly needed. |

### 4.2 Risks
1.  **Migration Effort**: Porting the custom ReAct loop (`src/backend/agents/gm.py`) is non-trivial. It handles `GMActionType.RESPOND` vs `GMActionType.CALL_AGENT` and manages a state machine. This logic must be rewritten in TS.
2.  **Numeric/Logic Heavy**: If the backend does heavy math (e.g. complex dice probabilities using numpy), TS is fine but libraries differ. (Astinus seems to use simple 2d6 logic, so low risk).
3.  **Dependency Maturity**: Python is the "native" language of AI. Some niche research papers/implementations land in Python first. However, for "Application Layer" AI (Orchestration), TS is catching up fast.

## 5. Migration Strategy (Recommended)
### Phase 1: Hybrid approach (Prototyping)
1.  Initialize a new **Next.js** project in `src/web-next` (or migrate `src/web`).
2.  Install `ai` and `chromadb`.
3.  Port one simple agent (e.g., `LoreAgent`) to a Next.js API Route to validate the stack.

### Phase 2: Core Loop Migration
1.  Port `GameState` Pydantic models to Zod schemas.
2.  Reimplement `GMAgent`'s `_run_react_loop` using `generateText` and a `while` loop in TS.
3.  Unit test the TS GM Agent against the same inputs as the Python version.

### Phase 3: Cutover
1.  Replace the FastAPI WebSocket with Vercel AI SDK `streamText` / `DataStream`.
2.  Decommission Python backend.

## 6. Frontend Implications
- **Current**: React + Vite + Python Backend (WebSocket).
- **Target**: Next.js (Fullstack) OR React + Vite + Node/Hono Backend.
- **Benefit**: `GameState` types can be shared directly (Monorepo or defined in shared package).
- **Benefit**: No need for `uv` / Python runtime for end-users (easier desktop packaging via Electron/Tauri).

## 7. Distribution & Cross-Platform Benefits
One of the strongest arguments for this refactor is **distribution**.
- **Python Backend**: Distributing a Python app to end-users (Desktop/Mobile) requires bundling a Python interpreter (e.g., PyInstaller, Briefcase), which is heavy (~100MB+) and complex to secure/sign.
- **TypeScript Backend**:
  - **Desktop**: Can be bundled with Electron or Tauri. Node.js is easier to bundle than Python.
  - **Mobile**: Logic can potentially run *on-device* if moved to the client (using proprietary device models or WebLLM), or keep the backend serverless.
  - **Web**: Deploys natively to Vercel/Netlify Edge.

## 8. Conclusion
Refactoring is **highly feasible** and recommended for a "Product" focus (distribution, UI/UX). The Python logic, while sophisticated, is architectural (loops, state) rather than computational (numpy/pandas), making it a good candidate for TypeScript. 

**Recommendation**: Proceed with **Phase 1 (Prototyping)** to validate the `GMAgent` loop in TypeScript before full commitment.

