import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { Message } from "../../api/types";
import Button from "../common/Button";

export interface ChatBoxProps {
  messages: Message[];
  onSendMessage: (content: string) => void;
  isStreaming: boolean;
  streamingContent: string;
  disabled: boolean;
}

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
}

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

const roleLabel: Record<Message["role"], string> = {
  user: "玩家",
  assistant: "GM",
};

const roleColor: Record<Message["role"], string> = {
  user: "text-primary",
  assistant: "text-amber-700",
};

function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  return (
    <div className="space-y-1">
      <div className={`text-xs font-semibold ${roleColor[message.role]}`}>
        {roleLabel[message.role]} · Turn {message.turn}
      </div>
      <div
        className={`whitespace-pre-wrap rounded-lg border border-gray-200 bg-white/80 px-3 py-2 text-sm text-gray-900 ${
          isStreaming ? "animate-pulse" : ""
        }`}
      >
        {message.content}
      </div>
      {message.metadata?.phase && (
        <div className="text-[11px] text-gray-500">
          Phase: {message.metadata.phase}
        </div>
      )}
    </div>
  );
}

function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [_historyIndex, setHistoryIndex] = useState<number | null>(null);
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

  return (
    <div className="space-y-2 rounded-lg border border-gray-200 bg-white/70 p-3 shadow-sm">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={3}
        className="w-full resize-none rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
        placeholder="描述你的行动，Shift+Enter 换行"
        disabled={disabled}
      />
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500">
          Enter 发送 · Shift+Enter 换行 · ↑↓ 浏览历史
        </p>
        <Button size="sm" onClick={send} disabled={disabled} loading={false}>
          发送
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
}: ChatBoxProps) {
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
    <div className="flex h-full flex-col gap-3">
      <div
        ref={containerRef}
        className="flex-1 space-y-3 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-4"
      >
        {combinedMessages.length === 0 ? (
          <div className="text-center text-sm text-gray-500">
            暂无消息，开始你的冒险吧！
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

      <ChatInput onSend={onSendMessage} disabled={disabled || isStreaming} />
    </div>
  );
}

export default ChatBox;
