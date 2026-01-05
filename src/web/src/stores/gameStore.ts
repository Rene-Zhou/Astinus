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

  // Player & game state
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
  startNewGame: (opts?: {
    worldPackId?: string;
    playerName?: string;
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
 * Generate introduction message from world info and starting scene
 */
function generateIntroductionMessage(
  worldInfo: WorldInfo,
  startingScene: StartingScene,
  lang: Language = "cn",
): string {
  const parts: string[] = [];

  // World background
  const worldName = getLocalizedValue(worldInfo.name, lang);
  const worldDesc = getLocalizedValue(worldInfo.description, lang);
  parts.push(`【${worldName}】`);
  parts.push(worldDesc);
  parts.push("");

  // Starting location
  const locationName = getLocalizedValue(startingScene.location_name, lang);
  const locationDesc = getLocalizedValue(startingScene.description, lang);
  parts.push(
    lang === "cn"
      ? `你来到了${locationName}。`
      : `You arrive at ${locationName}.`,
  );
  parts.push(locationDesc);

  // NPCs in scene
  if (startingScene.npcs && startingScene.npcs.length > 0) {
    parts.push("");
    const npcIntro =
      lang === "cn"
        ? "你注意到这里有："
        : "You notice the following people here:";
    parts.push(npcIntro);
    for (const npc of startingScene.npcs) {
      const npcDesc = getLocalizedValue(npc.description, lang);
      // Take first sentence or first 100 chars as brief
      const brief = npcDesc.split(/[。.]/)[0] + (lang === "cn" ? "。" : ".");
      parts.push(`- ${npc.name}：${brief}`);
    }
  }

  // Connected locations
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

    startNewGame: async (opts) => {
      console.log("[gameStore] startNewGame called", opts);
      const { worldPackId, playerName } = opts ?? {};
      const existing = get().wsClient;
      if (existing) {
        console.log("[gameStore] Disconnecting existing wsClient");
        existing.disconnect();
      }
      console.log("[gameStore] Calling apiClient.createNewGame");
      const res = await apiClient.createNewGame({
        world_pack_id: worldPackId ?? "demo_pack",
        player_name: playerName ?? "玩家",
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
