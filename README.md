# Astinus

> AI 驱动的叙事向单人 TTRPG 引擎

Astinus 是一个基于 AI 多智能体架构的叙事导向桌面角色扮演游戏引擎，通过自然语言交互提供沉浸式的单人 TTRPG 体验。

## 项目状态

✅ **Phase 5 已完成** - Textual TUI 前端实现已完成
🎯 **下一步** - Phase 6: 完整游戏体验与部署

### 最新进展

- ✅ **Phase 1**: 基础设施搭建
- ✅ **Phase 2**: 核心引擎（数据模型、骰子系统、Agent 基础）
- ✅ **Phase 3**: Agent 协作与 API 集成
  - NPC Agent - 基于双层结构的角色对话生成
  - 多 Agent 管线协作（GM、Rule、NPC、Lore）
  - WebSocket 流式输出与实时交互
- ✅ **Phase 4**: 向量检索与增强 JSON 解析
  - VectorStoreService - ChromaDB 向量存储
  - LoreAgent 混合搜索 - 关键词 + 向量语义检索
  - NPC 记忆检索 - 语义检索相关记忆
  - GM 历史检索 - 长游戏对话历史管理
- ✅ **Phase 5**: Textual TUI 前端
  - AstinusApp - TUI 应用主入口，屏幕导航管理
  - GameClient - HTTP/WebSocket 客户端
  - UI 组件 - ChatBox、StatBlock、DiceRoller
  - 游戏界面 - Game、Character、Inventory 屏幕
  - 425 个测试通过，71% 覆盖率

## 快速开始

### 环境要求

