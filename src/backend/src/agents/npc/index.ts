import { generateObject } from "ai";
import type { LanguageModel } from "ai";
import { z } from "zod";
import type { NPCData } from "../../schemas";
import type { LanceDBService } from "../../lib/lance";

const NPCResponseSchema = z.object({
  response: z.string().describe("Your dialogue response to the player"),
  emotion: z.string().default("neutral").describe("Your current emotional state"),
  action: z.string().default("").describe("Your physical action or body language, can be empty"),
  relation_change: z
    .number()
    .int()
    .min(-10)
    .max(10)
    .default(0)
    .describe("How this interaction changes your attitude toward the player. Integer from -10 to 10. Use ±1~3 for minor interactions, ±5~10 only for significant events."),
  new_memory: z.string().optional().describe("Important event worth remembering, if any"),
});

interface AgentResponse {
  content: string;
  success: boolean;
  error?: string;
  metadata?: Record<string, unknown>;
}

interface NPCProcessInput {
  npc_data: Record<string, unknown>;
  player_input: string;
  session_id?: string;  // For memory isolation
  context?: Record<string, unknown>;
  lang?: "cn" | "en";
  narrative_style?: "brief" | "detailed";
  roleplay_direction?: string;
  gm_instruction?: string;
}

export class NPCAgent {
  constructor(
    private llm: LanguageModel,
    private vectorStore?: LanceDBService,
    private maxTokens?: number
  ) {}

  async process(input: Record<string, unknown>): Promise<AgentResponse> {
    const inputData = input as unknown as NPCProcessInput;
    const npcDataDict = inputData.npc_data;
    const playerInput = inputData.player_input;
    const sessionId = inputData.session_id;
    const context = inputData.context || {};
    const lang = inputData.lang || "cn";
    const narrativeStyle = inputData.narrative_style || "detailed";
    const roleplayDirection = inputData.roleplay_direction;
    const gmInstruction = inputData.gm_instruction;

    if (!npcDataDict) {
      return {
        content: "",
        success: false,
        error: "NPCAgent: npc_data is required",
        metadata: { agent: "npc_agent" },
      };
    }

    if (!playerInput) {
      return {
        content: "",
        success: false,
        error: "NPCAgent: player_input is required",
        metadata: { agent: "npc_agent" },
      };
    }

    let npc: NPCData;
    try {
      npc = npcDataDict as NPCData;
    } catch (error) {
      return {
        content: "",
        success: false,
        error: `NPCAgent: Invalid npc_data - ${error}`,
        metadata: { agent: "npc_agent" },
      };
    }

    const relationshipLevel = npc.body.relations.player || 0;

    // Retrieve relevant memories using vector search (Phase 2.2)
    const relevantMemories = await this.retrieveRelevantMemories(
      sessionId,
      npc.id,
      playerInput,
      npc.body.memory || {}
    );

    const systemPrompt = this.buildSystemPrompt(
      npc,
      playerInput,
      context,
      lang,
      narrativeStyle,
      roleplayDirection,
      gmInstruction,
      relevantMemories  // Pass retrieved memories
    );

    const userPrompt = this.buildUserPrompt(npc, playerInput, context, lang);

    const maxOutputTokens = this.maxTokens ?? undefined;

    try {
      const { object } = await generateObject({
        model: this.llm,
        schema: NPCResponseSchema,
        system: systemPrompt,
        prompt: userPrompt,
        maxOutputTokens,
      });

      const responseMetadata: Record<string, unknown> = {
        agent: "npc_agent",
        npc_id: npc.id,
        npc_name: npc.soul.name,
        emotion: object.emotion,
        action: object.action,
        relationship_level: relationshipLevel,
      };

      if (object.relation_change !== 0) {
        responseMetadata.relation_change = object.relation_change;
      }

      // Persist new memory if generated (Phase 2.3)
      if (object.new_memory && sessionId) {
        // Extract keywords from the memory event
        const keywords = this.extractMemoryKeywords(object.new_memory);
        await this.persistMemory(sessionId, npc.id, object.new_memory, keywords);
        responseMetadata.new_memory = object.new_memory;
      }

      return {
        content: object.response,
        metadata: responseMetadata,
        success: true,
      };
    } catch (error) {
      return {
        content: "",
        success: false,
        error: `NPCAgent: LLM call failed - ${error}`,
        metadata: { agent: "npc_agent", npc_id: npc.id },
      };
    }
  }

