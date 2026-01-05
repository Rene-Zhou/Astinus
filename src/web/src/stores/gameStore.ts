import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import {
  type DiceCheckRequest,
  type DiceResult,
  type GamePhase,
  type GameState as BackendGameState,
  type Message,
  type NewGameResponse,
  type WorldInfo,
  type StartingScene,
  type PresetCharacter,
  type WorldPackDetailResponse,
  getLocalizedValue,
  type Language,
} from "../api/types";
import { apiClient } from "../api/client";
import { GameWebSocketClient } from "../api/websocket";
import { useConnectionStore } from "./connectionStore";

/**
 * GameStore state shape
 */
export interface GameStoreState {
  // Session
  sessionId: string | null;
  worldPackId: string;

  // World info
  worldInfo: WorldInfo | null;
  startingScene: StartingScene | null;

  // Character selection (before game starts)
  selectedWorldPackId: string;
  presetCharacters: PresetCharacter[];

  // Player & game state
  playerName: string; // PL (user) name - distinct from PC name
  player: BackendGameState["player"] | null;
  currentLocation: string;
  currentPhase: GamePhase;
  turnCount: number;
  activeNpcIds: string[];

  // Messaging
  messages: Message[];
  streamingContent: string;

  // Dice
  pendingDiceCheck: DiceCheckRequest | null;
  lastDiceResult: DiceResult | null;

  // Connection
  wsClient: GameWebSocketClient | null;
  isStreaming: boolean;

  // Actions
  loadWorldPackDetail: (packId: string) => Promise<WorldPackDetailResponse | null>;
  setSelectedWorldPackId: (packId: string) => void;
  setPlayerName: (name: string) => void;
  startNewGame: (opts?: {
    worldPackId?: string;
    playerName?: string;
    presetCharacterId?: string;
  }) => Promise<void>;
  sendPlayerInput: (content: string, lang?: "cn" | "en") => void;
  submitDiceResult: (result: DiceResult) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  appendStreamingContent: (chunk: string) => void;
  clearStreamingContent: () => void;
  setPhase: (phase: GamePhase) => void;
  setPendingDiceCheck: (check: DiceCheckRequest | null) => void;
  hydrateGameState: (gameState: BackendGameState) => void;
  reset: () => void;
}

/**
 * Generate introduction message from world info and starting scene.
 *
 * IMPORTANT: This function follows information control rules:
 * - Does NOT reveal NPC names (player hasn't learned them yet)
 * - Does NOT reveal background lore (player must discover it)
 * - Uses appearance descriptions for NPCs
 * - Includes atmosphere (time, weather) for immersion
 */
function generateIntroductionMessage(
  worldInfo: WorldInfo,
  startingScene: StartingScene,
  lang: Language = "cn",
): string {
  const parts: string[] = [];

  // World title (just the name, no spoiler description)
  const worldName = getLocalizedValue(worldInfo.name, lang);
  parts.push(`【${worldName}】`);

  // World setting (era, genre, tone) - establishes context without spoilers
  if (worldInfo.setting) {
    const era = getLocalizedValue(worldInfo.setting.era, lang);
    const genre = getLocalizedValue(worldInfo.setting.genre, lang);
    parts.push(lang === "cn" ? `时代：${era}` : `Era: ${era}`);
    parts.push(lang === "cn" ? `类型：${genre}` : `Genre: ${genre}`);
  }
  parts.push("");

  // Player hook - motivation for being here
  if (worldInfo.player_hook) {
    const hook = getLocalizedValue(worldInfo.player_hook, lang);
    parts.push(hook);
    parts.push("");
  }

  // Scene atmosphere (time, weather, environment) - sets the mood
  if (startingScene.atmosphere) {
    const atmosphere = getLocalizedValue(startingScene.atmosphere, lang);
    parts.push(atmosphere);
    parts.push("");
  }

  // Starting location description
  const locationName = getLocalizedValue(startingScene.location_name, lang);
  const locationDesc = getLocalizedValue(startingScene.description, lang);
  parts.push(
    lang === "cn"
      ? `你来到了${locationName}。`
      : `You arrive at ${locationName}.`,
  );
  parts.push(locationDesc);

  // NPCs in scene - describe by appearance only, NO NAMES
  if (startingScene.npcs && startingScene.npcs.length > 0) {
    parts.push("");
    const npcIntro =
      lang === "cn" ? "你注意到这里有人：" : "You notice someone here:";
    parts.push(npcIntro);
    for (const npc of startingScene.npcs) {
      // Use appearance, not name - player hasn't learned names yet
      const appearance = getLocalizedValue(npc.appearance, lang);
      parts.push(`- ${appearance}`);
    }
  }

  // Connected locations - only show names, not descriptions
  if (
    startingScene.connected_locations &&
    startingScene.connected_locations.length > 0
  ) {
    parts.push("");
    const connectionIntro =
      lang === "cn" ? "从这里，你可以前往：" : "From here, you can go to:";
    parts.push(connectionIntro);
    const locations = startingScene.connected_locations
      .map((loc) => getLocalizedValue(loc.name, lang))
      .join(lang === "cn" ? "、" : ", ");
    parts.push(locations);
  }

  return parts.join("\n");
}

