import { generateObject } from "ai";
import type { LanguageModel } from "ai";
import { z } from "zod";
import type { NPCData } from "../../schemas";

const NPCResponseSchema = z.object({
  response: z.string(),
  emotion: z.string().default("neutral"),
  action: z.string().default(""),
  relation_change: z.number().default(0),
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
    private llm: LanguageModel
  ) {}

  async process(inputData: NPCProcessInput): Promise<AgentResponse> {
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

    try {
      const { object } = await generateObject({
        model: this.llm,
        schema: NPCResponseSchema,
        system: systemPrompt,
        prompt: userPrompt,
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

    if (lang === "cn") {
      lines.push(`你是${soul.name}。以第一人称扮演这个角色。`);
      lines.push("");
      lines.push("## 角色背景");
      lines.push(soul.description.cn || soul.description.en);
      lines.push("");
      lines.push(`## 性格特征: ${soul.personality.join(", ")}`);
      const speechStyle = soul.speech_style;
      lines.push(speechStyle?.cn || speechStyle?.en || "");
      lines.push("");
      if (soul.example_dialogue && soul.example_dialogue.length > 0) {
        lines.push("示例对话:");
        for (const example of soul.example_dialogue) {
          lines.push(`玩家：${example.user}`);
          lines.push(`${soul.name}：${example.char}`);
        }
      }

      lines.push("");
      lines.push("## 当前状态");
      if (body.tags && body.tags.length > 0) {
        lines.push(`状态标签：${body.tags.join(", ")}`);
      }
      if (body.relations.player !== 0) {
        const rel = body.relations.player || 0;
        const relDesc = rel > 0 ? "友好" : rel < 0 ? "敌对" : "中立";
        lines.push(`对玩家态度：${relDesc} (${rel})`);
      }

      if (body.memory && Object.keys(body.memory).length > 0) {
        lines.push("");
        lines.push("## 近期记忆");
        const recentMemories = Object.keys(body.memory).slice(0, 3);
        for (const event of recentMemories) {
          lines.push(`- ${event}`);
        }
      }

      lines.push("");
      lines.push("## 叙事风格指示");
      if (narrativeStyle === "brief") {
        lines.push("当前处于连续对话中，请精简动作描写：");
        lines.push("- action 字段留空或只写极简动作（如「点头」「摇头」）");
        lines.push("- 重点放在对白本身，避免重复之前已描述过的神态动作");
      } else {
        lines.push("这是对话开始或间隔较久后的交互，请丰富动作描写：");
        lines.push("- action 字段写出有画面感的动作、神态、小动作");
        lines.push("- 体现角色性格特征和当前情绪状态");
      }

      if (roleplayDirection) {
        lines.push("");
        lines.push("## 扮演方向指示（重要）");
        lines.push(roleplayDirection);
      }

      lines.push("");
      lines.push("## 响应格式");
      lines.push("以 JSON 格式回复：");
      lines.push("{");
      lines.push('  "response": "你的对话内容",');
      lines.push('  "emotion": "情绪状态（如 happy, sad, angry, scared, neutral）",');
      lines.push('  "action": "伴随动作描述（根据叙事风格指示填写）",');
      lines.push('  "relation_change": 0  // 关系变化 -10 到 +10，通常为 0');
      lines.push("}");
    } else {
      lines.push(`You are ${soul.name}. Roleplay this character in first person.`);
      lines.push("");
      lines.push("## Character Background");
      lines.push(soul.description.en || soul.description.cn);
      lines.push("");
      lines.push(`## Personality: ${soul.personality.join(", ")}`);
      lines.push("");
      lines.push("## Speech Style");
      const speechStyle = soul.speech_style;
      lines.push(speechStyle?.en || speechStyle?.cn || "");
      lines.push("");
      if (soul.example_dialogue && soul.example_dialogue.length > 0) {
        lines.push("Example Dialogue:");
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
        lines.push("- Leave action field empty or very brief (e.g., 'nods', 'shakes head')");
        lines.push("- Focus on dialogue, avoid repeating previously described actions");
      } else {
        lines.push("Beginning of conversation or after long break. Rich action description:");
        lines.push("- action field should have vivid gestures, expressions, small actions");
        lines.push("- Reflect character personality and current emotional state");
      }

      if (roleplayDirection) {
        lines.push("");
        lines.push("## Roleplay Direction (Important)");
        lines.push(roleplayDirection);
      }

      lines.push("");
      lines.push("## Response Format");
      lines.push("Reply in JSON format:");
      lines.push("{");
      lines.push('  "response": "Your dialogue",');
      lines.push('  "emotion": "Emotional state (e.g., happy, sad, angry, scared, neutral)",');
      lines.push('  "action": "Accompanying action (follow narrative style)",');
      lines.push('  "relation_change": 0  // Relationship change -10 to +10, usually 0');
      lines.push("}");
    }

    return lines.join("\n");
  }

  private buildUserPrompt(
    npc: NPCData,
    playerInput: string,
    context: Record<string, unknown>,
    lang: "cn" | "en"
  ): string {
    const lines: string[] = [];

    if (lang === "cn") {
      lines.push("## 当前场景");
      if (context.location) {
        lines.push(`地点：${context.location}`);
      }
      if (context.time) {
        lines.push(`时间：${context.time}`);
      }
      if (context.atmosphere) {
        lines.push(`氛围：${context.atmosphere}`);
      }

      lines.push("");
      lines.push("## 玩家的话");
      lines.push(playerInput);

      lines.push("");
      lines.push(
        `现在，以${npc.soul.name}的身份回应。记住你的性格、说话风格和当前状态。`
      );
    } else {
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
    }

    return lines.join("\n");
  }
}
