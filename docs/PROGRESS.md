# Astinus 开发进度与规划

> 最后更新：2026-01-07

## 📋 目录
1. [项目概述](#项目概述)
2. [当前状态](#当前状态)
3. [已完成的工作](#已完成的工作)
4. [开发阶段规划](#开发阶段规划)
5. [近期修复](#近期修复)
6. [技术债务与待优化项](#技术债务与待优化项)
7. [下一步计划](#下一步计划)
8. [提交历史摘要](#提交历史摘要)
9. [参考文档](#参考文档)

---

## 项目概述

Astinus 是一个 AI 驱动的叙事向单人 TTRPG 引擎，采用多 Agent 协作架构，通过自然语言交互驱动剧情与规则运行。

### 核心设计理念
- **纯自然语言交互**：玩家通过自由文本描述行动，系统负责解析与裁决。
- **多智能体协作**：GM / NPC / Rule / Lore / Director 等 Agent 协同保障叙事一致性。
- **规则透明可追溯**：所有判定流程向玩家公开，鼓励策略叙事。
- **模块化叙事资产**：故事包与引擎解耦，支持复用与扩展。
- **多语言一致性**：前端界面、系统提示与世界包内容须通过本地化资源提供至少简体中文（cn）与英文（en）版本，禁止硬编码文案。

### 技术栈
| 层级 | 主要技术 | 状态 |
|------|----------|------|
| Web 前端 | React + Vite + TailwindCSS | 🔄 开发中 |
| TUI 前端 | Textual | ⚠️ 已弃用 |
| 后端 API | FastAPI + WebSocket | ✅ 端点定义 / 🔄 路由实现中 |
| AI Orchestrator | LangChain + 多提供商模型 | ✅ 已完成 |
| 数据层 | SQLite（结构化）+ ChromaDB（向量检索） | ✅ 向量完成 / ⏳ 持久化待实现 |
| 构建 & 依赖 | Python ≥3.13, uv | ✅ 已确认 |

---

## 当前状态

### 配置文件位置
| 配置类型 | 约定位置 | 说明 |
|----------|----------|------|
| 项目依赖 | `pyproject.toml`, `uv.lock` | 基础依赖尚未申明 |
| 运行配置 | `config/settings.yaml`（拟定） | 将包含模型/密钥等敏感信息（不入库） |
| 文档规范 | `docs/*.md`, `CLAUDE.md` | 已建立研发规范 |

### 项目结构
当前仓库结构仍处于初始化阶段，仅包含核心文档与占位代码。目标结构参见 `docs/ARCHITECTURE.md`。

---

## 已完成的工作

### Phase 0: 基础规划 ✅ 已完成
- ✅ 补充 `GUIDE.md`：定义世界观、Agent 角色、核心玩法与设计原则。
- ✅ 补充 `ARCHITECTURE.md`：明确前后端分层、目录结构与通信协议。
- ✅ 建立研发规范 (`CLAUDE.md`)：统一依赖管理、分支策略、TDD 要求。
- ✅ 初始化项目骨架：创建 `pyproject.toml`、入口脚本 `main.py`。

---

## 开发阶段规划

### Phase 1: 基础设施搭建 ✅ 已完成
| 任务 | 负责人 | 状态 |
|------|--------|------|
| 1.1 建立 `uv` 依赖清单与虚拟环境 | Backend Team | ✅ 已完成 |
| 1.2 初始化目录结构 `src/backend`, `src/frontend` | Platform Team | ✅ 已完成 |
| 1.3 配置格式化、静态检查与 CI | DevOps | ✅ 已完成（ruff, mypy, pytest 已配置） |
| 1.4 引入 pytest 并创建样例测试 | QA | ✅ 已完成 |
| 1.5 建立多语言资源目录与加载服务（`locale/`、i18n 管线） | Platform Team | ✅ 已完成（I18nService + locale 资源文件 + 21个测试） |

### Phase 2: 后端核心引擎准备 🔄 进行中

#### Week 1: Foundation Layer ✅ 已完成
| 任务 | 状态 | 备注 |
|------|------|------|
| 2.1.1 Data Models | ✅ 已完成 | LocalizedString, Trait, Character, GameState + 53个测试, 99%覆盖率 |
| 2.1.2 Dice System | ✅ 已完成 | DicePool, DiceResult, DiceCheckRequest + 47个测试, 95%覆盖率 |
| 2.1.3 I18nService | ✅ 已完成 | I18nService + system/common 双语资源 + 21个测试, 84%覆盖率 |

**Week 1 总计**: 121个测试通过, 95%整体覆盖率

#### Week 2: Agent Infrastructure ✅ 已完成
| 任务 | 状态 | 备注 |
|------|------|------|
| 2.2.1 LangChain Agent Base | ✅ 已完成 | BaseAgent(Runnable) + LLM Provider Factory + 38个测试, 89%/74%覆盖率 |
| 2.2.2 Prompt Template System | ✅ 已完成 | PromptLoader + YAML/Jinja2 + rule_agent/gm_agent模板 + 26个测试, 96%覆盖率 |

**Week 2 总计**: 64个测试通过, 新增依赖: langchain-openai, pyyaml, jinja2

#### Week 3: Core Agents ✅ 已完成
| 任务 | 状态 | 备注 |
|------|------|------|
| 2.3.1 Rule Agent | ✅ 已完成 | 规则裁判Agent - 判定行动、生成DiceCheckRequest + 12个测试, 92%覆盖率 |
| 2.3.2 GM Agent | ✅ 已完成 | 核心协调者 - 星型拓扑中心、上下文切片 + 14个测试, 98%覆盖率 |
| Agent 集成测试 | ✅ 已完成 | 7个集成测试验证多Agent协作和星型拓扑 |

**Week 3 总计**: 33个测试通过, Agent覆盖率: 92-98%

### Phase 3: Agent 协作与 API 集成 ✅ 已完成

#### Week 1: Agent 协作基础设施 ✅ 已完成
| 任务 | 状态 | 备注 |
|------|------|------|
| 3.1 NPC Agent | ✅ 已完成 | 基于 NPCData(Soul+Body) 生成角色对话 + 16个测试, 89%覆盖率 |
| 3.2 GM Agent 增强 | ✅ 已完成 | 支持 WorldPackLoader 获取 NPC 数据、完整上下文切片 + 17个测试, 90%覆盖率 |
| 3.3 Agent 管线集成 | ✅ 已完成 | GM → Rule / NPC / Lore 完整协作流程 + 7个集成测试 |
| 3.4 WebSocket 流式输出 | ✅ 已完成 | ConnectionManager、分块流式传输、状态/内容/完成消息协议 + 14个测试 |

**Week 1 总计**: 54个新测试通过, 总测试数: 324个, 84%覆盖率

### Phase 4: 向量检索与增强 JSON 解析 ✅ 已完成

#### Week 1: JSON Schema 验证与增强错误提示 ✅ 已完成
| 任务 | 状态 | 备注 |
|------|------|------|
| 4.1.1 JSON Schema 定义 | ✅ 已完成 | 创建 `world_pack.json` Schema + 加载工具，12个验证测试，100%覆盖率 |
| 4.1.2 增强 WorldPackLoader | ✅ 已完成 | Schema 预验证 + 错误格式化，8个错误信息测试，95%覆盖率 |

**Week 1 总计**: 20个测试通过，新增依赖: jsonschema

#### Week 2: 向量存储 & Lore 混合搜索 ✅ 已完成
| 任务 | 状态 | 备注 |
|------|------|------|
| 4.2.1 VectorStoreService 基础 | ✅ 已完成 | ChromaDB PersistentClient + 单例模式，20个测试，90%覆盖率 |
| 4.2.2 Lore 向量索引 | ✅ 已完成 | WorldPackLoader 索引 lore entries，中英文分别索引，8个测试，85%覆盖率 |
| 4.2.3 LoreAgent 混合搜索 | ✅ 已完成 | 关键词+向量混合评分算法，12个测试，85%覆盖率 |

**Week 2 总计**: 40个测试通过，新增依赖: chromadb

#### Week 3: NPC 记忆 & GM 历史检索 ✅ 已完成
| 任务 | 状态 | 备注 |
|------|------|------|
| 4.2.4 NPC 记忆检索 | ✅ 已完成 | 语义检索 top 3 记忆，10个测试，85%覆盖率 |
| 4.2.5 GM 对话历史检索 | ✅ 已完成 | 长游戏历史检索（≥10消息），8个测试，85%覆盖率 |
| 4.2.6 集成测试 | ✅ 已完成 | 7个端到端场景测试，400总测试，84%覆盖率 |

**Week 3 总计**: 25个新测试通过

#### Task 4.3: 文档更新 ✅ 已完成
| 任务 | 状态 | 备注 |
|------|------|------|
| 更新 ARCHITECTURE.md | ✅ 已完成 | 添加 3.3 节"向量数据库 (ChromaDB)" |
| 更新 PROGRESS.md | ✅ 已完成 | 更新 Phase 4 完成状态 |

**Phase 4 总计**: 85个新测试，400总测试，84%覆盖率

### Phase 5: Textual TUI 前端 ⚠️ 已弃用

> **状态说明**: TUI 前端已被弃用，将迁移至 React Web 前端。详见 `docs/WEB_FRONTEND_PLAN.md`。

#### Phase 5.1: TUI 基础架构 ✅ 已完成
| 任务 | 状态 | 备注 |
|------|------|------|
| 5.1.1 TUI 应用入口 | ✅ 已完成 | AstinusApp 主应用类，屏幕导航，响应式状态管理，键盘快捷键 |
| 5.1.2 HTTP/WebSocket 客户端 | ✅ 已完成 | GameClient 类，REST API + WebSocket，消息处理，连接管理 |
| 5.1.3 基础 UI 组件 | ✅ 已完成 | ChatBox(聊天框)，StatBlock(状态块)，DiceRoller(骰子) |
| 5.1.4 游戏主界面 | ✅ 已完成 | GameScreen 整合组件，消息流处理，骰子检查触发 |

**Phase 5.1 总计**: 4个组件完成，依赖: textual (已有)

#### Phase 5.2: 游戏界面 ✅ 已完成
| 任务 | 状态 | 备注 |
|------|------|------|
| 5.2.1 角色面板 | ✅ 已完成 | CharacterScreen 详细角色信息，特性显示，游戏状态 |
| 5.2.2 掷骰交互界面 | ✅ 已完成 | DiceRoller 虚拟骰子，结果提交，可视化反馈 |
| 5.2.3 背包界面 | ✅ 已完成 | InventoryScreen 物品列表，数量显示 |

**Phase 5.2 总计**: 3个界面完成

#### Phase 5.3: 测试与质量 ✅ 已完成
| 任务 | 状态 | 备注 |
|------|------|------|
| 5.3.1 前端测试 | ✅ 已完成 | 25个测试，100%通过，app.py 72%覆盖率，client.py 47%覆盖率 |
| 5.3.2 集成测试 | ✅ 已完成 | 前端与后端通信测试，WebSocket 消息测试 |

**Phase 5.3 总计**: 25个新测试

#### Phase 5.4: Bug 修复 ✅ 已完成
| 问题 | 状态 | 修复内容 |
|------|------|---------|
| Screen.app 只读属性 | ✅ 已修复 | 移除 Screen 子类中的 self.app 赋值 |
| CSS 无效变量 | ✅ 已修复 | `$text-muted` → `$text-disabled`, `$panel-darken` → `$surface`, `$info` → `$accent` |
| CSS 无效属性 | ✅ 已修复 | 移除 `font-size` 属性 |
| asyncio 导入缺失 | ✅ 已修复 | client.py 添加 `import asyncio` |
| 屏幕导航错误 | ✅ 已修复 | 初始屏幕用 `push_screen`，后续导航用 `switch_screen` |
| Reactive 列表共享 | ✅ 已修复 | `reactive([])` → `reactive(list)` |

**Phase 5 总计**: 25个新测试，425总测试

---

### Phase 6: 完整游戏体验与部署 🔄 进行中

> **目标**: 打通前后端集成，实现完整可玩的游戏体验

#### Phase 6.1: 前后端集成 (Critical Path) ✅ 已完成
| 任务 | 优先级 | 状态 | 文件 |
|------|--------|------|------|
| 6.1.1 WebSocket 消息处理 | 🔴 Critical | ✅ 完成 | `src/backend/api/websockets.py` |
| 6.1.2 GameClient 连接管理 | 🔴 Critical | ✅ 完成 | `src/frontend/client.py` |
| 6.1.3 游戏状态同步 | 🔴 Critical | ✅ 完成 | `src/frontend/screens/*.py` |
| 6.1.4 骰子检定流程 | 🔴 Critical | ✅ 完成 | `widgets/dice_roller.py`, `agents/rule.py` |

**说明**:
- ✅ WebSocket 消息路由: `player_input` → GM Agent → 响应流
- ✅ DICE_CHECK/DICE_RESULT 消息类型支持
- ✅ GameClient 异步连接生命周期管理，断线重连
- ✅ ConnectionState 状态枚举与自动重连机制
- ✅ DiceRoller 组件增强: 2d6 系统/优势劣势支持
- ✅ GameScreen 骰子检定流程集成

**完成工作量**: ~1200 行代码，73 个新测试

#### Phase 6.2: 持久化层 ✅ 已完成
| 任务 | 优先级 | 状态 | 文件 |
|------|--------|------|------|
| 6.2.1 数据库服务 | 🔴 Critical | ✅ 完成 | `src/backend/services/database.py` |
| 6.2.2 会话管理 | 🔴 Critical | ✅ 完成 | `src/backend/services/database.py` |
| 6.2.3 持久化模型 | 🔴 Critical | ✅ 完成 | `src/backend/models/persistence.py` |
| 6.2.4 存档 API | 🟡 High | ✅ 完成 | `src/backend/services/database.py` |
| 6.2.5 自动存档 | 🟡 High | ✅ 完成 | `src/backend/services/database.py` |

**说明**:
- ✅ SQLite 异步连接管理 (aiosqlite)
- ✅ SQLAlchemy ORM 持久化模型 (GameSessionModel, MessageModel, SaveSlotModel)
- ✅ 游戏会话 CRUD 操作
- ✅ 存档/读档功能
- ✅ 自动存档与轮换机制

**完成工作量**: ~600 行代码，24 个新测试

#### Phase 6.3: UI 完善 ✅ 已完成 (🔧 已重构)
| 任务 | 优先级 | 状态 | 文件 |
|------|--------|------|------|
| 6.3.1 开始菜单 | 🟡 High | ✅ 已完成 | `src/frontend/screens/menu_screen.py` |
| 6.3.2 角色创建 | 🟡 High | ✅ 已重构 | `src/frontend/screens/character_creation.py` |
| 6.3.3 状态显示增强 | 🟡 High | ✅ 已重构 | `src/frontend/widgets/stat_block.py` |
| 6.3.4 错误处理 UI | 🟢 Medium | ⏳ 待开始 | 各 screen/widget |

**说明**:
- ✅ 新游戏/读档/设置菜单 (MenuScreen)
- ✅ 角色创建流程 (已重构为 GUIDE.md 定义的特质系统)
- ✅ 状态显示 (已重构为特质/标签/命运点，移除 HP/MP)
- ⏳ 错误提示、加载指示器

**🔧 Phase 6.3 重构说明** (fix/phase6.3-ui-design-alignment 分支):

原实现存在以下与 GUIDE.md 设计规范的偏差：
1. ❌ CharacterCreationScreen 使用了 PbtA 风格数值属性 (strength, dexterity 等)
2. ❌ CharacterCreationScreen 使用预定义职业概念而非自由输入
3. ❌ StatBlock 显示 HP/MP 进度条
4. ❌ StatBlock 显示数值属性

已按 GUIDE.md Section 3 重构为：
1. ✅ CharacterCreationScreen: 名称 + 自由输入概念 + 特质系统 (name/description/positive_aspect/negative_aspect)
2. ✅ CharacterCreationScreen: 支持"边玩边建卡"模式
3. ✅ StatBlock: 显示特质列表、标签(状态效果)、命运点(★★★☆☆)
4. ✅ CharacterScreen: 更新为特质系统显示
5. ✅ 移除所有 HP/MP/数值属性相关代码
6. ✅ 82 个新测试验证特质系统实现

**已完成功能**:
- MenuScreen: 新游戏、读档、设置、退出按钮，键盘快捷键
- CharacterCreationScreen: 名称输入、概念自由输入、特质编辑器 (TraitEditor)、边玩边建卡模式、验证
- StatBlock: 特质显示(含正/负面)、标签显示、命运点星星、附近 NPC 显示
- CharacterScreen: 完整角色信息展示
- 测试覆盖: 82 个测试通过

**实际工作量**: ~1200 行代码 (含重构)

#### Phase 6.4: Agent 协作完善 ✅ 已完成
| 任务 | 优先级 | 状态 | 文件 |
|------|--------|------|------|
| 6.4.1 GM Agent 路由 | 🟡 High | ✅ 已完成 | `src/backend/agents/gm.py` |
| 6.4.2 NPC 状态更新 | 🟡 High | ✅ 已完成 | `src/backend/agents/npc.py` |
| 6.4.3 Rule Agent 结果处理 | 🟡 High | ✅ 已完成 | `src/backend/agents/rule.py` |
| 6.4.4 Director Agent | 🟢 Medium | ✅ 已完成 | `src/backend/agents/director.py` |

**说明**:
- ✅ GM Agent 意图解析和 Agent 分发已实现
- ✅ NPC 记忆和关系值持久化
- ✅ 检定结果叙事生成
- ✅ 游戏节奏管理 (Director Agent)

**已完成功能**:
- DirectorAgent: 叙事节拍管理 (hook, setup, rising_action, climax, etc.)
- 张力等级追踪 (1-10 scale)
- 节奏建议 (speed_up, slow_down, build_tension, etc.)
- 动作/对话比例平衡
- 启发式回退分析
- NPCAgent: 记忆持久化到向量数据库 (persist_memory)
- NPCAgent: 关系值计算与边界检查 (calculate_new_relation_level)
- NPCAgent: 状态更新提取 (get_state_updates_from_response)
- RuleAgent: 骰子结果叙事生成 (process_result)
- RuleAgent: 回退叙事生成 (_generate_fallback_narrative)
- RuleAgent: 结果类型判定 (_determine_outcome_type)
- DiceCheckResult 模型: 检定结果数据结构

**实际工作量**: ~800 行代码，72 个新测试

#### Phase 6.5: 测试与部署 ✅ 已完成
| 任务 | 优先级 | 状态 | 文件 |
|------|--------|------|------|
| 6.5.1 集成测试 | 🟡 High | ✅ 已完成 | `tests/integration/test_api_e2e.py`, `tests/integration/test_services_integration.py` |
| 6.5.2 覆盖率提升 | 🟡 High | ✅ 已完成 | `tests/backend/models/test_character_extended.py`, `tests/backend/models/test_dice_check_extended.py`, `tests/backend/services/test_dice_extended.py`, `tests/backend/test_coverage_boost.py` |
| 6.5.3 CI/CD 配置 | 🟢 Medium | ✅ 已完成 | `.github/workflows/ci.yml` |
| 6.5.4 部署文档 | 🟢 Medium | ✅ 已完成 | `docs/DEPLOYMENT.md` |

**说明**:
- 端到端游戏流程测试：API E2E、WebSocket、数据库服务集成测试
- 覆盖率达到 70%（849 测试通过，21 跳过）
- GitHub Actions CI：测试、Lint、类型检查、构建检查
- 部署文档：Docker、systemd、环境变量、备份策略

#### 重要说明：剧情节点图推迟
**Task 4.3 剧情节点图**在 Demo 阶段搁置，专注于单场景实现。

**原因**:
- Demo 阶段目标：验证核心机制（Agent 协作、向量检索、世界包加载）
- 多场景转换需要复杂的状态管理和过渡逻辑
- 当前重点：完善单场景内的叙事体验和检索精度

**后续计划**:
- 在完成 Phase 6 后再实现多场景管理
- 届时将基于实际使用反馈设计场景转换机制

---

## 相关文档

- `docs/WEB_FRONTEND_PLAN.md` - React Web 前端详细开发计划
- `docs/ARCHITECTURE.md` - 系统架构文档（已更新前端描述）
- `docs/DEPLOYMENT.md` - 部署文档

---

## 最近修复
| 日期 | 项目 | 分支 / 版本 | 说明 |
|------|------|-------------|------|
| 2026-01-07 | 移动端状态栏优化 | `main` | 移除移动端状态栏和输入标签，优化界面布局 |
| 2026-01-07 | 移动端菜单面板 | `main` | 添加移动端菜单面板和门户化UI |
| 2026-01-07 | 移动端防滚动 | `main` | 修复移动端游戏页面body滚动问题 |
| 2026-01-07 | 移动端友好UI | `main` | 实现底部面板、移动端适配、响应式设计 |
| 2026-01-07 | 游戏页面视口高度 | `main` | 修复游戏页面视口高度问题，不影响其他页面 |
| 2026-01-07 | 导航链接排序 | `main` | 重新排序导航链接，匹配游戏流程 |
| 2026-01-07 | 特性详情宽度 | `main` | 特性详情宽度调整至90%，关闭按钮放大 |
| 2026-01-07 | 特性详情浮层 | `main` | 特性详情浮层显示，带阴影效果 |
| 2026-01-07 | 特性工具提示 | `main` | 特性工具提示宽度优化，防止文本窄包装 |
| 2026-01-06 | 角色选择流程 | `main` | 实现角色选择流程和特性展示：1) 添加 PresetCharacter 模型和 world_pack.json Schema；2) demo_pack 添加 2 个预设角色（学者/流浪者）；3) API 添加 GET /world-pack/{id}、修改 NewGameRequest；4) MenuPage 简化为世界包选择；5) CharacterPage 改造为双模式（选择/查看）；6) StatBlock 添加特质标签显示；7) 区分玩家名(PL)和角色名(PC)；8) 更新 docs/API_TYPES.ts |
| 2026-01-06 | 预设角色支持 | `main` | 添加预设角色支持到前端API层 |
| 2026-01-06 | 游戏API更新 | `main` | 更新游戏API支持预设角色选择 |
| 2026-01-06 | 预设角色模型 | `main` | 添加 PresetCharacter 模型和预设角色数据 |
| 2026-01-05 | 游戏介绍消息重构 | `fix/gm-information-control` | 重构游戏开场介绍以避免剧透：1) 世界包添加 setting（年代/类型/氛围）、player_hook（玩家动机）、atmosphere（场景氛围）、appearance（NPC外观）字段；2) API 返回 NPC 外观而非名字；3) 前端 generateIntroductionMessage 重写，展示年代、玩家动机、场景氛围，只用外观描述NPC；4) 更新 JSON Schema 和 Pydantic 模型；5) 庄园背景改为 selective（需要发现） |
| 2026-01-05 | GM Agent 信息控制修复 | `fix/gm-information-control` | 防止 GM Agent 泄露敏感信息：1) 在 gm_agent.yaml 中添加 information_control 规则，禁止泄露内部ID、NPC名字、无来源的背景信息；2) 更新 prompt_loader.py 支持 information_control 字段；3) 在 _synthesize_response 中添加信息控制指引；4) 模板中明确标注内部参考信息，提示 GM 不可直接输出给玩家 |
| 2026-01-05 | Web前端Phase显示修复 | `fix/web-phase-display` | 修复 Phase 不更新/显示错误的问题：1) 后端在 _handle_player_input 和 _handle_dice_result 完成后发送 waiting_input 的 phase 变更消息；2) 确保 game_state.set_phase(GamePhase.WAITING_INPUT) 在处理完成后被调用；3) 添加前端 StatBlock Phase 显示测试覆盖全部5种 phase；4) 添加后端集成测试验证 phase 回到 waiting_input |
| 2026-01-05 | 掷骰结果叙事修复 | `fix/dice-result-narrative` | 修复掷骰后无叙事输出的问题：1) _handle_dice_result 调用 Rule Agent 的 process_result 生成叙事；2) 在发送 dice_check 时保存上下文到 temp_context，处理 dice_result 时取回；3) 传递场景上下文给 Rule Agent 以生成更好的叙事；4) 添加 fallback 叙事生成；5) 流式传输长叙事 |
| 2026-01-05 | NPC Agent 调度修复 | `fix/npc-agent-dispatch` | 修复 NPC 扮演无法触发的问题：1) 在 main.py 启动时为场景 NPC 注册 NPCAgent 到 GM sub_agents；2) 在 start_new_game API 中动态注册 NPC Agents；3) GM prompt 显示 NPC id 以便 LLM 正确调用；4) 添加指代消解指引，支持"那个老人"等模糊指代映射到 NPC id |
| 2026-01-05 | GamePage 布局和介绍消息修复 | `fix/gamepage-layout-and-intro` | 修复 Web 前端问题：1) 三栏布局 (StatBlock \| ChatBox \| DiceRoller)；2) 防止 intro 消息被 fetchMessages 覆盖；3) DiceRoller 固定显示，无检定时显示空状态；4) Button 组件支持 className 属性 |
| 2026-01-05 | GM Agent 场景上下文修复 | `fix/gm-agent-scene-context` | 修复 GM Agent 无法获取场景信息的问题：初始化 LoreAgent、WorldPackLoader、VectorStore；GM prompt 增加场景描述、物品、NPC、连接位置；支持直接回复简单行为；前端生成开场介绍 |
| 2026-01-05 | Phase 6.5 完成 | `feature/phase6-frontend-backend-integration` | 完成测试与部署：集成测试、覆盖率提升至70%、GitHub Actions CI、部署文档。197个新测试，849总测试，70%覆盖率 |
| 2026-01-05 | Phase 6.4 完成 | `feature/phase6-frontend-backend-integration` | 完成 Agent 协作完善：NPC 记忆/关系持久化、RuleAgent 结果处理、DiceCheckResult 模型。38个新测试，652总测试，68%覆盖率 |
| 2026-01-04 | TUI Bug 修复 | `fix/screen-app-property-readonly` | 修复 TUI 启动错误：Screen.app 只读属性、CSS 无效变量/属性、asyncio 导入、屏幕导航、Reactive 列表共享问题 |
| 2026-01-04 | Phase 5 完成 | `feature/phase5-textual-tui-frontend` | 完成 Textual TUI 前端实现：AstinusApp、GameClient、UI组件、游戏界面。25个新测试，425总测试，72%覆盖率 |
| 2026-01-04 | Phase 4 完成 | `feature/phase4-week1-json-schema-validation` | 完成向量检索与增强 JSON 解析：VectorStoreService、LoreAgent混合搜索、NPC记忆检索、GM历史检索。85个新测试，400总测试，84%覆盖率 |
| 2026-01-03 | Phase 3 完成 | `feature/phase3-agent-collaboration` | 完成 Agent 协作与 API 集成：NPC Agent、GM 增强、Agent 管线、WebSocket 流式。54个新测试，324总测试，84%覆盖率 |
| 2026-01-03 | Phase 2 Week 3 完成 | `feature/week3-core-agents` | 完成 Core Agents：RuleAgent + GMAgent + 集成测试。33个测试，92-98%覆盖率 |
| 2026-01-03 | Phase 2 Week 2 完成 | `master` | 完成 Agent Infrastructure：BaseAgent、LLM Provider、PromptLoader。64个测试，89-96%覆盖率 |
| 2026-01-03 | Phase 2 Week 1 完成 | `master` | 完成 Foundation Layer：数据模型、骰子系统、I18nService。121个测试，95%覆盖率 |
| 2026-01-03 | Phase 1 基础设施搭建 | `master` | 完成项目目录结构初始化、依赖配置、开发工具设置 |

