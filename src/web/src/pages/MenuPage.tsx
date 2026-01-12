import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Button from "../components/common/Button";
import { Card, Loading } from "../components/common/Card";
import { useGameStore } from "../stores/gameStore";

const MenuPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { loadWorldPackDetail } = useGameStore();

  const [worldPackId, setWorldPackId] = useState("demo_pack");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleContinue = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await loadWorldPackDetail(worldPackId);
      if (result) {
        navigate("/character");
      } else {
        setError(t("common.error"));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4 px-4 py-8">
      <Card title={t("menu.selectWorld")}>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              {t("menu.worldPack")}
            </label>
            <select
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              value={worldPackId}
              onChange={(e) => setWorldPackId(e.target.value)}
              disabled={loading}
            >
              <option value="demo_pack">{t("menu.darkManorDemo")}</option>
            </select>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {t("menu.demoInfo", "The Demo version only contains one world pack.")}
            </p>
          </div>

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-900/20 dark:border-red-800 dark:text-red-300">
              {error}
            </div>
          )}

          <div className="flex items-center gap-3">
            <Button
              onClick={handleContinue}
              disabled={!worldPackId.trim() || loading}
              loading={loading}
            >
              {t("menu.enterWorld")}
            </Button>
          </div>
        </div>
      </Card>

      <Card title={t("menu.instructions", "Instructions")} className="text-sm text-gray-700 dark:text-gray-300">
        <p className="mb-2">
          {t("menu.instructionText", "After selecting a world pack, you will enter the character selection screen to learn about the world background and choose your character.")}
        </p>
        <p className="text-gray-500 dark:text-gray-400">
          {t("menu.readyText", "Ready to start your adventure?")}
        </p>
      </Card>

      {loading && (
        <div className="flex justify-center">
          <Loading text={t("common.loading")} />
        </div>
      )}
    </div>
  );
};

export default MenuPage;
