import React, { useEffect, useState } from "react";
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
      setError("Provider ID is required");
      return;
    }

    if (!validateId(formData.id)) {
      setError(
        "ID must consist of lowercase alphanumeric characters or hyphens, and cannot start or end with a hyphen."
      );
      return;
    }

    if (!formData.name.trim()) {
      setError("Display Name is required");
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
      title={initialProvider ? "Edit Provider" : "Add Provider"}
      footer={
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} type="submit">
            Save
          </Button>
        </div>
      }
    >
      <form id="provider-form" onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="provider-id"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Provider ID
          </label>
          <input
            type="text"
            id="provider-id"
            value={formData.id}
            onChange={(e) => handleChange("id", e.target.value)}
            disabled={!!initialProvider}
            placeholder="e.g. openai-main"
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2 border disabled:bg-gray-100 disabled:text-gray-500"
          />
          {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
          {!initialProvider && (
            <p className="mt-1 text-xs text-gray-500">
              Unique ID for internal reference. Lowercase letters, numbers, and
              hyphens only.
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="provider-name"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Display Name
          </label>
          <input
            type="text"
            id="provider-name"
            value={formData.name}
            onChange={(e) => handleChange("name", e.target.value)}
            placeholder="e.g. OpenAI (Main)"
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2 border"
          />
        </div>

        <div>
          <label
            htmlFor="provider-type"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Type
          </label>
          <select
            id="provider-type"
            value={formData.type}
            onChange={(e) =>
              handleChange("type", e.target.value as ProviderType)
            }
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2 border"
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
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            API Key {requiresApiKey && <span className="text-red-500">*</span>}
          </label>
          <input
            type="password"
            id="provider-key"
            value={formData.api_key}
            onChange={(e) => handleChange("api_key", e.target.value)}
            placeholder={requiresApiKey ? "Enter API Key" : "Optional"}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2 border"
          />
        </div>

        <div>
          <label
            htmlFor="provider-url"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Base URL <span className="text-gray-400 font-normal">(Optional)</span>
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
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring-primary sm:text-sm p-2 border"
          />
        </div>
      </form>
    </Modal>
  );
};

export default ProviderEditModal;
