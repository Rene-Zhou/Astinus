import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { SaveSlotPreview } from "../api/types";
import { apiClient } from "../api/client";
import { useGameStore } from "./gameStore";
import { useConnectionStore } from "./connectionStore";
import { GameWebSocketClient } from "../api/websocket";
import i18n from "../utils/i18n";

export interface SaveStoreState {
  saves: SaveSlotPreview[];
  isLoading: boolean;
  error: string | null;

  fetchSaves: () => Promise<void>;
  createSave: (
    slotName: string,
    description?: string,
    overwrite?: boolean
  ) => Promise<{ success: boolean; exists?: boolean; existingId?: number }>;
  loadSave: (saveId: number) => Promise<boolean>;
  deleteSave: (saveId: number) => Promise<boolean>;
  clearError: () => void;
}

export const useSaveStore = create<SaveStoreState>()(
  immer((set, get) => ({
    saves: [],
    isLoading: false,
    error: null,

    fetchSaves: async () => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });

      try {
        const res = await apiClient.listSaves();
        if (res.data) {
          set((state) => {
            state.saves = res.data!.saves;
            state.isLoading = false;
          });
        } else {
          set((state) => {
            state.error = res.error || "Failed to fetch saves";
            state.isLoading = false;
          });
        }
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : "Unknown error";
          state.isLoading = false;
        });
      }
    },

    createSave: async (slotName, description, overwrite = false) => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });

      try {
        const res = await apiClient.createSave({
          slot_name: slotName,
          description,
          overwrite,
        });

        if (res.data?.exists) {
          set((state) => {
            state.isLoading = false;
          });
          return {
            success: false,
            exists: true,
            existingId: res.data.existing_id,
          };
        }

        if (res.data?.success && res.data.save) {
          await get().fetchSaves();
          return { success: true };
        }

        set((state) => {
          state.error = res.error || res.data?.error || "Failed to create save";
          state.isLoading = false;
        });
        return { success: false };
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : "Unknown error";
          state.isLoading = false;
        });
        return { success: false };
      }
    },

    loadSave: async (saveId) => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });

      try {
        const res = await apiClient.loadSave(saveId);

        if (!res.data?.success || !res.data.game_state) {
          set((state) => {
            state.error = res.error || "Failed to load save";
            state.isLoading = false;
          });
          return false;
        }

        const gameStore = useGameStore.getState();
        const connectionStore = useConnectionStore.getState();

        if (gameStore.wsClient) {
          gameStore.wsClient.disconnect();
        }

        gameStore.hydrateGameState(res.data.game_state);

        if (res.data.world_info) {
          useGameStore.setState((state) => {
            state.worldInfo = res.data!.world_info;
          });
        }

        connectionStore.setStatus("connecting");
        connectionStore.resetReconnectAttempts();
        connectionStore.setError(null);

        const wsClient = new GameWebSocketClient({
          sessionId: res.data.session_id,
          reconnect: { enabled: true },
          handlers: {
            onOpen: () => {
              connectionStore.setStatus("connected");
              connectionStore.resetReconnectAttempts();
            },
            onClose: () => {
              connectionStore.setStatus("disconnected");
            },
            onError: () => {
              connectionStore.setStatus("error");
            },
            onContent: (msg) =>
              useGameStore.setState((state) => {
                state.isStreaming = true;
                state.streamingContent = state.streamingContent + msg.data.chunk;
              }),
            onComplete: (msg) =>
              useGameStore.setState((state) => {
                state.isStreaming = false;
                state.isProcessing = false;
                state.processingStatus = null;
                state.processingAgent = null;
                state.streamingContent = "";
                if (msg.data.metadata?.player) {
                  state.player = msg.data.metadata.player as typeof state.player;
                }
                state.messages.push({
                  role: "assistant",
                  content: msg.data.content,
                  timestamp: new Date().toISOString(),
                  turn: state.turnCount,
                  metadata: msg.data.metadata,
                });
              }),
            onStatus: (msg) =>
              useGameStore.setState((state) => {
                state.isProcessing = true;
                const messageKey = msg.data.message;
                let translatedMessage: string | null = null;
                if (messageKey) {
                  const camelCaseKey = messageKey.replace(/_([a-z])/g, (_, letter: string) =>
                    letter.toUpperCase()
                  );
                  translatedMessage = i18n.t(`game.status.${camelCaseKey}`, messageKey);
                }
                if (!translatedMessage && msg.data.agent) {
                  const agentKey = msg.data.agent.startsWith("npc") ? "npc" : msg.data.agent;
                  translatedMessage = i18n.t(`settings.agentTitles.${agentKey}`, "");
                }
                state.processingStatus = translatedMessage || null;
                state.processingAgent = msg.data.agent || null;
              }),
            onPhase: (msg) =>
              useGameStore.setState((state) => {
                state.currentPhase = msg.data.phase;
              }),
            onDiceCheck: (msg) =>
              useGameStore.setState((state) => {
                state.pendingDiceCheck = msg.data.check_request;
              }),
            onServerError: (msg) =>
              useGameStore.setState((state) => {
                state.isStreaming = false;
                state.isProcessing = false;
                state.processingStatus = null;
                state.processingAgent = null;
                state.streamingContent = "";
                connectionStore.setStatus("error");
                connectionStore.setError(msg.data.error);
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

        useGameStore.setState((state) => {
          state.wsClient = wsClient;
        });

        set((state) => {
          state.isLoading = false;
        });

        return true;
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : "Unknown error";
          state.isLoading = false;
        });
        return false;
      }
    },

    deleteSave: async (saveId) => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });

      try {
        const res = await apiClient.deleteSave(saveId);

        if (res.data?.success) {
          set((state) => {
            state.saves = state.saves.filter((s) => s.id !== saveId);
            state.isLoading = false;
          });
          return true;
        }

        set((state) => {
          state.error = res.error || "Failed to delete save";
          state.isLoading = false;
        });
        return false;
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : "Unknown error";
          state.isLoading = false;
        });
        return false;
      }
    },

    clearError: () => {
      set((state) => {
        state.error = null;
      });
    },
  }))
);
