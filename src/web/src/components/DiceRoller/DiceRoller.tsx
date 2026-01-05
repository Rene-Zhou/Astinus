import React, { useCallback, useMemo, useState } from "react";
import type {
  DiceCheckRequest,
  DiceOutcome,
  DiceResult,
} from "../../api/types";
import {
  flattenInfluencingFactors,
  getInstructionsText,
} from "../../api/types";
import Button from "../common/Button";
import { Card } from "../common/Card";

export interface DiceRollerProps {
  visible: boolean;
  checkRequest: DiceCheckRequest | null;
  onRoll: (result: DiceResult) => void;
  onCancel: () => void;
}

interface ParsedFormula {
  count: number;
  sides: number;
  keep?: {
    type: "lowest" | "highest";
    count: number;
  };
}

const parseDiceFormula = (formula?: string): ParsedFormula => {
  if (!formula) return { count: 1, sides: 6 };
  const match = formula.trim().match(/^(\d+)d(\d+)(?:k(l)?(\d+))?$/i);
  if (!match) return { count: 1, sides: 6 };

  const count = Number(match[1]);
  const sides = Number(match[2]);
  const keepCount = match[4] ? Number(match[4]) : undefined;
  const keepType = match[3] ? "lowest" : "highest";

  if (Number.isNaN(count) || Number.isNaN(sides) || count <= 0 || sides <= 1) {
    return { count: 1, sides: 6 };
  }

  if (!keepCount || Number.isNaN(keepCount) || keepCount <= 0) {
    return { count, sides };
  }

  return {
    count,
    sides,
    keep: {
      type: keepType as "lowest" | "highest",
      count: Math.min(keepCount, count),
    },
  };
};

const buildOutcome = (total: number, maxPossible: number): DiceOutcome => {
  const ratio = total / maxPossible;
  if (ratio >= 0.95) return "critical";
  if (ratio >= 0.7) return "success";
  if (ratio >= 0.4) return "partial";
  return "failure";
};

const rollDiceInternal = (formula?: string): DiceResult => {
  const parsed = parseDiceFormula(formula);
  const rolls: number[] = [];
  for (let i = 0; i < parsed.count; i += 1) {
    rolls.push(1 + Math.floor(Math.random() * parsed.sides));
  }

  let kept = [...rolls];
  if (parsed.keep) {
    const { type, count } = parsed.keep;
    kept = [...rolls]
      .sort((a, b) => (type === "lowest" ? a - b : b - a))
      .slice(0, count);
  }

  const total = kept.reduce((sum, n) => sum + n, 0);
  const maxPossible = (parsed.keep?.count ?? parsed.count) * parsed.sides;
  const outcome = buildOutcome(total, maxPossible);

  return {
    total,
    all_rolls: rolls,
    kept_rolls: kept,
    outcome,
  };
};

/**
 * Dice icon SVG for idle state
 */
const DiceIcon: React.FC<{ className?: string }> = ({ className }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <circle cx="8.5" cy="8.5" r="1.5" fill="currentColor" />
    <circle cx="15.5" cy="8.5" r="1.5" fill="currentColor" />
    <circle cx="8.5" cy="15.5" r="1.5" fill="currentColor" />
    <circle cx="15.5" cy="15.5" r="1.5" fill="currentColor" />
    <circle cx="12" cy="12" r="1.5" fill="currentColor" />
  </svg>
);

/**
 * Idle state component when no dice check is pending
 */
const IdleState: React.FC = () => (
  <div className="flex h-full flex-col items-center justify-center py-8 text-center">
    <DiceIcon className="mb-4 h-16 w-16 text-gray-300" />
    <h3 className="text-lg font-medium text-gray-600">骰子面板</h3>
    <p className="mt-2 max-w-xs text-sm text-gray-400">
      当你的行动需要进行检定时，骰子检定将在这里显示。
    </p>
    <div className="mt-6 rounded-lg bg-gray-50 p-4">
      <p className="text-xs text-gray-500">
        <span className="font-semibold">提示：</span>
        某些行动（如攀爬、说服、战斗等）可能需要掷骰子来决定结果。
      </p>
    </div>
  </div>
);

