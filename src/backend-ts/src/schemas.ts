/**
 * Zod schemas for Astinus TTRPG Engine
 *
 * Port of Pydantic models from src/backend/models/
 * These schemas provide runtime validation and TypeScript type inference.
 */

import { z } from 'zod';

// ============================================================================
// I18n (LocalizedString)
// ============================================================================

/**
 * Multi-language string with fallback support.
 * Stores text in Chinese (cn) and English (en).
 */
export const LocalizedStringSchema = z.object({
  cn: z.string().describe('Chinese (simplified) text'),
  en: z.string().describe('English text'),
});

export type LocalizedString = z.infer<typeof LocalizedStringSchema>;

/**
 * Get localized string with fallback.
 */
export function getLocalizedString(
  str: LocalizedString,
  lang: 'cn' | 'en' = 'cn'
): string {
  if (lang === 'en' && str.en) {
    return str.en;
  }
  return str.cn;
}

// ============================================================================
// Trait
// ============================================================================

/**
 * Character trait with dual aspects (positive and negative).
 */
export const TraitSchema = z.object({
  name: LocalizedStringSchema.describe('Trait name'),
  description: LocalizedStringSchema.describe('Detailed trait description'),
  positive_aspect: LocalizedStringSchema.describe('Positive use of trait'),
  negative_aspect: LocalizedStringSchema.describe('Negative aspect of trait'),
});

export type Trait = z.infer<typeof TraitSchema>;

// ============================================================================
// Character
// ============================================================================

/**
 * Player character - pure trait-based design.
 *
 * A character is defined by:
 * - A core concept (one-sentence description)
 * - 1-4 traits (defining characteristics with dual aspects)
 * - Tags (status effects like "右腿受伤", "疲惫")
 * - Fate points (narrative currency, 3 starting, max 5)
 */
export const PlayerCharacterSchema = z.object({
  name: z.string().describe('Character name (proper noun, not localized)'),
  concept: LocalizedStringSchema.describe('One-sentence character concept'),
  traits: z
    .array(TraitSchema)
    .min(1)
    .max(4)
    .describe('Character traits (1-4 traits)'),
  fate_points: z
    .number()
    .int()
    .min(0)
    .max(5)
    .default(3)
    .describe('Narrative influence points (0-5)'),
  tags: z.array(z.string()).default([]).describe('Status effects and conditions'),
});

export type PlayerCharacter = z.infer<typeof PlayerCharacterSchema>;

/**
 * Helper functions for PlayerCharacter
 */
export const PlayerCharacterHelpers = {
  addTag(character: PlayerCharacter, tag: string): PlayerCharacter {
    if (!character.tags.includes(tag)) {
      return { ...character, tags: [...character.tags, tag] };
    }
    return character;
  },

  removeTag(character: PlayerCharacter, tag: string): PlayerCharacter {
    return {
      ...character,
      tags: character.tags.filter((t) => t !== tag),
    };
  },

  hasTag(character: PlayerCharacter, tag: string): boolean {
    return character.tags.includes(tag);
  },

  spendFatePoint(character: PlayerCharacter): PlayerCharacter | null {
    if (character.fate_points > 0) {
      return { ...character, fate_points: character.fate_points - 1 };
    }
    return null;
  },

  gainFatePoint(character: PlayerCharacter): PlayerCharacter | null {
    if (character.fate_points < 5) {
      return { ...character, fate_points: character.fate_points + 1 };
    }
    return null;
  },

  getConcept(character: PlayerCharacter, lang: 'cn' | 'en' = 'cn'): string {
    return getLocalizedString(character.concept, lang);
  },
};

// ============================================================================
// Dice Check
// ============================================================================

/**
 * Request for player to roll dice - sent from Rule Agent to frontend.
 */
export const DiceCheckRequestSchema = z.object({
  intention: z.string().describe('What the player is trying to do (in Chinese)'),
  influencing_factors: z
    .object({
      traits: z.array(z.string()).default([]),
      tags: z.array(z.string()).default([]),
    })
    .describe("Factors affecting the roll: {traits: [...], tags: [...]}"),
  dice_formula: z
    .string()
    .describe("Dice notation (e.g., '2d6', '3d6kh2', '3d6kl2')"),
  instructions: LocalizedStringSchema.describe('Explanation of why these modifiers apply'),
});

