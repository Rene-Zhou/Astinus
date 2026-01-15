# 架构重构计划：Lore 服务化与掷骰工具化

**日期**: 2026-01-15
**状态**: 待实施
**目标**: 简化 Agent 架构，明确职责边界，将确定性逻辑从 Agent 剥离为工具 (Tool)，降低 LLM 认知负荷。

## 1. 概述 (Overview)

目前的系统架构中，GM Agent 通过 ReAct 循环调用子 Agent。虽然 NPC Agent 需要复杂的角色扮演推理，适合作为独立 Agent，但 **Lore Agent** 和 **掷骰请求 (Dice Check)** 的实现方式存在架构冗余和语义混淆：

1.  **Lore Agent**：本质是确定性的混合搜索逻辑，不涉及 LLM 推理，却包装成 Agent，增加了调用链路复杂度。
2.  **掷骰请求**：目前通过 `RESPOND` 动作夹带 `needs_check` 字段实现，导致 `RESPOND` 语义不纯粹（既是“说话”又是“指令”），增加了 Prompt 的复杂度和出错率。

本计划旨在将这两者重构为 **GM Agent 的内置工具 (Tools/Function Calls)**。

---

## 2. 改造方案 (Refactoring Plan)

### 阶段一：Lore Agent -> Lore Service (Lore 服务化)

将 `LoreAgent` 降级为纯逻辑服务，GM 不再通过 `CALL_AGENT` 指令与“Lore Agent”对话，而是直接调用本地工具函数。

#### 核心改动

1.  **新建 `LoreService`**
    *   **位置**: `src/backend/services/lore.py`
    *   **职责**: 封装混合搜索（关键词+向量）逻辑。
    *   **迁移**: 将 `src/backend/agents/lore.py` 中的 `_search_lore` 和 `_format_lore` 逻辑完整迁移至此。
    *   **接口**: `search(query: str, location_id: str, ...)` -> `str` (格式化后的文本)

2.  **修改 `GMAgent`**
    *   **移除**: 从 `sub_agents` 中移除 `lore`。
    *   **新增工具**: 在 GM 的 ReAct 循环逻辑中，新增对 `SEARCH_LORE` (或 `CALL_TOOL(name="lore")`) 的支持。
    *   **执行**: 拦截该动作，直接调用 `LoreService.search()`，将结果立即加入 ReAct 上下文（无需走 Agent 异步调用链路）。

3.  **更新 Prompt (`gm_agent.yaml`)**
    *   **移除**: `CALL_AGENT` 说明中关于 Lore 的部分。
    *   **新增**: 在可用工具/动作列表中增加 `SEARCH_LORE`。
    *   **示例**:
        ```json
        {
          "action": "SEARCH_LORE",
          "reasoning": "玩家询问关于龙枪的历史，需要检索背景知识",
          "query": "龙枪战争 历史"
        }
        ```

#### 涉及文件

*   `src/backend/services/lore.py` (New)
*   `src/backend/agents/lore.py` (Delete/Deprecate)
*   `src/backend/agents/gm.py` (Modify `_run_react_loop`, `__init__`, logic flow)
*   `src/backend/agents/prompts/gm_agent.yaml` (Modify instructions)
*   `src/backend/main.py` (Update initialization)

---

### 阶段二：Dice Check -> Tool Call (掷骰工具化)

将掷骰请求从 `RESPOND` 动作中剥离，使其成为一个独立的控制流动作。

#### 核心改动

1.  **定义新动作 `REQUEST_CHECK`**
    *   GM 不再使用 `RESPOND` 来发起检定。
    *   新增动作类型 `REQUEST_CHECK`。

2.  **更新 Prompt (`gm_agent.yaml`)**
    *   **修改动作定义**:
        *   `RESPOND`: 仅用于输出最终叙事。
        *   `REQUEST_CHECK`: 仅用于发起掷骰。
        *   `CALL_AGENT`: 仅用于 NPC 交互。
    *   **JSON 结构**:
        ```json
        {
          "action": "REQUEST_CHECK",
          "reasoning": "玩家试图攀爬湿滑的城墙，这涉及体质挑战",
          "check_request": {
             "intention": "攀爬城墙",
             "dice_formula": "2d6",
             "difficulty": 7
             // ...其他字段保持不变
          },
          "narrative": "你抓住一块突出的石砖，脚下用力蹬起..." // 描述尝试动作
        }
        ```

3.  **修改 `GMAgent` 逻辑**
    *   在 `_run_react_loop` 中处理 `REQUEST_CHECK`。
    *   逻辑与原 `needs_check=True` 类似：保存 ReAct 状态 -> 设置游戏阶段为 `DICE_CHECK` -> 返回带有特定 Metadata 的 Response。

4.  **修改 WebSocket 处理 (`websockets.py`)**
    *   适配新的 Response Metadata 结构，触发 `send_dice_check`。

#### 涉及文件

*   `src/backend/agents/gm.py` (Enum `GMActionType`, logic flow)
*   `src/backend/agents/prompts/gm_agent.yaml` (Prompt update)
*   `src/backend/api/websockets.py` (Minor update to metadata parsing)

---

## 3. 测试影响 (Testing Implications)

这次重构会破坏现有的许多测试，需要同步更新。

1.  **单元测试 (`tests/backend/agents/test_gm.py`)**
    *   **Mock 对象**: 之前 Mock 的是 `LoreAgent`，现在需要 Mock `LoreService`。
    *   **断言更新**:
        *   检查 GM 是否生成 `SEARCH_LORE` 而不是 `CALL_AGENT(lore)`。
        *   检查 GM 是否生成 `REQUEST_CHECK` 而不是 `RESPOND(needs_check=True)`。

2.  **集成测试**
    *   验证 `LoreService` 能正确连接 ChromaDB 并返回结果。
    *   验证 ReAct 循环在 `REQUEST_CHECK` 后能正确挂起，并在 `resume_after_dice` 后正确恢复。

---

## 4. 实施步骤 (Implementation Guide)

建议按以下顺序执行：

1.  **Service 抽取**: 创建 `LoreService` 并编写单元测试，确保逻辑与原 `LoreAgent` 一致。
2.  **GM 逻辑改造 (Lore)**: 修改 GM 代码和 Prompt，接入 `LoreService`，移除 `LoreAgent`。运行测试确保 Lore 功能正常。
3.  **GM 逻辑改造 (Dice)**: 修改 GM 代码和 Prompt，实现 `REQUEST_CHECK`。更新 WebSocket 处理逻辑。
4.  **清理**: 删除废弃的 `LoreAgent` 代码，更新文档。

## 5. 预期收益

*   **Prompt 更纯净**: 模型不再需要在 `RESPOND` 的定义中纠结“何时加 check 字段”。
*   **架构更清晰**: 明确了 Service (工具) 与 Agent (智能体) 的界限。
*   **扩展性更强**: 未来添加更多工具（如查询天气、背包管理）时，可以直接复用 Tool Call 模式。
