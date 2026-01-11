import React from "react";
import { useTranslation } from "react-i18next";
import type { AgentConfig, ProviderConfig } from "../../api/types";
import { useSettingsStore } from "../../stores/settingsStore";
import Card from "../common/Card";

interface AgentConfigCardProps {
  agentType: "gm" | "npc" | "rule" | "lore";
  config: AgentConfig;
  title: string;
  description: string;
}

const AgentConfigCard: React.FC<AgentConfigCardProps> = ({
  agentType,
  config,
  title,
  description,
}) => {
  const { t } = useTranslation();
  const { providers, updateAgentConfig } = useSettingsStore();

  const handleChange = (field: keyof AgentConfig, value: string | number) => {
    updateAgentConfig(agentType, { [field]: value });
  };

  return (
    <Card className="h-full flex flex-col dark:bg-gray-800 dark:border-gray-700">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">{description}</p>
      </div>

      <div className="space-y-4 flex-1">
        <div>
          <label
            htmlFor={`provider-${agentType}`}
            className="block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300"
          >
            {t("settings.provider", "Provider")}
          </label>
          <select
            id={`provider-${agentType}`}
            value={config.provider_id}
            onChange={(e) => handleChange("provider_id", e.target.value)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2 border dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          >
            <option value="" disabled>
              {t("settings.selectProvider", "Select a provider")}
            </option>
            {providers.map((p: ProviderConfig) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.type})
              </option>
            ))}
          </select>
          {providers.length === 0 && (
            <p className="mt-1 text-xs text-red-500 dark:text-red-400">
              {t("settings.noProviders", "No providers available. Please add one first.")}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor={`model-${agentType}`}
            className="block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300"
          >
            {t("settings.model", "Model")}
          </label>
          <input
            type="text"
            id={`model-${agentType}`}
            value={config.model}
            onChange={(e) => handleChange("model", e.target.value)}
            placeholder="e.g. gpt-4o, claude-3-sonnet"
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2 border dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          />
        </div>

        <div>
          <div className="flex justify-between items-center mb-1">
            <label
              htmlFor={`temp-${agentType}`}
              className="block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              {t("settings.temperature", "Temperature")}
            </label>
            <span className="text-xs font-mono text-gray-500 dark:text-gray-400">
              {config.temperature.toFixed(1)}
            </span>
          </div>
          <input
            type="range"
            id={`temp-${agentType}`}
            min="0"
            max="2"
            step="0.1"
            value={config.temperature}
            onChange={(e) => handleChange("temperature", parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary dark:bg-gray-600"
          />
          <div className="flex justify-between text-xs text-gray-400 dark:text-gray-500 mt-1">
            <span>{t("settings.precise", "Precise")} (0.0)</span>
            <span>{t("settings.creative", "Creative")} (2.0)</span>
          </div>
        </div>

        <div>
          <label
            htmlFor={`tokens-${agentType}`}
            className="block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300"
          >
            {t("settings.maxTokens", "Max Tokens")}
          </label>
          <input
            type="number"
            id={`tokens-${agentType}`}
            value={config.max_tokens}
            onChange={(e) => handleChange("max_tokens", parseInt(e.target.value) || 0)}
            min="100"
            step="100"
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2 border dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          />
        </div>
      </div>
    </Card>
  );
};

export default AgentConfigCard;
