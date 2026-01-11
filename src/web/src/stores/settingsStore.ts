import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type {
  AgentsConfig,
  ProviderConfig,
  ProviderTypeInfo,
  SettingsResponse,
  GameSettings,
} from "../api/types";
import { apiClient } from "../api/client";

export interface SettingsStoreState {
  providers: ProviderConfig[];
  agents: AgentsConfig | null;
  game: GameSettings | null;
  providerTypes: ProviderTypeInfo[];

  isLoading: boolean;
  isSaving: boolean;
  error: string | null;

  testingProviderId: string | null;
  testResults: Record<string, { success: boolean; message: string; latency_ms: number | null }>;

  hasUnsavedChanges: boolean;
}

export interface SettingsStoreActions {
  fetchSettings: () => Promise<void>;
  fetchProviderTypes: () => Promise<void>;
  saveSettings: () => Promise<boolean>;

  setProviders: (providers: ProviderConfig[]) => void;
  addProvider: (provider: ProviderConfig) => void;
  updateProvider: (id: string, updates: Partial<ProviderConfig>) => void;
  removeProvider: (id: string) => void;

  updateAgentConfig: (
    agentName: "gm" | "npc" | "rule" | "lore",
    updates: Partial<AgentsConfig["gm"]>,
  ) => void;

  testProviderConnection: (providerId: string) => Promise<void>;

  resetChanges: () => void;
  clearError: () => void;
}

export type SettingsStore = SettingsStoreState & SettingsStoreActions;

const initialState: SettingsStoreState = {
  providers: [],
  agents: null,
  game: null,
  providerTypes: [],
  isLoading: false,
  isSaving: false,
  error: null,
  testingProviderId: null,
  testResults: {},
  hasUnsavedChanges: false,
};

let savedSnapshot: { providers: ProviderConfig[]; agents: AgentsConfig | null } | null = null;

export const useSettingsStore = create<SettingsStore>()(
  immer((set, get) => ({
    ...initialState,

    fetchSettings: async () => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });

      const result = await apiClient.getSettings();

      if (result.error) {
        set((state) => {
          state.isLoading = false;
          state.error = result.error;
        });
        return;
      }

      const data = result.data as SettingsResponse;
      savedSnapshot = { providers: data.providers, agents: data.agents };

      set((state) => {
        state.providers = data.providers;
        state.agents = data.agents;
        state.game = data.game;
        state.isLoading = false;
        state.hasUnsavedChanges = false;
      });
    },

    fetchProviderTypes: async () => {
      const result = await apiClient.getProviderTypes();
      if (result.data) {
        set((state) => {
          state.providerTypes = result.data!.types;
        });
      }
    },

    saveSettings: async () => {
      set((state) => {
        state.isSaving = true;
        state.error = null;
      });

      const { providers, agents } = get();

      const result = await apiClient.updateSettings({
        providers: providers.map((p) => ({
          id: p.id,
          name: p.name,
          type: p.type,
          api_key: p.api_key,
          base_url: p.base_url,
        })),
        agents: agents
          ? {
              gm: agents.gm,
              npc: agents.npc,
              rule: agents.rule,
              lore: agents.lore,
            }
          : undefined,
      });

      if (result.error) {
        set((state) => {
          state.isSaving = false;
          state.error = result.error;
        });
        return false;
      }

      const data = result.data as SettingsResponse;
      savedSnapshot = { providers: data.providers, agents: data.agents };

      set((state) => {
        state.providers = data.providers;
        state.agents = data.agents;
        state.isSaving = false;
        state.hasUnsavedChanges = false;
      });

      return true;
    },

    setProviders: (providers) => {
      set((state) => {
        state.providers = providers;
        state.hasUnsavedChanges = true;
      });
    },

    addProvider: (provider) => {
      set((state) => {
        state.providers.push(provider);
        state.hasUnsavedChanges = true;
      });
    },

    updateProvider: (id, updates) => {
      set((state) => {
        const idx = state.providers.findIndex((p) => p.id === id);
        if (idx !== -1) {
          state.providers[idx] = { ...state.providers[idx], ...updates };
          state.hasUnsavedChanges = true;
        }
      });
    },

    removeProvider: (id) => {
      const { agents } = get();
      if (agents) {
        const inUse = [agents.gm, agents.npc, agents.rule, agents.lore].some(
          (a) => a.provider_id === id,
        );
        if (inUse) {
          set((state) => {
            state.error = `Cannot delete provider "${id}": it is being used by one or more agents`;
          });
          return;
        }
      }

      set((state) => {
        state.providers = state.providers.filter((p) => p.id !== id);
        state.hasUnsavedChanges = true;
      });
    },

    updateAgentConfig: (agentName, updates) => {
      set((state) => {
        if (state.agents) {
          state.agents[agentName] = { ...state.agents[agentName], ...updates };
          state.hasUnsavedChanges = true;
        }
      });
    },

    testProviderConnection: async (providerId) => {
      set((state) => {
        state.testingProviderId = providerId;
      });

      const result = await apiClient.testProviderConnection({ provider_id: providerId });

      set((state) => {
        state.testingProviderId = null;
        if (result.data) {
          state.testResults[providerId] = {
            success: result.data.success,
            message: result.data.message,
            latency_ms: result.data.latency_ms,
          };
        } else if (result.error) {
          state.testResults[providerId] = {
            success: false,
            message: result.error,
            latency_ms: null,
          };
        }
      });
    },

    resetChanges: () => {
      if (savedSnapshot) {
        set((state) => {
          state.providers = savedSnapshot!.providers;
          state.agents = savedSnapshot!.agents;
          state.hasUnsavedChanges = false;
          state.error = null;
        });
      }
    },

    clearError: () => {
      set((state) => {
        state.error = null;
      });
    },
  })),
);
