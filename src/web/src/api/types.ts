/**
 * Astinus API Types Definition
 *
 * This file serves as a reference for frontend development.
 * It defines all types used in communication with the backend API.
 *
 * @see docs/WEB_FRONTEND_PLAN.md for full API documentation
 */

// ============================================================================
// Common Types
// ============================================================================

/**
 * Localized string supporting Chinese and English
 */
export interface LocalizedString {
  cn: string;
  en: string;
}

/**
 * Supported languages
 */
export type Language = "cn" | "en";

// ============================================================================
// Character Types
// ============================================================================

/**
 * Character trait with dual aspects (positive/negative)
 */
export interface Trait {
  name: LocalizedString;
  description: LocalizedString;
  positive_aspect: LocalizedString;
  negative_aspect: LocalizedString;
}

/**
 * Player character data
 */
export interface PlayerCharacter {
  name: string;
  concept: LocalizedString;
  traits: Trait[];
  tags: string[];
  fate_points: number;
}

/**
 * Preset character for player selection
 */
export interface PresetCharacter {
  id: string;
  name: string; // Fixed PC name
  concept: LocalizedString;
  traits: Trait[];
}

// ============================================================================
// Game State Types
// ============================================================================

/**
 * Game phases - matches backend GamePhase enum
 */
export type GamePhase =
  | "waiting_input" // Waiting for player input
  | "processing" // GM is processing player action
  | "dice_check" // Waiting for player to roll dice
  | "npc_response" // NPC is responding
  | "narrating"; // GM is narrating outcome

/**
 * Current game state
 */
export interface GameState {
  session_id: string;
  world_pack_id: string;
  player_name: string; // PL (user) name - distinct from PC name
  player: PlayerCharacter;
  current_location: string;
  active_npc_ids: string[];
  current_phase: GamePhase;
  turn_count: number;
  language: Language;
  messages: Message[];
}

/**
 * A single message in the conversation history
 */
export interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string; // ISO 8601 format
  turn: number;
  metadata?: {
    agent?: string; // Which agent generated this (gm, npc, rule, lore)
    phase?: GamePhase;
    [key: string]: unknown;
  };
}

// ============================================================================
// Dice Types
// ============================================================================

/**
 * Influencing factors affecting a dice roll
 */
export interface InfluencingFactors {
  traits: string[];
  tags: string[];
}

/**
 * Dice check request from Rule Agent
 */
export interface DiceCheckRequest {
  /** What the player is trying to do */
  intention: string;
  /** Traits/tags affecting the roll */
  influencing_factors: InfluencingFactors;
  /** Dice notation (e.g., "2d6", "3d6kl2") */
  dice_formula: string;
  /** Explanation of modifiers - can be string or LocalizedString */
  instructions: string | LocalizedString;
}

/**
 * Helper to flatten influencing factors into a string array for display
 */
export function flattenInfluencingFactors(
  factors: InfluencingFactors,
): string[] {
  const result: string[] = [];
  if (factors.traits && factors.traits.length > 0) {
    result.push(...factors.traits);
  }
  if (factors.tags && factors.tags.length > 0) {
    result.push(...factors.tags);
  }
  return result;
}

/**
 * Helper to get instructions as string
 */
export function getInstructionsText(
  instructions: string | LocalizedString,
  lang: Language = "cn",
): string {
  if (typeof instructions === "string") {
    return instructions;
  }
  return getLocalizedValue(instructions, lang);
}

/**
 * Dice roll result submitted by player
 */
export interface DiceResult {
  /** Total value of the roll */
  total: number;
  /** All dice rolled (e.g., [3, 5, 6] for 3d6) */
  all_rolls: number[];
  /** Dice kept after advantage/disadvantage */
  kept_rolls: number[];
  /** Roll outcome */
  outcome: DiceOutcome;
}

/**
 * Possible outcomes of a dice roll
 */
export type DiceOutcome = "critical" | "success" | "partial" | "failure";

// ============================================================================
// REST API Types
// ============================================================================

// --- POST /api/v1/game/new ---