export type DiceCheckRequest = z.infer<typeof DiceCheckRequestSchema>;

/**
 * Result of a dice check after rolling.
 */
export const DiceCheckResultSchema = z.object({
  intention: z.string().describe('What the player was trying to do'),
  dice_formula: z.string().describe("Dice notation used (e.g., '2d6', '3d6kh2')"),
  dice_values: z.array(z.number().int()).describe('Individual dice roll values'),
  total: z.number().int().describe('Final total after applying modifiers'),
  threshold: z.number().int().default(7).describe('Target number needed for success'),
  success: z.boolean().describe('Whether the check succeeded'),
  critical: z.boolean().default(false).describe('Whether this was a critical success/failure'),
  modifiers: z
    .array(
      z.object({
        source: z.string(),
        effect: z.string(),
      })
    )
    .default([])
    .describe("Modifiers applied: [{source: 'trait_name', effect: 'advantage'}]"),
});

export type DiceCheckResult = z.infer<typeof DiceCheckResultSchema>;

/**
 * Player's response to a dice check request.
 */
export const DiceCheckResponseSchema = z.object({
  action: z.enum(['roll', 'argue', 'cancel']).describe("Action taken: 'roll', 'argue', or 'cancel'"),
  dice_result: z
    .record(z.any())
    .optional()
    .describe("DiceResult as dict (if action='roll')"),
  argument: z
    .string()
    .optional()
    .describe("Player's argument for advantage (if action='argue')"),
  trait_claimed: z
    .string()
    .optional()
    .describe('Which trait player claims helps (if action=\'argue\')'),
  fate_point_spent: z
    .boolean()
    .default(false)
    .describe('Whether a fate point was spent to reroll this result'),
});

export type DiceCheckResponse = z.infer<typeof DiceCheckResponseSchema>;

// ============================================================================
// Game State
// ============================================================================

/**
 * Current phase of the game loop.
 */
export const GamePhaseSchema = z.enum([
  'waiting_input',
  'processing',
  'dice_check',
  'npc_response',
  'narrating',
]);

export type GamePhase = z.infer<typeof GamePhaseSchema>;

/**
 * Message in conversation history.
 */
export const MessageSchema = z.object({
  role: z.enum(['user', 'assistant']),
  content: z.string(),
  timestamp: z.string(), // ISO 8601 datetime
  turn: z.number().int().min(0),
  metadata: z.record(z.any()).optional(),
});

export type Message = z.infer<typeof MessageSchema>;

/**
 * Global game state - GM Agent's world view.
 *
 * This is the single source of truth for the game. The GM Agent owns this
 * and updates it. Sub-agents (Rule, NPC, Lore) receive sliced context from
 * this state but never see or modify it directly.
 */
export const GameStateSchema = z.object({
  // Session metadata
  session_id: z.string().describe('Unique session identifier'),
  player_name: z.string().default('玩家').describe('Player (user) name - distinct from character name'),
  created_at: z.string().describe('Session creation time (ISO 8601)'), // datetime
  updated_at: z.string().describe('Last update time (ISO 8601)'), // datetime

  // Core state
  player: PlayerCharacterSchema.describe('Player character'),
  current_phase: GamePhaseSchema.default('waiting_input').describe('Current game phase'),
  next_agent: z.string().nullable().default(null).describe('Which agent should act next (routing target)'),

  // World state
  world_pack_id: z.string().describe('ID of loaded world/story pack'),
  current_location: z.string().describe('Current location ID in world pack'),
  active_npc_ids: z.array(z.string()).default([]).describe('NPCs present in current scene'),
  discovered_items: z.array(z.string()).default([]).describe('Items player has discovered/interacted with'),
  flags: z.array(z.string()).default([]).describe("Story flags (e.g., 'found_key', 'knows_secret')"),

  // Temporal tracking
  game_time: z.string().default('00:00').describe("In-game time (e.g., '23:47')"),
  turn_count: z.number().int().min(0).default(0).describe('Number of turns elapsed'),

  // Communication
  messages: z.array(MessageSchema).default([]).describe("Full conversation history - GM's complete context"),
  temp_context: z.record(z.any()).default({}).describe('Temporary context for passing data to/from sub-agents'),
  last_check_result: z.record(z.any()).nullable().default(null).describe('Most recent dice check outcome'),
  react_pending_state: z.record(z.any()).nullable().default(null).describe('Pending ReAct loop state when waiting for dice roll'),

  // Settings
  language: z.string().default('cn').describe('Current language (cn/en)'),
});

