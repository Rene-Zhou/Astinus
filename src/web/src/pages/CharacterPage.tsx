import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Card, Loading } from "../components/common/Card";
import Button from "../components/common/Button";
import { useGameStore } from "../stores/gameStore";
import { useUIStore } from "../stores/uiStore";
import { getLocalizedValue, type PresetCharacter, type Trait } from "../api/types";

// ============================================================================
// Shared Components
// ============================================================================

const SectionTitle: React.FC<{ title: string }> = ({ title }) => (
  <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-600">
    {title}
  </h3>
);

const Pill: React.FC<{ label: string; className?: string }> = ({ label, className = "" }) => (
  <span className={`rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700 ${className}`}>
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
  const concept = getLocalizedValue(character.concept, language);

  return (
    <div
      className={`cursor-pointer rounded-lg border-2 p-4 transition-all ${
        isSelected
          ? "border-indigo-500 bg-indigo-50 ring-2 ring-indigo-200"
          : "border-gray-200 bg-white hover:border-indigo-300"
      }`}
      onClick={onSelect}
    >
      <h3 className="text-lg font-semibold text-gray-900">{character.name}</h3>
      <p className="mt-1 text-sm text-gray-600">"{concept}"</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {character.traits.map((trait, idx) => (
          <Pill
            key={idx}
            label={getLocalizedValue(trait.name, language)}
            className={isSelected ? "bg-indigo-100 text-indigo-700" : ""}
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
            ? language === "cn"
              ? "已选择"
              : "Selected"
            : language === "cn"
              ? "选择此角色"
              : "Select"}
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
  const name = getLocalizedValue(trait.name, language);
  const description = getLocalizedValue(trait.description, language);
  const positive = getLocalizedValue(trait.positive_aspect, language);
  const negative = getLocalizedValue(trait.negative_aspect, language);

  return (
    <div className="rounded-lg border border-gray-200 bg-white/70 p-3 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-gray-900">{name}</h4>
      </div>
      <p className="mt-1 text-sm text-gray-700">{description}</p>
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        <div className="rounded bg-green-50 px-2 py-1">
          <span className="text-xs font-medium text-green-800">
            {language === "cn" ? "正面: " : "Positive: "}
          </span>
          <span className="text-xs text-green-700">{positive}</span>
        </div>
        <div className="rounded bg-red-50 px-2 py-1">
          <span className="text-xs font-medium text-red-800">
            {language === "cn" ? "负面: " : "Negative: "}
          </span>
          <span className="text-xs text-red-700">{negative}</span>
        </div>
      </div>
    </div>
  );
};

const CharacterSelectionMode: React.FC = () => {
  const navigate = useNavigate();
  const { language } = useUIStore();
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
      setError(language === "cn" ? "请选择一个角色" : "Please select a character");
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
        <Card title={language === "cn" ? "请先选择世界" : "Please select a world"}>
          <p className="text-sm text-gray-700">
            {language === "cn"
              ? "请先在菜单页选择一个世界包，然后返回此处选择角色。"
              : "Please select a world pack from the menu first, then return here to select a character."}
          </p>
          <div className="mt-4">
            <Link to="/">
              <Button variant="primary">
                {language === "cn" ? "返回菜单" : "Back to Menu"}
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
          <h1 className="text-2xl font-bold text-gray-900">
            【{getLocalizedValue(worldInfo.name, language)}】
          </h1>

          {worldInfo.setting && (
            <div className="grid gap-2 sm:grid-cols-3">
              <div className="rounded bg-gray-50 px-3 py-2">
                <span className="text-xs text-gray-500">
                  {language === "cn" ? "时代" : "Era"}
                </span>
                <p className="text-sm font-medium text-gray-900">
                  {getLocalizedValue(worldInfo.setting.era, language)}
                </p>
              </div>
              <div className="rounded bg-gray-50 px-3 py-2">
                <span className="text-xs text-gray-500">
                  {language === "cn" ? "类型" : "Genre"}
                </span>
                <p className="text-sm font-medium text-gray-900">
                  {getLocalizedValue(worldInfo.setting.genre, language)}
                </p>
              </div>
              <div className="rounded bg-gray-50 px-3 py-2">
                <span className="text-xs text-gray-500">
                  {language === "cn" ? "氛围" : "Tone"}
                </span>
                <p className="text-sm font-medium text-gray-900">
                  {getLocalizedValue(worldInfo.setting.tone, language)}
                </p>
              </div>
            </div>
          )}

          {worldInfo.player_hook && (
            <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-4">
              <p className="text-sm italic text-indigo-900">
                {getLocalizedValue(worldInfo.player_hook, language)}
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Player Name Input */}
      <Card title={language === "cn" ? "你的名字" : "Your Name"}>
        <div className="space-y-2">
          <p className="text-xs text-gray-500">
            {language === "cn"
              ? "这是你作为玩家的名字，与角色名字不同。"
              : "This is your name as a player, distinct from your character's name."}
          </p>
          <input
            type="text"
            className="w-full max-w-md rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
            placeholder={language === "cn" ? "输入你的名字" : "Enter your name"}
            disabled={loading}
          />
        </div>
      </Card>

      {/* Character Selection */}
      <Card title={language === "cn" ? "选择你的角色" : "Select Your Character"}>
        {presetCharacters.length === 0 ? (
          <div className="flex justify-center py-8">
            <Loading text={language === "cn" ? "加载角色..." : "Loading characters..."} />
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
        <Card title={language === "cn" ? "角色特质" : "Character Traits"}>
          <div className="space-y-3">
            {selectedCharacter.traits.map((trait, idx) => (
              <TraitDetail key={idx} trait={trait} language={language} />
            ))}
          </div>
        </Card>
      )}

      {/* Error Message */}
      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
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
          {language === "cn" ? "开始冒险" : "Start Adventure"}
        </Button>
      </div>

      {loading && (
        <div className="flex justify-center">
          <Loading text={language === "cn" ? "创建游戏..." : "Creating game..."} />
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Character View Mode (During Game)
// ============================================================================

const CharacterViewMode: React.FC = () => {
  const { player, playerName } = useGameStore();
  const { language } = useUIStore();

  if (!player) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <Card title={language === "cn" ? "暂无角色信息" : "No character info"}>
          <p className="text-sm text-gray-700">
            {language === "cn"
              ? "请先在菜单页创建新会话，然后返回此处查看角色详情。"
              : "Please create a new session from the menu first, then return here to view character details."}
          </p>
          <div className="mt-4 flex gap-3">
            <Link to="/">
              <Button variant="primary">
                {language === "cn" ? "返回菜单" : "Back to Menu"}
              </Button>
            </Link>
            <Link to="/game">
              <Button variant="secondary">
                {language === "cn" ? "进入游戏" : "Enter Game"}
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
              <p className="text-xs uppercase tracking-wide text-gray-500">
                {language === "cn" ? "玩家" : "Player"}
              </p>
              <h2 className="text-lg font-medium text-gray-700">{playerName}</h2>
              <p className="text-xs uppercase tracking-wide text-gray-500 mt-2">
                {language === "cn" ? "角色" : "Character"}
              </p>
              <h1 className="text-2xl font-semibold text-gray-900">
                {player.name}
              </h1>
            </div>
            <Pill
              label={`${language === "cn" ? "命运点" : "Fate Points"}: ${player.fate_points}`}
              className="bg-indigo-50 text-indigo-700"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <SectionTitle title={language === "cn" ? "角色概念" : "Concept"} />
              <p className="rounded-md bg-indigo-50 px-3 py-2 text-sm text-indigo-900">
                {getLocalizedValue(player.concept, language)}
              </p>
            </div>
            <div className="space-y-1">
              <SectionTitle title={language === "cn" ? "状态标签" : "Tags"} />
              {player.tags.length === 0 ? (
                <p className="text-sm text-gray-500">
                  {language === "cn" ? "暂无标签" : "No tags"}
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

      <Card title={language === "cn" ? "特质" : "Traits"}>
        {player.traits.length === 0 ? (
          <p className="text-sm text-gray-500">
            {language === "cn" ? "暂无特质" : "No traits"}
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
            {language === "cn" ? "返回游戏" : "Back to Game"}
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

export const NotFoundPage: React.FC = () => (
  <div className="mx-auto max-w-4xl px-4 py-12 text-center">
    <h1 className="text-3xl font-semibold text-gray-900">404</h1>
    <p className="mt-2 text-gray-600">页面未找到。</p>
    <div className="mt-6 flex justify-center gap-3">
      <Link to="/">
        <Button variant="primary">返回菜单</Button>
      </Link>
      <Link to="/game">
        <Button variant="secondary">进入游戏</Button>
      </Link>
    </div>
  </div>
);

export default CharacterPage;