  // ============================================================
  // NPC Memory System (Phase 2)
  // ============================================================

  /**
   * Retrieve relevant memories using vector similarity search.
   * Falls back gracefully when vector store is unavailable.
   *
   * Collection naming: npc_memories_{session_id}_{npc_id}
   *
   * @param sessionId - Session identifier for memory isolation
   * @param npcId - NPC identifier
   * @param playerInput - Current player input (for semantic search)
   * @param allMemories - All NPC memories from state {event: keywords[]}
   * @param nResults - Number of memories to retrieve (default: 3)
   * @returns List of relevant memory event descriptions
   */
  private async retrieveRelevantMemories(
    sessionId: string | undefined,
    npcId: string,
    playerInput: string,
    allMemories: Record<string, string[]>,
    nResults: number = 3
  ): Promise<string[]> {
    // If no vector store, session, or memories, return empty
    if (!this.vectorStore || !sessionId || Object.keys(allMemories).length === 0) {
      return [];
    }

    const collectionName = `npc_memories_${sessionId}_${npcId}`;

    try {
      // Check if collection exists
      const tableExists = await this.vectorStore.tableExists(collectionName);
      if (!tableExists) {
        return [];
      }

      const results = await this.vectorStore.search(collectionName, playerInput, nResults);
      return results.map((r) => r.text);
    } catch (error) {
      // Graceful degradation - return empty list if search fails
      console.error(`[NPCAgent] Memory retrieval failed for ${npcId}:`, error);
      return [];
    }
  }

  /**
   * Persist a new memory event to the vector store.
   * Memories are session-isolated to prevent cross-session leakage.
   *
   * @param sessionId - Session identifier
   * @param npcId - NPC identifier
   * @param memoryEvent - The memory event description
   * @param keywords - Keywords associated with the memory
   */
  async persistMemory(
    sessionId: string,
    npcId: string,
    memoryEvent: string,
    keywords: string[]
  ): Promise<void> {
    if (!this.vectorStore) {
      return;
    }

    const collectionName = `npc_memories_${sessionId}_${npcId}`;
    const memoryId = `${Date.now()}_${Math.random().toString(36).slice(2)}`;

    try {
      await this.vectorStore.addDocuments(
        collectionName,
        [memoryEvent],
        [memoryId],
        [
          {
            keywords: keywords.join(','),
            timestamp: Date.now(),
            session_id: sessionId,
            npc_id: npcId,
          },
        ]
      );
      console.log(`[NPCAgent] Memory persisted for ${npcId}: ${memoryEvent.slice(0, 50)}...`);
    } catch (error) {
      console.error(`[NPCAgent] Failed to persist memory for ${npcId}:`, error);
    }
  }

  /**
   * Extract keywords from a memory event description.
   * Uses simple word segmentation and filtering.
   *
   * @param memoryEvent - The memory event description
   * @returns List of extracted keywords
   */
  private extractMemoryKeywords(memoryEvent: string): string[] {
    const stopWords = new Set([
      "的", "了", "是", "在", "我", "你", "他", "她", "它", "有", "没有",
      "什么", "怎么", "如何", "这", "那", "就", "也", "都", "很", "非常",
      "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
      "have", "has", "had", "do", "does", "did", "will", "would", "should",
    ]);

    const segmenter = new Intl.Segmenter(["zh-CN", "en"], { granularity: "word" });
    const segments = segmenter.segment(memoryEvent);

    const keywords: string[] = [];
    const seen = new Set<string>();

    for (const { segment } of segments) {
      const cleanWord = segment.trim().replace(/[，。！？：；''()（）\[\]【】""]/g, "");

      if (
        cleanWord &&
        !stopWords.has(cleanWord) &&
        cleanWord.length > 1 &&
        !seen.has(cleanWord)
      ) {
        seen.add(cleanWord);
        keywords.push(cleanWord);
        if (keywords.length >= 5) {
          break;
        }
      }
    }

    return keywords;
  }

