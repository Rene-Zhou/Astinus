/**
 * Astinus API Types Definition
 *
 * This file serves as a reference for frontend development.
 * It defines all types used in communication with the backend API.
 *
 * @see docs/ARCHITECTURE.md for full architecture documentation
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
export type Language = 'cn' | 'en';

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
 * Preset character for player selection (before game starts)
 */
export interface PresetCharacter {
  id: string;
  name: string;
  concept: LocalizedString;
  traits: Trait[];
}

// ============================================================================
// World Pack Types
// ============================================================================

/**
 * World setting information (era, genre, tone)
 */
export interface WorldPackSetting {
  era: LocalizedString;
  genre: LocalizedString;
  tone: LocalizedString;
}

/**
 * World pack metadata
 */
export interface WorldPackInfo {
  name: LocalizedString;
  description: LocalizedString;
  version?: string;
  author?: string;
  setting?: WorldPackSetting;
  player_hook?: LocalizedString;
}

/**
 * A hierarchical region containing multiple locations
 */
export interface RegionData {
  id: string;
  name: LocalizedString;
  description: LocalizedString;
  narrative_tone?: LocalizedString;
  atmosphere_keywords: string[];
  location_ids: string[];
  tags: string[];
}

/**
 * A lore entry for world background information
 */
export interface LoreEntry {
  uid: number;
  key: string[];
  secondary_keys: string[];
  content: LocalizedString;
  comment?: LocalizedString;
  constant: boolean;
  selective: boolean;
  order: number;
  visibility: "basic" | "detailed";
  applicable_regions: string[];
  applicable_locations: string[];
}

/**
 * NPC narrative layer (The Soul) - determines how they speak
 */
export interface NPCSoul {
  name: string;
  description: LocalizedString;
  appearance?: LocalizedString;
  personality: string[];
  speech_style: LocalizedString;
  example_dialogue: Array<{ user: string; char: string }>;
}

/**
 * NPC data layer (The Body) - structured state
 */
export interface NPCBody {
  location: string;
  inventory: string[];
  relations: Record<string, number>;
  tags: string[];
  memory: Record<string, string[]>;
  location_knowledge: Record<string, number[]>;
}

/**
 * Complete NPC definition combining soul and body layers
 */
export interface NPCData {
  id: string;
  soul: NPCSoul;
  body: NPCBody;
}

/**
 * A location/scene in the world
 */
export interface LocationData {
  id: string;
  name: LocalizedString;
  description: LocalizedString;
  atmosphere?: LocalizedString;
  connected_locations: string[];
  present_npc_ids: string[];
  items: string[];
  tags: string[];
  region_id?: string;
  visible_items: string[];
  hidden_items: string[];
  lore_tags: string[];
}

/**
 * Complete world pack containing all world data
 */
export interface WorldPack {
  info: WorldPackInfo;
  entries: Record<string, LoreEntry>;
  npcs: Record<string, NPCData>;
  locations: Record<string, LocationData>;
  preset_characters: PresetCharacter[];
  regions: Record<string, RegionData>;
}

/**
 * Response from GET /api/v1/game/world-pack/{pack_id}
 */
export interface WorldPackDetailResponse {
  id: string;
  info: WorldPackInfo;
  summary: {
    locations: number;
    npcs: number;
    lore_entries: number;
    preset_characters: number;
  };
  locations: Array<{ id: string; name: LocalizedString; tags: string[] }>;
  npcs: Array<{ id: string; name: string; location: string }>;
  preset_characters: PresetCharacter[];
}

/**
 * Response from GET /api/v1/game/world-packs
 */
export interface ListWorldPacksResponse {
  packs: string[];
}

// ============================================================================
// Game State Types
// ============================================================================

/**
 * Game phases - matches backend GamePhase enum
 */
export type GamePhase =
  | 'waiting_input'  // Waiting for player input
  | 'processing'     // GM is processing player action
  | 'dice_check'     // Waiting for player to roll dice
  | 'npc_response'   // NPC is responding
  | 'narrating';     // GM is narrating outcome

/**
 * Current game state - GM Agent's world view
 */
export interface GameState {
  session_id: string;
  world_pack_id: string;
  player_name: string;
  player: PlayerCharacter;
  current_location: string;
  active_npc_ids: string[];
  current_phase: GamePhase;
  turn_count: number;
  language: Language;
  messages: Message[];
  // Missing fields from backend:
  created_at?: string;
  updated_at?: string;
  next_agent?: string | null;
  discovered_items?: string[];
  flags?: string[];
  game_time?: string;
  temp_context?: Record<string, unknown>;
  last_check_result?: Record<string, unknown> | null;
  react_pending_state?: Record<string, unknown> | null;
}

