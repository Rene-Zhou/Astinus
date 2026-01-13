import i18n from "./i18n";
import type {
  DiceOutcome,
  DiceResult,
  Language,
  LocalizedString,
} from "../api/types";

export type KeepType = "highest" | "lowest";

export interface ParsedDiceFormula {
  count: number;
  sides: number;
  keep?: {
    type: KeepType;
    count: number;
  };
}

/**
 * Localized string helper with graceful fallback.
 */
export function pickLocalized(
  str: LocalizedString | string,
  lang: Language = "cn",
): string {
  if (typeof str === "string") return str;
  return str[lang] || str.cn || str.en || "";
}

/**
 * Parse dice notation like "2d6", "3d6kh2", "4d6kl3".
 * Defaults to 2d6 on invalid input (standard PbtA dice).
 */
export function parseDiceFormula(formula?: string): ParsedDiceFormula {
  if (!formula) return { count: 2, sides: 6 };
  const match = formula.trim().match(/^(?<count>\d+)d(?<sides>\d+)(?:k(?<keepDir>h|l)?(?<keep>\d+))?$/i);

  if (!match || !match.groups) return { count: 2, sides: 6 };

  const count = Number(match.groups.count);
  const sides = Number(match.groups.sides);
  const keepCount = match.groups.keep ? Number(match.groups.keep) : undefined;
  const keepDir = match.groups.keepDir;

  if (!Number.isFinite(count) || !Number.isFinite(sides) || count <= 0 || sides <= 1) {
    return { count: 2, sides: 6 };
  }

  if (!keepCount || keepCount <= 0) {
    return { count, sides };
  }

  return {
    count,
    sides,
    keep: {
      type: keepDir === "l" ? "lowest" : "highest",
      count: Math.min(keepCount, count),
    },
  };
}

/**
 * Compute a narrative outcome based on fixed PbtA thresholds.
 * Per GUIDE.md:
 *   12+: critical (exceptional success)
 *   10-11: success (full success)
 *   7-9: partial (success with cost/complication)
 *   6-: failure
 *
 * Note: keptCount and sides are kept for API compatibility but unused.
 */
export function computeOutcome(
  total: number,
  _keptCount: number,
  _sides: number,
): DiceOutcome {
  if (total >= 12) return "critical";
  if (total >= 10) return "success";
  if (total >= 7) return "partial";
  return "failure";
}

/**
 * Roll dice according to a formula. Allows injecting RNG for testing.
 */
export function rollDice(
  formula?: string,
  rng: () => number = Math.random,
): DiceResult & { formula: string } {
  const parsed = parseDiceFormula(formula);
  const rolls: number[] = [];

  for (let i = 0; i < parsed.count; i += 1) {
    rolls.push(1 + Math.floor(rng() * parsed.sides));
  }

  let kept = [...rolls];
  if (parsed.keep) {
    const { type, count } = parsed.keep;
    kept = [...rolls]
      .sort((a, b) => (type === "lowest" ? a - b : b - a))
      .slice(0, count);
  }

  const total = kept.reduce((sum, n) => sum + n, 0);
  const outcome = computeOutcome(total, kept.length, parsed.sides);

  return {
    formula: formula?.trim() || "2d6",
    total,
    all_rolls: rolls,
    kept_rolls: kept,
    outcome,
  };
}

/**
 * Format a roll result into a human-readable summary.
 */
export function formatDiceResult(result: DiceResult): string {
  const t = i18n.t;
  const outcomeLabels: Record<DiceOutcome, string> = {
    critical: t("dice.outcome.critical"),
    success: t("dice.outcome.success"),
    partial: t("dice.outcome.partial"),
    failure: t("dice.outcome.failure"),
  };

  const keptNote =
    result.kept_rolls.length !== result.all_rolls.length
      ? ` → ${t("dice.kept")} ${result.kept_rolls.join(", ")}`
      : "";
  return `${t("dice.total")} ${result.total} （${result.all_rolls.join(", ")}${keptNote}），${t("dice.result")}：${outcomeLabels[result.outcome]}`;
}
