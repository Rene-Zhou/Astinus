import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import {
  type DiceCheckRequest,
  type DiceResult,
  type GamePhase,
  type GameState as BackendGameState,
  type Message,
  type NewGameResponse,
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
      const { worldPackId, playerName } = opts ?? {};
      const existing = get().wsClient;
      if (existing) {
        existing.disconnect();
      }
      const res = await apiClient.createNewGame({
        world_pack_id: worldPackId ?? "demo_pack",
        player_name: playerName ?? "玩家",
      });

      if (!res.data) {
        throw new Error(res.error ?? "Failed to create new game");
      }

      const data: NewGameResponse = res.data;
      set((state) => {
        state.sessionId = data.session_id;
        state.worldPackId = worldPackId ?? "demo_pack";
        state.player = data.player;
        state.currentLocation = data.game_state.current_location;
        state.currentPhase = data.game_state.current_phase;
        state.turnCount = data.game_state.turn_count;
        state.activeNpcIds = data.game_state.active_npc_ids;
        state.messages = [
          {
            role: "assistant",
            content: data.message,
            timestamp: new Date().toISOString(),
            turn: data.game_state.turn_count,
            metadata: { phase: data.game_state.current_phase },
          },
        ];
        state.pendingDiceCheck = null;
        state.lastDiceResult = null;
        state.streamingContent = "";
      });

      // Initialize WebSocket connection for the session
      const connection = useConnectionStore.getState();
      connection.setStatus("connecting");
      connection.resetReconnectAttempts();
      connection.setError(null);

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

      wsClient.connect();

      set((state) => {
        state.wsClient = wsClient;
      });
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
        state.messages = gameState.messages;
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
