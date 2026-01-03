# Astinus 开发进度与规划

> 最后更新：2026-06-24  

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
| TUI 前端 | Textual | ⏳ 规划中 |
| 后端 API | FastAPI + WebSocket | ⏳ 规划中 |
| AI Orchestrator | LangChain + 多提供商模型 | ⏳ 规划中 |
| 数据层 | SQLite（结构化）+ ChromaDB（向量检索） | ⏳ 规划中 |
| 构建 & 依赖 | Python ≥3.14, uv | ✅ 已确认 |

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

#### 重要说明：剧情节点图推迟
**Task 4.3 剧情节点图**在 Demo 阶段搁置，专注于单场景实现。

**原因**:
- Demo 阶段目标：验证核心机制（Agent 协作、向量检索、世界包加载）
- 多场景转换需要复杂的状态管理和过渡逻辑
- 当前重点：完善单场景内的叙事体验和检索精度

**后续计划**:
- 在完成 Phase 5 (TUI 前端) 后再实现多场景管理
- 届时将基于实际使用反馈设计场景转换机制

### Phase 5: Frontend Textual TUI & Polish
- 5.1 Textual UI 布局、状态同步
- 5.2 掷骰交互界面
- 5.3 QA、性能与文档完善

---

## 最近修复
| 日期 | 项目 | 分支 / 版本 | 说明 |
|------|------|-------------|------|
| 2026-01-03 | Phase 3 完成 | `feature/phase3-agent-collaboration` | 完成 Agent 协作与 API 集成：NPC Agent、GM 增强、Agent 管线、WebSocket 流式。54个新测试，324总测试，84%覆盖率 |
| 2026-01-03 | Phase 2 Week 3 完成 | `feature/week3-core-agents` | 完成 Core Agents：RuleAgent + GMAgent + 集成测试。33个测试，92-98%覆盖率 |
| 2026-01-03 | Phase 2 Week 2 完成 | `master` | 完成 Agent Infrastructure：BaseAgent、LLM Provider、PromptLoader。64个测试，89-96%覆盖率 |
| 2026-01-03 | Phase 2 Week 1 完成 | `master` | 完成 Foundation Layer：数据模型、骰子系统、I18nService。121个测试，95%覆盖率 |
| 2026-01-03 | Phase 1 基础设施搭建 | `master` | 完成项目目录结构初始化、依赖配置、开发工具设置 |

---

## 技术债务与待优化项

### 高优先级
- ~~`pyproject.toml` 缺少核心依赖（FastAPI, Textual, LangChain, ChromaDB 等）。~~ ✅ 已完成（除 ChromaDB 外）
- ~~建立 i18n 加载服务，统一管理前端与后端所有可见文本并提供 `cn`/`en` 双语。~~ ✅ 已完成（I18nService + locale 资源）
- ~~尚未创建 `src` 目录与模块化结构，需尽快搭建以解锁后续任务。~~ ✅ 已完成
- ~~缺失单元测试与 CI 流水线，阻碍 TDD 推进。~~ 🔄 单元测试框架已搭建，CI 待配置

### 中优先级
- Story Pack 格式与迁移脚本未落地。
- ~~Prompt 管理方案（Jinja2 模板 + 版本管理）待实现。~~ ✅ 已完成（PromptLoader + YAML/Jinja2）
- 配置与密钥管理策略需文档（区分本地/生产）。

### 低优先级
- 文档国际化规划（中英双语）有待评估。
- 开发者体验提升（预构建 Makefile / uv 脚本）待执行。

---

## 下一步计划

### 立即执行（Phase 4）
1. 实现世界包 JSON/YAML 解析与索引。
2. 添加 ChromaDB 依赖，实现向量检索。
3. 设计剧情节点图 / 场景管理系统。
4. 配置 GitHub Actions CI 流水线。

### 短期目标（Phase 4-5）
- 实现 ChromaDB 向量检索，支持语义搜索 Lore 条目。
- 设计并实现 Textual TUI 布局。
- 完善掷骰交互界面与 WebSocket 实时更新。

### 中期目标（Phase 5）
- 实现 Textual TUI 端到端体验。
- 打磨 UX、日志、监控与可观测性。
- 完整撰写发布前质量策略（测试矩阵、Beta 计划）。

---

## 提交历史摘要
| 日期 | 提交 | 重点 |
|------|------|------|
| 2026-06-24 | `main` (HEAD) | 创建项目骨架与文档规范 |

> 注：详细提交记录可通过 `git log --oneline` 查看。

---

## 参考文档
- `docs/GUIDE.md`
- `docs/ARCHITECTURE.md`
- `CLAUDE.md`

---