export interface NewGameRequest {
  world_pack_id?: string;
  player_name?: string;
  preset_character_id?: string;
}

/**
 * World setting information for establishing game context
 */
export interface WorldSetting {
  era: LocalizedString;
  genre: LocalizedString;
  tone: LocalizedString;
}

/**
 * World pack info returned when starting a new game
 */
export interface WorldInfo {
  id: string;
  name: LocalizedString;
  description: LocalizedString;
  version: string;
  author: string;
  /** Optional world setting (era, genre, tone) */
  setting?: WorldSetting;
  /** Optional player motivation/hook */
  player_hook?: LocalizedString;
}

/**
 * Connected location reference
 */
export interface ConnectedLocation {
  id: string;
  name: LocalizedString;
}

/**
 * NPC info in scene - only appearance, no name (to prevent metagaming)
 */
export interface SceneNPC {
  id: string;
  /** External appearance description (player hasn't learned name yet) */
  appearance: LocalizedString;
}

/**
 * Starting scene information
 */
export interface StartingScene {
  location_id: string;
  location_name: LocalizedString;
  description: LocalizedString;
  /** Optional atmosphere (time, weather, environment) */
  atmosphere?: LocalizedString;
  items: string[];
  connected_locations: ConnectedLocation[];
  npcs: SceneNPC[];
}

export interface NewGameResponse {
  session_id: string;
  player: PlayerCharacter;
  game_state: {
    current_location: string;
    current_phase: GamePhase;
    turn_count: number;
    active_npc_ids: string[];
  };
  world_info: WorldInfo;
  starting_scene: StartingScene;
  message: string;
}

// --- POST /api/v1/game/action ---

export interface ActionRequest {
  player_input: string;
  lang?: Language; // Default: "cn"
}

export interface ActionResponse {
  success: boolean;
  content: string;
  metadata: {
    phase?: GamePhase;
    needs_check?: boolean;
    dice_check?: DiceCheckRequest;
    [key: string]: unknown;
  };
  error: string | null;
}

// --- GET /api/v1/game/state ---

export type GetGameStateResponse = GameState;

// --- POST /api/v1/game/dice-result ---

export interface DiceResultRequest {
  total: number;
  all_rolls: number[];
  kept_rolls: number[];
  outcome: DiceOutcome;
}

export interface DiceResultResponse {
  success: boolean;
  message: string;
  next_phase: GamePhase;
}

// --- GET /api/v1/game/messages ---

export interface GetMessagesResponse {
  messages: Message[];
  count: number;
}

// --- POST /api/v1/game/reset ---

export interface ResetResponse {
  success: boolean;
  message: string;
}

// --- GET /api/v1/game/world-pack/{pack_id} ---

/**
 * World pack detail response including preset characters
 */
export interface WorldPackDetailResponse {
  id: string;
  info: WorldInfo;
  summary: {
    locations: number;
    npcs: number;
    lore_entries: number;
    preset_characters: number;
  };
  locations: Array<{
    id: string;
    name: LocalizedString;
    tags: string[];
  }>;
  npcs: Array<{
    id: string;
    name: string;
    location: string;
  }>;
  preset_characters: PresetCharacter[];
}

// --- GET /health ---

export interface HealthResponse {
  status: "healthy" | "unhealthy";
  version: string;
  agents: {
    gm_agent: boolean;
    rule_agent: boolean;
  };
}

// --- GET / ---

export interface RootResponse {
  name: string;
  version: string;
  status: string;
  docs: string;
  openapi: string;
}

// ============================================================================
// WebSocket Types
// ============================================================================

/**
 * WebSocket message types
 */
export type WSMessageType =
  | "player_input" // Client -> Server: Player action
  | "dice_result" // Client -> Server: Dice roll result
  | "status" // Server -> Client: Processing status
  | "content" // Server -> Client: Streamed content chunk
  | "complete" // Server -> Client: Final response
  | "dice_check" // Server -> Client: Dice check required
  | "phase" // Server -> Client: Phase change
  | "error"; // Server -> Client: Error message

/**
 * Base WebSocket message structure
 */
export interface WSMessage<
  T extends WSMessageType = WSMessageType,
  D = unknown,
