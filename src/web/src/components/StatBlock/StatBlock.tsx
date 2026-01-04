import React from "react";
import type { GamePhase, LocalizedString } from "../../api/types";
import { getLocalizedValue } from "../../api/types";

export interface StatBlockProps {
  playerName: string;
  concept: LocalizedString;
  location: string;
  phase: GamePhase;
  turnCount: number;
  fatePoints: number;
  tags: string[];
  language: "cn" | "en";
  className?: string;
}

const phaseLabel: Record<GamePhase, { cn: string; en: string }> = {
  waiting_input: { cn: "等待输入", en: "Waiting Input" },
  processing: { cn: "处理行动", en: "Processing" },
  dice_check: { cn: "骰子检定", en: "Dice Check" },
  npc_response: { cn: "NPC 回应", en: "NPC Response" },
  narrating: { cn: "叙述中", en: "Narrating" },
};

export const StatBlock: React.FC<StatBlockProps> = ({
  playerName,
  concept,
  location,
  phase,
  turnCount,
  fatePoints,
  tags,
  language,
  className = "",
}) => {
  const conceptText = getLocalizedValue(concept, language);
  const phaseText = getLocalizedValue(phaseLabel[phase], language);

  return (
    <div
      className={[
        "rounded-lg border border-gray-200 bg-white shadow-sm",
        "p-4 space-y-3",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">
            {language === "cn" ? "玩家" : "Player"}
          </p>
          <h2 className="text-lg font-semibold text-gray-900">{playerName}</h2>
        </div>
        <div className="flex items-center gap-2 text-sm font-medium text-indigo-700">
          <span className="rounded-md bg-indigo-50 px-3 py-1">
            {language === "cn" ? "命运点" : "Fate Points"}: {fatePoints}
          </span>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-gray-500">
            {language === "cn" ? "角色概念" : "Concept"}
          </p>
          <p className="rounded-md bg-indigo-50 px-3 py-2 text-sm text-indigo-900">
            {conceptText}
          </p>
        </div>

        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-gray-500">
            {language === "cn" ? "当前位置" : "Location"}
          </p>
          <p className="rounded-md bg-gray-50 px-3 py-2 text-sm text-gray-900">
            {location || (language === "cn" ? "未知" : "Unknown")}
          </p>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-gray-500">
            {language === "cn" ? "阶段" : "Phase"}
          </p>
          <p className="inline-flex items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
            <span className="h-2 w-2 rounded-full bg-amber-400" aria-hidden />
            {phaseText}
          </p>
        </div>

        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-gray-500">
            {language === "cn" ? "回合" : "Turn"}
          </p>
          <p className="rounded-md bg-gray-50 px-3 py-2 text-sm text-gray-900">
            {turnCount}
          </p>
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-xs uppercase tracking-wide text-gray-500">
          {language === "cn" ? "状态标签" : "Tags"}
        </p>
        {tags.length === 0 ? (
          <p className="text-sm text-gray-500">
            {language === "cn" ? "暂无标签" : "No tags"}
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default StatBlock;
