import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useGameActions } from "../hooks/useGameActions";
import Button from "../components/common/Button";
import { Card, Loading } from "../components/common/Card";

const MenuPage: React.FC = () => {
  const navigate = useNavigate();
  const { createNewGame, loading, error } = useGameActions();

  const [worldPackId, setWorldPackId] = useState("demo_pack");
  const [playerName, setPlayerName] = useState("玩家");

  const isSubmitDisabled = useMemo(
    () => !worldPackId.trim() || !playerName.trim() || loading,
    [worldPackId, playerName, loading],
  );

  const handleStart = async () => {
    await createNewGame({ worldPackId, playerName });
    navigate("/game");
  };

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4 px-4 py-8">
      <Card title="开始新的冒险">
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              世界包 ID
            </label>
            <input
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="demo_pack"
              value={worldPackId}
              onChange={(e) => setWorldPackId(e.target.value)}
              disabled={loading}
            />
            <p className="text-xs text-gray-500">
              参考 docs/WEB_FRONTEND_PLAN.md 中的世界包配置。
            </p>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              玩家名称
            </label>
            <input
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="玩家"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              disabled={loading}
            />
          </div>

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex items-center gap-3">
            <Button onClick={handleStart} disabled={isSubmitDisabled} loading={loading}>
              开始游戏
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setWorldPackId("demo_pack");
                setPlayerName("玩家");
              }}
              disabled={loading}
            >
              重置
            </Button>
          </div>
        </div>
      </Card>

      <Card title="说明" className="text-sm text-gray-700">
        <p className="mb-2">
          按照 docs/WEB_FRONTEND_PLAN.md：创建新游戏后会自动连接 WebSocket，进入 Game 页面继续交互。
        </p>
        <p className="mb-1">前端契约：见 docs/API_TYPES.ts 与后端 /api/v1/game/* 端点。</p>
        <p className="text-gray-500">
          本页面为最简占位实现，可在后续阶段补充世界包选择、角色预设与最近会话列表。
        </p>
      </Card>

      {loading && (
        <div className="flex justify-center">
          <Loading text="正在创建会话..." />
        </div>
      )}
    </div>
  );
};

export default MenuPage;
