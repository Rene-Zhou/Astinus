import React, { useEffect, useState } from "react";
import type { ProviderConfig } from "../api/types";
import { useSettingsStore } from "../stores/settingsStore";
import Button from "../components/common/Button";
import { Loading } from "../components/common/Card";
import AgentConfigCard from "../components/Settings/AgentConfigCard";
import ProviderCard from "../components/Settings/ProviderCard";
import ProviderEditModal from "../components/Settings/ProviderEditModal";

const SettingsPage: React.FC = () => {
  const {
    providers,
    agents,
    isLoading,
    isSaving,
    error,
    hasUnsavedChanges,
    fetchSettings,
    fetchProviderTypes,
    saveSettings,
    addProvider,
    updateProvider,
    removeProvider,
    resetChanges,
    clearError,
  } = useSettingsStore();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<ProviderConfig | null>(
    null
  );

  useEffect(() => {
    fetchSettings();
    fetchProviderTypes();
  }, [fetchSettings, fetchProviderTypes]);

  const handleAddProvider = () => {
    setEditingProvider(null);
    setIsModalOpen(true);
  };

  const handleEditProvider = (provider: ProviderConfig) => {
    setEditingProvider(provider);
    setIsModalOpen(true);
  };

  const handleSaveProvider = (provider: ProviderConfig) => {
    if (editingProvider) {
      updateProvider(provider.id, provider);
    } else {
      addProvider(provider);
    }
  };

  const handleDeleteClick = (id: string) => {
    if (window.confirm(`Are you sure you want to delete provider "${id}"?`)) {
      removeProvider(id);
    }
  };

  if (isLoading && !providers.length) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loading text="Loading settings..." size="lg" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="mt-1 text-sm text-gray-500">
            Configure AI providers and agent behaviors
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="ghost"
            onClick={resetChanges}
            disabled={!hasUnsavedChanges || isSaving}
          >
            Reset
          </Button>
          <Button
            onClick={() => saveSettings()}
            loading={isSaving}
            disabled={!hasUnsavedChanges || isSaving}
          >
            Save Changes
          </Button>
        </div>
      </header>

      {error && (
        <div className="mb-6 rounded-md bg-red-50 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Error saving settings
              </h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error}</p>
              </div>
              <div className="mt-4">
                <button
                  type="button"
                  onClick={clearError}
                  className="rounded-md bg-red-50 px-2 py-1.5 text-sm font-medium text-red-800 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-red-50"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-10">
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">
              AI Providers
            </h2>
            <Button onClick={handleAddProvider} size="sm">
              + Add Provider
            </Button>
          </div>

          {providers.length === 0 ? (
            <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
              <h3 className="mt-2 text-sm font-semibold text-gray-900">
                No providers
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                Get started by adding a new AI provider.
              </p>
              <div className="mt-6">
                <Button onClick={handleAddProvider} size="sm">
                  Add Provider
                </Button>
              </div>
            </div>
          ) : (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {providers.map((provider) => (
                <ProviderCard
                  key={provider.id}
                  provider={provider}
                  onEdit={handleEditProvider}
                  onDelete={handleDeleteClick}
                />
              ))}
            </div>
          )}
        </section>

        {agents && (
          <section>
            <h2 className="mb-4 text-xl font-semibold text-gray-900">
              Agent Configuration
            </h2>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-2">
              <AgentConfigCard
                agentType="gm"
                config={agents.gm}
                title="GM Agent"
                description="Core Narrative Engine. Handles story progression, scene description, and overall coordination."
              />
              <AgentConfigCard
                agentType="npc"
                config={agents.npc}
                title="NPC Agent"
                description="Roleplay Engine. Controls NPC dialogue, emotions, and interactions."
              />
              <AgentConfigCard
                agentType="rule"
                config={agents.rule}
                title="Rule Agent"
                description="Rules Judge. Handles dice checks, mechanics, and game logic."
              />
              <AgentConfigCard
                agentType="lore"
                config={agents.lore}
                title="Lore Agent"
                description="Knowledge Base. Retrieves world information and context."
              />
            </div>
          </section>
        )}
      </div>

      <ProviderEditModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        initialProvider={editingProvider}
        onSave={handleSaveProvider}
      />
    </div>
  );
};

export default SettingsPage;
