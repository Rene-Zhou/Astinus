import { generateText, stepCountIs } from "ai";
import type { LanguageModel } from "ai";
import type { GameState, DiceCheckRequest } from "../../schemas";
import { LocationContextService } from "../../services/location-context";
import { WorldPackLoader } from "../../services/world";
import { getLocalizedString } from "../../schemas";
import type { NPCData } from "../../schemas";
import { DicePool } from "../../services/dice";
import { createGMTools } from "./tools";

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

export class GMAgent {
  private statusCallback?: StatusCallback;
  private locationContextService?: LocationContextService;

  constructor(
    private llm: LanguageModel,
    private subAgents: Record<string, SubAgent>,
    private gameState: GameState,
    private loreService?: any,
    private worldPackLoader?: WorldPackLoader
  ) {
    if (this.worldPackLoader) {
      this.locationContextService = new LocationContextService(this.worldPackLoader);
    }
  }

  setStatusCallback(callback: StatusCallback): void {
    this.statusCallback = callback;
  }

  getGameState(): GameState {
    return this.gameState;
  }

  private async getCurrentRegion(): Promise<string | undefined> {
    if (!this.worldPackLoader) {
      return undefined;
    }

    try {
      const pack = await this.worldPackLoader.load(this.gameState.world_pack_id);
      const location = pack.locations[this.gameState.current_location];
      return location?.region_id;
    } catch (error) {
      console.error("[GMAgent] Failed to get current region:", error);
      return undefined;
    }
  }

  private buildDiceCheckRequest(
    intention: string,
    reason: string,
    lang: "cn" | "en"
  ): DiceCheckRequest {
    const playerTraits = this.gameState.player?.traits || [];
    const playerTags = this.gameState.player?.tags || [];

    const relevantTraits: string[] = [];
    const relevantTags: string[] = [];

    for (const trait of playerTraits) {
      const traitName = typeof trait.name === 'string' 
        ? trait.name 
        : (trait.name as any)[lang] || (trait.name as any).cn;
      
      if (intention.toLowerCase().includes(traitName.toLowerCase()) || 
          reason.toLowerCase().includes(traitName.toLowerCase())) {
        relevantTraits.push(traitName);
      }
    }

    for (const tag of playerTags) {
      if (intention.toLowerCase().includes(tag.toLowerCase()) || 
          reason.toLowerCase().includes(tag.toLowerCase())) {
        relevantTags.push(tag);
      }
    }

    let bonusDice = 0;
    let penaltyDice = 0;

    if (relevantTraits.length > 0) {
      bonusDice = 1;
    }

    if (relevantTags.length > 0) {
      penaltyDice = 1;
    }

    const pool = new DicePool(0, bonusDice, penaltyDice);
    const diceFormula = pool.getDiceFormula();

    let instructionsCn = reason || "进行一次检定。";
    let instructionsEn = reason || "Make a check.";

    if (relevantTraits.length > 0) {
      const traitList = relevantTraits.join("、");
      instructionsCn += ` 你的特质「${traitList}」在此发挥作用。`;
      instructionsEn += ` Your trait(s) "${traitList}" come into play.`;
    }

    if (relevantTags.length > 0) {
      const tagList = relevantTags.join("、");
      instructionsCn += ` 当前状态「${tagList}」影响了你的行动。`;
      instructionsEn += ` Current status "${tagList}" affects your action.`;
    }

    return {
      intention,
      influencing_factors: {
        traits: relevantTraits,
        tags: relevantTags
      },
      dice_formula: diceFormula,
      instructions: {
        cn: instructionsCn,
        en: instructionsEn
      }
    };
  }

