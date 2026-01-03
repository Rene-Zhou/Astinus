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
├── locale/                   # Localization resources (en, cn) with fallback metadata
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
  - `GM Agent`: Indexing conversation history for long games.

### 3.3 向量数据库 (ChromaDB)

ChromaDB provides semantic search capabilities for retrieval-augmented generation (RAG).

#### 3.3.1 存储策略

**持久化模式**:
- 使用 `PersistentClient` 存储向量数据到磁盘
- 默认存储路径: `data/vector_store/chroma_db`
- 单例模式 (`VectorStoreService`) 确保全局唯一实例
- 懒加载初始化，首次使用时创建 Collection

**Embedding 模型**:
- 模型: `all-MiniLM-L6-v2` (ChromaDB 默认)
- 向量维度: 384
- 支持中英文语义检索
- CPU 快速推理 (~1000 docs/sec)
- 无 API 成本

#### 3.3.2 Collection 设计

三种核心 Collection 类型:

**1. Lore Entries Collection**
```python
collection_name = f"lore_entries_{world_pack_id}"
# 存储: 世界包的 Lore Entry 内容
# 文档: 中英文分别索引 (content.cn, content.en)
# 元数据: {"uid": int, "keys": list, "order": int, "lang": str}
# 示例: lore_entries_demo_pack
```

**2. NPC Memories Collection**
```python
collection_name = f"npc_memories_{npc_id}"
# 存储: NPC 的历史记忆事件
# 文档: 记忆内容 ("玩家给了我一本珍贵的古籍")
# 元数据: {"npc_id": str, "keywords": str, "timestamp": str}
# 示例: npc_memories_chen_ling
```

**3. Conversation History Collection**
```python
collection_name = f"conversation_history_{session_id}"
# 存储: 游戏会话的对话历史
# 文档: 消息内容
# 元数据: {"role": str, "turn": int, "timestamp": str, "agent": str}
# 示例: conversation_history_test-game-123
```

#### 3.3.3 Agent 使用模式

**LoreAgent 混合搜索**:
```python
# 权重配置
KEYWORD_MATCH_WEIGHT = 1.0      # 关键词明确信号强
VECTOR_MATCH_WEIGHT = 0.7       # 语义相似度次要
DUAL_MATCH_BOOST = 1.5          # 双重匹配加成

# 搜索流程
1. 关键词匹配 (现有实现)
2. 向量相似度搜索 (top 10)
3. 综合评分算法
4. 按 score 降序 + entry.order 升序排序
5. 返回 top 5
```

**NPCAgent 记忆检索**:
```python
# 检索逻辑
- 当 NPC 有记忆且启用向量存储时
- 使用语义搜索检索 top 3 相关记忆
- 在系统提示的"近期记忆"部分展示
- 失败时优雅降级到关键词或最近记忆
```

**GMAgent 历史检索**:
```python
# 阈值策略
- 消息 < 10: 返回全部 (无需检索)
- 消息 ≥ 10: 向量搜索 top 5
- 搜索结果按 turn 排序保持时间顺序
- 失败时降级到最近消息
```

#### 3.3.4 性能与容错

**性能优化**:
- 批量索引 (100+ 文档/批)
- 懒加载索引 (首次使用时)
- 限制结果集大小 (top 5-10)

**容错机制**:
- 所有向量操作包装在 try-except 中
- 向量存储不可用时自动降级到关键词搜索
- 搜索失败时回退到最近内容

**持久化**:
- ChromaDB 自动持久化到磁盘
- 应用重启后自动加载现有数据
- VectorStoreService.reset_instance() 用于测试隔离

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

## 8. Internationalization Strategy

### 8.1 Resource Organization
- All user-facing strings must live in locale bundles under `locale/<lang-code>/*.json` (or equivalent), following the `en` and `cn` baseline.
- Textual widgets load through a dedicated localization service that supports runtime language switching and pluralization.
- Backend services expose language-neutral identifiers; FastAPI responses select message templates based on the `Accept-Language` header with fallback to project default.

### 8.2 Content Assets
- World packs and prompt templates store multi-language payloads (`content.cn`, `content.en`) as described in `GUIDE.md`, and deployments must run validation to guarantee parity across required locales.
- Narrative graph metadata, dice messages, and error descriptions follow the same structured format to avoid hardcoded literals in code.

### 8.3 Tooling & Testing
- Introduce localization linters in CI to detect missing keys, orphaned strings, and untranslated content.
- Automated tests must cover at least `en` and `cn` rendering paths for the TUI and key REST endpoints.
- Developer documentation should outline the process for adding new locales, including translation memory updates and fallback behavior.