  private buildSystemPrompt(
    npc: NPCData,
    _playerInput: string,
    _context: Record<string, unknown>,
    lang: "cn" | "en",
    narrativeStyle: "brief" | "detailed",
    roleplayDirection?: string,
    gmInstruction?: string,
    relevantMemories?: string[]  // Retrieved memories from vector search
  ): string {
    const soul = npc.soul;
    const body = npc.body;

    const lines: string[] = [];

    // Core Instruction (English for Logic)
    lines.push(`You are ${soul.name}. Roleplay this character in first person.`);
    lines.push(`Target Output Language: ${lang === 'cn' ? 'Chinese (Simplified)' : 'English'}`);
    
    lines.push("");
    lines.push("## Character Background");
    // Use localized description if available, fall back to what's present
    const desc = soul.description[lang] || soul.description.en || soul.description.cn;
    lines.push(desc);
    
    lines.push("");
    lines.push(`## Personality: ${soul.personality.join(", ")}`);
    
    lines.push("");
    lines.push("## Speech Style");
    const speechStyle = soul.speech_style ? (soul.speech_style[lang] || soul.speech_style.en || soul.speech_style.cn) : "";
    if (speechStyle) lines.push(speechStyle);

    lines.push("");
    if (soul.example_dialogue && soul.example_dialogue.length > 0) {
      lines.push("## Example Dialogue");
      for (const example of soul.example_dialogue) {
        lines.push(`Player: ${example.user}`);
        lines.push(`${soul.name}: ${example.char}`);
      }
    }

    lines.push("");
    lines.push("## Current State");
    if (body.tags && body.tags.length > 0) {
      lines.push(`Status tags: ${body.tags.join(", ")}`);
    }
    if (body.relations.player !== 0) {
      const rel = body.relations.player || 0;
      const relDesc = rel > 0 ? "friendly" : rel < 0 ? "hostile" : "neutral";
      lines.push(`Attitude toward player: ${relDesc} (${rel})`);
    }

    // Use retrieved memories if available, otherwise fall back to all memories
    if (relevantMemories && relevantMemories.length > 0) {
      lines.push("");
      lines.push("## Relevant Memories (Retrieved)");
      for (const memory of relevantMemories) {
        lines.push(`- ${memory}`);
      }
    } else if (body.memory && Object.keys(body.memory).length > 0) {
      lines.push("");
      lines.push("## Recent Memories");
      const recentMemories = Object.keys(body.memory).slice(0, 3);
      for (const event of recentMemories) {
        lines.push(`- ${event}`);
      }
    }

    lines.push("");
    lines.push("## Narrative Style");
    if (narrativeStyle === "brief") {
      lines.push("In continuous dialogue. Keep action minimal:");
      lines.push("- Leave 'action' field empty or very brief (e.g., 'nods', 'shakes head')");
      lines.push("- Focus on dialogue, avoid repeating previously described actions");
    } else {
      lines.push("Beginning of conversation or after long break. Rich action description:");
      lines.push("- 'action' field should have vivid gestures, expressions, small actions");
      lines.push("- Reflect character personality and current emotional state");
    }

    if (roleplayDirection) {
      lines.push("");
      lines.push("## Roleplay Direction (Important)");
      lines.push(roleplayDirection);
    }

    if (gmInstruction) {
      lines.push("");
      lines.push("## GM Instruction (Critical)");
      lines.push(gmInstruction);
    }

    return lines.join("\n");
  }

  private buildUserPrompt(
    npc: NPCData,
    playerInput: string,
    context: Record<string, unknown>,
    _lang: "cn" | "en"
  ): string {
    const lines: string[] = [];

    lines.push("## Current Scene");
    if (context.location) {
      lines.push(`Location: ${context.location}`);
    }
    if (context.time) {
      lines.push(`Time: ${context.time}`);
    }
    if (context.atmosphere) {
      lines.push(`Atmosphere: ${context.atmosphere}`);
    }

    lines.push("");
    lines.push("## Player's Words");
    lines.push(playerInput);

    lines.push("");
    lines.push(
      `Now, respond as ${npc.soul.name}. Remember your personality, speech style, and current state.`
    );

    return lines.join("\n");
  }
}
