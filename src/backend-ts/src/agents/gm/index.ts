import { generateObject, generateText } from "ai";
import type { LanguageModel } from "ai";
import type { GameState } from "../../schemas";
import { z } from "zod";

const GMActionTypeSchema = z.enum([
  "RESPOND",
  "CALL_AGENT",
  "SEARCH_LORE",
  "REQUEST_CHECK",
]);

const GMActionSchema = z.object({
  action_type: GMActionTypeSchema,
  content: z.string().default(""),
  agent_name: z.string().optional(),
  agent_context: z.record(z.any()).default({}),
  check_request: z.record(z.any()).optional(),
  reasoning: z.string().default(""),
});

type GMAction = z.infer<typeof GMActionSchema>;

type StatusCallback = (agentName: string, status: string | null) => Promise<void>;

interface SubAgent {
  process: (input: Record<string, unknown>) => Promise<AgentResponse>;
}

interface AgentResponse {
  content: string;
  success: boolean;
  error?: string;
  metadata?: Record<string, unknown>;
}

interface GMProcessInput {
  player_input: string;
  lang?: "cn" | "en";
}

interface ReActLoopParams {
  playerInput: string;
  lang: "cn" | "en";
  iteration: number;
  agentResults: Array<Record<string, unknown>>;
  diceResult: Record<string, unknown> | null;
}

export class GMAgent {
  private statusCallback?: StatusCallback;

  constructor(
    private llm: LanguageModel,
    private subAgents: Record<string, SubAgent>,
    private gameState: GameState,
    private loreService?: any
  ) {}

  setStatusCallback(callback: StatusCallback): void {
    this.statusCallback = callback;
  }

  getGameState(): GameState {
    return this.gameState;
  }

  async process(inputData: GMProcessInput): Promise<AgentResponse> {
    const playerInput = inputData.player_input;
    const lang = inputData.lang || "cn";

    if (!playerInput) {
      return {
        content: "",
        success: false,
        error: "GM Agent: No player input provided",
        metadata: { agent: "gm_agent" },
      };
    }

    if (this.statusCallback) {
      await this.statusCallback("gm", null);
    }

    this.gameState.messages.push({
      role: "user",
      content: playerInput,
      timestamp: new Date().toISOString(),
      turn: this.gameState.turnCount,
    });

    return this.runReActLoop({
      playerInput,
      lang,
      iteration: 0,
      agentResults: [],
      diceResult: null,
    });
  }

  async resumeAfterDice(
    diceResult: Record<string, unknown>,
    lang: "cn" | "en" = "cn"
  ): Promise<AgentResponse> {
      const pendingState = this.gameState.reactPendingState;

    if (!pendingState) {
      return {
        content: "",
        success: false,
        error: "No pending ReAct state to resume",
        metadata: { agent: "gm_agent" },
      };
    }

    const playerInput = pendingState.player_input as string;
    const iteration = pendingState.iteration as number;
    const agentResults = pendingState.agent_results as Array<
      Record<string, unknown>
    >;

          this.gameState.reactPendingState = null;

    return this.runReActLoop({
      playerInput,
      lang,
      iteration,
      agentResults,
      diceResult,
    });
  }

  private async runReActLoop(params: ReActLoopParams): Promise<AgentResponse> {
    const { playerInput, lang, iteration, agentResults, diceResult } = params;

    const maxIterations = 5;
    const agentsCalled: string[] = [];

    if (iteration >= maxIterations) {
      return {
        content: "",
        success: false,
        error: "Max ReAct iterations reached",
        metadata: { agent: "gm_agent", iteration },
      };
    }

    const context = this.buildContext(
      playerInput,
      lang,
      iteration,
      agentResults,
      diceResult
    );

    const action = await this.decideAction(context, lang);

    switch (action.action_type) {
      case "RESPOND":
        return this.generateResponse(context, action, lang);

      case "SEARCH_LORE":
        if (this.loreService) {
          const loreResult = await this.loreService.search({
            query: action.content,
            context: playerInput,
            worldPackId: this.gameState.worldPackId,
            currentLocation: this.gameState.currentLocation,
            currentRegion: this.getCurrentRegion(),
            lang,
          });

          agentResults.push({
            agent: "lore",
            result: loreResult,
            reasoning: action.reasoning,
          });

          return this.runReActLoop({
            playerInput,
            lang,
            iteration: iteration + 1,
            agentResults,
            diceResult,
          });
        }
        break;

      case "REQUEST_CHECK":
        this.gameState.reactPendingState = {
          player_input: playerInput,
          iteration: iteration + 1,
          agent_results: agentResults,
        };

        return {
          content: action.content,
          success: true,
          metadata: {
            agent: "gm_agent",
            requires_dice: true,
            check_request: action.check_request,
          },
        };

      case "CALL_AGENT":
        if (action.agent_name && this.subAgents[action.agent_name]) {
          if (this.statusCallback) {
            await this.statusCallback(action.agent_name, null);
          }

          agentsCalled.push(action.agent_name);

          const subAgent = this.subAgents[action.agent_name];
          if (!subAgent) {
            throw new Error(`Sub-agent not found: ${action.agent_name}`);
          }

          const subAgentResponse = await subAgent.process(action.agent_context);

          agentResults.push({
            agent: action.agent_name,
            result: subAgentResponse.content,
            success: subAgentResponse.success,
            reasoning: action.reasoning,
          });

          return this.runReActLoop({
            playerInput,
            lang,
            iteration: iteration + 1,
            agentResults,
            diceResult,
          });
        }
        break;
    }

    return {
      content: "",
      success: false,
      error: "Unknown action or missing service",
      metadata: { agent: "gm_agent" },
    };
  }

