import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../components/common/Button";
import { Card, Loading } from "../components/common/Card";
import { useGameStore } from "../stores/gameStore";

const MenuPage: React.FC = () => {
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
        setError("Failed to load world pack details");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4 px-4 py-8">
      <Card title="选择世界">
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              世界包
            </label>
            <select
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
              value={worldPackId}
              onChange={(e) => setWorldPackId(e.target.value)}
              disabled={loading}
            >
              <option value="demo_pack">幽暗庄园 (Demo)</option>
            </select>
            <p className="text-xs text-gray-500">
              Demo 版本仅包含一个世界包。
            </p>
          </div>

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex items-center gap-3">
            <Button
              onClick={handleContinue}
              disabled={!worldPackId.trim() || loading}
              loading={loading}
            >
              进入世界
            </Button>
          </div>
        </div>
      </Card>

      <Card title="说明" className="text-sm text-gray-700">
        <p className="mb-2">
          选择一个世界包后，你将进入角色选择界面，了解世界背景并选择你的角色。
        </p>
        <p className="text-gray-500">
          准备好开始你的冒险了吗？
        </p>
      </Card>

      {loading && (
        <div className="flex justify-center">
          <Loading text="加载世界包..." />
        </div>
      )}
    </div>
  );
};

export default MenuPage;
