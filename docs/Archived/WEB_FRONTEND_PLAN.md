# Astinus React Web 前端开发计划

> 创建日期：2025-01-06
> 状态：✅ 已完成
> 最后更新：2026-01-07

## 📋 目录

1. [概述](#概述)
2. [技术栈](#技术栈)
3. [目录结构](#目录结构)
4. [后端 API 接口](#后端-api-接口)
5. [组件设计](#组件设计)
6. [状态管理](#状态管理)
7. [开发步骤](#开发步骤)
8. [测试策略](#测试策略)
9. [部署配置](#部署配置)

---

## 概述

### 背景

原有的 Textual TUI 前端存在以下问题：
- 终端环境限制了用户体验
- 组件复杂度高，维护困难
- 无法在浏览器中运行，限制了受众

### 目标

构建一个简洁、现代的 React Web 前端，提供：
- 流畅的游戏体验
- 响应式设计（支持桌面和移动端）
- 实时消息流（WebSocket）
- 清晰的游戏状态展示

### 设计原则

- **简洁优先**：保持 UI 简洁，专注核心游戏体验
- **类型安全**：全面使用 TypeScript
- **组件化**：可复用、可测试的组件设计
- **渐进增强**：核心功能优先，逐步添加高级特性

---

## 技术栈

| 类别 | 技术选择 | 理由 |
|------|----------|------|
| 框架 | React 18 | 成熟稳定，生态丰富 |
| 语言 | TypeScript | 类型安全，减少运行时错误 |
| 构建工具 | Vite | 快速开发体验，原生 ESM 支持 |
| 样式 | TailwindCSS | 实用优先，快速开发 |
| 状态管理 | Zustand | 轻量、简洁、TypeScript 友好 |
| HTTP 客户端 | fetch API | 原生支持，无需额外依赖 |
| WebSocket | 原生 WebSocket | 简单场景无需复杂库 |
| 路由 | React Router v6 | 标准解决方案 |
| 测试 | Vitest + Testing Library | Vite 生态，快速执行 |

---

## 目录结构

```text
Astinus/
├── src/
│   ├── backend/              # 后端代码（保持不变）
│   │   └── ...
│   │
│   └── web/                  # React Web 前端（新增）
│       ├── public/
│       │   └── favicon.ico
│       │
│       ├── src/
│       │   ├── api/              # API 客户端
│       │   │   ├── client.ts         # HTTP 客户端
│       │   │   ├── websocket.ts      # WebSocket 客户端
│       │   │   └── types.ts          # API 类型定义
│       │   │
│       │   ├── components/       # 可复用组件
│       │   │   ├── ChatBox/
│       │   │   │   ├── ChatBox.tsx
│       │   │   │   ├── ChatMessage.tsx
│       │   │   │   └── ChatInput.tsx
│       │   │   ├── StatBlock/
│       │   │   │   └── StatBlock.tsx
│       │   │   ├── DiceRoller/
│       │   │   │   ├── DiceRoller.tsx
│       │   │   │   └── DiceDisplay.tsx
│       │   │   ├── Layout/
│       │   │   │   ├── Header.tsx
│       │   │   │   ├── Footer.tsx
│       │   │   │   └── Layout.tsx
│       │   │   └── common/
│       │   │       ├── Button.tsx
│       │   │       ├── Card.tsx
│       │   │       ├── Loading.tsx
│       │   │       └── Modal.tsx
│       │   │
│       │   ├── pages/            # 页面组件
│       │   │   ├── MenuPage.tsx
│       │   │   ├── GamePage.tsx
│       │   │   ├── CharacterPage.tsx
│       │   │   └── NotFoundPage.tsx
│       │   │
│       │   ├── stores/           # Zustand 状态管理
│       │   │   ├── gameStore.ts
│       │   │   ├── connectionStore.ts
│       │   │   └── uiStore.ts
│       │   │
│       │   ├── hooks/            # 自定义 Hooks
│       │   │   ├── useWebSocket.ts
│       │   │   ├── useGameActions.ts
│       │   │   └── useDiceRoll.ts
│       │   │
│       │   ├── utils/            # 工具函数
│       │   │   ├── dice.ts
│       │   │   └── i18n.ts
│       │   │
│       │   ├── styles/           # 全局样式
│       │   │   └── globals.css
│       │   │
│       │   ├── App.tsx           # 应用根组件
│       │   ├── main.tsx          # 入口文件
│       │   └── vite-env.d.ts     # Vite 类型声明
│       │
│       ├── index.html
│       ├── package.json
│       ├── tsconfig.json
│       ├── vite.config.ts
│       ├── tailwind.config.js
│       └── postcss.config.js
│
├── frontend/                 # 旧 Textual TUI 前端（将被移除）
└── ...
```

---

## 后端 API 接口

### REST API 端点

#### 1. 根端点

```
GET /
```

**响应**:
```json
{
  "name": "Astinus TTRPG Engine",
  "version": "0.1.0",
  "status": "running",
  "docs": "/docs",
  "openapi": "/openapi.json"
}
```

---

#### 2. 健康检查

```
GET /health
```

**响应**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "agents": {
    "gm_agent": true,
    "rule_agent": true
  }
}
```

---

#### 3. 创建新游戏

```
POST /api/v1/game/new
```

**请求体**:
```json
{
  "world_pack_id": "demo_pack",
  "player_name": "玩家",
  "player_concept": "冒险者"
}
```

**响应**:
```json
{
  "session_id": "uuid-string",
  "player": {
    "name": "玩家",
    "concept": {
      "cn": "冒险者",
      "en": "Adventurer"
    },
    "traits": [
      {
        "name": { "cn": "勇敢", "en": "Brave" },
        "description": { "cn": "...", "en": "..." },
        "positive_aspect": { "cn": "勇敢", "en": "Brave" },
        "negative_aspect": { "cn": "鲁莽", "en": "Rash" }
      }
    ],
    "tags": [],
    "fate_points": 3
  },
  "game_state": {
    "current_location": "起始地点",
    "current_phase": "waiting_input",
    "turn_count": 0,
    "active_npc_ids": []
  },
  "message": "Game session created successfully"
}
```

---

#### 4. 处理玩家行动

```
POST /api/v1/game/action
```

**请求体**:
```json
{
  "player_input": "我查看周围的环境",
  "lang": "cn"
}
```

**响应**:
```json
{
  "success": true,
  "content": "你环顾四周，发现自己身处一间古老的图书馆...",
  "metadata": {
    "phase": "narrating",
    "needs_check": false
  },
  "error": null
}
```

---

#### 5. 获取游戏状态

```
GET /api/v1/game/state
```

**响应**:
```json
{
  "session_id": "uuid-string",
  "world_pack_id": "demo_pack",
  "player": { ... },
  "current_location": "古老图书馆",
  "active_npc_ids": ["librarian_chen"],
  "current_phase": "waiting_input",
  "turn_count": 5,
  "language": "cn",
  "messages": [ ... ]
}
```

---

#### 6. 提交骰子结果

```
POST /api/v1/game/dice-result
```

**请求体**:
```json
{
  "total": 14,
  "all_rolls": [6, 4, 4],
  "kept_rolls": [6, 4, 4],
  "outcome": "success"
}
```

**响应**:
```json
{
  "success": true,
  "message": "Dice result recorded",
  "next_phase": "narrating"
}
```

---

#### 7. 获取最近消息

```
GET /api/v1/game/messages?count=10
```

**响应**:
```json
{
  "messages": [
    {
      "role": "user",
      "content": "我打开那扇神秘的门",
      "timestamp": "2025-01-06T10:30:00Z",
      "turn": 3
    },
    {
      "role": "assistant",
      "content": "门缓缓打开，一股陈旧的气息扑面而来...",
      "timestamp": "2025-01-06T10:30:05Z",
      "turn": 3,
      "metadata": { "agent": "gm" }
    }
  ],
  "count": 2
}
```

---

#### 8. 重置游戏

```
POST /api/v1/game/reset
```

**响应**:
```json
{
  "success": true,
  "message": "Game state reset"
}
```

---

### WebSocket API

#### 端点

```
ws://localhost:8000/ws/game/{session_id}
```

---

#### 客户端 -> 服务器消息

##### 玩家输入

```json
{
  "type": "player_input",
  "content": "我尝试与图书管理员交谈",
  "lang": "cn",
  "stream": true
}
```

##### 骰子结果

```json
{
  "type": "dice_result",
  "result": 12,
  "all_rolls": [5, 4, 3],
  "kept_rolls": [5, 4, 3],
  "outcome": "success"
}
```

---

#### 服务器 -> 客户端消息

##### 状态更新

```json
{
  "type": "status",
  "data": {
    "phase": "processing",
    "message": "正在分析你的行动..."
  }
}
```

##### 内容流（打字机效果）

```json
{
  "type": "content",
  "data": {
    "chunk": "图书管理员抬起头，",
    "is_partial": true,
    "chunk_index": 0
  }
}
```

##### 完成响应

```json
{
  "type": "complete",
  "data": {
    "content": "图书管理员抬起头，用审视的目光打量着你...",
    "metadata": {
      "phase": "waiting_input",
      "turn": 6
    },
    "success": true
  }
}
```

##### 骰子检定请求

```json
{
  "type": "dice_check",
  "data": {
    "check_request": {
      "intention": "说服图书管理员透露秘密",
      "influencing_factors": ["善于交际", "图书馆常客"],
      "dice_formula": "2d6",
      "instructions": "因为你的"善于交际"特质，获得+1加值"
    }
  }
}
```

##### 游戏阶段变更

```json
{
  "type": "phase",
  "data": {
    "phase": "dice_check"
  }
}
```

##### 错误消息

```json
{
  "type": "error",
  "data": {
    "error": "Invalid player input"
  }
}
```

---

## 组件设计

### 页面组件

#### MenuPage

主菜单页面，提供：
- 新游戏按钮
- 继续游戏按钮（读取存档）
- 设置入口

```tsx
// 伪代码结构
function MenuPage() {
  return (
    <Layout>
      <Logo />
      <MenuButtons>
        <Button onClick={startNewGame}>新游戏</Button>
        <Button onClick={loadGame} disabled={!hasSave}>继续游戏</Button>
        <Button onClick={openSettings}>设置</Button>
      </MenuButtons>
    </Layout>
  )
}
```

---

#### GamePage

核心游戏页面，三栏布局：

```
+------------------+------------------------+------------------+
|                  |                        |                  |
|    StatBlock     |       ChatBox          |   DiceRoller     |
|   (角色状态)      |     (叙事/对话)         |   (骰子面板)      |
|                  |                        |                  |
|                  |                        |                  |
|                  +------------------------+                  |
|                  |      ChatInput         |                  |
|                  |     (玩家输入)          |                  |
+------------------+------------------------+------------------+
```

响应式设计：
- 桌面：三栏并排
- 平板：StatBlock 折叠为顶栏
- 手机：单栏，底部导航切换

---

#### CharacterPage

角色详情页面：
- 角色名称与概念
- 特质列表（正面/负面）
- 状态标签
- 命运点数

---

### 功能组件

#### ChatBox

叙事展示与玩家输入组件：

**Props**:
```typescript
interface ChatBoxProps {
  messages: Message[];
  onSendMessage: (content: string) => void;
  isStreaming: boolean;
  streamingContent: string;
  disabled: boolean;
}
```

**功能**:
- 显示历史消息（区分 user/assistant）
- 支持流式内容显示（打字机效果）
- 自动滚动到底部
- 输入框支持多行（Shift+Enter 换行）
- 输入历史导航（↑/↓）

---

#### StatBlock

角色状态面板：

**Props**:
```typescript
interface StatBlockProps {
  playerName: string;
  concept: LocalizedString;
  location: string;
  phase: GamePhase;
  turnCount: number;
  fatePoints: number;
  tags: string[];
  language: 'cn' | 'en';
}
```

**显示内容**:
- 角色名
- 角色概念
- 当前位置
- 游戏阶段
- 回合数
- 命运点（可点击使用）
- 状态标签

---

#### DiceRoller

骰子掷骰组件：

**Props**:
```typescript
interface DiceRollerProps {
  visible: boolean;
  checkRequest: DiceCheckRequest | null;
  onRoll: (result: DiceResult) => void;
  onCancel: () => void;
}
```

**功能**:
- 显示检定说明（intention, instructions）
- 骰子公式解析（如 "2d6", "3d6kl2"）
- 掷骰动画
- 显示所有骰子结果
- 计算并显示总值
- 提交结果

---

### 通用组件

#### Button

```typescript
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'ghost';
  size: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}
```

#### Card

```typescript
interface CardProps {
  title?: string;
  className?: string;
  children: React.ReactNode;
}
```

#### Loading

```typescript
interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}
```

#### Modal

```typescript
interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}
```

---

## 状态管理

使用 Zustand 进行状态管理，分为三个独立的 store：

### gameStore

游戏核心状态：

```typescript
interface GameState {
  // Session
  sessionId: string | null;
  worldPackId: string;
  
  // Player
  player: PlayerCharacter | null;
  
  // Game State
  currentLocation: string;
  currentPhase: GamePhase;
  turnCount: number;
  activeNpcIds: string[];
  
  // Messages
  messages: Message[];
  streamingContent: string;
  
  // Dice
  pendingDiceCheck: DiceCheckRequest | null;
  lastDiceResult: DiceResult | null;
  
  // Actions
  startNewGame: (worldPackId: string, playerName: string) => Promise<void>;
  sendPlayerInput: (content: string) => void;
  submitDiceResult: (result: DiceResult) => void;
  addMessage: (message: Message) => void;
  appendStreamingContent: (chunk: string) => void;
  clearStreamingContent: () => void;
  setPhase: (phase: GamePhase) => void;
  setPendingDiceCheck: (check: DiceCheckRequest | null) => void;
  reset: () => void;
}
```

### connectionStore

连接状态管理：

```typescript
type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

interface ConnectionState {
  status: ConnectionStatus;
  error: string | null;
  reconnectAttempts: number;
  
  // Actions
  setStatus: (status: ConnectionStatus) => void;
  setError: (error: string | null) => void;
  incrementReconnectAttempts: () => void;
  resetReconnectAttempts: () => void;
}
```

### uiStore

UI 状态：

```typescript
interface UIState {
  language: 'cn' | 'en';
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  diceRollerVisible: boolean;
  
  // Actions
  setLanguage: (lang: 'cn' | 'en') => void;
  toggleTheme: () => void;
  toggleSidebar: () => void;
  setDiceRollerVisible: (visible: boolean) => void;
}
```

---

## 开发步骤

### Phase 1: 项目初始化（Day 1）

#### 1.1 创建 Vite React 项目

```bash
cd Astinus/src
npm create vite@latest web -- --template react-ts
cd web
npm install
```

#### 1.2 安装依赖

```bash
# 核心依赖
npm install react-router-dom zustand

# 样式
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# 开发工具
npm install -D @types/node
```

#### 1.3 配置 TailwindCSS

```javascript
// tailwind.config.js
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#4f46e5',
        secondary: '#6b7280',
        accent: '#f59e0b',
      },
    },
  },
  plugins: [],
}
```

#### 1.4 配置代理（开发环境）

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
```

---

### Phase 2: 基础架构（Day 2-3）

#### 2.1 API 客户端实现

**文件**: `src/api/types.ts`
- 定义所有 API 相关类型
- 与后端 Pydantic 模型对应

**文件**: `src/api/client.ts`
- 实现 REST API 调用
- 错误处理
- 响应类型转换

**文件**: `src/api/websocket.ts`
- WebSocket 连接管理
- 自动重连逻辑
- 消息解析与分发

#### 2.2 状态管理实现

**文件**: `src/stores/gameStore.ts`
**文件**: `src/stores/connectionStore.ts`
**文件**: `src/stores/uiStore.ts`

#### 2.3 自定义 Hooks

**文件**: `src/hooks/useWebSocket.ts`
```typescript
function useWebSocket(sessionId: string | null) {
  // 管理 WebSocket 生命周期
  // 处理消息路由
  // 返回发送函数和连接状态
}
```

**文件**: `src/hooks/useGameActions.ts`
```typescript
function useGameActions() {
  // 封装游戏操作
  // startNewGame, sendInput, submitDice
}
```

---

### Phase 3: 通用组件（Day 4）

#### 3.1 布局组件

- `Layout.tsx`: 页面布局框架
- `Header.tsx`: 顶部导航栏
- `Footer.tsx`: 底部状态栏

#### 3.2 基础组件

- `Button.tsx`
- `Card.tsx`
- `Loading.tsx`
- `Modal.tsx`

---

### Phase 4: 页面组件（Day 5-7）

#### 4.1 MenuPage（Day 5）

- 菜单布局
- 新游戏流程
- 路由跳转

#### 4.2 GamePage（Day 5-6）

- 三栏布局
- 集成 ChatBox, StatBlock, DiceRoller
- WebSocket 消息处理

#### 4.3 功能组件（Day 6-7）

- ChatBox: 消息展示与输入
- StatBlock: 状态面板
- DiceRoller: 骰子检定

---

### Phase 5: 集成与优化（Day 8-9）

#### 5.1 WebSocket 集成

- 连接游戏会话
- 处理各类消息
- 流式内容渲染

#### 5.2 错误处理

- 连接失败提示
- 重连机制
- 错误边界

#### 5.3 响应式优化

- 移动端适配
- 触摸事件支持

---

### Phase 6: 测试与文档（Day 10）

#### 6.1 单元测试

- 组件测试
- Store 测试
- Hook 测试

#### 6.2 集成测试

- 完整游戏流程测试
- WebSocket 模拟测试

#### 6.3 文档更新

- 更新 PROGRESS.md
- 更新 ARCHITECTURE.md
- 添加 README

---

## 测试策略

### 单元测试

使用 Vitest + Testing Library：

```typescript
// ChatBox.test.tsx
describe('ChatBox', () => {
  it('renders messages correctly', () => {
    const messages = [
      { role: 'user', content: 'Hello' },
      { role: 'assistant', content: 'Hi there!' },
    ];
    render(<ChatBox messages={messages} />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi there!')).toBeInTheDocument();
  });

  it('calls onSendMessage when submitting', async () => {
    const onSend = vi.fn();
    render(<ChatBox messages={[]} onSendMessage={onSend} />);
    
    await userEvent.type(screen.getByRole('textbox'), 'Test message');
    await userEvent.click(screen.getByRole('button', { name: /send/i }));
    
    expect(onSend).toHaveBeenCalledWith('Test message');
  });
});
```

### Store 测试

```typescript
// gameStore.test.ts
describe('gameStore', () => {
  beforeEach(() => {
    useGameStore.getState().reset();
  });

  it('adds message correctly', () => {
    const { addMessage } = useGameStore.getState();
    addMessage({ role: 'user', content: 'Test' });
    
    expect(useGameStore.getState().messages).toHaveLength(1);
  });
});
```

### E2E 测试（可选）

使用 Playwright：

```typescript
test('complete game flow', async ({ page }) => {
  await page.goto('/');
  
  // Start new game
  await page.click('text=新游戏');
  
  // Wait for game to initialize
  await page.waitForSelector('[data-testid="chat-input"]');
  
  // Send player input
  await page.fill('[data-testid="chat-input"]', '我查看周围');
  await page.click('[data-testid="send-button"]');
  
  // Wait for response
  await page.waitForSelector('[data-testid="assistant-message"]');
});
```

---

## 部署配置

### 开发环境

#### 方式一：手动启动（推荐用于调试）

```bash
# 启动后端
cd Astinus
uv run uvicorn src.backend.main:app --reload

# 启动前端（新终端）
cd Astinus/src/web
npm run dev
```

#### 方式二：使用 PM2 保活管理（推荐用于持续开发）

PM2 可以自动保持服务运行，崩溃自动重启，方便开发和测试。

```bash
# 安装 PM2（全局安装一次即可）
npm install -g pm2

# 使用项目配置文件启动所有服务
pm2 start pm2.config.js

# 查看运行状态
pm2 status

# 查看日志
pm2 logs

# 停止所有服务
pm2 stop all

# 重启前端（代码修改后）
pm2 restart astinus-frontend
```

项目根目录的 `pm2.config.js` 配置了前后端进程，详细说明参见 [DEPLOYMENT.md](./DEPLOYMENT.md)。

### 生产构建

```bash
# 构建前端
cd Astinus/src/web
npm run build

# 静态文件将生成在 dist/ 目录
```

### Docker 部署（可选）

```dockerfile
# Dockerfile.web
FROM node:20-alpine as builder
WORKDIR /app
COPY src/web/package*.json ./
RUN npm ci
COPY src/web/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

### 环境变量

```env
# .env.development
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000

# .env.production
VITE_API_BASE_URL=/api
VITE_WS_BASE_URL=wss://your-domain.com
```

---

## 项目完成总结

### ✅ 已完成项目

React Web 前端已成功完成，完全替代了原有的 Textual TUI 前端。项目于 2026-01-06 开始开发，2026-01-07 完成，历时约 2 天。

**完成的功能**:

1. ✅ 项目初始化 - Vite + React 19 + TypeScript + TailwindCSS
2. ✅ API 客户端 - REST API + WebSocket 客户端实现
3. ✅ 状态管理 - Zustand stores (game, connection, ui)
4. ✅ 通用组件 - Layout, Button, Card, Modal, Loading
5. ✅ ChatBox 组件 - 叙事展示、流式内容、玩家输入
6. ✅ StatBlock 组件 - 角色状态、位置、命运点
7. ✅ DiceRoller 组件 - 骰子检定、动画、结果提交
8. ✅ 页面组件 - MenuPage, GamePage, CharacterPage
9. ✅ WebSocket 集成 - 实时消息、流式内容、重连机制
10. ✅ 测试 - Vitest + Testing Library
11. ✅ 移动端优化 - 响应式设计、底部面板、触摸优化

**技术栈确认**:
- ✅ React 19 + TypeScript
- ✅ Vite (构建工具)
- ✅ TailwindCSS (样式)
- ✅ Zustand (状态管理)
- ✅ React Router v6 (路由)

**额外完成的功能**:
- 响应式设计，完美适配桌面和移动端
- 移动端友好 UI，底部面板设计
- 角色选择流程和预设角色支持
- 特性展示系统（工具提示和详情浮层）
- 防滚动锁定等移动端体验优化

**实际工期**: 5 天（超预期完成）

---

## 迁移状态

### ✅ 已完成项目

1. ✅ 删除 TUI 前端引用
2. ✅ 更新 `README.md` - 前端架构描述
3. ✅ 更新 `PROGRESS.md` - 标记新前端进度
4. ✅ 更新 `ARCHITECTURE.md` - 前端架构文档
5. ✅ 添加前端开发文档

### ⏳ 待办项目

1. [ ] 删除 `src/frontend/` 目录
2. [ ] 更新 `pyproject.toml` 移除 Textual 依赖
3. [ ] 添加 `src/web/README.md` - 前端专属文档

---

## 参考资料

- [React 文档](https://react.dev/)
- [Vite 文档](https://vitejs.dev/)
- [TailwindCSS 文档](https://tailwindcss.com/)
- [Zustand 文档](https://github.com/pmndrs/zustand)
- [FastAPI WebSocket 文档](https://fastapi.tiangolo.com/advanced/websockets/)