  async process(inputData: GMProcessInput): Promise<AgentResponse> {
    console.log("[GMAgent] Processing input:", inputData);
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
      turn: this.gameState.turn_count,
    });

    return this.runReActWithTools({
      playerInput,
      lang,
      diceResult: null,
    });
  }

  async resumeAfterDice(
    diceResult: Record<string, unknown>,
    lang: "cn" | "en" = "cn"
  ): Promise<AgentResponse> {
    const pendingState = this.gameState.react_pending_state;

    if (!pendingState) {
      return {
        content: "",
        success: false,
        error: "No pending ReAct state to resume",
        metadata: { agent: "gm_agent" },
      };
    }

    const playerInput = pendingState.player_input as string;

    this.gameState.react_pending_state = null;

    return this.runReActWithTools({
      playerInput,
      lang,
      diceResult,
    });
  }

  private async runReActWithTools(params: {
    playerInput: string;
    lang: "cn" | "en";
    diceResult: Record<string, unknown> | null;
  }): Promise<AgentResponse> {
    const { playerInput, lang, diceResult } = params;
    const maxIterations = 5;

    const tools = createGMTools(
      {
        loreService: this.loreService,
        subAgents: this.subAgents,
        gameState: this.gameState,
        worldPackLoader: this.worldPackLoader,
        prepareAgentContext: this.prepareAgentContext.bind(this),
        buildDiceCheckRequest: this.buildDiceCheckRequest.bind(this),
        getCurrentRegion: this.getCurrentRegion.bind(this),
      },
      lang
    );

    const context = await this.buildContext(
      playerInput,
      lang,
      diceResult
    );

    const systemPrompt = this.buildSystemPrompt(lang);

    try {
      const { text, finishReason, steps } = await generateText({
        model: this.llm,
        system: systemPrompt,
        prompt: context,
        tools,
        stopWhen: stepCountIs(maxIterations),
      });

      console.log(`[GMAgent] Generated response after ${steps.length} steps`);
      console.log(`[GMAgent] Finish reason: ${finishReason}`);

      if (this.gameState.current_phase === "dice_check") {
        const pendingCheckRequest = this.gameState.temp_context?.pending_check_request;

        this.gameState.react_pending_state = {
          player_input: playerInput,
          iteration: steps.length,
          agent_results: [],
        };

        return {
          content: text || "",
          success: true,
          metadata: {
            agent: "gm_agent",
            requires_dice: true,
            check_request: pendingCheckRequest,
          },
        };
      }

      this.gameState.turn_count += 1;
      this.gameState.updated_at = new Date().toISOString();

      this.gameState.messages.push({
        role: "assistant",
        content: text,
        timestamp: new Date().toISOString(),
        turn: this.gameState.turn_count,
        metadata: {
          phase: "gm_response",
        },
      });

      this.gameState.current_phase = "waiting_input";

      return {
        content: text,
        success: true,
        metadata: { agent: "gm_agent" },
      };
    } catch (error) {
      console.error("[GMAgent] Error in runReActWithTools:", error);
      return {
        content: "",
        success: false,
        error: error instanceof Error ? error.message : String(error),
        metadata: { agent: "gm_agent" },
      };
    }
  }

  private async prepareAgentContext(
    agentName: string,
    playerInput: string,
    lang: "cn" | "en",
    providedContext: Record<string, any>,
    diceResult: Record<string, any> | null
  ): Promise<Record<string, any>> {
    if (agentName.startsWith("npc_")) {
      const npcId = agentName.replace("npc_", "");
      return this.sliceContextForNpc(npcId, playerInput, lang, diceResult);
    }
    
    return {
      player_input: playerInput,
      lang: lang,
      ...providedContext
    };
  }

  private async buildContext(
    playerInput: string,
    lang: "cn" | "en",
    diceResult: Record<string, unknown> | null
  ): Promise<string> {
    const sceneContext = await this.getSceneContext(lang);
    const parts: string[] = [];

    parts.push(`Language: ${lang === 'cn' ? 'Chinese (Simplified)' : 'English'}`);
    parts.push(`Player Input: ${playerInput}`);

    parts.push(`\n[Game State]`);
    parts.push(`Phase: ${this.gameState.current_phase}`);
    parts.push(`Turn: ${this.gameState.turn_count}`);
    parts.push(`Location ID: ${this.gameState.current_location}`);

    if (sceneContext) {
      parts.push(`\n[Region & Location]`);
      parts.push(`Region: ${sceneContext.region.name}`);
      if (sceneContext.region.narrative_tone) {
        parts.push(`Tone: ${sceneContext.region.narrative_tone}`);
      }
      if (sceneContext.region.atmosphere_keywords && sceneContext.region.atmosphere_keywords.length > 0) {
        parts.push(`Atmosphere Keywords: ${sceneContext.region.atmosphere_keywords.join(", ")}`);
      }

      parts.push(`Location: ${sceneContext.location.name}`);
      parts.push(`Description: ${sceneContext.location.description}`);
      if (sceneContext.location.atmosphere) {
        parts.push(`Atmosphere: ${sceneContext.location.atmosphere}`);
      }
      if (sceneContext.atmosphere_guidance) {
        parts.push(`Guidance: ${sceneContext.atmosphere_guidance}`);
      }
      parts.push(`Visible Items: ${sceneContext.location.visible_items.join(", ")}`);

      const hiddenHints = this.generateHiddenItemHints(sceneContext.location.hidden_items_remaining || [], lang);
      if (hiddenHints) {
        parts.push(`Hidden Clues: ${hiddenHints}`);
      }

      if (this.worldPackLoader && this.gameState.world_pack_id) {
        try {
          const pack = await this.worldPackLoader.load(this.gameState.world_pack_id);
          const loc = pack.locations[this.gameState.current_location];
          if (loc && loc.connected_locations) {
            const connections = loc.connected_locations.map(id => {
              const target = pack.locations[id];
              const name = target ? getLocalizedString(target.name, lang) : id;
              return `${name} (ID: ${id})`;
            });
            parts.push(`Can Go To: ${connections.join(", ")}`);
          }
        } catch (e) {
          console.error("[GMAgent] Failed to load connected locations:", e);
        }
      }

      if (sceneContext.basic_lore.length > 0) {
        parts.push(`\n[Relevant Lore]`);
        sceneContext.basic_lore.forEach(lore => parts.push(`- ${lore}`));
      }

      if (this.worldPackLoader) {
        try {
          const pack = await this.worldPackLoader.load(this.gameState.world_pack_id);
          const constantEntries = pack.entries 
            ? Object.values(pack.entries).filter((e: any) => e.is_constant)
            : [];

          if (constantEntries.length > 0) {
            parts.push(`\n[World Background]`);
            constantEntries.forEach((e: any) => {
              const content = getLocalizedString(e.content, lang);
              if (content) parts.push(content);
            });
          }
        } catch (e) {
          console.error("[GMAgent] Failed to load world background:", e);
        }
      }
    }

    if (this.gameState.active_npc_ids.length > 0 && this.worldPackLoader) {
      try {
        const pack = await this.worldPackLoader.load(this.gameState.world_pack_id);
        parts.push(`\n[Active NPCs]`);
        for (const npcId of this.gameState.active_npc_ids) {
          const npc = pack.npcs[npcId];
          if (npc) {
            const name = npc.soul.name;
            const desc = getLocalizedString(npc.soul.description, lang);
            const brief = desc.length > 100 ? desc.substring(0, 100) + "..." : desc;
            parts.push(`- ID: ${npcId} | Name: ${name} | Description: ${brief}`);
          }
        }
      } catch (e) {
        console.error("[GMAgent] Failed to load active NPCs context", e);
      }
    }

    if (this.gameState.player) {
      parts.push(`\n[Player Character]`);
      parts.push(`Name: ${this.gameState.player.name}`);
      const concept = typeof this.gameState.player.concept === 'string'
        ? this.gameState.player.concept
        : (this.gameState.player.concept as any)[lang] || JSON.stringify(this.gameState.player.concept);
      parts.push(`Concept: ${concept}`);

      parts.push(`Traits:`);
      this.gameState.player.traits.forEach(t => {
        const name = (t.name as any)[lang] || t.name;
        const desc = (t.description as any)[lang] || t.description;
        const pos = (t.positive_aspect as any)[lang] || t.positive_aspect;
        const neg = (t.negative_aspect as any)[lang] || t.negative_aspect;

        parts.push(`- ${name}`);
        parts.push(`  Description: ${desc}`);
        parts.push(`  Positive: ${pos}`);
        parts.push(`  Negative: ${neg}`);
      });

      if (this.gameState.player.tags && this.gameState.player.tags.length > 0) {
        parts.push(`Current Tags: ${this.gameState.player.tags.join(", ")}`);
      }
    }

    const recentMessages = this.gameState.messages.slice(-10);
    if (recentMessages.length > 0) {
      parts.push(`\n[Conversation History]`);
      for (const msg of recentMessages) {
        parts.push(`  [Turn ${msg.turn}] ${msg.role}: ${msg.content}`);
      }
    }

    if (diceResult) {
      parts.push(`\n[Dice Result]`);
      parts.push(`Intention: ${diceResult.intention}`);
      parts.push(`Result: ${diceResult.total} (${diceResult.outcome})`);
    }

    return parts.join("\n");
  }

  private buildSystemPrompt(lang: "cn" | "en"): string {
    return lang === "cn" 
      ? `你是游戏主持人（GM），负责协调一个 TTRPG 游戏。

你的角色是分析玩家的输入并决定下一步行动。你拥有以下工具：

1. **search_lore**: 查询世界观、历史或背景信息
2. **call_agent**: 调用子 Agent（特别是 NPC）处理特定任务
3. **request_dice_check**: 请求玩家进行骰子检定（当行动有风险时）

重要规则：
- 当玩家与 NPC 对话时，**必须**使用 call_agent 工具，绝对禁止你自己扮演 NPC
- 当需要背景信息时，使用 search_lore 工具
- 当玩家行动有风险或不确定性时，使用 request_dice_check 工具
- 调用 request_dice_check 后，回合结束，等待玩家掷骰
- 使用第二人称（"你"）保持沉浸感
- 绝对禁止在叙事中显示任何 ID 或技术名称
- 不要透露玩家不应该知道的信息`
      : `You are the Game Master (GM) orchestrating a TTRPG session.

Your role is to analyze player input and decide the next action. You have the following tools:

1. **search_lore**: Query world lore, history, or background information
2. **call_agent**: Call sub-agents (especially NPCs) to handle specific tasks
3. **request_dice_check**: Request player to roll dice (when action is risky)

Important Rules:
- When player talks to NPCs, you **MUST** use call_agent tool. You are FORBIDDEN from roleplaying NPCs yourself
- When background information is needed, use search_lore tool
- When player action has risk or uncertainty, use request_dice_check tool
- After calling request_dice_check, the turn ends and waits for player to roll
- Use second person ("you") to maintain immersion
- NEVER show any IDs or technical names in narrative
- Do NOT reveal information the player shouldn't know`;
  }

  private async sliceContextForNpc(
    npcId: string,
    playerInput: string,
    lang: "cn" | "en",
    diceResult: Record<string, any> | null
  ): Promise<Record<string, any>> {
    const recentMessages = this.gameState.messages.slice(-10);

    let npcData: NPCData | undefined;
    if (this.worldPackLoader) {
      try {
        const pack = await this.worldPackLoader.load(this.gameState.world_pack_id);
        npcData = pack.npcs[npcId];
      } catch (error) {
        console.error(`Failed to load NPC data for ${npcId}:`, error);
      }
    }

    const narrativeStyle = "detailed";

    const context: Record<string, any> = {
      npc_id: npcId,
      player_input: playerInput,
      recent_messages: recentMessages,
      lang: lang,
      narrative_style: narrativeStyle,
      context: {
        location: this.gameState.current_location,
        world_pack_id: this.gameState.world_pack_id,
      }
    };

    if (npcData) {
      context.npc_data = npcData;
    }

    if (diceResult) {
      context.roleplay_direction = this.generateRoleplayDirection(diceResult, lang);
    }

    return context;
  }

  private generateRoleplayDirection(
    diceResult: Record<string, any>,
    lang: "cn" | "en"
  ): string {
    const outcome = diceResult.outcome as string;
    if (!outcome) return "";

    const directions: Record<string, Record<string, string>> = {
      cn: {
        critical_success: "NPC 应该非常积极地回应，态度明显软化甚至热情，愿意主动提供帮助或重要信息。",
        success: "NPC 应该积极回应，态度有所软化，愿意提供帮助或信息。",
        partial: "NPC 的态度应有所松动，但仍保持一定警惕，可能只透露有限信息、给出警告、或提出额外条件。",
        failure: "NPC 应该拒绝请求，态度可能更加冷淡或警惕。",
        critical_failure: "NPC 应该强烈拒绝，态度恶化，可能产生敌意或采取对抗行动。",
      },
      en: {
        critical_success: "The NPC should respond very positively, with a notably softened or even warm attitude, willing to proactively offer help or important information.",
        success: "The NPC should respond positively, with a softened attitude, willing to provide help or information.",
        partial: "The NPC's attitude should soften somewhat, but remain guarded, perhaps only revealing limited information, giving a warning, or requesting additional conditions.",
        failure: "The NPC should refuse the request, with a colder or more guarded attitude.",
        critical_failure: "The NPC should strongly refuse, with worsened attitude, possibly showing hostility or taking confrontational action.",
      },
    };

    const langDirections = directions[lang] || directions["en"];
    if (!langDirections) return "";
    return langDirections[outcome] || "";
  }

  private async getSceneContext(lang: "cn" | "en") {
    if (!this.locationContextService) {
      return null;
    }

    return await this.locationContextService.getContextForLocation(
      this.gameState.world_pack_id,
      this.gameState.current_location,
      this.gameState.discovered_items,
      lang
    );
  }

  private generateHiddenItemHints(hiddenItems: string[], lang: "cn" | "en"): string {
    if (!hiddenItems || hiddenItems.length === 0) return "";
    return lang === "cn" 
      ? "房间里似乎还有一些不易察觉的细节..."
      : "There seem to be some subtle details yet to notice...";
  }
}
