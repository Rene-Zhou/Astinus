import { generateObject } from "ai";
import type { LanguageModel } from "ai";
import { z } from "zod";
import type { NPCData } from "../../schemas";

const NPCResponseSchema = z.object({
  response: z.string(),
  emotion: z.string().default("neutral"),
  action: z.string().default(""),
  relation_change: z.number().int().min(-10).max(10).default(0),
  new_memory: z.string().optional(),
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
  context?: Record<string, unknown>;
  lang?: "cn" | "en";
  narrative_style?: "brief" | "detailed";
  roleplay_direction?: string;
}

export class NPCAgent {
  constructor(
    private llm: LanguageModel,
    private maxTokens?: number
  ) {}

  async process(input: Record<string, unknown>): Promise<AgentResponse> {
    const inputData = input as unknown as NPCProcessInput;
    const npcDataDict = inputData.npc_data;
    const playerInput = inputData.player_input;
    const context = inputData.context || {};
    const lang = inputData.lang || "cn";
    const narrativeStyle = inputData.narrative_style || "detailed";
    const roleplayDirection = inputData.roleplay_direction;

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

    const systemPrompt = this.buildSystemPrompt(
      npc,
      playerInput,
      context,
      lang,
      narrativeStyle,
      roleplayDirection
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

      if (object.new_memory) {
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

  private buildSystemPrompt(
    npc: NPCData,
    _playerInput: string,
    _context: Record<string, unknown>,
    lang: "cn" | "en",
    narrativeStyle: "brief" | "detailed",
    roleplayDirection?: string
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

    if (body.memory && Object.keys(body.memory).length > 0) {
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