/**
 * Current scene/location details
 */
export interface CurrentScene {
  location_name: LocalizedString;
  description: LocalizedString;
  items: string[];
  connected_locations: string[];
  npcs: Array<{ id: string; name: string }>;
  atmosphere?: LocalizedString;
}

/**
 * A single message in the conversation history
 */
export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;  // ISO 8601 format
  turn: number;
  metadata?: {
    agent?: string;   // Which agent generated this (gm, npc, rule, lore)
    phase?: GamePhase;
    [key: string]: unknown;
  };
}

// ============================================================================
// Dice Types
// ============================================================================

/**
 * Dice check request from Rule Agent
 */
export interface DiceCheckRequest {
  /** What the player is trying to do */
  intention: string;
  /** Traits/tags affecting the roll - dict with 'traits' and 'tags' arrays */
  influencing_factors: {
    traits: string[];
    tags: string[];
  };
  /** Dice notation (e.g., "2d6", "3d6kl2") */
  dice_formula: string;
  /** Explanation of modifiers */
  instructions: LocalizedString;
}

/**
 * Result of a dice check after rolling
 */
export interface DiceCheckResult {
  intention: string;
  dice_formula: string;
  dice_values: number[];
  total: number;
  threshold: number;
  success: boolean;
  critical: boolean;
  modifiers: Array<{ source: string; effect: string }>;
}

/**
 * Player's response to a dice check request
 */
export interface DiceCheckResponse {
  action: "roll" | "argue" | "cancel";
  dice_result?: {
    all_rolls: number[];
    kept_rolls: number[];
    total: number;
    outcome: DiceOutcome;
  };
  argument?: string;
  trait_claimed?: string;
}

/**
 * Dice roll result submitted by player
 */
export interface DiceResult {
  /** All dice rolled (e.g., [3, 5, 6] for 3d6) */
  all_rolls: number[];
  /** Dice kept after advantage/disadvantage */
  kept_rolls: number[];
  /** Dice rolled but not kept */
  dropped_rolls: number[];
  /** Modifier applied after dice selection */
  modifier: number;
  /** Total value of the roll (kept dice + modifier) */
  total: number;
  /** Roll outcome */
  outcome: DiceOutcome;
  /** True if bonus dice were used */
  is_bonus: boolean;
  /** True if penalty dice were used */
  is_penalty: boolean;
}

/**
 * Possible outcomes of a dice roll
 */
export type DiceOutcome = 'critical' | 'success' | 'partial' | 'failure';

// ============================================================================
// Narrative Types
// ============================================================================

/**
 * Types of scenes in the narrative
 */
export type SceneType =
  | "location"
  | "encounter"
  | "dialogue"
  | "cutscene"
  | "puzzle"
  | "combat";

/**
 * Condition for scene transition
 */
export interface TransitionCondition {
  type: string;
  key: string;
  value: unknown;
}

/**
 * Transition from one scene to another
 */
export interface SceneTransition {
  target_scene_id: string;
  condition?: TransitionCondition;
  description?: string;
}

/**
 * A scene in the narrative graph
 */
export interface Scene {
  id: string;
  name: string;
  type: SceneType;
  description: string;
  narrative_state: Record<string, unknown>;
  active_npcs: string[];
  available_actions: string[];
  transitions: SceneTransition[];
}

/**
 * Complete narrative graph for a world pack
 */
export interface NarrativeGraph {
  world_pack_id: string;
  scenes: Record<string, Scene>;
  current_scene_id: string | null;
  global_narrative_state: Record<string, unknown>;
}

// ============================================================================
// REST API Types
// ============================================================================

// --- POST /api/v1/game/new ---

export interface NewGameRequest {
  world_pack_id?: string;
  player_name?: string;
  preset_character_id?: string | null;
}

/**
 * Response from starting a new game
 */