  private async decideAction(
    context: string,
    lang: "cn" | "en"
  ): Promise<GMAction> {
    const systemPrompt = this.buildDecisionPrompt(lang);

    const { object } = await generateObject({
      model: this.llm,
      schema: GMActionSchema,
      system: systemPrompt,
      prompt: context,
    });

    return object;
  }

  private async generateResponse(
    context: string,
    action: GMAction,
    lang: "cn" | "en"
  ): Promise<AgentResponse> {
    const systemPrompt = this.buildNarrativePrompt(lang);

    const { text } = await generateText({
      model: this.llm,
      system: systemPrompt,
      prompt: context + "\n\nReasoning: " + action.reasoning,
    });

    this.gameState.messages.push({
      role: "assistant",
      content: text,
      timestamp: new Date().toISOString(),
      turn: this.gameState.turnCount,
    });

    return {
      content: text,
      success: true,
      metadata: { agent: "gm_agent" },
    };
  }

  private buildContext(
    playerInput: string,
    lang: "cn" | "en",
    iteration: number,
    agentResults: Array<Record<string, unknown>>,
    diceResult: Record<string, unknown> | null
  ): string {
    const parts: string[] = [];

    parts.push(`Player Input: ${playerInput}`);
    parts.push(`Language: ${lang}`);
    parts.push(`Iteration: ${iteration}`);

    parts.push(`\nGame State:`);
    parts.push(`  Phase: ${this.gameState.currentPhase}`);
    parts.push(`  Turn: ${this.gameState.turnCount}`);
    parts.push(`  Location: ${this.gameState.currentLocation}`);

    if (this.gameState.player) {
      parts.push(`  Player:`);
      parts.push(`  Name: ${this.gameState.player.name}`);
      parts.push(`  Traits: ${this.gameState.player.traits.length}`);
    }

    if (agentResults.length > 0) {
      parts.push(`\nAgent Results:`);
      for (const result of agentResults) {
        parts.push(`  - ${result.agent}: ${result.reasoning}`);
        parts.push(`    Result: ${JSON.stringify(result.result)}`);
      }
    }

    if (diceResult) {
      parts.push(`\nDice Result: ${JSON.stringify(diceResult)}`);
    }

    const recentMessages = this.gameState.messages.slice(-10);
    if (recentMessages.length > 0) {
      parts.push(`\nRecent Messages:`);
      for (const msg of recentMessages) {
        parts.push(`  ${msg.role}: ${msg.content}`);
      }
    }

    return parts.join("\n");
  }

  private buildDecisionPrompt(lang: "cn" | "en"): string {
    if (lang === "cn") {
      return `你是游戏主持人(GM),负责协调多个子代理。
分析玩家输入,决定下一步行动:
- RESPOND: 直接回应玩家
- SEARCH_LORE: 搜索背景知识
- REQUEST_CHECK: 请求掷骰检定
- CALL_AGENT: 调用子代理(rule, npc等)

返回JSON格式的行动决策。`;
    }

    return `You are the Game Master (GM) coordinating multiple sub-agents.
Analyze player input and decide the next action:
- RESPOND: Directly respond to player
- SEARCH_LORE: Search background lore
- REQUEST_CHECK: Request dice check
- CALL_AGENT: Call sub-agent (rule, npc, etc.)

Return action decision in JSON format.`;
  }

  private buildNarrativePrompt(lang: "cn" | "en"): string {
    if (lang === "cn") {
      return `你是一位经验丰富的游戏主持人。
基于游戏状态和代理结果,生成引人入胜的叙事描述。
保持角色扮演的沉浸感,使用生动的语言。`;
    }

    return `You are an experienced Game Master.
Based on game state and agent results, generate engaging narrative.
Maintain immersive roleplay and use vivid language.`;
  }

  private getCurrentRegion(): string | undefined {
    return undefined;
  }
}