export type GameState = z.infer<typeof GameStateSchema>;

/**
 * Helper functions for GameState
 */
export const GameStateHelpers = {
  addMessage(
    state: GameState,
    role: 'user' | 'assistant',
    content: string,
    metadata?: Record<string, unknown>
  ): GameState {
    const message: Message = {
      role,
      content,
      timestamp: new Date().toISOString(),
      turn: state.turn_count,
      metadata,
    };

    return {
      ...state,
      messages: [...state.messages, message],
      updated_at: new Date().toISOString(),
    };
  },

  getRecentMessages(state: GameState, count: number = 5): Message[] {
    return state.messages.slice(-count);
  },

  updateLocation(state: GameState, locationId: string, npcIds?: string[]): GameState {
    return {
      ...state,
      current_location: locationId,
      active_npc_ids: npcIds !== undefined ? npcIds : state.active_npc_ids,
      updated_at: new Date().toISOString(),
    };
  },

  addFlag(state: GameState, flag: string): GameState {
    if (!state.flags.includes(flag)) {
      return {
        ...state,
        flags: [...state.flags, flag],
        updated_at: new Date().toISOString(),
      };
    }
    return state;
  },

  hasFlag(state: GameState, flag: string): boolean {
    return state.flags.includes(flag);
  },

  addDiscoveredItem(state: GameState, itemId: string): GameState {
    if (!state.discovered_items.includes(itemId)) {
      return {
        ...state,
        discovered_items: [...state.discovered_items, itemId],
        updated_at: new Date().toISOString(),
      };
    }
    return state;
  },

  hasDiscoveredItem(state: GameState, itemId: string): boolean {
    return state.discovered_items.includes(itemId);
  },

  incrementTurn(state: GameState): GameState {
    return {
      ...state,
      turn_count: state.turn_count + 1,
      updated_at: new Date().toISOString(),
    };
  },

  setPhase(state: GameState, phase: GamePhase, nextAgent?: string | null): GameState {
    return {
      ...state,
      current_phase: phase,
      next_agent: nextAgent !== undefined ? nextAgent : state.next_agent,
      updated_at: new Date().toISOString(),
    };
  },

  saveReactState(
    state: GameState,
    iteration: number,
    llmMessages: unknown[],
    playerInput: string,
    agentResults: unknown[]
  ): GameState {
    return {
      ...state,
      react_pending_state: {
        iteration,
        llmMessages,
        playerInput,
        agentResults,
      },
      updated_at: new Date().toISOString(),
    };
  },

  clearReactState(state: GameState): GameState {
    return {
      ...state,
      react_pending_state: null,
      updated_at: new Date().toISOString(),
    };
  },

  hasPendingReactState(state: GameState): boolean {
    return state.react_pending_state !== null;
  },
};

// ============================================================================
// Dice Service Types
// ============================================================================

/**
 * Possible outcomes from a dice roll.
 */
export const OutcomeSchema = z.enum(['critical', 'success', 'partial', 'failure']);

export type Outcome = z.infer<typeof OutcomeSchema>;

/**
 * Result of a dice roll from DicePool.
 */
export const DiceResultSchema = z.object({
  all_rolls: z.array(z.number().int()).describe('All dice that were rolled'),
  kept_rolls: z.array(z.number().int()).describe('The two dice kept (highest or lowest)'),
  dropped_rolls: z.array(z.number().int()).describe('Dice rolled but not kept'),
  modifier: z.number().int().default(0).describe('Modifier applied after dice selection'),
  total: z.number().int().describe('Final total (kept dice + modifier)'),
  outcome: OutcomeSchema.describe('Outcome category based on total'),
  is_bonus: z.boolean().default(false).describe('True if bonus dice were used'),
  is_penalty: z.boolean().default(false).describe('True if penalty dice were used'),
});

