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
 * Defaults to 1d6 on invalid input.
 */
export function parseDiceFormula(formula?: string): ParsedDiceFormula {
  if (!formula) return { count: 1, sides: 6 };
  const match = formula.trim().match(/^(?<count>\d+)d(?<sides>\d+)(?:k(?<keepDir>h|l)?(?<keep>\d+))?$/i);

  if (!match || !match.groups) return { count: 1, sides: 6 };

  const count = Number(match.groups.count);
  const sides = Number(match.groups.sides);
  const keepCount = match.groups.keep ? Number(match.groups.keep) : undefined;
  const keepDir = match.groups.keepDir;

  if (!Number.isFinite(count) || !Number.isFinite(sides) || count <= 0 || sides <= 1) {
    return { count: 1, sides: 6 };
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
 * Compute a narrative outcome based on total vs. max possible.
 */
export function computeOutcome(
  total: number,
  keptCount: number,
  sides: number,
): DiceOutcome {
  const maxPossible = keptCount * sides;
  const ratio = total / maxPossible;

  if (ratio >= 0.95) return "critical";
  if (ratio >= 0.7) return "success";
  if (ratio >= 0.4) return "partial";
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
    formula: formula?.trim() || "1d6",
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
  const keptNote =
    result.kept_rolls.length !== result.all_rolls.length
      ? ` → 保留 ${result.kept_rolls.join(", ")}`
      : "";
  return `总值 ${result.total} （${result.all_rolls.join(", ")}${keptNote}），结果：${result.outcome}`;
}
