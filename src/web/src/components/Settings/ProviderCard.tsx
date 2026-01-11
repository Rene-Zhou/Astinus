import React, { useMemo } from "react";
import type { ProviderConfig } from "../../api/types";
import { useSettingsStore } from "../../stores/settingsStore";
import Button from "../common/Button";
import Card from "../common/Card";

interface ProviderCardProps {
  provider: ProviderConfig;
  onEdit: (provider: ProviderConfig) => void;
  onDelete: (id: string) => void;
}

const ProviderCard: React.FC<ProviderCardProps> = ({
  provider,
  onEdit,
  onDelete,
}) => {
  const { testProviderConnection, testingProviderId, testResults } =
    useSettingsStore();

  const isTesting = testingProviderId === provider.id;
  const testResult = testResults[provider.id];

  const maskedKey = useMemo(() => {
    if (!provider.api_key) return "No API Key";
    if (provider.api_key.length <= 8) return "********";
    return `${provider.api_key.slice(0, 4)}****${provider.api_key.slice(-4)}`;
  }, [provider.api_key]);

  const handleTest = async () => {
    await testProviderConnection(provider.id);
  };

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            {provider.name}
          </h3>
          <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10">
            {provider.type}
          </span>
        </div>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEdit(provider)}
            aria-label={`Edit ${provider.name}`}
          >
            Edit
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(provider.id)}
            className="text-red-600 hover:text-red-700 hover:bg-red-50"
            aria-label={`Delete ${provider.name}`}
          >
            Delete
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-2 text-sm text-gray-600">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-500 w-16">ID:</span>
          <span className="font-mono text-gray-700">{provider.id}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-500 w-16">API Key:</span>
          <span className="font-mono text-gray-700">{maskedKey}</span>
        </div>
        {provider.base_url && (
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-500 w-16">Base URL:</span>
            <span className="font-mono text-gray-700 truncate max-w-[200px]" title={provider.base_url}>
              {provider.base_url}
            </span>
          </div>
        )}
      </div>

      <div className="mt-2 flex items-center justify-between border-t border-gray-100 pt-3">
        <div className="flex items-center gap-2">
          {testResult && !isTesting && (
            <span
              className={`text-sm ${
                testResult.success ? "text-green-600" : "text-red-600"
              }`}
            >
              {testResult.success ? (
                <>
                  ✓ Connected{" "}
                  {testResult.latency_ms !== null &&
                    `(${testResult.latency_ms}ms)`}
                </>
              ) : (
                `✗ Failed: ${testResult.message}`
              )}
            </span>
          )}
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={handleTest}
          loading={isTesting}
        >
          Test Connection
        </Button>
      </div>
    </Card>
  );
};

export default ProviderCard;
