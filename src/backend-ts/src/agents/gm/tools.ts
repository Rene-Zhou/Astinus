/**
 * GM Agent Tools for Vercel AI SDK Function Calling
 * 
 * Defines tools for:
 * - search_lore: Query world lore and background information
 * - call_agent: Delegate to sub-agents (NPC, Rule, etc.)
 * - request_dice_check: Request player to roll dice for risky actions
 */

import { tool } from "ai";
import { z } from "zod";
import type { GameState, DiceCheckRequest } from "../../schemas";
import type { LoreService } from "../../services/lore";

interface SubAgent {
  process: (input: Record<string, unknown>) => Promise<AgentResponse>;
}

interface AgentResponse {
  content: string;
  success: boolean;
  error?: string;
  metadata?: Record<string, unknown>;
}

interface GMToolsContext {
  loreService?: LoreService;
  subAgents: Record<string, SubAgent>;
  gameState: GameState;
  worldPackLoader?: any;
  prepareAgentContext: (
    agentName: string,
    playerInput: string,
    lang: "cn" | "en",
    providedContext: Record<string, any>,
    diceResult: Record<string, any> | null
  ) => Promise<Record<string, any>>;
  buildDiceCheckRequest: (
    intention: string,
    reason: string,
    lang: "cn" | "en"
  ) => DiceCheckRequest;
  getCurrentRegion: () => Promise<string | undefined>;
}

export function createGMTools(context: GMToolsContext, lang: "cn" | "en") {
  const {
    loreService,
    subAgents,
    gameState,
    prepareAgentContext,
    buildDiceCheckRequest,
    getCurrentRegion,
  } = context;

  return {
    search_lore: tool({
      description:
        lang === "cn"
          ? "查询世界观、历史或背景设定信息"
          : "Search for lore, history, or world setting information",
      inputSchema: z.object({
        query: z
          .string()
          .describe(
            lang === "cn" ? "搜索关键词" : "Search query"
          ),
        reasoning: z
          .string()
          .optional()
          .describe(
            lang === "cn"
              ? "为什么需要查询这个信息（可选）"
              : "Why this search is needed (optional)"
          ),
      }),
      execute: async ({ query, reasoning }) => {
        if (!loreService) {
          return lang === "cn"
            ? "背景信息服务不可用。"
            : "Lore service unavailable.";
        }

        console.log(
          `[GM Tool: search_lore] Query: "${query}" | Reasoning: ${reasoning || "N/A"}`
        );

        const result = await loreService.search({
          query,
          context: gameState.messages[gameState.messages.length - 1]?.content || "",
          worldPackId: gameState.world_pack_id,
          currentLocation: gameState.current_location,
          currentRegion: await getCurrentRegion(),
          lang,
        });

        return result;
      },
    }),

    call_agent: tool({
      description:
        lang === "cn"
          ? "调用子 Agent（特别是 NPC）处理特定任务。NPC 对话时必须使用此工具（agent_name 格式: 'npc_<id>'）。绝对禁止你自己扮演 NPC。"
          : "Call a sub-agent to handle specific tasks. MUST use this tool for NPC dialogue (agent_name format: 'npc_<id>'). You are FORBIDDEN from roleplaying NPCs yourself.",
      inputSchema: z.object({
        agent_name: z
          .string()
          .describe(
            lang === "cn"
              ? "Agent 标识符（例如：'npc_guard' 表示守卫 NPC）"
              : "Agent identifier (e.g., 'npc_guard' for guard NPC)"
          ),
        instruction: z
          .string()
          .optional()
          .describe(
            lang === "cn"
              ? "给 Agent 的指令或上下文（可选）"
              : "Instruction or context for the agent (optional)"
          ),
        reasoning: z
          .string()
          .optional()
          .describe(
            lang === "cn" ? "调用此 Agent 的理由" : "Reason for calling this agent"
          ),
      }),
      execute: async ({ agent_name, instruction, reasoning }) => {
        console.log(
          `[GM Tool: call_agent] Agent: ${agent_name} | Reasoning: ${reasoning || "N/A"}`
        );

        let actualAgentName = agent_name;
        if (agent_name.startsWith("npc_")) {
          actualAgentName = "npc";
        }

        const subAgent = subAgents[actualAgentName];
        if (!subAgent) {
          return lang === "cn"
            ? `错误：找不到 Agent '${agent_name}'`
            : `Error: Agent '${agent_name}' not found`;
        }

        const playerInput = gameState.messages[gameState.messages.length - 1]?.content || "";
        const agentContext = await prepareAgentContext(
          agent_name,
          playerInput,
          lang,
          { instruction },
          null
        );

        const response = await subAgent.process(agentContext);

        if (!response.success) {
          return lang === "cn"
            ? `Agent ${agent_name} 调用失败: ${response.error || "未知错误"}`
            : `Agent ${agent_name} failed: ${response.error || "unknown error"}`;
        }

        if (agent_name.startsWith("npc_")) {
          const metadata = response.metadata || {};
          const emotion = metadata.emotion || "neutral";
          const action = metadata.action || "";

          const parts: string[] = [];
          parts.push(`对白: ${response.content}`);
          if (emotion !== "neutral") {
            parts.push(`情绪: ${emotion}`);
          }
          if (action) {
            parts.push(`动作: ${action}`);
          }

          return parts.join("\n");
        }

        return response.content;
      },
    }),

    request_dice_check: tool({
      description:
        lang === "cn"
          ? "请求玩家进行骰子检定。当玩家尝试有风险、不确定或有重大后果的行动时使用。调用此工具后，当前回合结束，等待玩家掷骰。"
          : "Request a dice check from the player. Use when player attempts risky, uncertain, or consequential actions. Calling this tool ends the current turn and waits for player to roll.",
      inputSchema: z.object({
        intention: z
          .string()
          .describe(
            lang === "cn"
              ? "玩家尝试做什么（例如：'说服守卫放行'）"
              : "What the player is trying to do (e.g., 'persuade the guard')"
          ),
        reason: z
          .string()
          .describe(
            lang === "cn"
              ? "为什么需要检定（向玩家解释）"
              : "Why a check is needed (explain to player)"
          ),
      }),
      execute: async ({ intention, reason }) => {
        console.log(
          `[GM Tool: request_dice_check] Intention: "${intention}" | Reason: "${reason}"`
        );

        const checkRequest = buildDiceCheckRequest(intention, reason, lang);

        gameState.current_phase = "dice_check";

        gameState.temp_context = {
          ...gameState.temp_context,
          pending_check_request: checkRequest,
        };

        return lang === "cn"
          ? `已请求骰子检定：${intention}`
          : `Dice check requested: ${intention}`;
      },
    }),
  };
}