export interface NewGameResponse {
  session_id: string;
  player: PlayerCharacter;
  game_state: {
    current_location: string;
    current_phase: GamePhase;
    turn_count: number;
    active_npc_ids: string[];
  };
  world_info: {
    id: string;
    name: LocalizedString;
    description: LocalizedString;
    version?: string;
    author?: string;
    setting?: WorldPackSetting;
    player_hook?: LocalizedString;
  };
  starting_scene: {
    location_id: string;
    location_name: LocalizedString;
    description: LocalizedString;
    items: string[];
    connected_locations: Array<{ id: string; name: LocalizedString }>;
    npcs: Array<{
      id: string;
      appearance?: LocalizedString;
    }>;
    atmosphere?: LocalizedString;
  };
  message: string;
}

// --- POST /api/v1/game/action ---

export interface ActionRequest {
  player_input: string;
  lang?: Language;  // Default: "cn"
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

export type GetGameStateResponse = GameState & {
  current_scene?: CurrentScene;
};

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

// --- GET /health ---

export interface HealthResponse {
  status: 'healthy' | 'unhealthy';
  version: string;
  agents: {
    gm_agent: boolean;
    npc_agent: boolean;
  };
  services: {
    world_pack_loader: boolean;
    vector_store: boolean;
    lore_service: boolean;
  };
}

// --- GET / ---

export interface RootResponse {
  name: string;
  version: string;
  status: string;
  runtime: string;
  docs: string;
}

// ============================================================================
// Persistence/Storage Types
// ============================================================================

/**
 * Game session database model
 */
export interface GameSession {
  id: number;
  session_id: string;
  world_pack_id: string;
  player_name: string;
  player_data: PlayerCharacter | null;
  current_location: string;
  current_phase: GamePhase;
  turn_count: number;
  active_npc_ids: string[];
  created_at: string;
  updated_at: string;
}

/**
 * Message database model
 */
export interface MessageRecord {
  id: number;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  turn: number;
  extra_data: Record<string, unknown> | null;
  created_at: string;
}

/**
 * Save slot database model
 */
export interface SaveSlot {
  id: number;
  session_id: string;
  slot_name: string;
  game_state: Record<string, unknown>;
  description: string | null;
  is_auto_save: boolean;
  created_at: string;
  updated_at: string;
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
export interface WSMessage<T extends WSMessageType = WSMessageType, D = unknown> {
  type: T;
  data: D;
}

// --- Client -> Server Messages ---

export interface WSPlayerInputMessage extends WSMessage<"player_input"> {
  type: "player_input";
  content: string;
  lang?: Language;
  stream?: boolean;
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
    agent?: string;
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

// --- Observer WebSocket (Read-only) ---

/**
 * Observer mode - read-only streaming
 */
export interface WSObserverMessage extends WSMessage<"content" | "complete" | "status"> {
  type: "content" | "complete" | "status";
  data: {
    chunk?: string;
    content?: string;
    message?: string;
    is_partial?: boolean;
    chunk_index?: number;
    success?: boolean;
    metadata?: Record<string, unknown>;
  };
}

// ============================================================================
// Connection State Types (for frontend state management)
// ============================================================================

/**
 * WebSocket connection status
 */
export type ConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error';

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
export function getLocalizedValue(str: LocalizedString, lang: Language): string {
  return str[lang] || str.cn || str.en;
}

// ============================================================================
// Settings API Types
// ============================================================================

// --- Provider Types ---

export type ProviderType = 'openai' | 'anthropic' | 'google' | 'ollama' | 'custom' | 'openai-compatible';

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

export type AgentName = 'gm' | 'npc' | 'lore';

export interface AgentsConfig {
  gm: AgentConfig;
  npc: AgentConfig;
  rule?: AgentConfig;
  lore?: AgentConfig;
}

export interface GameSettings {
  default_language: Language;
  dice: {
    use_advantage_system: boolean;
    show_roll_details: boolean;
  };
}

// --- GET /api/v1/settings ---

export interface SettingsResponse {
  providers: ProviderConfig[];
  agents: AgentsConfig | null;
  game: GameSettings;
}

// --- PUT /api/v1/settings ---

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
  lore?: AgentInput;
}

export interface UpdateSettingsRequest {
  providers?: ProviderInput[];
  agents?: AgentsInput;
}

// --- POST /api/v1/settings/test ---

export interface TestConnectionRequest {
  provider_id: string;
}

export interface TestConnectionResponse {
  success: boolean;
  provider_id: string;
  message: string;
  latency_ms: number | null;
}

// --- GET /api/v1/settings/provider-types ---

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

// --- POST /api/v1/settings/reload-agents ---

export interface ReloadAgentsResponse {
  success: boolean;
  message: string;
}
