import React, { useState } from "react";
import type { GamePhase, LocalizedString, Trait } from "../../api/types";
import { getLocalizedValue } from "../../api/types";

export interface StatBlockProps {
  playerName: string; // PL (user) name
  characterName: string; // PC name
  concept: LocalizedString;
  location: string;
  phase: GamePhase;
  turnCount: number;
  fatePoints: number;
  traits: Trait[];
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

interface TraitDetailProps {
  trait: Trait;
  language: "cn" | "en";
  onClose: () => void;
}

const TraitDetail: React.FC<TraitDetailProps> = ({ trait, language, onClose }) => {
  const name = getLocalizedValue(trait.name, language);
  const description = getLocalizedValue(trait.description, language);
  const positive = getLocalizedValue(trait.positive_aspect, language);
  const negative = getLocalizedValue(trait.negative_aspect, language);

  return (
    <div className="absolute z-10 left-[10%] right-[10%] mt-2 rounded-lg border border-gray-200 bg-white p-3 shadow-lg">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-gray-900">{name}</h4>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 flex-shrink-0"
          aria-label="Close"
        >
          ×
        </button>
      </div>
      <p className="mt-1 text-xs text-gray-600">{description}</p>
      <div className="mt-2 grid gap-1">
        <div className="rounded bg-green-50 px-2 py-1">
          <span className="text-xs font-medium text-green-700">+ </span>
          <span className="text-xs text-green-600">{positive}</span>
        </div>
        <div className="rounded bg-red-50 px-2 py-1">
          <span className="text-xs font-medium text-red-700">- </span>
          <span className="text-xs text-red-600">{negative}</span>
        </div>
      </div>
    </div>
  );
};

interface TraitPillProps {
  trait: Trait;
  language: "cn" | "en";
  isOpen: boolean;
  onToggle: () => void;
}

const TraitPill: React.FC<TraitPillProps> = ({ trait, language, isOpen, onToggle }) => {
  const name = getLocalizedValue(trait.name, language);

  return (
    <button
      className={[
        "rounded-full px-2 py-0.5 text-xs font-medium transition-colors cursor-pointer",
        isOpen
          ? "bg-indigo-200 text-indigo-800"
          : "bg-indigo-50 text-indigo-700 hover:bg-indigo-100",
      ].join(" ")}
      onClick={onToggle}
      title={language === "cn" ? "点击查看详情" : "Click to see details"}
    >
      {name}
    </button>
  );
};

interface TraitsListProps {
  traits: Trait[];
  language: "cn" | "en";
}

const TraitsList: React.FC<TraitsListProps> = ({ traits, language }) => {
  const [openTraitIndex, setOpenTraitIndex] = useState<number | null>(null);

  const handleToggle = (index: number) => {
    setOpenTraitIndex(openTraitIndex === index ? null : index);
  };

  const openTrait = openTraitIndex !== null ? traits[openTraitIndex] : null;

  return (
    <div className="relative">
      <div className="flex flex-wrap gap-1">
        {traits.map((trait, idx) => (
          <TraitPill
            key={idx}
            trait={trait}
            language={language}
            isOpen={openTraitIndex === idx}
            onToggle={() => handleToggle(idx)}
          />
        ))}
      </div>
      {openTrait && (
        <TraitDetail
          trait={openTrait}
          language={language}
          onClose={() => setOpenTraitIndex(null)}
        />
      )}
    </div>
  );
};

export const StatBlock: React.FC<StatBlockProps> = ({
  playerName,
  characterName,
  concept,
  location,
  phase,
  turnCount,
  fatePoints,
  traits,
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
      {/* Player and Character Info */}
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">
            {language === "cn" ? "玩家" : "Player"}
          </p>
          <p className="text-sm text-gray-700">{playerName}</p>
          <p className="text-xs uppercase tracking-wide text-gray-500 mt-1">
            {language === "cn" ? "角色" : "Character"}
          </p>
          <h2 className="text-lg font-semibold text-gray-900">{characterName}</h2>
        </div>
        <div className="flex items-center gap-2 text-sm font-medium text-indigo-700">
          <span className="rounded-md bg-indigo-50 px-3 py-1">
            {language === "cn" ? "命运点" : "FP"}: {fatePoints}
          </span>
        </div>
      </div>

      {/* Concept */}
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-gray-500">
          {language === "cn" ? "角色概念" : "Concept"}
        </p>
        <p className="rounded-md bg-indigo-50 px-3 py-2 text-sm text-indigo-900">
          {conceptText}
        </p>
      </div>

      {/* Traits */}
      <div className="space-y-2">
        <p className="text-xs uppercase tracking-wide text-gray-500">
          {language === "cn" ? "特质" : "Traits"}
        </p>
        {traits.length === 0 ? (
          <p className="text-xs text-gray-400">
            {language === "cn" ? "暂无特质" : "No traits"}
          </p>
        ) : (
          <TraitsList traits={traits} language={language} />
        )}
      </div>

      {/* Location and Phase */}
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-gray-500">
            {language === "cn" ? "当前位置" : "Location"}
          </p>
          <p className="rounded-md bg-gray-50 px-3 py-2 text-sm text-gray-900">
            {location || (language === "cn" ? "未知" : "Unknown")}
          </p>
        </div>

        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-gray-500">
            {language === "cn" ? "阶段" : "Phase"}
          </p>
          <p className="inline-flex items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
            <span className="h-2 w-2 rounded-full bg-amber-400" aria-hidden />
            {phaseText}
          </p>
        </div>
      </div>

      {/* Turn */}
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-gray-500">
          {language === "cn" ? "回合" : "Turn"}
        </p>
        <p className="text-sm text-gray-900">{turnCount}</p>
      </div>

      {/* Tags */}
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
