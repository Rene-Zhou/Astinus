import React, { useEffect, useMemo } from "react";
import { createPortal } from "react-dom";
import { Link, useNavigate } from "react-router-dom";
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
  const navigate = useNavigate();

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

  // Prevent body scroll on mobile
  useEffect(() => {
    if (isMobile && sessionId) {
      document.body.style.overflow = "hidden";
      document.body.style.height = "100vh";
      document.body.style.height = "100dvh";
      return () => {
        document.body.style.overflow = "";
        document.body.style.height = "";
      };
    }
  }, [isMobile, sessionId]);

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
  const handleMenuClick = () => {
    setMobileActivePanel(mobileActivePanel === "menu" ? null : "menu");
  };

  const handleCharacterClick = () => {
    setMobileActivePanel(mobileActivePanel === "character" ? null : "character");
  };

  const handleDiceClick = () => {
    setMobileActivePanel(mobileActivePanel === "dice" ? null : "dice");
  };

  const handleNavigate = (path: string) => {
    closeMobilePanel();
    navigate(path);
  };

  // Mobile layout - rendered via Portal to bypass Layout's Header/Footer
  if (isMobile) {
    const mobileContent = (
      <div className="fixed inset-0 z-40 flex h-dvh flex-col overflow-hidden bg-gray-50">
        {/* Main Content - Full screen ChatBox */}
        <main className="flex flex-1 flex-col overflow-hidden px-2 pb-20 pt-2">
          {!player ? (
            <div className="flex h-full items-center justify-center">
              <Loading text="正在加载角色信息..." />
            </div>
          ) : (
            <div className="flex-1 overflow-hidden">
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
          onMenuClick={handleMenuClick}
          onCharacterClick={handleCharacterClick}
          onDiceClick={handleDiceClick}
          activePanel={mobileActivePanel}
          hasPendingDice={showDice}
        />

        {/* Menu Bottom Sheet */}
        <BottomSheet
          isOpen={mobileActivePanel === "menu"}
          onClose={closeMobilePanel}
          title="导航"
          maxHeight="50vh"
        >
          <nav className="flex flex-col gap-2">
            <button
              onClick={() => handleNavigate("/")}
              className="flex items-center gap-3 rounded-lg px-4 py-3 text-left text-gray-700 hover:bg-gray-100"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
              </svg>
              <span className="font-medium">菜单</span>
            </button>
            <button
              onClick={() => handleNavigate("/character")}
              className="flex items-center gap-3 rounded-lg px-4 py-3 text-left text-gray-700 hover:bg-gray-100"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
              </svg>
              <span className="font-medium">角色创建</span>
            </button>
          </nav>
        </BottomSheet>

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

    return createPortal(mobileContent, document.body);
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