---

## 技术债务与待优化项

### 高优先级（阻塞可玩性）
- ~~🔴 **前后端集成未完成** - WebSocket 消息路由未实现，玩家输入无法传递到后端~~ ✅ 已完成
- ~~🔴 **持久化层缺失** - 无存档/读档功能，游戏进度无法保存~~ ✅ DatabaseService 已实现
- ~~🔴 **骰子检定流程断裂** - Rule Agent 无法触发前端骰子界面~~ ✅ RuleAgent.process_result 已实现
- ~~🟡 **测试覆盖率不足** - 当前覆盖率 68%，目标 70%+~~ ✅ 已达到 70%（849测试）

### 中优先级
- 🟡 **配置系统混乱** - settings.yaml 结构需重构，支持多 Provider → Phase 8 处理中
- Story Pack 格式与迁移脚本未落地
- ~~配置与密钥管理策略需文档（区分本地/生产）~~ ✅ 已完成（DEPLOYMENT.md）
- ~~缺失单元测试与 CI 流水线~~ ✅ 已完成（849测试，GitHub Actions CI）
- 前端硬编码文案需提取到 locale 文件

### 低优先级
- 文档国际化规划（中英双语）有待评估
- 开发者体验提升（预构建 Makefile / uv 脚本）待执行
- ~~Director Agent 未实现（游戏节奏管理）~~ ✅ 已完成
- Token 验证（访问控制）- 当前纯本地使用，未来支持局域网访问时需要

