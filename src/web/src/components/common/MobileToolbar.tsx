import React from "react";

export type MobilePanelType = "character" | "dice" | null;

export interface MobileToolbarProps {
  onCharacterClick: () => void;
  onDiceClick: () => void;
  activePanel: MobilePanelType;
  hasPendingDice: boolean;
}

/**
 * Fixed bottom toolbar for mobile game interface.
 * Contains buttons to open character and dice panels.
 */
export const MobileToolbar: React.FC<MobileToolbarProps> = ({
  onCharacterClick,
  onDiceClick,
  activePanel,
  hasPendingDice,
}) => {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 border-t border-gray-200 bg-white/95 backdrop-blur-sm">
      <div className="flex items-center justify-around py-2">
        {/* Character Button */}
        <button
          onClick={onCharacterClick}
          className={[
            "flex flex-col items-center gap-1 rounded-lg px-6 py-2 transition-colors",
            activePanel === "character"
              ? "bg-indigo-100 text-indigo-700"
              : "text-gray-600 hover:bg-gray-100",
          ].join(" ")}
        >
          <svg
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
            />
          </svg>
          <span className="text-xs font-medium">角色</span>
        </button>

        {/* Dice Button */}
        <button
          onClick={onDiceClick}
          className={[
            "relative flex flex-col items-center gap-1 rounded-lg px-6 py-2 transition-colors",
            activePanel === "dice"
              ? "bg-indigo-100 text-indigo-700"
              : "text-gray-600 hover:bg-gray-100",
          ].join(" ")}
        >
          {/* Notification dot */}
          {hasPendingDice && (
            <span className="absolute right-4 top-1 h-2.5 w-2.5 animate-pulse rounded-full bg-red-500" />
          )}
          <svg
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9"
            />
          </svg>
          <span className="text-xs font-medium">骰子</span>
        </button>
      </div>
    </div>
  );
};

export default MobileToolbar;