- Python >= 3.13
- [uv](https://github.com/astral-sh/uv) - 现代 Python 包管理器

### 安装

```bash
# 克隆仓库
git clone https://github.com/Rene-Zhou/Astinus.git
cd Astinus

# 安装依赖
uv sync

# 复制配置模板
cp config/settings.example.yaml config/settings.yaml
# 编辑 config/settings.yaml 填入你的 API 密钥
```

### 运行 TUI 前端

```bash
# 启动 Textual TUI 应用
uv run python -m src.frontend.app

# 或直接运行
python src/frontend/app.py
```

**键盘快捷键**:
- `g` - 切换到游戏界面
- `c` - 切换到角色面板
- `i` - 切换到背包界面
- `q` - 退出应用

### 启动后端 API（可选）

```bash
# 启动 FastAPI 后端服务器
uv run uvicorn src.backend.main:app --reload --port 8000
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行代码检查
uv run ruff check src/ tests/

# 运行类型检查
uv run mypy src/
```

## 项目结构

```
Astinus/
├── src/
│   ├── backend/         # FastAPI 后端与 AI Agents
│   ├── frontend/        # Textual TUI 前端
│   └── shared/          # 共享工具
├── data/                # 数据存储（世界包、存档、向量库）
├── locale/              # 多语言资源（cn/en）
├── tests/               # 测试套件
├── config/              # 配置文件
└── docs/                # 项目文档
```

## 文档

- [开发指南](docs/GUIDE.md) - 游戏设计与规则系统
- [架构文档](docs/ARCHITECTURE.md) - 技术架构与 API 设计
- [开发进度](docs/PROGRESS.md) - 项目路线图与待办事项
- [开发规范](CLAUDE.md) - 代码规范与工作流程

## 核心特性

- 🎭 **纯自然语言交互** - 无菜单选项，自由描述行动
- 🖥️ **丰富的 TUI 界面** - 基于 Textual 的现代终端用户界面
  - 实时聊天窗口，自动滚动显示叙事内容
  - 角色状态面板，动态显示游戏状态
  - 虚拟骰子界面，可视化掷骰结果
  - 键盘快捷键，快速导航
- 🤖 **多智能体协作** - GM、NPC、Rule、Lore 等 Agent 分工协作
  - GM Agent - 核心协调者，星型拓扑中心
  - Rule Agent - 规则裁判，生成骰子检定
  - NPC Agent - 角色对话，情感与关系系统
  - Lore Agent - 世界观检索，背景信息提供
- 🧠 **智能向量检索** - ChromaDB 语义搜索
  - Lore 混合搜索：关键词 + 向量语义匹配
  - NPC 记忆检索：语义检索相关记忆
  - GM 历史检索：长游戏对话历史管理
- 🎲 **透明的规则系统** - 基于 2d6 的掷骰机制（掷 2d6，奖励/惩罚骰子取最高/最低 2 枚）
- 📦 **模块化世界包** - 故事内容与引擎解耦，支持扩展
- 🌏 **多语言支持** - 中英双语界面与内容
- ⚡ **实时流式交互** - WebSocket 流式输出，typewriter 效果
- 💾 **持久化存储** - SQLite 存档 + ChromaDB 向量库

## TUI 界面预览

Astinus 提供现代化的终端用户界面，无需图形界面即可享受完整的游戏体验：

### 游戏主界面
```
┌─────────────────────────────────────────────────────────┐
│ Astinus - AI TTRPG                          [C] [I]      │
├─────────────────────────────────────────────────────────┤
│ Character: 张伟 (Adventurer)                               │
│ Location: Library | Phase: Waiting | Turn: 5             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  GM: 你进入了图书馆，古老的书香扑面而来...                │
│                                                         │
│  Player: 我 look around                                  │
│                                                         │
│  GM: 你看到陈玲在整理古籍，她注意到你...                   │
│                                                         │
│  [Dice Check Required - Agility DC 15]                  │
│                                                         │
│ > I try to sneak past her...                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 主要组件

- **顶部状态栏**: 显示角色信息、当前位置、游戏阶段和回合数
- **聊天窗口**: 实时显示 GM 叙事和玩家行动，支持自动滚动
- **输入区**: 底部输入框，支持输入历史（↑/↓ 键浏览）
- **导航按钮**: 快速切换到角色面板和背包界面
- **骰子界面**: 需要时自动显示，提供可视化掷骰功能

### 键盘快捷键

- `g` - 切换到游戏界面
- `c` - 切换到角色面板
- `i` - 切换到背包界面
- `↑/↓` - 浏览输入历史
- `Enter` - 发送行动
- `q` - 退出应用

## 技术栈

### 后端
- **框架**: FastAPI - 高性能异步 API
- **AI Orchestration**: LangChain - 多提供商模型支持
- **Agent**: 自研多 Agent 协作系统（星型拓扑）

### 前端
- **TUI**: Textual - 终端用户界面（已完成）
  - AstinusApp - 应用主入口
  - GameClient - HTTP/WebSocket 客户端
  - Screens - Game、Character、Inventory 界面
  - Widgets - ChatBox、StatBlock、DiceRoller 组件
- **实时通信**: WebSocket - 流式响应

### 数据层
- **结构化数据**: Pydantic models + SQLite
- **向量检索**: ChromaDB - 语义搜索（已完成）
- **世界包**: JSON 格式，模块化管理

### 开发工具
- **包管理**: uv - 现代 Python 包管理器
- **测试**: pytest (425 个测试，71% 覆盖率)
- **代码质量**: ruff + mypy
- **类型系统**: Pydantic v2

## 开发

### 代码质量

项目使用以下工具保证代码质量：

- `ruff` - 代码格式化与静态检查
- `mypy` - 类型检查
- `pytest` - 单元测试

### 分支策略

- `main` - 主分支，保持稳定
- `feature/*` - 功能开发分支
- `fix/*` - 问题修复分支

### 提交规范

- 使用清晰的提交信息描述更改
- 重大更新需同步更新 `docs/PROGRESS.md`

## 架构设计

### Agent 星型拓扑

```mermaid
graph TD
    GM[GM Agent<br/>核心协调者] --> R[Rule Agent<br/>规则裁判]
    GM --> N[NPC Agent<br/>角色对话]
    GM --> L[Lore Agent<br/>世界观检索]
    GM --> O[其他 Agent<br/>可扩展]

    style GM fill:#e1f5fe,stroke:#01579b,color:#000000
    style R fill:#f3e5f5,stroke:#4a148c,color:#000000
    style N fill:#f3e5f5,stroke:#4a148c,color:#000000
    style L fill:#f3e5f5,stroke:#4a148c,color:#000000
    style O fill:#f3e5f5,stroke:#4a148c,color:#000000
```

- **信息隔离**: 每个 Agent 只能访问必要的上下文切片
- **职责单一**: 每个 Agent 有明确的职责边界
- **可扩展**: 易于添加新的 Agent 类型

### 上下文切片机制

GM Agent 负责为每个子 Agent 准备精准的上下文切片，确保：
- NPC Agent 不会知道其他 NPC 的信息
- Rule Agent 不会访问游戏历史
- Lore Agent 只获取相关的世界观信息

## 测试与质量保证

### 测试统计

- **总测试数**: 425 个
- **测试覆盖率**: 71%
- **测试类型**:
  - 单元测试 - Agent、模型、核心组件
  - 集成测试 - 多 Agent 协作流程
  - API 测试 - REST 和 WebSocket 端点
  - 前端测试 - TUI 组件和交互（25个测试，100%通过）

### 质量标准

- 所有新功能必须包含测试
- 单元测试覆盖率 > 80%
- 集成测试覆盖率 > 70%
- 前端测试覆盖率 > 70%
- 通过 ruff + mypy 检查

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'Add some feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 创建 Pull Request

### 开发工作流

1. 从 `main` 分支创建 feature 分支
2. 遵循 TDD：先写测试，再写实现
3. 确保所有测试通过：`uv run pytest`
4. 运行代码检查：`uv run ruff check`
5. 运行类型检查：`uv run mypy src/`
6. 更新相关文档（包括 README.md 和 PROGRESS.md）

### 运行完整检查

```bash
# 运行所有测试
uv run pytest

# 代码格式化与检查
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# 类型检查
uv run mypy src/

# 完整测试套件（包括前端测试）
uv run pytest tests/frontend/
```

## 许可证

本项目采用 MIT 许可证。详情请见 [LICENSE](LICENSE) 文件。

## 致谢

- 基于 LangChain 构建 AI Agent 系统
- 使用 Textual 打造现代 TUI 体验

## 联系方式

- 项目主页: [GitHub Repository](https://github.com/Rene-Zhou/Astinus)
- 问题反馈: [GitHub Issues](https://github.com/Rene-Zhou/Astinus/issues)
