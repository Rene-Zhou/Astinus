import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Card, Loading } from "../components/common/Card";
import Button from "../components/common/Button";
import { useGameStore } from "../stores/gameStore";
import { getLocalizedValue, type PresetCharacter, type Trait } from "../api/types";

// ============================================================================
// Shared Components
// ============================================================================

const SectionTitle: React.FC<{ title: string }> = ({ title }) => (
  <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-400">
    {title}
  </h3>
);

const Pill: React.FC<{ label: string; className?: string }> = ({ label, className = "" }) => (
  <span className={`rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700 dark:bg-gray-700 dark:text-gray-300 ${className}`}>
    {label}
  </span>
);

// ============================================================================
// Character Selection Mode (Before Game Starts)
// ============================================================================

interface CharacterCardProps {
  character: PresetCharacter;
  isSelected: boolean;
  onSelect: () => void;
  language: "cn" | "en";
}

const CharacterCard: React.FC<CharacterCardProps> = ({
  character,
  isSelected,
  onSelect,
  language,
}) => {
  const { t } = useTranslation();
  const concept = getLocalizedValue(character.concept, language);

  return (
    <div
      className={`cursor-pointer rounded-lg border-2 p-4 transition-all ${
        isSelected
          ? "border-indigo-500 bg-indigo-50 ring-2 ring-indigo-200 dark:bg-indigo-900/20 dark:ring-indigo-800"
          : "border-gray-200 bg-white hover:border-indigo-300 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-indigo-700"
      }`}
      onClick={onSelect}
    >
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{character.name}</h3>
      <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">"{concept}"</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {character.traits.map((trait, idx) => (
          <Pill
            key={idx}
            label={getLocalizedValue(trait.name, language)}
            className={isSelected ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-200" : ""}
          />
        ))}
      </div>
      <div className="mt-3">
        <Button
          variant={isSelected ? "primary" : "secondary"}
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onSelect();
          }}
        >
          {isSelected
            ? t("common.selected", "Selected")
            : t("common.select", "Select")}
        </Button>
      </div>
    </div>
  );
};

interface TraitDetailProps {
  trait: Trait;
  language: "cn" | "en";
}

const TraitDetail: React.FC<TraitDetailProps> = ({ trait, language }) => {
  const { t } = useTranslation();
  const name = getLocalizedValue(trait.name, language);
  const description = getLocalizedValue(trait.description, language);
  const positive = getLocalizedValue(trait.positive_aspect, language);
  const negative = getLocalizedValue(trait.negative_aspect, language);

  return (
    <div className="rounded-lg border border-gray-200 bg-white/70 p-3 shadow-sm dark:border-gray-700 dark:bg-gray-800/70">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{name}</h4>
      </div>
      <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">{description}</p>
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        <div className="rounded bg-green-50 px-2 py-1 dark:bg-green-900/20">
          <span className="text-xs font-medium text-green-800 dark:text-green-400">
            {t("character.positive")}: 
          </span>
          <span className="text-xs text-green-700 dark:text-green-300">{positive}</span>
        </div>
        <div className="rounded bg-red-50 px-2 py-1 dark:bg-red-900/20">
          <span className="text-xs font-medium text-red-800 dark:text-red-400">
            {t("character.negative")}: 
          </span>
          <span className="text-xs text-red-700 dark:text-red-300">{negative}</span>
        </div>
      </div>
    </div>
  );
};