### 已解决
- ~~`pyproject.toml` 缺少核心依赖~~ ✅ 已完成
- ~~建立 i18n 加载服务~~ ✅ 已完成（I18nService + locale 资源）
- ~~尚未创建 `src` 目录与模块化结构~~ ✅ 已完成
- ~~Prompt 管理方案~~ ✅ 已完成（PromptLoader + YAML/Jinja2）
- ~~TUI CSS 和导航问题~~ ✅ 已修复（fix/screen-app-property-readonly）
- ~~GM Agent 缺少场景上下文~~ ✅ 已修复（fix/gm-agent-scene-context）
- ~~Lore Agent 未接入系统~~ ✅ 已修复（fix/gm-agent-scene-context）
- ~~前端缺少开场介绍~~ ✅ 已修复（fix/gm-agent-scene-context）
- ~~Web前端 Phase 不更新~~ ✅ 已修复（fix/web-phase-display）

---

## 下一步计划

### 立即执行（Phase 6.5）
1. ~~**WebSocket 消息路由** - 完成 `player_input` → GM Agent → 响应流~~ ✅
2. ~~**GameClient 连接管理** - 实现异步连接生命周期、断线重连~~ ✅
3. ~~**数据库服务** - SQLite 连接管理与 SQLAlchemy 模型~~ ✅
4. ~~**会话管理** - 游戏会话 CRUD 与存档 API~~ ✅
5. ~~**开始菜单** - 新游戏/读档/设置菜单界面~~ ✅
6. ~~**NPC 状态持久化** - 记忆和关系值持久化~~ ✅
7. ~~**Rule Agent 结果处理** - 骰子检定叙事生成~~ ✅
8. ~~**集成测试** - 端到端游戏流程测试~~ ✅
9. ~~**CI/CD 配置** - GitHub Actions 配置~~ ✅