export type DiceResult = z.infer<typeof DiceResultSchema>;

export const WorldPackSettingSchema = z.object({
  era: LocalizedStringSchema,
  genre: LocalizedStringSchema,
  tone: LocalizedStringSchema,
});

export type WorldPackSetting = z.infer<typeof WorldPackSettingSchema>;

export const WorldPackInfoSchema = z.object({
  name: LocalizedStringSchema,
  description: LocalizedStringSchema,
  version: z.string().default('1.0.0'),
  author: z.string().default('Unknown'),
  setting: WorldPackSettingSchema.optional(),
  player_hook: LocalizedStringSchema.optional(),
});

export type WorldPackInfo = z.infer<typeof WorldPackInfoSchema>;

export const RegionDataSchema = z.object({
  id: z.string(),
  name: LocalizedStringSchema,
  description: LocalizedStringSchema,
  narrative_tone: LocalizedStringSchema.optional(),
  atmosphere_keywords: z.array(z.string()).default([]),
  location_ids: z.array(z.string()).default([]),
  tags: z.array(z.string()).default([]),
});

export type RegionData = z.infer<typeof RegionDataSchema>;

export const LoreEntrySchema = z.object({
  uid: z.number().int(),
  key: z.array(z.string()),
  secondary_keys: z.array(z.string()).default([]),
  content: LocalizedStringSchema,
  comment: LocalizedStringSchema.nullable(),
  constant: z.boolean().default(false),
  selective: z.boolean().default(true),
  order: z.number().int().default(100),
  visibility: z.string().default('basic'),
  applicable_regions: z.array(z.string()).default([]),
  applicable_locations: z.array(z.string()).default([]),
});

export type LoreEntry = z.infer<typeof LoreEntrySchema>;

export const NPCSoulSchema = z.object({
  name: z.string(),
  description: LocalizedStringSchema,
  appearance: LocalizedStringSchema.optional(),
  personality: z.array(z.string()).min(1).max(5),
  speech_style: LocalizedStringSchema.optional(),
  example_dialogue: z
    .array(
      z.object({
        user: z.string(),
        char: z.string(),
      })
    )
    .default([]),
});

export type NPCSoul = z.infer<typeof NPCSoulSchema>;

export const NPCBodySchema = z.object({
  location: z.string(),
  inventory: z.array(z.string()).default([]),
  relations: z.record(z.number().int()).default({}),
  tags: z.array(z.string()).default([]),
  memory: z.record(z.array(z.string())).default({}),
  location_knowledge: z.record(z.array(z.number().int())).default({}),
});

export type NPCBody = z.infer<typeof NPCBodySchema>;

export const NPCDataSchema = z.object({
  id: z.string(),
  soul: NPCSoulSchema,
  body: NPCBodySchema,
});

export type NPCData = z.infer<typeof NPCDataSchema>;

export const PresetCharacterSchema = z.object({
  id: z.string(),
  name: z.string(),
  concept: LocalizedStringSchema,
  traits: z.array(TraitSchema).min(1).max(4).default([]),
});

export type PresetCharacter = z.infer<typeof PresetCharacterSchema>;

export const LocationDataSchema = z.object({
  id: z.string(),
  name: LocalizedStringSchema,
  description: LocalizedStringSchema,
  atmosphere: LocalizedStringSchema.optional(),
  connected_locations: z.array(z.string()).default([]),
  present_npc_ids: z.array(z.string()).default([]),
  items: z.array(z.string()).default([]),
  tags: z.array(z.string()).default([]),
  region_id: z.string().optional(),
  visible_items: z.array(z.string()).default([]),
  hidden_items: z.array(z.string()).default([]),
  lore_tags: z.array(z.string()).default([]),
});

export type LocationData = z.infer<typeof LocationDataSchema>;

export const WorldPackSchema = z.object({
  info: WorldPackInfoSchema,
  entries: z.record(LoreEntrySchema).default({}),
  npcs: z.record(NPCDataSchema).default({}),
  locations: z.record(LocationDataSchema).default({}),
  preset_characters: z.array(PresetCharacterSchema).default([]),
  regions: z.record(RegionDataSchema).default({}),
});

export type WorldPack = z.infer<typeof WorldPackSchema>;