export const DiceRoller: React.FC<DiceRollerProps> = ({
  visible,
  checkRequest,
  onRoll,
  onCancel,
}) => {
  const [result, setResult] = useState<DiceResult | null>(null);
  const [rolling, setRolling] = useState(false);

  const formula = checkRequest?.dice_formula ?? "1d6";

  const handleRoll = useCallback(() => {
    setRolling(true);
    const next = rollDiceInternal(formula);
    setResult(next);
    setRolling(false);
  }, [formula]);

  const handleSubmit = useCallback(() => {
    if (!result) return;
    onRoll(result);
    // Reset state after submitting
    setResult(null);
  }, [onRoll, result]);

  const handleCancel = useCallback(() => {
    setResult(null);
    onCancel();
  }, [onCancel]);

  const summary = useMemo(() => {
    if (!result) return "";
    return `总值 ${result.total} （${result.all_rolls.join(
      ", ",
    )}${result.kept_rolls.length !== result.all_rolls.length ? ` → 保留 ${result.kept_rolls.join(", ")}` : ""}），结果：${result.outcome}`;
  }, [result]);

  const outcomeStyles: Record<DiceOutcome, string> = {
    critical: "bg-yellow-100 text-yellow-800 border-yellow-300",
    success: "bg-green-100 text-green-800 border-green-300",
    partial: "bg-blue-100 text-blue-800 border-blue-300",
    failure: "bg-red-100 text-red-800 border-red-300",
  };

  const outcomeLabels: Record<DiceOutcome, string> = {
    critical: "大成功！",
    success: "成功",
    partial: "部分成功",
    failure: "失败",
  };

  // Always render the container for consistent layout
  if (!visible) {
    return null;
  }

  return (
    <Card className="flex h-full flex-col">
      <div className="border-b border-gray-100 pb-3">
        <h2 className="text-lg font-semibold text-gray-900">🎲 骰子检定</h2>
      </div>

      {!checkRequest ? (
        // Idle state - no pending check
        <IdleState />
      ) : (
        // Active check state
        <div className="flex flex-1 flex-col space-y-4 pt-3">
          {/* Check intention/description */}
          <div className="space-y-1">
            <p className="text-sm font-medium text-gray-700">检定目标</p>
            <p className="rounded-md bg-primary/5 px-3 py-2 text-sm text-gray-800">
              {checkRequest.intention || "进行一次检定"}
            </p>
          </div>

          {/* Formula and factors */}
          <div className="space-y-3 rounded-md bg-gray-50 p-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">公式</span>
              <span className="rounded bg-white px-2 py-1 font-mono text-sm font-semibold text-primary shadow-sm">
                {formula}
              </span>
            </div>

            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-500">
                影响因素
              </p>
              {(() => {
                const factors = flattenInfluencingFactors(
                  checkRequest.influencing_factors,
                );
                if (factors.length === 0) {
                  return <p className="text-sm text-gray-400">无</p>;
                }
                return (
                  <div className="flex flex-wrap gap-1.5">
                    {factors.map((factor) => (
                      <span
                        key={factor}
                        className="rounded-full bg-white px-2.5 py-0.5 text-xs font-medium text-gray-700 shadow-sm"
                      >
                        {factor}
                      </span>
                    ))}
                  </div>
                );
              })()}
            </div>

            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-500">
                说明
              </p>
              <p className="text-sm text-gray-700">
                {getInstructionsText(checkRequest.instructions) ||
                  "请掷骰并提交结果。"}
              </p>
            </div>
          </div>

          {/* Result display */}
          {result && (
            <div
              className={`rounded-md border px-3 py-3 ${outcomeStyles[result.outcome]}`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">
                  {outcomeLabels[result.outcome]}
                </span>
                <span className="text-2xl font-bold">{result.total}</span>
              </div>
              <p className="mt-1 text-xs opacity-80">{summary}</p>
            </div>
          )}

          {/* Action buttons */}
          <div className="mt-auto flex flex-col gap-2 pt-2">
            <div className="flex gap-2">
              <Button
                onClick={handleRoll}
                loading={rolling}
                size="md"
                className="flex-1"
              >
                🎲 掷骰
              </Button>
              <Button
                variant="secondary"
                onClick={handleSubmit}
                disabled={!result}
                size="md"
                className="flex-1"
              >
                ✓ 提交
              </Button>
            </div>
            <Button
              variant="ghost"
              onClick={handleCancel}
              size="sm"
              className="w-full"
            >
              取消检定
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
};

export default DiceRoller;