### 短期目标（Phase 6.5）✅ 已完成
- ~~编写集成测试覆盖完整游戏流程~~ ✅
- ~~配置 GitHub Actions CI 流水线~~ ✅
- ~~提升测试覆盖率到 70%+~~ ✅ 达到 70%
- ~~编写部署文档 (DEPLOYMENT.md)~~ ✅
- ~~GM Agent 意图解析与 Agent 分发~~ ✅
- ~~NPC 状态更新与记忆持久化~~ ✅

### Phase 7: React Web 前端 ✅ 已完成

> **详细计划**: 参见 `docs/WEB_FRONTEND_PLAN.md`

| 任务 | 优先级 | 状态 | 说明 |
|------|--------|------|------|
| 7.1 项目初始化 | 🔴 Critical | ✅ 已完成 | Vite + React 19 + TypeScript + TailwindCSS |
| 7.2 API 客户端 | 🔴 Critical | ✅ 已完成 | REST API + WebSocket 客户端实现 |
| 7.3 状态管理 | 🔴 Critical | ✅ 已完成 | Zustand stores (game, connection, ui) |
| 7.4 通用组件 | 🟡 High | ✅ 已完成 | Layout, Button, Card, Modal, Loading |
| 7.5 ChatBox 组件 | 🔴 Critical | ✅ 已完成 | 叙事展示、流式内容、玩家输入 |
| 7.6 StatBlock 组件 | 🟡 High | ✅ 已完成 | 角色状态、位置、命运点 |
| 7.7 DiceRoller 组件 | 🟡 High | ✅ 已完成 | 骰子检定、动画、结果提交 |
| 7.8 页面组件 | 🔴 Critical | ✅ 已完成 | MenuPage, GamePage, CharacterPage |
| 7.9 WebSocket 集成 | 🔴 Critical | ✅ 已完成 | 实时消息、流式内容、重连机制 |
| 7.10 测试 | 🟡 High | ✅ 已完成 | Vitest + Testing Library |
| 7.11 移动端优化 | 🟡 High | ✅ 已完成 | 响应式设计、底部面板、触摸优化 |

