import React, { useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import ChatBox from "../components/ChatBox/ChatBox";
import StatBlock from "../components/StatBlock/StatBlock";
import DiceRoller from "../components/DiceRoller/DiceRoller";
import Button from "../components/common/Button";
import { Card, Loading } from "../components/common/Card";
import { useGameStore } from "../stores/gameStore";
import { useUIStore } from "../stores/uiStore";
import { useGameActions } from "../hooks/useGameActions";

const GamePage: React.FC = () => {
  const {
    sessionId,
    player,
    currentLocation,
    currentPhase,
    turnCount,
    messages,
    streamingContent,
    isStreaming,
    pendingDiceCheck,
    submitDiceResult,
    sendPlayerInput,
    setPendingDiceCheck,
    addMessage,
  } = useGameStore();

  const { language } = useUIStore();
  const { refreshState, fetchMessages } = useGameActions();

  useEffect(() => {
    if (!sessionId) return;
    void refreshState();
    void fetchMessages();
  }, [sessionId, refreshState, fetchMessages]);

  const fatePoints = player?.fate_points ?? 0;
  const tags = player?.tags ?? [];
  const concept = player?.concept ?? { cn: "", en: "" };
  const playerName = player?.name ?? "";

  const showDice = Boolean(pendingDiceCheck);

  const handleSend = (content: string) => {
    addMessage({
      role: "user",
      content,
      timestamp: new Date().toISOString(),
      turn: turnCount,
      metadata: { phase: currentPhase },
    });
    sendPlayerInput(content, language);
  };

  const handleDiceRoll = (result: Parameters<typeof submitDiceResult>[0]) => {
    submitDiceResult(result);
  };

  const handleDiceCancel = () => setPendingDiceCheck(null);

  const headerStatus = useMemo(() => {
    if (!sessionId) return "未连接";
    if (isStreaming) return "处理中…";
    return "就绪";
  }, [sessionId, isStreaming]);

  if (!sessionId) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <Card title="尚未开始游戏">
          <p className="text-sm text-gray-700">
            请先在菜单页创建新会话，然后返回此处继续游戏。
          </p>
          <div className="mt-4">
            <Link to="/">
              <Button variant="primary">返回菜单</Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <span className="rounded-full bg-green-100 px-2 py-1 text-green-700">
            {headerStatus}
          </span>
          <span className="text-gray-500">Session: {sessionId}</span>
        </div>
        <Link to="/">
          <Button variant="ghost" size="sm">
            返回菜单
          </Button>
        </Link>
      </div>

      {!player ? (
        <div className="flex justify-center py-8">
          <Loading text="正在加载角色信息..." />
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <StatBlock
            playerName={playerName}
            concept={concept}
            location={currentLocation}
            phase={currentPhase}
            turnCount={turnCount}
            fatePoints={fatePoints}
            tags={tags}
            language={language}
            className="lg:col-span-1"
          />
          <div className="lg:col-span-2 h-[70vh]">
            <ChatBox
              messages={messages}
              onSendMessage={handleSend}
              isStreaming={isStreaming}
              streamingContent={streamingContent}
              disabled={showDice}
            />
          </div>
        </div>
      )}

      <DiceRoller
        visible={showDice}
        checkRequest={pendingDiceCheck}
        onRoll={handleDiceRoll}
        onCancel={handleDiceCancel}
      />
    </div>
  );
};

export default GamePage;
