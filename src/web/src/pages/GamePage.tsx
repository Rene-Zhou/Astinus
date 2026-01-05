import React, { useEffect, useMemo, useRef } from "react";
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

  // Track if this is a fresh session start to avoid overwriting intro message
  const isNewSessionRef = useRef(false);
  const prevSessionIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      prevSessionIdRef.current = null;
      return;
    }

    // Detect if sessionId just changed (new game started)
    const isNewSession = prevSessionIdRef.current !== sessionId;
    prevSessionIdRef.current = sessionId;

    if (isNewSession) {
      // Mark as new session - don't fetch messages since startNewGame already set intro
      isNewSessionRef.current = true;
      // Only refresh state to sync with backend
      void refreshState();
    } else {
      // Reconnecting or page refresh - fetch messages only if we don't have any
      void refreshState();
      // Only fetch messages if our local messages array is empty
      // This preserves intro messages set by startNewGame
      if (messages.length === 0) {
        void fetchMessages();
      }
    }
  }, [sessionId, refreshState, fetchMessages, messages.length]);

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
    <div className="flex h-screen flex-col overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-gray-200 bg-white px-4 py-3">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-3 text-sm text-gray-600">
            <span className="rounded-full bg-green-100 px-2 py-1 text-green-700">
              {headerStatus}
            </span>
            <span className="hidden text-gray-500 sm:inline">
              Session: {sessionId}
            </span>
          </div>
          <Link to="/">
            <Button variant="ghost" size="sm">
              返回菜单
            </Button>
          </Link>
        </div>
      </header>

      {/* Main Content - Three Column Layout */}
      <main className="flex-1 overflow-hidden">
        {!player ? (
          <div className="flex h-full items-center justify-center">
            <Loading text="正在加载角色信息..." />
          </div>
        ) : (
          <div className="mx-auto grid h-full max-w-7xl grid-cols-1 gap-4 p-4 lg:grid-cols-4">
            {/* Left Column - StatBlock */}
            <aside className="h-full overflow-y-auto lg:col-span-1">
              <StatBlock
                playerName={playerName}
                concept={concept}
                location={currentLocation}
                phase={currentPhase}
                turnCount={turnCount}
                fatePoints={fatePoints}
                tags={tags}
                language={language}
                className="h-full"
              />
            </aside>

            {/* Center Column - ChatBox */}
            <section className="h-full min-h-[400px] overflow-hidden lg:col-span-2">
              <ChatBox
                messages={messages}
                onSendMessage={handleSend}
                isStreaming={isStreaming}
                streamingContent={streamingContent}
                disabled={showDice}
              />
            </section>

            {/* Right Column - DiceRoller (always visible) */}
            <aside className="h-full overflow-y-auto lg:col-span-1">
              <DiceRoller
                visible={true}
                checkRequest={pendingDiceCheck}
                onRoll={handleDiceRoll}
                onCancel={handleDiceCancel}
              />
            </aside>
          </div>
        )}
      </main>
    </div>
  );
};

export default GamePage;
