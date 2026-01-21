import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { useSaveStore } from "../stores/saveStore";
import { useGameStore } from "../stores/gameStore";
import Button from "../components/common/Button";
import { Loading } from "../components/common/Card";

const SavesPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const { saves, isLoading, error, fetchSaves, createSave, loadSave, deleteSave, clearError } =
    useSaveStore();
  const sessionId = useGameStore((state) => state.sessionId);

  const [slotName, setSlotName] = useState("");
  const [description, setDescription] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const [confirmDialog, setConfirmDialog] = useState<{
    type: "load" | "delete" | "overwrite";
    saveId?: number;
    saveName?: string;
  } | null>(null);

  useEffect(() => {
    fetchSaves();
  }, [fetchSaves]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => clearError(), 5000);
      return () => clearTimeout(timer);
    }
  }, [error, clearError]);

  const handleCreateSave = async () => {
    if (!slotName.trim()) return;

    setIsCreating(true);
    const result = await createSave(slotName.trim(), description.trim() || undefined);

    if (result.exists && result.existingId) {
      setConfirmDialog({
        type: "overwrite",
        saveId: result.existingId,
        saveName: slotName.trim(),
      });
    } else if (result.success) {
      setSlotName("");
      setDescription("");
    }
    setIsCreating(false);
  };

  const handleConfirmOverwrite = async () => {
    if (!confirmDialog?.saveName) return;

    setIsCreating(true);
    const result = await createSave(confirmDialog.saveName, description.trim() || undefined, true);
    if (result.success) {
      setSlotName("");
      setDescription("");
    }
    setIsCreating(false);
    setConfirmDialog(null);
  };

  const handleLoadClick = (saveId: number, saveName: string) => {
    setConfirmDialog({ type: "load", saveId, saveName });
  };

  const handleConfirmLoad = async () => {
    if (!confirmDialog?.saveId) return;

    const success = await loadSave(confirmDialog.saveId);
    setConfirmDialog(null);
    if (success) {
      navigate("/game");
    }
  };

  const handleDeleteClick = (saveId: number, saveName: string) => {
    setConfirmDialog({ type: "delete", saveId, saveName });
  };

  const handleConfirmDelete = async () => {
    if (!confirmDialog?.saveId) return;

    await deleteSave(confirmDialog.saveId);
    setConfirmDialog(null);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4 sm:p-6 lg:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t("saves.title")}</h1>
          <Button variant="secondary" size="sm" onClick={() => navigate("/game")}>
            {t("common.back")}
          </Button>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-100 dark:bg-red-900/30 border border-red-400 dark:border-red-700 rounded-lg text-red-700 dark:text-red-300">
            {error}
            <button
              onClick={clearError}
              className="ml-4 text-red-500 hover:text-red-700 dark:hover:text-red-400"
            >
              ×
            </button>
          </div>
        )}

        {sessionId ? (
          <div className="mb-8 p-6 bg-white dark:bg-gray-800 rounded-lg shadow">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {t("saves.createSave")}
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {t("saves.slotName")}
                </label>
                <input
                  type="text"
                  value={slotName}
                  onChange={(e) => setSlotName(e.target.value)}
                  placeholder={t("saves.slotNamePlaceholder")}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  maxLength={128}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {t("saves.description")}
                </label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={t("saves.descriptionPlaceholder")}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  maxLength={512}
                />
              </div>
              <Button
                onClick={handleCreateSave}
                disabled={!slotName.trim() || isCreating}
                loading={isCreating}
              >
                {t("saves.createSave")}
              </Button>
            </div>
          </div>
        ) : (
          <div className="mb-8 p-6 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-700 rounded-lg">
            <h2 className="text-lg font-semibold text-yellow-800 dark:text-yellow-200 mb-2">
              {t("saves.noActiveGame")}
            </h2>
            <p className="text-yellow-700 dark:text-yellow-300 mb-4">{t("saves.noActiveGameHint")}</p>
            <Button variant="secondary" onClick={() => navigate("/")}>
              {t("saves.goToMenu")}
            </Button>
          </div>
        )}

        <div className="mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t("saves.loadSave")}
          </h2>
        </div>

        {isLoading && saves.length === 0 ? (
          <div className="flex justify-center py-12">
            <Loading text={t("common.loading")} />
          </div>
        ) : saves.length === 0 ? (
          <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
            <p className="text-gray-500 dark:text-gray-400 text-lg mb-2">{t("saves.noSaves")}</p>
            <p className="text-gray-400 dark:text-gray-500">{t("saves.noSavesHint")}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {saves.map((save) => (
              <div
                key={save.id}
                className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 flex flex-col"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-gray-900 dark:text-white truncate">
                    {save.slot_name}
                  </h3>
                  {save.is_auto_save && (
                    <span className="ml-2 px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded">
                      {t("saves.autoSave")}
                    </span>
                  )}
                </div>

                {save.description && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2 line-clamp-2">
                    {save.description}
                  </p>
                )}

                <div className="text-sm text-gray-600 dark:text-gray-300 space-y-1 flex-1">
                  <p>
                    <span className="font-medium">{t("saves.character")}:</span> {save.character_name}
                  </p>
                  <p>
                    <span className="font-medium">{t("saves.location")}:</span> {save.current_location}
                  </p>
                  <p>
                    <span className="font-medium">{t("saves.turn")}:</span> {save.turn_count}
                  </p>
                </div>

                {save.last_message && (
                  <p className="mt-2 text-xs text-gray-400 dark:text-gray-500 italic line-clamp-2">
                    "{save.last_message}"
                  </p>
                )}

                <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                  {t("saves.lastPlayed")}: {formatDate(save.updated_at)}
                </p>

                <div className="mt-4 flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => handleLoadClick(save.id, save.slot_name)}
                    disabled={isLoading}
                  >
                    {t("saves.loadSave")}
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => handleDeleteClick(save.id, save.slot_name)}
                    disabled={isLoading}
                  >
                    {t("common.delete")}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {confirmDialog && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                {confirmDialog.type === "load" && t("saves.loadSave")}
                {confirmDialog.type === "delete" && t("saves.deleteSave")}
                {confirmDialog.type === "overwrite" && t("saves.createSave")}
              </h3>
              <p className="text-gray-600 dark:text-gray-300 mb-6">
                {confirmDialog.type === "load" && t("saves.confirmLoad")}
                {confirmDialog.type === "delete" &&
                  t("saves.confirmDelete", { name: confirmDialog.saveName })}
                {confirmDialog.type === "overwrite" &&
                  t("saves.confirmOverwrite", { name: confirmDialog.saveName })}
              </p>
              <div className="flex justify-end gap-3">
                <Button variant="secondary" onClick={() => setConfirmDialog(null)}>
                  {t("common.cancel")}
                </Button>
                <Button
                  variant={confirmDialog.type === "delete" ? "danger" : "primary"}
                  onClick={() => {
                    if (confirmDialog.type === "load") handleConfirmLoad();
                    else if (confirmDialog.type === "delete") handleConfirmDelete();
                    else if (confirmDialog.type === "overwrite") handleConfirmOverwrite();
                  }}
                  loading={isLoading}
                >
                  {t("common.confirm")}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SavesPage;