**技术栈**:
- React 19 + TypeScript
- Vite (构建工具)
- TailwindCSS (样式)
- Zustand (状态管理)
- React Router v6 (路由)

**已完成功能**:
- 完整的前端架构（API 客户端、状态管理、组件系统）
- 三大核心页面（菜单、游戏、角色页面）
- 响应式设计，支持桌面和移动端
- 移动端优化：底部面板、防滚动锁定、触摸友好界面
- 角色选择流程和特性展示系统
- 完整的 WebSocket 实时通信
- 单元测试和集成测试

**实际工期**: 5 天（超预期完成）

### Phase 8: Settings 系统重构 🔄 进行中

> **详细计划**: 参见 `docs/SETTINGS_SYSTEM_PLAN.md`

**目标**: 前端设置页面 + 灵活的 Provider/Agent 配置

| 任务 | 优先级 | 状态 | 说明 |
|------|--------|------|------|
| 8.1.1 重构配置结构 | 🔴 Critical | ⏳ 待开始 | 支持多 Provider + 独立 Agent 配置 |
| 8.1.2 Settings API | 🔴 Critical | ⏳ 待开始 | GET/PUT /api/v1/settings |
| 8.1.3 连通性测试 API | 🔴 Critical | ⏳ 待开始 | POST /api/v1/settings/test |
| 8.1.4 LLM Provider 重构 | 🔴 Critical | ⏳ 待开始 | 支持动态 Provider 加载 |
| 8.2.1 Settings 类型定义 | 🔴 Critical | ⏳ 待开始 | 前端 TypeScript 类型 |
| 8.2.2 SettingsPage 页面 | 🔴 Critical | ⏳ 待开始 | Provider 管理 + Agent 配置 |
| 8.2.3 ProviderEditModal | 🟡 High | ⏳ 待开始 | Provider 编辑弹窗 |
| 8.2.4 前端测试 | 🟡 High | ⏳ 待开始 | Vitest 单元测试 |
| 8.3.1 迁移脚本 | 🟢 Medium | ⏳ 待开始 | 旧配置 → 新配置格式 |
| 8.3.2 文档更新 | 🟢 Medium | ⏳ 待开始 | API_TYPES.ts, PROGRESS.md |