const CharacterSelectionMode: React.FC = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const language = (i18n.language === "en" ? "en" : "cn") as "cn" | "en";
  
  const {
    worldInfo,
    presetCharacters,
    playerName,
    setPlayerName,
    selectedWorldPackId,
    startNewGame,
  } = useGameStore();

  const [selectedCharacterId, setSelectedCharacterId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-select first character if none selected
  useEffect(() => {
    if (presetCharacters.length > 0 && !selectedCharacterId) {
      setSelectedCharacterId(presetCharacters[0].id);
    }
  }, [presetCharacters, selectedCharacterId]);

  const selectedCharacter = presetCharacters.find((c) => c.id === selectedCharacterId);

  const handleStartGame = async () => {
    if (!selectedCharacterId) {
      setError(t("character.selectError", "Please select a character"));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await startNewGame({
        worldPackId: selectedWorldPackId,
        playerName,
        presetCharacterId: selectedCharacterId,
      });
      navigate("/game");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start game");
    } finally {
      setLoading(false);
    }
  };

  // If no world info, redirect to menu
  if (!worldInfo) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <Card title={t("character.selectWorldFirst", "Please select a world")}>
          <p className="text-sm text-gray-700 dark:text-gray-300">
            {t("character.selectWorldPrompt", "Please select a world pack from the menu first, then return here to select a character.")}
          </p>
          <div className="mt-4">
            <Link to="/">
              <Button variant="primary">
                {t("nav.menu")}
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 px-4 py-8">
      {/* World Introduction */}
      <Card>
        <div className="space-y-3">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            【{getLocalizedValue(worldInfo.name, language)}】
          </h1>

          {worldInfo.setting && (
            <div className="grid gap-2 sm:grid-cols-3">
              <div className="rounded bg-gray-50 px-3 py-2 dark:bg-gray-700">
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {t("world.era", "Era")}
                </span>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {getLocalizedValue(worldInfo.setting.era, language)}
                </p>
              </div>
              <div className="rounded bg-gray-50 px-3 py-2 dark:bg-gray-700">
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {t("world.genre", "Genre")}
                </span>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {getLocalizedValue(worldInfo.setting.genre, language)}
                </p>
              </div>
              <div className="rounded bg-gray-50 px-3 py-2 dark:bg-gray-700">
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {t("world.tone", "Tone")}
                </span>
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  {getLocalizedValue(worldInfo.setting.tone, language)}
                </p>
              </div>
            </div>
          )}

          {worldInfo.player_hook && (
            <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-4 dark:bg-indigo-900/20 dark:border-indigo-800">
              <p className="text-sm italic text-indigo-900 dark:text-indigo-200">
                {getLocalizedValue(worldInfo.player_hook, language)}
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Player Name Input */}
      <Card title={t("character.yourName", "Your Name")}>
        <div className="space-y-2">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {t("character.nameHint", "This is your name as a player, distinct from your character's name.")}
          </p>
          <input
            type="text"
            className="w-full max-w-md rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
            placeholder={t("character.enterName", "Enter your name")}
            disabled={loading}
          />
        </div>
      </Card>

      {/* Character Selection */}
      <Card title={t("character.selectCharacter", "Select Your Character")}>
        {presetCharacters.length === 0 ? (
          <div className="flex justify-center py-8">
            <Loading text={t("common.loading")} />
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {presetCharacters.map((character) => (
              <CharacterCard
                key={character.id}
                character={character}
                isSelected={selectedCharacterId === character.id}
                onSelect={() => setSelectedCharacterId(character.id)}
                language={language}
              />
            ))}
          </div>
        )}
      </Card>

      {/* Selected Character Details */}
      {selectedCharacter && (
        <Card title={t("character.traits")}>
          <div className="space-y-3">
            {selectedCharacter.traits.map((trait, idx) => (
              <TraitDetail key={idx} trait={trait} language={language} />
            ))}
          </div>
        </Card>
      )}

      {/* Error Message */}
      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-900/20 dark:border-red-800 dark:text-red-300">
          {error}
        </div>
      )}

      {/* Start Game Button */}
      <div className="flex justify-center pt-4">
        <Button
          onClick={handleStartGame}
          disabled={!selectedCharacterId || !playerName.trim() || loading}
          loading={loading}
          size="lg"
        >
          {t("character.startAdventure", "Start Adventure")}
        </Button>
      </div>

      {loading && (
        <div className="flex justify-center">
          <Loading text={t("character.creatingGame", "Creating game...")} />
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Character View Mode (During Game)
// ============================================================================

const CharacterViewMode: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { player, playerName } = useGameStore();
  const language = (i18n.language === "en" ? "en" : "cn") as "cn" | "en";

  if (!player) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <Card title={t("character.noInfo", "No character info")}>
          <p className="text-sm text-gray-700 dark:text-gray-300">
            {t("character.createSessionFirst", "Please create a new session from the menu first, then return here to view character details.")}
          </p>
          <div className="mt-4 flex gap-3">
            <Link to="/">
              <Button variant="primary">
                {t("nav.menu")}
              </Button>
            </Link>
            <Link to="/game">
              <Button variant="secondary">
                {t("nav.game")}
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 px-4 py-8">
      <Card>
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                {t("game.player")}
              </p>
              <h2 className="text-lg font-medium text-gray-700 dark:text-gray-200">{playerName}</h2>
              <p className="text-xs uppercase tracking-wide text-gray-500 mt-2 dark:text-gray-400">
                {t("character.name")}
              </p>
              <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                {player.name}
              </h1>
            </div>
            <Pill
              label={`${t("character.fatePoints")}: ${player.fate_points}`}
              className="bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <SectionTitle title={t("character.concept")} />
              <p className="rounded-md bg-indigo-50 px-3 py-2 text-sm text-indigo-900 dark:bg-indigo-900/30 dark:text-indigo-200">
                {getLocalizedValue(player.concept, language)}
              </p>
            </div>
            <div className="space-y-1">
              <SectionTitle title={t("character.tags")} />
              {player.tags.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {t("common.none", "No tags")}
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {player.tags.map((tag) => (
                    <Pill key={tag} label={tag} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </Card>

      <Card title={t("character.traits")}>
        {player.traits.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t("common.none", "No traits")}
          </p>
        ) : (
          <div className="space-y-3">
            {player.traits.map((trait, idx) => (
              <TraitDetail key={idx} trait={trait} language={language} />
            ))}
          </div>
        )}
      </Card>

      <div className="flex justify-center gap-3 pt-4">
        <Link to="/game">
          <Button variant="primary">
            {t("character.backToGame", "Back to Game")}
          </Button>
        </Link>
      </div>
    </div>
  );
};

// ============================================================================
// Main CharacterPage Component
// ============================================================================

const CharacterPage: React.FC = () => {
  const { sessionId } = useGameStore();

  // If we have a session, show view mode; otherwise show selection mode
  if (sessionId) {
    return <CharacterViewMode />;
  }

  return <CharacterSelectionMode />;
};

const CharacterPage: React.FC = () => {
  const { sessionId } = useGameStore();

  if (sessionId) {
    return <CharacterViewMode />;
  }

  return <CharacterSelectionMode />;
};

export const NotFoundPage: React.FC = () => {
  const { t } = useTranslation();
  return (
    <div className="mx-auto max-w-4xl px-4 py-12 text-center">
      <h1 className="text-3xl font-semibold text-gray-900 dark:text-gray-100">404</h1>
      <p className="mt-2 text-gray-600 dark:text-gray-400">{t("common.pageNotFound", "Page Not Found")}</p>
      <div className="mt-6 flex justify-center gap-3">
        <Link to="/">
          <Button variant="primary">{t("nav.menu")}</Button>
        </Link>
        <Link to="/game">
          <Button variant="secondary">{t("nav.game")}</Button>
        </Link>
      </div>
    </div>
  );
};

export default CharacterPage;