> {
  type: T;
  data: D;
}

// --- Client -> Server Messages ---

export interface WSPlayerInputMessage extends WSMessage<"player_input"> {
  type: "player_input";
  content: string;
  lang?: Language;
  stream?: boolean; // Default: true
}

export interface WSDiceResultMessage extends WSMessage<"dice_result"> {
  type: "dice_result";
  result: number;
  all_rolls: number[];
  kept_rolls: number[];
  outcome: DiceOutcome;
}

export type WSClientMessage = WSPlayerInputMessage | WSDiceResultMessage;

// --- Server -> Client Messages ---

export interface WSStatusMessage extends WSMessage<"status"> {
  type: "status";
  data: {
    phase: string;
    message: string;
  };
}

export interface WSContentMessage extends WSMessage<"content"> {
  type: "content";
  data: {
    chunk: string;
    is_partial: boolean;
    chunk_index: number;
  };
}

export interface WSCompleteMessage extends WSMessage<"complete"> {
  type: "complete";
  data: {
    content: string;
    metadata: Record<string, unknown>;
    success: boolean;
  };
}

export interface WSDiceCheckMessage extends WSMessage<"dice_check"> {
  type: "dice_check";
  data: {
    check_request: DiceCheckRequest;
  };
}

export interface WSPhaseMessage extends WSMessage<"phase"> {
  type: "phase";
  data: {
    phase: GamePhase;
  };
}

export interface WSErrorMessage extends WSMessage<"error"> {
  type: "error";
  data: {
    error: string;
  };
}

export type WSServerMessage =
  | WSStatusMessage
  | WSContentMessage
  | WSCompleteMessage
  | WSDiceCheckMessage
  | WSPhaseMessage
  | WSErrorMessage;

// ============================================================================
// Connection State Types (for frontend state management)
// ============================================================================

/**
 * WebSocket connection status
 */
export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "error";

// ============================================================================
// Utility Types
// ============================================================================

/**
 * API error response
 */
export interface APIError {
  detail: string;
}

/**
 * Helper to get localized string value
 */
export function getLocalizedValue(
  str: LocalizedString,
  lang: Language,
): string {
  return str[lang] || str.cn || str.en;
}

// ============================================================================
// Settings Types
// ============================================================================

export type ProviderType = "openai" | "anthropic" | "google" | "ollama";

export interface ProviderConfig {
  id: string;
  name: string;
  type: ProviderType;
  api_key: string;
  base_url: string | null;
}

export interface AgentConfig {
  provider_id: string;
  model: string;
  temperature: number;
  max_tokens: number;
}

export type AgentName = "gm" | "npc" | "rule" | "lore";

export interface AgentsConfig {
  gm: AgentConfig;
  npc: AgentConfig;
  rule: AgentConfig;
  lore: AgentConfig;
}

export interface GameSettings {
  default_language: Language;
  dice: {
    use_advantage_system: boolean;
    show_roll_details: boolean;
  };
}

export interface SettingsResponse {
  providers: ProviderConfig[];
  agents: AgentsConfig | null;
  game: GameSettings;
}

export interface ProviderInput {
  id: string;
  name: string;
  type: ProviderType;
  api_key: string;
  base_url: string | null;
}

export interface AgentInput {
  provider_id: string;
  model: string;
  temperature: number;
  max_tokens: number;
}

export interface AgentsInput {
  gm?: AgentInput;
  npc?: AgentInput;
  rule?: AgentInput;
  lore?: AgentInput;
}

export interface UpdateSettingsRequest {
  providers?: ProviderInput[];
  agents?: AgentsInput;
}

export interface TestConnectionRequest {
  provider_id: string;
}

export interface TestConnectionResponse {
  success: boolean;
  provider_id: string;
  message: string;
  latency_ms: number | null;
}

export interface ProviderTypeInfo {
  type: ProviderType;
  name: string;
  requires_api_key: boolean;
  default_base_url: string | null;
  placeholder_models: string[];
}

export interface ProviderTypesResponse {
  types: ProviderTypeInfo[];
}
