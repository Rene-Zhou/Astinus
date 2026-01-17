import type { Outcome, DiceResult } from '../schemas';

export class DicePool {
  constructor(
    public modifier: number = 0,
    public bonusDice: number = 0,
    public penaltyDice: number = 0
  ) {}

  roll(): DiceResult {
    const netBonus = this.bonusDice - this.penaltyDice;
    const diceCount = 2 + Math.abs(netBonus);
    
    const allRolls: number[] = [];
    for (let i = 0; i < diceCount; i++) {
      allRolls.push(Math.floor(Math.random() * 6) + 1);
    }

    const sortedRolls = [...allRolls].sort((a, b) => b - a);

    let keptRolls: number[];
    let droppedRolls: number[];
    let isBonus = false;
    let isPenalty = false;

    if (netBonus >= 0) {
      keptRolls = sortedRolls.slice(0, 2);
      droppedRolls = sortedRolls.slice(2);
      isBonus = netBonus > 0;
      isPenalty = false;
    } else {
      keptRolls = sortedRolls.slice(-2);
      droppedRolls = sortedRolls.slice(0, -2);
      isBonus = false;
      isPenalty = true;
    }

    keptRolls.sort((a, b) => b - a);

    const diceSum = keptRolls.reduce((sum, val) => sum + val, 0);
    const total = diceSum + this.modifier;

    return {
      allRolls,
      keptRolls,
      droppedRolls,
      modifier: this.modifier,
      total,
      outcome: DicePool.determineOutcome(total),
      isBonus,
      isPenalty,
    };
  }

  static determineOutcome(total: number): Outcome {
    if (total >= 12) return 'critical';
    if (total >= 10) return 'success';
    if (total >= 7) return 'partial';
    return 'failure';
  }

  getDiceFormula(): string {
    const netBonus = this.bonusDice - this.penaltyDice;
    const diceCount = 2 + Math.abs(netBonus);

    if (netBonus > 0) {
      return `${diceCount}d6kh2`;
    } else if (netBonus < 0) {
      return `${diceCount}d6kl2`;
    } else {
      return '2d6';
    }
  }
}

export function toDisplay(
  result: DiceResult,
  lang: 'cn' | 'en' = 'cn'
): {
  rollDetail: string;
  outcome: string;
  modifierText: string | null;
} {
  const outcomeTexts: Record<Outcome, { cn: string; en: string }> = {
    critical: { cn: '大成功', en: 'Critical Success' },
    success: { cn: '成功', en: 'Success' },
    partial: { cn: '部分成功', en: 'Partial Success' },
    failure: { cn: '失败', en: 'Failure' },
  };

  const modifierTexts = {
    bonus: { cn: '优势骰', en: 'Advantage' },
    penalty: { cn: '劣势骰', en: 'Disadvantage' },
  };

  const parts: string[] = [];

  if (result.allRolls.length > 2) {
    const allDiceStr = result.allRolls.join('+');
    const keptDiceStr = result.keptRolls.join('+');
    const arrow = result.isBonus ? '↑' : '↓';
    parts.push(`[${allDiceStr}]→[${keptDiceStr}]${arrow}`);
  } else {
    parts.push(`[${result.keptRolls.join('+')}]`);
  }

  if (result.modifier !== 0) {
    const sign = result.modifier > 0 ? '+' : '';
    parts.push(`${sign}${result.modifier}`);
  }

  parts.push(`= ${result.total}`);
  const rollDetail = parts.join(' ');

  const outcomeText = outcomeTexts[result.outcome][lang];

  let modifierText: string | null = null;
  if (result.isBonus) {
    modifierText = modifierTexts.bonus[lang];
  } else if (result.isPenalty) {
    modifierText = modifierTexts.penalty[lang];
  }

  return {
    rollDetail,
    outcome: outcomeText,
    modifierText,
  };
}
