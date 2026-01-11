import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import type { GamePhase, LocalizedString, Trait } from "../../api/types";
import { getLocalizedValue } from "../../api/types";

export interface StatBlockProps {
  playerName: string;
  characterName: string;
  concept: LocalizedString;
  location: string;
  phase: GamePhase;
  turnCount: number;
  fatePoints: number;
  traits: Trait[];
  tags: string[];
  language?: "cn" | "en";
  className?: string;
}

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
    <div className="absolute z-10 left-[5%] right-[5%] mt-2 rounded-lg border border-gray-200 bg-white p-3 shadow-lg dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{name}</h4>
        <button
          onClick={onClose}
          className="text-lg leading-none text-gray-400 hover:text-gray-600 flex-shrink-0 px-1 dark:hover:text-gray-300"
          aria-label="Close"
        >
          ×
        </button>
      </div>
      <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">{description}</p>
      <div className="mt-2 grid gap-1">
        <div className="rounded bg-green-50 px-2 py-1 dark:bg-green-900/20">
          <span className="text-xs font-medium text-green-700 dark:text-green-400">+ </span>
          <span className="text-xs text-green-600 dark:text-green-300">{positive}</span>
        </div>
        <div className="rounded bg-red-50 px-2 py-1 dark:bg-red-900/20">
          <span className="text-xs font-medium text-red-700 dark:text-red-400">- </span>
          <span className="text-xs text-red-600 dark:text-red-300">{negative}</span>
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
          ? "bg-indigo-200 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200"
          : "bg-indigo-50 text-indigo-700 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:text-indigo-300 dark:hover:bg-indigo-900/50",
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
  language: propLanguage,
  className = "",
}) => {
  const { t, i18n } = useTranslation();
  const language = (propLanguage || (i18n.language === "en" ? "en" : "cn")) as "cn" | "en";

  const conceptText = getLocalizedValue(concept, language);
  
  const phaseLabel: Record<GamePhase, string> = {
    waiting_input: t("game.status.waitingInput"),
    processing: t("game.status.processing"),
    dice_check: t("game.status.diceCheck"),
    npc_response: t("game.status.processing"),
    narrating: t("game.status.narrating"),
  };
  
  const phaseText = phaseLabel[phase];

  return (
    <div
      className={[
        "rounded-lg border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800",
        "p-4 space-y-3",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {/* Player and Character Info */}
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {t("game.player", "Player")}
          </p>
          <p className="text-sm text-gray-700 dark:text-gray-200">{playerName}</p>
          <p className="text-xs uppercase tracking-wide text-gray-500 mt-1 dark:text-gray-400">
            {t("character.name", "Character")}
          </p>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{characterName}</h2>
        </div>
        <div className="flex items-center gap-2 text-sm font-medium text-indigo-700 dark:text-indigo-400">
          <span className="rounded-md bg-indigo-50 px-3 py-1 dark:bg-indigo-900/30">
            {t("character.fatePoints")}: {fatePoints}
          </span>
        </div>
      </div>

      {/* Concept */}
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
          {t("character.concept")}
        </p>
        <p className="rounded-md bg-indigo-50 px-3 py-2 text-sm text-indigo-900 dark:bg-indigo-900/30 dark:text-indigo-200">
          {conceptText}
        </p>
      </div>

      {/* Traits */}
      <div className="space-y-2">
        <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
          {t("character.traits")}
        </p>
        {traits.length === 0 ? (
          <p className="text-xs text-gray-400 dark:text-gray-500">
            {t("common.none", "No traits")}
          </p>
        ) : (
          <TraitsList traits={traits} language={language} />
        )}
      </div>

      {/* Location and Phase */}
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {t("game.location", "Location")}
          </p>
          <p className="rounded-md bg-gray-50 px-3 py-2 text-sm text-gray-900 dark:bg-gray-700 dark:text-gray-200">
            {location || t("common.unknown", "Unknown")}
          </p>
        </div>

        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {t("game.phase", "Phase")}
          </p>
          <p className="inline-flex items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
            <span className="h-2 w-2 rounded-full bg-amber-400" aria-hidden />
            {phaseText}
          </p>
        </div>
      </div>

      {/* Turn */}
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
          {t("game.turn", "Turn")}
        </p>
        <p className="text-sm text-gray-900 dark:text-gray-200">{turnCount}</p>
      </div>

      {/* Tags */}
      <div className="space-y-2">
        <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
          {t("character.tags", "Tags")}
        </p>
        {tags.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t("common.none", "No tags")}
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700 dark:bg-gray-700 dark:text-gray-300"
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