**核心特性**:
- 用户可自定义多个 Provider（支持自定义 base_url）
- 每个 Agent 独立选择 Provider + Model + 参数
- API 密钥掩码处理，前端永不持久化密钥
- 一键测试 API 连通性

**预计工期**: 4-5 天

### 长期目标（Phase 9+）
- 打磨 UX、错误处理与加载指示器
- Story Pack 格式与迁移脚本
- 前端文案国际化（提取到 locale 文件）
- 多场景管理与剧情节点图
- Token 验证（访问控制，支持局域网访问）

### 开发顺序建议
```
Week 1-2: Critical Path (6.1 + 6.2.1-6.2.3)
├── WebSocket 消息路由
├── GameClient 连接管理
├── 数据库服务
└── 会话管理

Week 3: 游戏流程 (6.1.4 + 6.4.1-6.4.3)
├── 骰子检定流程
├── GM Agent 路由
└── Rule Agent 结果

Week 4: UI 与测试 (6.3 + 6.5)
├── 开始菜单
├── 集成测试
└── 部署文档
```

---

## 提交历史摘要
| 日期 | 提交 | 重点 |
|------|------|------|
| 2026-01-07 | `feat/web): implement mobile-friendly UI with bottom sheet panels` | 移动端友好UI：实现底部面板、移动端适配 |
| 2026-01-07 | `fix(web): prevent body scroll on mobile game page` | 移动端优化：防止页面滚动锁定 |
| 2026-01-07 | `fix(web): fix game page viewport height` | 游戏页面视口高度修复 |
| 2026-01-07 | `fix(web): reorder nav links to match game flow` | 导航链接重新排序，匹配游戏流程 |
| 2026-01-07 | `fix(web): widen trait detail to 90%` | 特性详情宽度调整至90% |
| 2026-01-07 | `fix(web): make trait detail float over content` | 特性详情浮层显示 |
| 2026-01-07 | `fix(web): widen trait tooltip` | 特性工具提示宽度优化 |
| 2026-01-06 | `feat(web): implement character selection flow` | 实现角色选择流程和特性展示 |
| 2026-01-06 | `feat(web): add preset character support` | 添加预设角色支持 |
| 2026-01-06 | `feat(api): update game API for preset character` | 更新游戏API支持预设角色 |
| 2026-01-06 | `feat(models): add PresetCharacter model` | 添加预设角色模型和数据 |
| 2026-01-06 | `docs: add PresetCharacter types and update schema` | 添加预设角色类型定义 |
| 2026-01-05 | `feature/phase6-frontend-backend-integration` | Phase 6.5 完成：集成测试、覆盖率提升至70%、CI/CD、部署文档 |
| 2026-01-05 | `feature/phase6-frontend-backend-integration` | Phase 6.4 完成：Agent协作完善、NPC状态持久化、RuleAgent结果处理 |
| 2026-01-05 | `feature/phase6-frontend-backend-integration` | Phase 6.3 完成：UI完善、角色创建重构、特质系统实现 |
| 2026-01-05 | `feature/phase6-frontend-backend-integration` | Phase 6.2 完成：持久化层、数据库服务、会话管理，24个新测试 |
| 2026-01-05 | `feature/phase6-frontend-backend-integration` | Phase 6.1 完成：WebSocket消息路由、GameClient连接管理、骰子检定流程 |
| 2026-01-04 | `fix/screen-app-property-readonly` | TUI Bug修复：CSS、屏幕导航、asyncio导入等 |
| 2026-01-04 | `feature/phase5-textual-tui-frontend` | 完成Phase 5：Textual TUI前端实现，25个测试，425总测试 |
| 2026-01-04 | `feature/phase4-week1-json-schema-validation` | 完成Phase 4：向量检索与增强JSON解析，85个测试，400总测试 |
| 2026-01-03 | `feature/phase3-agent-collaboration` | 完成Phase 3：Agent协作与API集成，54个测试，324总测试 |
| 2026-01-03 | `feature/week3-core-agents` | 完成Phase 2 Week 3：Core Agents，33个测试 |
| 2026-01-03 | `master` | 完成Phase 2 Week 2：Agent Infrastructure，64个测试 |
| 2026-01-03 | `master` | 完成Phase 2 Week 1：Foundation Layer，121个测试 |
| 2026-01-03 | `master` | 完成Phase 1：基础设施搭建 |

> 注：详细提交记录可通过 `git log --oneline` 查看。
> 当前活跃分支: `main` (Web前端开发已完成)

---

## 参考文档
- `docs/GUIDE.md`
- `docs/ARCHITECTURE.md`
- `docs/SETTINGS_SYSTEM_PLAN.md`
- `CLAUDE.md`

---
