import React from "react";
import { Link } from "react-router-dom";
import { Card } from "../components/common/Card";
import Button from "../components/common/Button";
import { useGameStore } from "../stores/gameStore";
import { useUIStore } from "../stores/uiStore";
import { getLocalizedValue } from "../api/types";

const SectionTitle: React.FC<{ title: string }> = ({ title }) => (
  <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-600">
    {title}
  </h3>
);

const Pill: React.FC<{ label: string }> = ({ label }) => (
  <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
    {label}
  </span>
);

const CharacterPage: React.FC = () => {
  const { player } = useGameStore();
  const { language } = useUIStore();

  if (!player) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <Card title="暂无角色信息">
          <p className="text-sm text-gray-700">
            请先在菜单页创建新会话，然后返回此处查看角色详情。
          </p>
          <div className="mt-4 flex gap-3">
            <Link to="/">
              <Button variant="primary">返回菜单</Button>
            </Link>
            <Link to="/game">
              <Button variant="secondary">进入游戏</Button>
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
                玩家
              </p>
              <h1 className="text-2xl font-semibold text-gray-900">
                {player.name}
              </h1>
            </div>
            <Pill
              label={`命运点: ${player.fate_points.toString()}`}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <SectionTitle title="角色概念" />
              <p className="rounded-md bg-indigo-50 px-3 py-2 text-sm text-indigo-900">
                {getLocalizedValue(player.concept, language)}
              </p>
            </div>
            <div className="space-y-1">
              <SectionTitle title="状态标签" />
              {player.tags.length === 0 ? (
                <p className="text-sm text-gray-500">暂无标签</p>
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

      <Card title="特质">
        {player.traits.length === 0 ? (
          <p className="text-sm text-gray-500">暂无特质</p>
        ) : (
          <div className="space-y-3">
            {player.traits.map((trait, idx) => (
              <div
                key={`${trait.name.cn}-${idx}`}
                className="rounded-lg border border-gray-200 bg-white/70 p-3 shadow-sm"
              >
                <div className="flex items-center justify-between gap-2">
                  <h4 className="text-sm font-semibold text-gray-900">
                    {getLocalizedValue(trait.name, language)}
                  </h4>
                  <Pill label={getLocalizedValue(trait.positive_aspect, language)} />
                </div>
                <p className="mt-1 text-sm text-gray-700">
                  {getLocalizedValue(trait.description, language)}
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  负面: {getLocalizedValue(trait.negative_aspect, language)}
                </p>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="提示" className="text-sm text-gray-700">
        <p className="mb-1">
          本页面为占位实现，后续可根据 docs/WEB_FRONTEND_PLAN.md 增加可编辑角色、装备、成长记录等功能。
        </p>
        <p className="text-gray-500">
          当前数据源自后端会话状态（见 docs/API_TYPES.ts）。
        </p>
      </Card>
    </div>
  );
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
