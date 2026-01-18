import { generateObject, generateText } from "ai";
import type { LanguageModel } from "ai";
import type { GameState } from "../../schemas";
import { z } from "zod";
import { LocationContextService } from "../../services/location-context";
import { WorldPackLoader } from "../../services/world";
import { getLocalizedString } from "../../schemas";
import type { NPCData } from "../../schemas";

const GMActionTypeSchema = z.enum([
  "RESPOND",
  "CALL_AGENT",
  "SEARCH_LORE",
  "REQUEST_CHECK",
]);

const GMAgentContextSchema = z.object({
  target_location: z.string().optional().describe("Target location ID for scene transition"),
  npc_id: z.string().optional().describe("ID of the NPC to interact with"),
  topic: z.string().optional().describe("Topic for lore search or conversation"),
  details: z.string().optional().describe("Additional details for the action"),
});

const GMCheckRequestSchema = z.object({
  intention: z.string().describe("What the player is attempting to do"),
  difficulty: z.number().optional().describe("Target number (default 7)"),
  stat: z.string().optional().describe("Relevant stat/trait"),
  reason: z.string().optional().describe("Reasoning for the difficulty"),
  modifiers: z.array(z.string()).optional().describe("Applicable modifiers"),
});

const GMActionSchema = z.object({
  action_type: GMActionTypeSchema,
  content: z.string().default(""),
  agent_name: z.string().optional(),
  agent_context: GMAgentContextSchema.default({}),
  check_request: GMCheckRequestSchema.optional(),
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
    const iteration = pendingState.iteration as number;
    const agentResults = pendingState.agent_results as Array<
      Record<string, unknown>
    >;

          this.gameState.react_pending_state = null;

    return this.runReActLoop({
      playerInput,
      lang,
      iteration,
      agentResults,
      diceResult,
    });
  }

  private async runReActLoop(params: ReActLoopParams): Promise<AgentResponse> {
    console.log(`[GMAgent] ReAct Loop Iteration ${params.iteration}`);
    const { playerInput, lang, iteration, agentResults, diceResult } = params;

    const maxIterations = 5;
    const agentsCalled: string[] = [];

    // Force output if max iterations reached
    if (iteration >= maxIterations) {
        // Fallback: Generate response with what we have
        const context = await this.buildContext(
            playerInput,
            lang,
            iteration,
            agentResults,
            diceResult
        );
        const action: GMAction = {
            action_type: "RESPOND",
            content: "Max iterations reached. Generating best effort response.",
            reasoning: "Forced response due to loop limit.",
            agent_context: {}
        };
        return this.generateResponse(context, action, lang);
    }

    const context = await this.buildContext(
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
            worldPackId: this.gameState.world_pack_id,
            currentLocation: this.gameState.current_location,
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
        // If no lore service, skip to next iteration (or default to respond if no other actions)
        return this.runReActLoop({
            playerInput,
            lang,
            iteration: iteration + 1,
            agentResults,
            diceResult,
        });

      case "REQUEST_CHECK":
        this.gameState.react_pending_state = {
          player_input: playerInput,
          iteration: iteration + 1,
          agent_results: agentResults,
        };
        
        this.gameState.current_phase = "dice_check";

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
        if (action.agent_name) {
          let agentName = action.agent_name;
          let subAgent = this.subAgents[agentName];

          // Handle NPC routing (npc_ID -> npc)
          if (agentName.startsWith("npc_")) {
            subAgent = this.subAgents["npc"];
          }

          if (subAgent) {
            if (this.statusCallback) {
              await this.statusCallback(agentName, null);
            }

            agentsCalled.push(agentName);

            const agentContext = await this.prepareAgentContext(
              agentName,
              playerInput,
              lang,
              action.agent_context,
              diceResult
            );

            const subAgentResponse = await subAgent.process(agentContext);

            agentResults.push({
              agent: agentName,
              result: subAgentResponse.content,
              success: subAgentResponse.success,
              reasoning: action.reasoning,
              metadata: subAgentResponse.metadata
            });

            return this.runReActLoop({
              playerInput,
              lang,
              iteration: iteration + 1,
              agentResults,
              diceResult, // Pass dice result to next iteration so GM can see it
            });
          }
        }
        // Agent not found or invalid
        return this.runReActLoop({
            playerInput,
            lang,
            iteration: iteration + 1,
            agentResults,
            diceResult,
        });
    }

    // Default fallback
    return {
      content: "",
      success: false,
      error: "Unknown action or missing service",
      metadata: { agent: "gm_agent" },
    };
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

  private getDiceOutcomeExplanation(
    diceResult: Record<string, any>,
    lang: "cn" | "en"
  ): string {
    const outcome = diceResult.outcome as string;
    if (!outcome) return "";

    const explanations: Record<string, Record<string, string>> = {
      cn: {
        critical_success: "【大成功】玩家的行动完美达成，甚至超出预期。应该给予额外的正面效果或意外收获。",
        success: "【成功】玩家的行动顺利达成目标，没有负面后果或代价。",
        partial: "【部分成功】玩家达成了目标，但伴随代价、复杂情况或不完美的结果。",
        failure: "【失败】玩家的行动未能达成目标，应该引入负面后果或新的困境。",
        critical_failure: "【大失败】玩家的行动彻底失败，并且引发了严重的负面后果或危机。"
      },
      en: {
        critical_success: "[Critical Success] The action succeeds perfectly, exceeding expectations. Grant extra positive effects or unexpected benefits.",
        success: "[Success] The action succeeds smoothly with no negative consequences.",
        partial: "[Partial Success] The goal is achieved but with a cost, complication, or imperfect result.",
        failure: "[Failure] The action fails to achieve the goal. Introduce negative consequences or new dilemmas.",
        critical_failure: "[Critical Failure] The action fails catastrophically, triggering serious negative consequences or crisis."
      }
    };

    const langExplanations = explanations[lang] || explanations["en"];
    if (!langExplanations) return "";
    return langExplanations[outcome] || "";
  }

  private async decideAction(
    context: string,
    lang: "cn" | "en"
  ): Promise<GMAction> {
    console.log("[GMAgent] Deciding action...");
    const systemPrompt = this.buildDecisionPrompt(lang);

    try {
      const { object } = await generateObject({
        model: this.llm,
        schema: GMActionSchema,
        system: systemPrompt,
        prompt: context,
      });
      console.log("[GMAgent] Decision:", object);

      // Default agent_context if undefined
      if (!object.agent_context) {
          object.agent_context = {};
      }

      return object;
    } catch (error) {
      console.error("[GMAgent] decideAction failed:", error);
      throw error;
    }
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

    this.gameState.turn_count += 1;
    this.gameState.updated_at = new Date().toISOString();
    
    this.gameState.messages.push({
      role: "assistant",
      content: text,
      timestamp: new Date().toISOString(),
      turn: this.gameState.turn_count,
      metadata: {
          phase: "gm_response",
          reasoning: action.reasoning
      }
    });

    this.gameState.current_phase = "waiting_input";

    return {
      content: text,
      success: true,
      metadata: { agent: "gm_agent" },
    };
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

  private async buildContext(
    playerInput: string,
    lang: "cn" | "en",
    iteration: number,
    agentResults: Array<Record<string, unknown>>,
    diceResult: Record<string, unknown> | null
  ): Promise<string> {
    const sceneContext = await this.getSceneContext(lang);
    const parts: string[] = [];

    // 1. Basic Info (Always English for System Logic)
    parts.push(`Language: ${lang === 'cn' ? 'Chinese (Simplified)' : 'English'}`);
    parts.push(`Iteration: ${iteration}`);
    parts.push(`Player Input: ${playerInput}`);

    // 2. Game State & Location Context
    parts.push(`\n[Game State]`);
    parts.push(`Phase: ${this.gameState.current_phase}`);
    parts.push(`Turn: ${this.gameState.turn_count}`);
    parts.push(`Location ID: ${this.gameState.current_location}`);
    
    if (sceneContext) {
        // Provide localized names but keep structure in English
        parts.push(`Region: ${sceneContext.region.name} (${sceneContext.region.narrative_tone})`);
        parts.push(`Location: ${sceneContext.location.name}`);
        parts.push(`Description: ${sceneContext.location.description}`);
        if (sceneContext.location.atmosphere) {
            parts.push(`Atmosphere: ${sceneContext.location.atmosphere}`);
        }
        if (sceneContext.atmosphere_guidance) {
            parts.push(`Guidance: ${sceneContext.atmosphere_guidance}`);
        }
        parts.push(`Visible Items: ${sceneContext.location.visible_items.join(", ")}`);
        
        if (sceneContext.basic_lore.length > 0) {
            parts.push(`\n[Relevant Lore]`);
            sceneContext.basic_lore.forEach(lore => parts.push(`- ${lore}`));
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
            console.error("Failed to load active NPCs context", e);
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
          parts.push(`- ${name}`);
      });
    }

    if (agentResults.length > 0) {
      parts.push(`\n[Agent Results]`);
      for (const result of agentResults) {
        parts.push(`  - Agent: ${result.agent}`);
        parts.push(`    Reasoning: ${result.reasoning}`);
        // Agent results might be in mixed language depending on the agent, pass as is
        parts.push(`    Result: ${JSON.stringify(result.result)}`);
      }
    }

    if (diceResult) {
      parts.push(`\n[Dice Result]`);
      const outcomeExplanation = this.getDiceOutcomeExplanation(diceResult, lang);
      const displayResult = {
        ...diceResult,
        outcome_explanation: outcomeExplanation
      };
      parts.push(JSON.stringify(displayResult, null, 2));
    }

    const recentMessages = this.gameState.messages.slice(-10);
    if (recentMessages.length > 0) {
      parts.push(`\n[Conversation History]`);
      for (const msg of recentMessages) {
        parts.push(`  ${msg.role}: ${msg.content}`);
      }
    }

    return parts.join("\n");
  }

  private buildDecisionPrompt(lang: "cn" | "en"): string {
    // ALWAYS use English for Logic Prompts to improve reasoning quality
    return `You are the Game Master (GM) orchestrating a TTRPG session.
Your role is to analyze the player's input and decide the next logical step in the game loop.

Current Language for Output: ${lang === 'cn' ? 'Chinese (Simplified)' : 'English'}

Analyze the input and context to choose ONE action:
- RESPOND: Direct narrative response to the player. Use this for general interactions, descriptions, or when no other action applies.
- SEARCH_LORE: The player is asking about world history, background, or specific details that might be in the lore database.
- REQUEST_CHECK: The player attempts an action with a chance of failure or significant consequence (e.g., attacking, climbing, persuading).
- CALL_AGENT: The player is interacting with a specific sub-agent (e.g., talking to an NPC).

Context Analysis:
1. Is the player interacting with a specific NPC? -> CALL_AGENT (agent_name: "npc_{id}")
   - REFER to the [Active NPCs] section to find the correct ID.
2. Is the player asking about history/lore? -> SEARCH_LORE
3. Is the player attempting a risky action? -> REQUEST_CHECK
4. Otherwise -> RESPOND

Return the decision as a JSON object matching the GMAction schema.`;
  }

  private buildNarrativePrompt(lang: "cn" | "en"): string {
    // ALWAYS use English for Logic Prompts to improve reasoning quality
    // Only the FINAL OUTPUT instruction specifies the target language.
    return `You are an experienced Game Master narrator.
Your task is to synthesize the game state, agent results, and context into a coherent, immersive narrative response.

Target Language: ${lang === 'cn' ? 'Chinese (Simplified)' : 'English'}

【Information Control Rules - STRICTLY ENFORCE】:
1. NEVER expose internal IDs (e.g., "npc_old_man", "loc_tavern"). Use in-world names.
2. Do NOT use an NPC's true name unless the player has already learned it. Use descriptions (e.g., "the hooded figure").
3. Do NOT reveal secret background info unless explicitly discovered.
4. Do NOT mention game mechanics or agents (e.g., "The Rule Agent says..."). Describe the outcome naturally.

【Narrative Integration Rules】:
1. Player Actions: Do NOT repeat or embellish what the player just said they did. Acknowledge the consequence, not the action itself.
2. NPC Dialogue: Output dialogue EXACTLY as provided by the NPC agent. Do not rewrite.
3. NPC Actions: Integrate provided NPC actions naturally.
4. Immersion: Use second-person perspective ("You see...", "You hear...").

Generate the final narrative response in ${lang === 'cn' ? 'Chinese (Simplified)' : 'English'}.`;
  }

  private getCurrentRegion(): string | undefined {
    return undefined;
  }
}
