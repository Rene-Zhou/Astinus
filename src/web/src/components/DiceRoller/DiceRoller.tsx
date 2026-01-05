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
  }, [onRoll, result]);

  const summary = useMemo(() => {
    if (!result) return "";
    return `总值 ${result.total} （${result.all_rolls.join(
      ", ",
    )}${result.kept_rolls.length !== result.all_rolls.length ? ` → 保留 ${result.kept_rolls.join(", ")}` : ""}），结果：${result.outcome}`;
  }, [result]);

  if (!visible || !checkRequest) {
    return null;
  }

  return (
    <Card className="space-y-4">
      <div className="space-y-1">
        <h3 className="text-lg font-semibold text-gray-900">骰子检定</h3>
        <p className="text-sm text-gray-600">
          {checkRequest.intention || "进行一次检定"}
        </p>
      </div>

      <div className="space-y-2 rounded-md bg-gray-50 p-3 text-sm text-gray-800">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-gray-900">公式</span>
          <span className="rounded bg-white px-2 py-1 font-mono text-primary">
            {formula}
          </span>
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">
            影响因素
          </p>
          {(() => {
            const factors = flattenInfluencingFactors(
              checkRequest.influencing_factors,
            );
            if (factors.length === 0) {
              return <p className="text-sm text-gray-500">无</p>;
            }
            return (
              <div className="mt-1 flex flex-wrap gap-2">
                {factors.map((factor) => (
                  <span
                    key={factor}
                    className="rounded-full bg-white px-3 py-1 text-xs font-medium text-gray-700"
                  >
                    {factor}
                  </span>
                ))}
              </div>
            );
          })()}
        </div>
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-500">说明</p>
          <p className="text-sm text-gray-700">
            {getInstructionsText(checkRequest.instructions) ||
              "请掷骰并提交结果。"}
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <Button onClick={handleRoll} loading={rolling} size="md">
            掷骰
          </Button>
          <Button
            variant="secondary"
            onClick={handleSubmit}
            disabled={!result}
            size="md"
          >
            提交结果
          </Button>
          <Button variant="ghost" onClick={onCancel} size="md">
            取消
          </Button>
        </div>
        {result && (
          <div className="rounded-md border border-dashed border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-800">
            <div className="font-semibold text-gray-900">结果</div>
            <div className="mt-1">{summary}</div>
          </div>
        )}
      </div>
    </Card>
  );
};

export default DiceRoller;
