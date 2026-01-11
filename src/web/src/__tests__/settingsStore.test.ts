import { describe, it, expect, vi, beforeEach } from "vitest";
import { useSettingsStore } from "../stores/settingsStore";

vi.mock("../api/client", () => ({
  apiClient: {
    getSettings: vi.fn(),
    getProviderTypes: vi.fn(),
    updateSettings: vi.fn(),
    testProviderConnection: vi.fn(),
  },
}));

import { apiClient } from "../api/client";

const mockApiClient = vi.mocked(apiClient);

const mockSettingsResponse = {
  providers: [
    {
      id: "test-provider",
      name: "Test Provider",
      type: "openai" as const,
      api_key: "sk-t****key",
      base_url: null,
    },
  ],
  agents: {
    gm: { provider_id: "test-provider", model: "gpt-4o", temperature: 0.7, max_tokens: 2048 },
    npc: { provider_id: "test-provider", model: "gpt-4o", temperature: 0.8, max_tokens: 1024 },
    rule: { provider_id: "test-provider", model: "gpt-4o", temperature: 0.3, max_tokens: 512 },
    lore: { provider_id: "test-provider", model: "gpt-4o", temperature: 0.5, max_tokens: 1024 },
  },
  game: {
    default_language: "cn" as const,
    dice: { use_advantage_system: true, show_roll_details: true },
  },
};

describe("settingsStore", () => {
  beforeEach(() => {
    useSettingsStore.setState({
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
    });
    vi.clearAllMocks();
  });

  describe("fetchSettings", () => {
    it("loads settings from API", async () => {
      mockApiClient.getSettings.mockResolvedValue({ data: mockSettingsResponse, error: null, status: 200 });

      await useSettingsStore.getState().fetchSettings();

      const state = useSettingsStore.getState();
      expect(state.providers).toHaveLength(1);
      expect(state.providers[0].id).toBe("test-provider");
      expect(state.agents).not.toBeNull();
      expect(state.isLoading).toBe(false);
    });

    it("handles API error", async () => {
      mockApiClient.getSettings.mockResolvedValue({ data: null, error: "Network error", status: 500 });

      await useSettingsStore.getState().fetchSettings();

      const state = useSettingsStore.getState();
      expect(state.error).toBe("Network error");
      expect(state.isLoading).toBe(false);
    });
  });

  describe("provider management", () => {
    beforeEach(async () => {
      mockApiClient.getSettings.mockResolvedValue({ data: mockSettingsResponse, error: null, status: 200 });
      await useSettingsStore.getState().fetchSettings();
    });

    it("adds a provider", () => {
      const newProvider = {
        id: "new-provider",
        name: "New Provider",
        type: "anthropic" as const,
        api_key: "sk-new",
        base_url: null,
      };

      useSettingsStore.getState().addProvider(newProvider);

      const state = useSettingsStore.getState();
      expect(state.providers).toHaveLength(2);
      expect(state.hasUnsavedChanges).toBe(true);
    });

    it("updates a provider", () => {
      useSettingsStore.getState().updateProvider("test-provider", { name: "Updated Name" });

      const state = useSettingsStore.getState();
      expect(state.providers[0].name).toBe("Updated Name");
      expect(state.hasUnsavedChanges).toBe(true);
    });

    it("removes a provider not in use", () => {
      const newProvider = {
        id: "unused-provider",
        name: "Unused",
        type: "openai" as const,
        api_key: "",
        base_url: null,
      };
      useSettingsStore.getState().addProvider(newProvider);
      useSettingsStore.getState().removeProvider("unused-provider");

      const state = useSettingsStore.getState();
      expect(state.providers).toHaveLength(1);
      expect(state.providers[0].id).toBe("test-provider");
    });

    it("prevents removing a provider in use", () => {
      useSettingsStore.getState().removeProvider("test-provider");

      const state = useSettingsStore.getState();
      expect(state.providers).toHaveLength(1);
      expect(state.error).toContain("Cannot delete provider");
    });
  });

  describe("agent config", () => {
    beforeEach(async () => {
      mockApiClient.getSettings.mockResolvedValue({ data: mockSettingsResponse, error: null, status: 200 });
      await useSettingsStore.getState().fetchSettings();
    });

    it("updates agent config", () => {
      useSettingsStore.getState().updateAgentConfig("gm", { temperature: 0.9 });

      const state = useSettingsStore.getState();
      expect(state.agents?.gm.temperature).toBe(0.9);
      expect(state.hasUnsavedChanges).toBe(true);
    });
  });

  describe("saveSettings", () => {
    beforeEach(async () => {
      mockApiClient.getSettings.mockResolvedValue({ data: mockSettingsResponse, error: null, status: 200 });
      await useSettingsStore.getState().fetchSettings();
    });

    it("saves settings to API", async () => {
      mockApiClient.updateSettings.mockResolvedValue({ data: mockSettingsResponse, error: null, status: 200 });

      useSettingsStore.getState().updateAgentConfig("gm", { temperature: 0.9 });
      const success = await useSettingsStore.getState().saveSettings();

      expect(success).toBe(true);
      expect(useSettingsStore.getState().hasUnsavedChanges).toBe(false);
      expect(mockApiClient.updateSettings).toHaveBeenCalled();
    });

    it("handles save error", async () => {
      mockApiClient.updateSettings.mockResolvedValue({ data: null, error: "Save failed", status: 500 });

      const success = await useSettingsStore.getState().saveSettings();

      expect(success).toBe(false);
      expect(useSettingsStore.getState().error).toBe("Save failed");
    });
  });

  describe("resetChanges", () => {
    it("restores original state", async () => {
      mockApiClient.getSettings.mockResolvedValue({ data: mockSettingsResponse, error: null, status: 200 });
      await useSettingsStore.getState().fetchSettings();

      useSettingsStore.getState().updateAgentConfig("gm", { temperature: 0.9 });
      expect(useSettingsStore.getState().agents?.gm.temperature).toBe(0.9);

      useSettingsStore.getState().resetChanges();

      expect(useSettingsStore.getState().agents?.gm.temperature).toBe(0.7);
      expect(useSettingsStore.getState().hasUnsavedChanges).toBe(false);
    });
  });

  describe("testProviderConnection", () => {
    it("stores test result", async () => {
      mockApiClient.testProviderConnection.mockResolvedValue({
        data: { success: true, provider_id: "test-provider", message: "OK", latency_ms: 150 },
        error: null,
        status: 200,
      });

      await useSettingsStore.getState().testProviderConnection("test-provider");

      const state = useSettingsStore.getState();
      expect(state.testResults["test-provider"]).toBeDefined();
      expect(state.testResults["test-provider"].success).toBe(true);
      expect(state.testResults["test-provider"].latency_ms).toBe(150);
    });
  });
});
