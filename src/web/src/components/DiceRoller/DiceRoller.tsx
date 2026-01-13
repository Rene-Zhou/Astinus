import React, { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
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
  if (!formula) return { count: 2, sides: 6 };
  const match = formula.trim().match(/^(\d+)d(\d+)(?:k(l)?(\d+))?$/i);
  if (!match) return { count: 2, sides: 6 };

  const count = Number(match[1]);
  const sides = Number(match[2]);
  const keepCount = match[4] ? Number(match[4]) : undefined;
  const keepType = match[3] ? "lowest" : "highest";

  if (Number.isNaN(count) || Number.isNaN(sides) || count <= 0 || sides <= 1) {
    return { count: 2, sides: 6 };
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

const buildOutcome = (total: number, _maxPossible: number): DiceOutcome => {
  if (total >= 12) return "critical";
  if (total >= 10) return "success";
  if (total >= 7) return "partial";
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
const IdleState: React.FC = () => {
  const { t } = useTranslation();
  return (
    <div className="flex h-full flex-col items-center justify-center py-8 text-center">
      <DiceIcon className="mb-4 h-16 w-16 text-gray-300 dark:text-gray-600" />
      <h3 className="text-lg font-medium text-gray-600 dark:text-gray-300">{t("dice.panelTitle")}</h3>
      <p className="mt-2 max-w-xs text-sm text-gray-400 dark:text-gray-500">
        {t("dice.waitingForCheck")}
      </p>
      <div className="mt-6 rounded-lg bg-gray-50 p-4 dark:bg-gray-800">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          <span className="font-semibold">{t("dice.hint")}: </span>
          {t("dice.hintText")}
        </p>
      </div>
    </div>
  );
};

export const DiceRoller: React.FC<DiceRollerProps> = ({
  visible,
  checkRequest,
  onRoll,
  onCancel,
}) => {
  const { t, i18n } = useTranslation();
  const [result, setResult] = useState<DiceResult | null>(null);
  const [rolling, setRolling] = useState(false);

  const formula = checkRequest?.dice_formula ?? "2d6";

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

  const outcomeLabels: Record<DiceOutcome, string> = useMemo(() => ({
    critical: t("dice.outcome.critical"),
    success: t("dice.outcome.success"),
    partial: t("dice.outcome.partial"),
    failure: t("dice.outcome.failure"),
  }), [t]);

  const summary = useMemo(() => {
    if (!result) return "";
    return `${t("dice.total")} ${result.total} (${result.all_rolls.join(
      ", ",
    )}${result.kept_rolls.length !== result.all_rolls.length ? ` → ${t("dice.kept")} ${result.kept_rolls.join(", ")}` : ""}), ${t("dice.result")}: ${outcomeLabels[result.outcome]}`;
  }, [result, t, outcomeLabels]);

  const outcomeStyles: Record<DiceOutcome, string> = {
    critical: "bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-200 dark:border-yellow-700",
    success: "bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-200 dark:border-green-700",
    partial: "bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-900/30 dark:text-blue-200 dark:border-blue-700",
    failure: "bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-200 dark:border-red-700",
  };

  // Always render the container for consistent layout
  if (!visible) {
    return null;
  }

  return (
    <Card className="flex h-full flex-col dark:bg-gray-800 dark:border-gray-700">
      <div className="border-b border-gray-100 pb-3 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">🎲 {t("dice.panelTitle")}</h2>
      </div>

      {!checkRequest ? (
        // Idle state - no pending check
        <IdleState />
      ) : (
        // Active check state
        <div className="flex flex-1 flex-col space-y-4 pt-3">
          {/* Check intention/description */}
          <div className="space-y-1">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{t("dice.target")}</p>
            <p className="rounded-md bg-primary/5 px-3 py-2 text-sm text-gray-800 dark:bg-primary/10 dark:text-gray-200">
              {checkRequest.intention || t("dice.roll")}
            </p>
          </div>

          {/* Formula and factors */}
          <div className="space-y-3 rounded-md bg-gray-50 p-3 dark:bg-gray-750">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{t("dice.formula")}</span>
              <span className="rounded bg-white px-2 py-1 font-mono text-sm font-semibold text-primary shadow-sm dark:bg-gray-700 dark:text-primary-300">
                {formula}
              </span>
            </div>

            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                {t("dice.factors")}
              </p>
              {(() => {
                const factors = flattenInfluencingFactors(
                  checkRequest.influencing_factors,
                );
                if (factors.length === 0) {
                  return <p className="text-sm text-gray-400 dark:text-gray-500">None</p>;
                }
                return (
                  <div className="flex flex-wrap gap-1.5">
                    {factors.map((factor) => (
                      <span
                        key={factor}
                        className="rounded-full bg-white px-2.5 py-0.5 text-xs font-medium text-gray-700 shadow-sm dark:bg-gray-700 dark:text-gray-200"
                      >
                        {factor}
                      </span>
                    ))}
                  </div>
                );
              })()}
            </div>

            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
                Instructions
              </p>
              <p className="text-sm text-gray-700 dark:text-gray-300">
                {getInstructionsText(checkRequest.instructions, i18n.language as "cn" | "en") ||
                  "Please roll the dice."}
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
            <div className="grid grid-cols-2 gap-2">
              <Button onClick={handleRoll} loading={rolling} size="md">
                🎲 {t("dice.roll")}
              </Button>
              <Button
                variant="secondary"
                onClick={handleSubmit}
                disabled={!result}
                size="md"
              >
                ✓ {t("common.confirm")}
              </Button>
            </div>
            <div>
              <Button variant="ghost" onClick={handleCancel} size="sm">
                {t("common.cancel")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
};

export default DiceRoller;
