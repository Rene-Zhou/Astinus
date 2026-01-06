import React, { useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import ChatBox from "../components/ChatBox/ChatBox";
import StatBlock from "../components/StatBlock/StatBlock";
import DiceRoller from "../components/DiceRoller/DiceRoller";
import Button from "../components/common/Button";
import { Card, Loading } from "../components/common/Card";
import { BottomSheet } from "../components/common/BottomSheet";
import { MobileToolbar } from "../components/common/MobileToolbar";
import { useGameStore } from "../stores/gameStore";
import { useUIStore } from "../stores/uiStore";
import { useGameActions } from "../hooks/useGameActions";
import { useIsMobile } from "../hooks/useMediaQuery";

const GamePage: React.FC = () => {
  const {
    sessionId,
    playerName,
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

  const { language, mobileActivePanel, setMobileActivePanel, closeMobilePanel } =
    useUIStore();
  const { refreshState } = useGameActions();
  const isMobile = useIsMobile();

  // Sync game state when sessionId changes
  // Note: We only call refreshState, not fetchMessages, to avoid overwriting
  // intro messages that were set by startNewGame in the store.
  // hydrateGameState in the store now preserves existing local messages.
  useEffect(() => {
    if (!sessionId) return;
    void refreshState();
  }, [sessionId, refreshState]);

  // Auto-open dice panel when there's a pending dice check on mobile
  useEffect(() => {
    if (pendingDiceCheck && isMobile) {
      setMobileActivePanel("dice");
    }
  }, [pendingDiceCheck, isMobile, setMobileActivePanel]);

  const fatePoints = player?.fate_points ?? 0;
  const tags = player?.tags ?? [];
  const traits = player?.traits ?? [];
  const concept = player?.concept ?? { cn: "", en: "" };
  const characterName = player?.name ?? "";

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

  // Mobile layout handlers
  const handleCharacterClick = () => {
    setMobileActivePanel(mobileActivePanel === "character" ? null : "character");
  };

  const handleDiceClick = () => {
    setMobileActivePanel(mobileActivePanel === "dice" ? null : "dice");
  };

  // Mobile layout
  if (isMobile) {
    return (
      <div className="flex h-[calc(100dvh-57px)] flex-col">
        {/* Status Bar - Compact for mobile */}
        <div className="flex-shrink-0 border-b border-gray-200 bg-white px-3 py-1.5">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">
              {headerStatus}
            </span>
          </div>
        </div>

        {/* Main Content - Full screen ChatBox */}
        <main className="flex-1 overflow-hidden pb-14">
          {!player ? (
            <div className="flex h-full items-center justify-center">
              <Loading text="正在加载角色信息..." />
            </div>
          ) : (
            <div className="h-full p-2">
              <ChatBox
                messages={messages}
                onSendMessage={handleSend}
                isStreaming={isStreaming}
                streamingContent={streamingContent}
                disabled={showDice}
              />
            </div>
          )}
        </main>

        {/* Mobile Toolbar */}
        <MobileToolbar
          onCharacterClick={handleCharacterClick}
          onDiceClick={handleDiceClick}
          activePanel={mobileActivePanel}
          hasPendingDice={showDice}
        />

        {/* Character Bottom Sheet */}
        <BottomSheet
          isOpen={mobileActivePanel === "character"}
          onClose={closeMobilePanel}
          title="角色状态"
          maxHeight="75vh"
        >
          {player && (
            <StatBlock
              playerName={playerName}
              characterName={characterName}
              concept={concept}
              location={currentLocation}
              phase={currentPhase}
              turnCount={turnCount}
              fatePoints={fatePoints}
              traits={traits}
              tags={tags}
              language={language}
            />
          )}
        </BottomSheet>

        {/* Dice Bottom Sheet */}
        <BottomSheet
          isOpen={mobileActivePanel === "dice"}
          onClose={closeMobilePanel}
          title="骰子检定"
          maxHeight="80vh"
        >
          <DiceRoller
            visible={true}
            checkRequest={pendingDiceCheck}
            onRoll={handleDiceRoll}
            onCancel={handleDiceCancel}
          />
        </BottomSheet>
      </div>
    );
  }

  // Desktop layout - Three Column Layout
  // Calculate height: 100vh - global header (~57px) - global footer (~49px)
  return (
    <div className="flex h-[calc(100vh-106px)] flex-col overflow-hidden">
      {/* Status Bar */}
      <div className="flex-shrink-0 border-b border-gray-200 bg-white px-4 py-2">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-3 text-sm text-gray-600">
            <span className="rounded-full bg-green-100 px-2 py-1 text-green-700">
              {headerStatus}
            </span>
            <span className="text-gray-500">Session: {sessionId}</span>
          </div>
        </div>
      </div>

      {/* Main Content - Three Column Layout */}
      <main className="flex-1 overflow-hidden">
        {!player ? (
          <div className="flex h-full items-center justify-center">
            <Loading text="正在加载角色信息..." />
          </div>
        ) : (
          <div className="mx-auto grid h-full max-w-7xl grid-cols-4 gap-4 p-4">
            {/* Left Column - StatBlock */}
            <aside className="h-full overflow-y-auto">
              <StatBlock
                playerName={playerName}
                characterName={characterName}
                concept={concept}
                location={currentLocation}
                phase={currentPhase}
                turnCount={turnCount}
                fatePoints={fatePoints}
                traits={traits}
                tags={tags}
                language={language}
                className="h-full"
              />
            </aside>

            {/* Center Column - ChatBox */}
            <section className="col-span-2 h-full min-h-[400px] overflow-hidden">
              <ChatBox
                messages={messages}
                onSendMessage={handleSend}
                isStreaming={isStreaming}
                streamingContent={streamingContent}
                disabled={showDice}
              />
            </section>

            {/* Right Column - DiceRoller (always visible) */}
            <aside className="h-full overflow-y-auto">
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
