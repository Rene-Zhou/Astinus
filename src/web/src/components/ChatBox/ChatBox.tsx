import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useTranslation } from "react-i18next";
import type { Message } from "../../api/types";
import type { MobilePanelType } from "../../stores/uiStore";
import Button from "../common/Button";

export interface MobileToolbarActions {
  onMenuClick: () => void;
  onCharacterClick: () => void;
  onDiceClick: () => void;
  activePanel: MobilePanelType;
  hasPendingDice: boolean;
}

export interface ChatBoxProps {
  messages: Message[];
  onSendMessage: (content: string) => void;
  isStreaming: boolean;
  streamingContent: string;
  disabled: boolean;
  /** Mobile mode: compact input with integrated toolbar */
  isMobile?: boolean;
  /** Mobile toolbar actions (required when isMobile is true) */
  mobileToolbar?: MobileToolbarActions;
}

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
}

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  isMobile?: boolean;
  mobileToolbar?: MobileToolbarActions;
}

const roleColor: Record<Message["role"], string> = {
  user: "text-primary dark:text-primary-400",
  assistant: "text-amber-700 dark:text-amber-500",
};

function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const { t } = useTranslation();
  
  const roleLabel: Record<Message["role"], string> = {
    user: t("game.player", "Player"),
    assistant: "GM",
  };

  return (
    <div className="space-y-1">
      <div className={`text-xs font-semibold ${roleColor[message.role]}`}>
        {roleLabel[message.role]}
      </div>
      <div
        className={`whitespace-pre-wrap rounded-lg border border-gray-200 bg-white/80 px-3 py-2 text-sm text-gray-900 dark:border-gray-700 dark:bg-gray-800/80 dark:text-gray-100 ${
          isStreaming ? "animate-pulse" : ""
        }`}
      >
        {message.content}
      </div>

    </div>
  );
}

function ChatInput({ onSend, disabled = false, isMobile = false, mobileToolbar }: ChatInputProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [, setHistoryIndex] = useState<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const send = useCallback(() => {
    const content = value.trim();
    if (!content) return;
    onSend(content);
    setHistory((prev) => [...prev, content]);
    setHistoryIndex(null);
    setValue("");
    textareaRef.current?.focus();
  }, [onSend, value]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (!disabled) send();
      } else if (e.key === "ArrowUp" && history.length > 0) {
        e.preventDefault();
        setHistoryIndex((idx) => {
          const next = idx === null ? history.length - 1 : Math.max(0, idx - 1);
          setValue(history[next] ?? "");
          return next;
        });
      } else if (e.key === "ArrowDown" && history.length > 0) {
        e.preventDefault();
        setHistoryIndex((idx) => {
          if (idx === null) return null;
          const next = idx + 1;
          if (next >= history.length) {
            setValue("");
            return null;
          }
          setValue(history[next] ?? "");
          return next;
        });
      }
    },
    [disabled, history, send],
  );

  // Mobile compact layout with integrated toolbar
  if (isMobile && mobileToolbar) {
    const { onMenuClick, onCharacterClick, onDiceClick, activePanel, hasPendingDice } = mobileToolbar;
    
    const toolbarBtnClass = (panel: MobilePanelType) =>
      [
        "flex items-center justify-center rounded-lg p-2 transition-colors",
        activePanel === panel
          ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400"
          : "text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700",
      ].join(" ");

    return (
      <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-gray-200 bg-white/95 px-2 py-2 backdrop-blur-sm dark:border-gray-700 dark:bg-gray-800/95">
        <div className="flex items-center gap-1">
          {/* Toolbar buttons */}
          <button onClick={onMenuClick} className={toolbarBtnClass("menu")} aria-label={t("nav.menu")}>
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
          <button onClick={onCharacterClick} className={toolbarBtnClass("character")} aria-label={t("nav.character")}>
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
            </svg>
          </button>
          <button onClick={onDiceClick} className={`relative ${toolbarBtnClass("dice")}`} aria-label={t("dice.roll")}>
            {hasPendingDice && (
              <span className="absolute right-1 top-1 h-2 w-2 animate-pulse rounded-full bg-red-500" />
            )}
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
            </svg>
          </button>

          {/* Input field */}
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            className="min-h-[36px] flex-1 resize-none rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            placeholder={t("game.inputPlaceholder")}
            disabled={disabled}
          />

          {/* Send button */}
          <button
            onClick={send}
            disabled={disabled || !value.trim()}
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-white transition-colors hover:bg-primary/90 disabled:opacity-50 dark:bg-primary"
            aria-label={t("game.send")}
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </div>
      </div>
    );
  }

  // Desktop layout (unchanged)
  return (
    <div className="space-y-2 rounded-lg border border-gray-200 bg-white/70 p-3 shadow-sm dark:border-gray-700 dark:bg-gray-800/70">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={3}
        className="w-full resize-none rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
        placeholder={t("game.inputPlaceholder")}
        disabled={disabled}
      />
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Enter {t("game.send")} · Shift+Enter {t("game.newLine")} · ↑↓ {t("game.history")}
        </p>
        <Button size="sm" onClick={send} disabled={disabled} loading={false}>
          {t("game.send")}
        </Button>
      </div>
    </div>
  );
}

export function ChatBox({
  messages,
  onSendMessage,
  isStreaming,
  streamingContent,
  disabled,
  isMobile = false,
  mobileToolbar,
}: ChatBoxProps) {
  const { t } = useTranslation();
  const containerRef = useRef<HTMLDivElement | null>(null);

  const combinedMessages = useMemo(() => {
    if (!streamingContent) return messages;
    const lastTurn = messages.at(-1)?.turn ?? 0;
    const tempMessage: Message = {
      role: "assistant",
      content: streamingContent,
      timestamp: new Date().toISOString(),
      turn: lastTurn,
      metadata: { phase: messages.at(-1)?.metadata?.phase },
    };
    return [...messages, tempMessage];
  }, [messages, streamingContent]);

  useEffect(() => {
    if (!containerRef.current) return;
    containerRef.current.scrollTop = containerRef.current.scrollHeight;
  }, [combinedMessages]);

  return (
    <div className="flex h-full flex-col gap-2">
      <div
        ref={containerRef}
        className="flex-1 space-y-3 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-900"
      >
        {combinedMessages.length === 0 ? (
          <div className="text-center text-sm text-gray-500 dark:text-gray-400">
            {t("game.startPrompt")}
          </div>
        ) : (
          combinedMessages.map((msg, idx) => (
            <ChatMessage
              key={`${msg.timestamp}-${idx}`}
              message={msg}
              isStreaming={
                isStreaming &&
                idx === combinedMessages.length - 1 &&
                !!streamingContent
              }
            />
          ))
        )}
      </div>

      {/* Mobile: ChatInput is fixed to bottom; Desktop: inline */}
      {!isMobile && (
        <ChatInput onSend={onSendMessage} disabled={disabled || isStreaming} />
      )}
      {isMobile && (
        <ChatInput
          onSend={onSendMessage}
          disabled={disabled || isStreaming}
          isMobile
          mobileToolbar={mobileToolbar}
        />
      )}
    </div>
  );
}

export default ChatBox;
