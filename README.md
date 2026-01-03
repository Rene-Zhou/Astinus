# Astinus

> AI 驱动的叙事向单人 TTRPG 引擎

Astinus 是一个基于 AI 多智能体架构的叙事导向桌面角色扮演游戏引擎，通过自然语言交互提供沉浸式的单人 TTRPG 体验。

## 项目状态

🚧 **开发中** - Phase 1 基础设施搭建已完成

## 快速开始

### 环境要求

- Python >= 3.14
- [uv](https://github.com/astral-sh/uv) - 现代 Python 包管理器

### 安装

```bash
# 克隆仓库
git clone <repository-url>
cd Astinus

# 安装依赖
uv sync

# 复制配置模板
cp config/settings.example.yaml config/settings.yaml
# 编辑 config/settings.yaml 填入你的 API 密钥
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
- 🤖 **多智能体协作** - GM、NPC、规则、剧情等 Agent 分工协作
- 🎲 **透明的规则系统** - 基于 2d6 的简洁掷骰机制
- 📦 **模块化世界包** - 故事内容与引擎解耦
- 🌏 **多语言支持** - 中英双语界面与内容

## 技术栈

- **后端**: FastAPI + LangChain + SQLAlchemy
- **前端**: Textual (Terminal UI)
- **AI**: LangChain (支持多个 LLM 提供商)
- **数据**: SQLite + ChromaDB (规划中)

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

## 许可证

[待定]

## 致谢

本项目参考了 `cli-ttrpg` 项目的设计思路。