/**
 * Helpers
 */
const initialState = (): Omit<
  GameStoreState,
  | "loadWorldPackDetail"
  | "setSelectedWorldPackId"
  | "setPlayerName"
  | "startNewGame"
  | "sendPlayerInput"
  | "submitDiceResult"
  | "setMessages"
  | "addMessage"
  | "appendStreamingContent"
  | "clearStreamingContent"
  | "setPhase"
  | "setPendingDiceCheck"
  | "hydrateGameState"
  | "reset"
> => ({
  sessionId: null,
  worldPackId: "demo_pack",
  worldInfo: null,
  startingScene: null,
  selectedWorldPackId: "demo_pack",
  presetCharacters: [],
  playerName: "玩家",
  player: null,
  currentLocation: "",
  currentPhase: "waiting_input",
  turnCount: 0,
  activeNpcIds: [],
  messages: [],
  streamingContent: "",
  pendingDiceCheck: null,
  lastDiceResult: null,
  wsClient: null,
  isStreaming: false,
});

export const useGameStore = create<GameStoreState>()(
  immer((set, get) => ({
    ...initialState(),

    loadWorldPackDetail: async (packId: string) => {
      console.log("[gameStore] loadWorldPackDetail called", packId);
      const res = await apiClient.getWorldPackDetail(packId);
      if (!res.data) {
        console.error("[gameStore] getWorldPackDetail failed:", res.error);
        return null;
      }
      set((state) => {
        state.selectedWorldPackId = packId;
        state.worldInfo = res.data!.info;
        state.presetCharacters = res.data!.preset_characters;
      });
      return res.data;
    },

    setSelectedWorldPackId: (packId: string) =>
      set((state) => {
        state.selectedWorldPackId = packId;
      }),

    setPlayerName: (name: string) =>
      set((state) => {
        state.playerName = name;
      }),

    startNewGame: async (opts) => {
      console.log("[gameStore] startNewGame called", opts);
      const { worldPackId, playerName, presetCharacterId } = opts ?? {};
      const existing = get().wsClient;
      if (existing) {
        console.log("[gameStore] Disconnecting existing wsClient");
        existing.disconnect();
      }
      console.log("[gameStore] Calling apiClient.createNewGame");
      const res = await apiClient.createNewGame({
        world_pack_id: worldPackId ?? "demo_pack",
        player_name: playerName ?? "玩家",
        preset_character_id: presetCharacterId,
      });
      console.log("[gameStore] apiClient.createNewGame response:", res);

      if (!res.data) {
        console.error("[gameStore] createNewGame failed:", res.error);
        throw new Error(res.error ?? "Failed to create new game");
      }

      const data: NewGameResponse = res.data;

      // Generate introduction message from world info and starting scene
      const introMessage = generateIntroductionMessage(
        data.world_info,
        data.starting_scene,
        "cn",
      );

      set((state) => {
        state.sessionId = data.session_id;
        state.worldPackId = worldPackId ?? "demo_pack";
        state.worldInfo = data.world_info;
        state.startingScene = data.starting_scene;
        state.player = data.player;
        state.currentLocation = data.game_state.current_location;
        state.currentPhase = data.game_state.current_phase;
        state.turnCount = data.game_state.turn_count;
        state.activeNpcIds = data.game_state.active_npc_ids;
        state.messages = [
          {
            role: "assistant",
            content: introMessage,
            timestamp: new Date().toISOString(),
            turn: 0,
            metadata: { phase: "narrating", agent: "gm" },
          },
        ];
        state.pendingDiceCheck = null;
        state.lastDiceResult = null;
        state.streamingContent = "";
      });

      console.log(
        "[gameStore] Game state updated, sessionId:",
        data.session_id,
      );

      // Initialize WebSocket connection for the session
      const connection = useConnectionStore.getState();
      connection.setStatus("connecting");
      connection.resetReconnectAttempts();
      connection.setError(null);

      console.log(
        "[gameStore] Creating WebSocket client for session:",
        data.session_id,
      );
      const wsClient = new GameWebSocketClient({
        sessionId: data.session_id,
        reconnect: { enabled: true },
        handlers: {
          onOpen: () => {
            connection.setStatus("connected");
            connection.resetReconnectAttempts();
          },
          onClose: () => {
            connection.setStatus("disconnected");
          },
          onError: () => {
            connection.setStatus("error");
          },
          onContent: (msg) =>
            set((state) => {
              state.isStreaming = true;
              state.streamingContent = state.streamingContent + msg.data.chunk;
            }),
          onComplete: (msg) =>
            set((state) => {
              state.isStreaming = false;
              state.streamingContent = "";
              state.messages.push({
                role: "assistant",
                content: msg.data.content,
                timestamp: new Date().toISOString(),
                turn: state.turnCount,
                metadata: msg.data.metadata as Message["metadata"],
              });
            }),
          onStatus: () => {
            /* noop UI can listen to connection store */
          },
          onPhase: (msg) =>
            set((state) => {
              state.currentPhase = msg.data.phase;
            }),
          onDiceCheck: (msg) =>
            set((state) => {
              state.pendingDiceCheck = msg.data.check_request;
            }),
          onServerError: (msg) =>
            set((state) => {
              state.isStreaming = false;
              state.streamingContent = "";
              connection.setStatus("error");
              connection.setError(msg.data.error);
              state.messages.push({
                role: "assistant",
                content: `⚠️ ${msg.data.error}`,
                timestamp: new Date().toISOString(),
                turn: state.turnCount,
              });
            }),
        },
      });

      console.log("[gameStore] Connecting WebSocket...");
      wsClient.connect();

      set((state) => {
        state.wsClient = wsClient;
      });
      console.log("[gameStore] startNewGame completed");
    },

    sendPlayerInput: (content, lang = "cn") => {
      const ws = get().wsClient;
      if (ws) {
        ws.sendPlayerInput(content, lang);
      }
    },

    submitDiceResult: (result) => {
      const ws = get().wsClient;
      if (ws) {
        ws.sendDiceResult(result);
      }
      set((state) => {
        state.lastDiceResult = result;
        state.pendingDiceCheck = null;
      });
    },

    setMessages: (messages) =>
      set((state) => {
        state.messages = messages;
      }),

    addMessage: (message) =>
      set((state) => {
        state.messages.push(message);
      }),

    appendStreamingContent: (chunk) =>
      set((state) => {
        state.streamingContent = state.streamingContent + chunk;
        state.isStreaming = true;
      }),

    clearStreamingContent: () =>
      set((state) => {
        state.streamingContent = "";
        state.isStreaming = false;
      }),

    setPhase: (phase) =>
      set((state) => {
        state.currentPhase = phase;
      }),

    setPendingDiceCheck: (check) =>
      set((state) => {
        state.pendingDiceCheck = check;
      }),

    hydrateGameState: (gameState) =>
      set((state) => {
        state.sessionId = gameState.session_id;
        state.worldPackId = gameState.world_pack_id;
        state.player = gameState.player;
        state.currentLocation = gameState.current_location;
        state.currentPhase = gameState.current_phase;
        state.turnCount = gameState.turn_count;
        state.activeNpcIds = gameState.active_npc_ids;
        // Only overwrite messages if we don't have any local messages
        // This preserves intro messages generated by startNewGame
        if (state.messages.length === 0 && gameState.messages.length > 0) {
          state.messages = gameState.messages;
        }
        state.pendingDiceCheck = null;
        state.lastDiceResult = null;
        state.streamingContent = "";
      }),

    reset: () => {
      const ws = get().wsClient;
      if (ws) {
        ws.disconnect();
      }
      const connection = useConnectionStore.getState();
      connection.setStatus("disconnected");
      connection.setError(null);
      connection.resetReconnectAttempts();
      set(() => ({
        ...initialState(),
      }));
    },
  })),
);
