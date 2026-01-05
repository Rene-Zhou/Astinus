import React, { useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import ChatBox from "../components/ChatBox/ChatBox";
import StatBlock from "../components/StatBlock/StatBlock";
import DiceRoller from "../components/DiceRoller/DiceRoller";
import Button from "../components/common/Button";
import { Card, Loading } from "../components/common/Card";
import { CollapsiblePanel } from "../components/common/CollapsiblePanel";
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

  const {
    language,
    mobileStatBlockOpen,
    mobileDiceRollerOpen,
    setMobileDiceRollerOpen,
    toggleMobileStatBlock,
    toggleMobileDiceRoller,
  } = useUIStore();
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

  // Auto-expand dice roller panel when there's a pending dice check on mobile
  useEffect(() => {
    if (pendingDiceCheck && isMobile) {
      setMobileDiceRollerOpen(true);
    }
  }, [pendingDiceCheck, isMobile, setMobileDiceRollerOpen]);

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

  // Calculate height: use dynamic viewport height for mobile browser support
  // Fallback to calc() for browsers without dvh support
  return (
    <div className="flex h-screen-dynamic flex-col overflow-hidden" style={{ height: "calc(100vh - 106px)" }}>
      {/* Status Bar */}
      <div className="flex-shrink-0 border-b border-gray-200 bg-white px-4 py-2">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div className="flex items-center gap-3 text-sm text-gray-600">
            <span className="rounded-full bg-green-100 px-2 py-1 text-green-700">
              {headerStatus}
            </span>
            <span className="hidden text-gray-500 sm:inline">
              Session: {sessionId}
            </span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {!player ? (
          <div className="flex h-full items-center justify-center">
            <Loading text="正在加载角色信息..." />
          </div>
        ) : isMobile ? (
          /* Mobile Layout - Collapsible panels */
          <div className="flex h-full flex-col gap-2 p-2">
            {/* StatBlock - Collapsible */}
            <CollapsiblePanel
              title="角色状态"
              isOpen={mobileStatBlockOpen}
              onToggle={toggleMobileStatBlock}
              icon={
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              }
            >
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
            </CollapsiblePanel>

            {/* ChatBox - Main area */}
            <div className="min-h-0 flex-1 overflow-hidden">
              <ChatBox
                messages={messages}
                onSendMessage={handleSend}
                isStreaming={isStreaming}
                streamingContent={streamingContent}
                disabled={showDice}
              />
            </div>

            {/* DiceRoller - Collapsible */}
            <CollapsiblePanel
              title="骰子检定"
              isOpen={mobileDiceRollerOpen}
              onToggle={toggleMobileDiceRoller}
              icon={
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
              }
              badge={
                pendingDiceCheck ? (
                  <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
                ) : undefined
              }
            >
              <DiceRoller
                visible={true}
                checkRequest={pendingDiceCheck}
                onRoll={handleDiceRoll}
                onCancel={handleDiceCancel}
              />
            </CollapsiblePanel>
          </div>
        ) : (
          /* Desktop Layout - Three columns */
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

            {/* Right Column - DiceRoller */}
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
