import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ProviderConfig, ProviderType } from "../../api/types";
import { useSettingsStore } from "../../stores/settingsStore";
import Button from "../common/Button";
import { Modal } from "../common/Card";

interface ProviderEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialProvider: ProviderConfig | null;
  onSave: (provider: ProviderConfig) => void;
}

const FALLBACK_PROVIDER_TYPES = [
  { type: "openai", name: "OpenAI" },
  { type: "anthropic", name: "Anthropic" },
  { type: "google", name: "Google AI" },
  { type: "ollama", name: "Ollama (Local)" },
];

const ProviderEditModal: React.FC<ProviderEditModalProps> = ({
  isOpen,
  onClose,
  initialProvider,
  onSave,
}) => {
  const { t } = useTranslation();
  const { providerTypes } = useSettingsStore();
  const [formData, setFormData] = useState<ProviderConfig>({
    id: "",
    name: "",
    type: "openai",
    api_key: "",
    base_url: null,
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      const timer = setTimeout(() => {
        if (initialProvider) {
          setFormData({ ...initialProvider });
        } else {
          setFormData({
            id: "",
            name: "",
            type: "openai",
            api_key: "",
            base_url: null,
          });
        }
        setError(null);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [isOpen, initialProvider]);

  const handleChange = (field: keyof ProviderConfig, value: string | null) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (field === "id") setError(null);
  };

  const validateId = (id: string) => {
    const regex = /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/;
    return regex.test(id);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.id.trim()) {
      setError(t("settings.errorProviderId", "Provider ID is required"));
      return;
    }

    if (!validateId(formData.id)) {
      setError(
        t("settings.errorProviderIdFormat", "ID must consist of lowercase alphanumeric characters or hyphens, and cannot start or end with a hyphen.")
      );
      return;
    }

    if (!formData.name.trim()) {
      setError(t("settings.errorDisplayName", "Display Name is required"));
      return;
    }

    onSave(formData);
    onClose();
  };

  const selectedTypeInfo = providerTypes.find((t) => t.type === formData.type);
  const requiresApiKey = selectedTypeInfo?.requires_api_key ?? true;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={initialProvider ? t("settings.editProvider", "Edit Provider") : t("settings.addProvider", "Add Provider")}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button onClick={handleSubmit} type="submit">
            {t("common.save", "Save")}
          </Button>
        </div>
      }
    >
      <form id="provider-form" onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="provider-id"
            className="block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300"
          >
            {t("settings.providerId", "Provider ID")}
          </label>
          <input
            type="text"
            id="provider-id"
            value={formData.id}
            onChange={(e) => handleChange("id", e.target.value)}
            disabled={!!initialProvider}
            placeholder="e.g. openai-main"
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2 border disabled:bg-gray-100 disabled:text-gray-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:disabled:bg-gray-800 dark:disabled:text-gray-500"
          />
          {error && <p className="mt-1 text-sm text-red-600 dark:text-red-400">{error}</p>}
          {!initialProvider && (
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {t("settings.idHint", "Unique ID for internal reference. Lowercase letters, numbers, and hyphens only.")}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="provider-name"
            className="block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300"
          >
            {t("settings.displayName", "Display Name")}
          </label>
          <input
            type="text"
            id="provider-name"
            value={formData.name}
            onChange={(e) => handleChange("name", e.target.value)}
            placeholder="e.g. OpenAI (Main)"
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2 border dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          />
        </div>

        <div>
          <label
            htmlFor="provider-type"
            className="block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300"
          >
            {t("settings.type", "Type")}
          </label>
          <select
            id="provider-type"
            value={formData.type}
            onChange={(e) =>
              handleChange("type", e.target.value as ProviderType)
            }
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2 border dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          >
            {(providerTypes.length > 0 ? providerTypes : FALLBACK_PROVIDER_TYPES).map((type) => (
              <option key={type.type} value={type.type}>
                {type.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="provider-key"
            className="block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300"
          >
            {t("settings.apiKey", "API Key")} {requiresApiKey && <span className="text-red-500">*</span>}
          </label>
          <input
            type="password"
            id="provider-key"
            value={formData.api_key}
            onChange={(e) => handleChange("api_key", e.target.value)}
            placeholder={requiresApiKey ? t("settings.enterApiKey", "Enter API Key") : t("settings.optional", "Optional")}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2 border dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          />
        </div>

        <div>
          <label
            htmlFor="provider-url"
            className="block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300"
          >
            {t("settings.baseUrl", "Base URL")} <span className="text-gray-400 font-normal">({t("settings.optional", "Optional")})</span>
          </label>
          <input
            type="text"
            id="provider-url"
            value={formData.base_url || ""}
            onChange={(e) =>
              handleChange("base_url", e.target.value || null)
            }
            placeholder={
              selectedTypeInfo?.default_base_url || "https://api.example.com/v1"
            }
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2 border dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          />
        </div>
      </form>
    </Modal>
  );
};

export default ProviderEditModal;
