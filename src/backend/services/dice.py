"""
Dice rolling system for Astinus.

This module implements a 2d6-based dice system with support for:
- Modifiers (positive or negative)
- Bonus dice (roll more dice, take the highest two)
- Penalty dice (roll more dice, take the lowest two)

Migrated from weave with the following changes:
- Converted from @dataclass to Pydantic BaseModel
- Added i18n support for display strings
- Added to_display() method for localized output

The core mechanic is always "take 2 dice" from a pool:
- Base roll: 2d6, take both
- With bonus: roll (2 + bonus) dice, take highest 2
- With penalty: roll (2 + penalty) dice, take lowest 2
- Bonus and penalty cancel each other out

This ensures that:
- Maximum natural roll is always 12 (two 6s)
- Critical success (12+) requires modifier or luck
- Bonus dice increase odds of high rolls but don't exceed 12

Outcomes are determined by the total:
- 12+: Critical Success
- 10-11: Success
- 7-9: Partial Success
- 6-: Failure
"""

import random
from enum import Enum

from pydantic import BaseModel, Field


class Outcome(Enum):
    """Possible outcomes from a dice roll."""

    CRITICAL = "critical"  # 12+
    SUCCESS = "success"  # 10-11
    PARTIAL = "partial"  # 7-9
    FAILURE = "failure"  # 6-


class DiceResult(BaseModel):
    """
    Result of a dice roll.

    Attributes:
        all_rolls: All dice that were rolled.
        kept_rolls: The two dice that were kept (highest or lowest).
        dropped_rolls: Dice that were rolled but not kept.
        modifier: The modifier applied after dice selection.
        total: Final total (sum of kept_rolls + modifier).
        outcome: The outcome category based on total.
        is_bonus: True if bonus dice were used (took highest).
        is_penalty: True if penalty dice were used (took lowest).

    Examples:
        >>> result = DiceResult(
        ...     all_rolls=[6, 5, 2],
        ...     kept_rolls=[6, 5],
        ...     dropped_rolls=[2],
        ...     modifier=0,
        ...     total=11,
        ...     outcome=Outcome.SUCCESS,
        ...     is_bonus=True
        ... )
        >>> result.total
        11
    """

    all_rolls: list[int] = Field(..., description="All dice that were rolled")
    kept_rolls: list[int] = Field(..., description="The two dice kept (highest or lowest)")
    dropped_rolls: list[int] = Field(..., description="Dice rolled but not kept")
    modifier: int = Field(default=0, description="Modifier applied after dice selection")
    total: int = Field(..., description="Final total (kept dice + modifier)")
    outcome: Outcome = Field(..., description="Outcome category based on total")
    is_bonus: bool = Field(default=False, description="True if bonus dice were used")
    is_penalty: bool = Field(default=False, description="True if penalty dice were used")

    # Legacy compatibility properties (from weave)
    @property
    def base_rolls(self) -> list[int]:
        """Legacy property for compatibility."""
        return self.kept_rolls

    @property
    def bonus_rolls(self) -> list[int]:
        """Legacy property - returns dropped rolls if bonus was used."""
        return self.dropped_rolls if self.is_bonus else []

    @property
    def penalty_rolls(self) -> list[int]:
        """Legacy property - returns dropped rolls if penalty was used."""
        return self.dropped_rolls if self.is_penalty else []

    def to_display(self, lang: str = "cn") -> dict[str, str]:
        """
        Generate localized display strings for the roll.

        Args:
            lang: Language code ("cn" or "en")

        Returns:
            Dictionary with display strings:
            - "roll_detail": Detailed roll breakdown
            - "outcome": Outcome text
            - "modifier_text": Modifier description (if any)

        Examples:
            >>> result.to_display("cn")
            {'roll_detail': '[6+5+2]→[6+5]↑ = 11', 'outcome': '成功', ...}
        """
        # Import here to avoid circular dependency
        # Will be replaced with i18n service once implemented
        outcome_text = {
            "cn": {
                Outcome.CRITICAL: "大成功",
                Outcome.SUCCESS: "成功",
                Outcome.PARTIAL: "部分成功",
                Outcome.FAILURE: "失败",
            },
            "en": {
                Outcome.CRITICAL: "Critical Success",
                Outcome.SUCCESS: "Success",
                Outcome.PARTIAL: "Partial Success",
                Outcome.FAILURE: "Failure",
            },
        }

        modifier_text = {
            "cn": {"bonus": "优势", "penalty": "劣势"},
            "en": {"bonus": "Advantage", "penalty": "Disadvantage"},
        }

        # Build roll detail string
        parts = []
        if len(self.all_rolls) > 2:
            all_dice_str = "+".join(str(d) for d in self.all_rolls)
            kept_dice_str = "+".join(str(d) for d in self.kept_rolls)
            if self.is_bonus:
                parts.append(f"[{all_dice_str}]→[{kept_dice_str}]↑")
            else:
                parts.append(f"[{all_dice_str}]→[{kept_dice_str}]↓")
        else:
            parts.append(f"[{'+'.join(str(d) for d in self.kept_rolls)}]")

        if self.modifier:
            parts.append(f"{self.modifier:+d}")

        parts.append(f"= {self.total}")
        roll_detail = " ".join(parts)

        # Determine modifier description
        mod_desc = None
        if self.is_bonus:
            mod_desc = modifier_text[lang]["bonus"]
        elif self.is_penalty:
            mod_desc = modifier_text[lang]["penalty"]

        return {
            "roll_detail": roll_detail,
            "outcome": outcome_text[lang][self.outcome],
            "modifier_text": mod_desc,
        }

    def __str__(self) -> str:
        """Return a human-readable representation of the roll (Chinese)."""
        display = self.to_display("cn")
        parts = [display["roll_detail"]]
        if display["modifier_text"]:
            parts.append(f"({display['modifier_text']})")
        parts.append(f"- {display['outcome']}")
        return " ".join(parts)

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"DiceResult(total={self.total}, outcome={self.outcome.value})"


class DicePool:
    """
    Handles dice rolling with bonus/penalty dice.

    The dice pool determines how many dice to roll and which to keep:
    - Base: always roll at least 2 dice
    - Bonus dice: roll extra dice, keep the highest 2
    - Penalty dice: roll extra dice, keep the lowest 2
    - Bonus and penalty cancel each other out first

    Examples:
        >>> pool = DicePool()
        >>> result = pool.roll()
        >>> 2 <= result.total <= 12
        True

        >>> pool_with_bonus = DicePool(bonus_dice=1)
        >>> result = pool_with_bonus.roll()
        >>> len(result.all_rolls) == 3
        True
    """

    def __init__(
        self,
        modifier: int = 0,
        bonus_dice: int = 0,
        penalty_dice: int = 0,
    ):
        """
        Initialize a dice pool.

        Args:
            modifier: Fixed modifier to add to the roll.
            bonus_dice: Number of bonus dice (roll more, take highest 2).
            penalty_dice: Number of penalty dice (roll more, take lowest 2).
        """
        self.modifier = modifier
        self.bonus_dice = bonus_dice
        self.penalty_dice = penalty_dice

    def roll(self) -> DiceResult:
        """
        Roll the dice pool and return the result.

        Returns:
            A DiceResult containing all roll information.
        """
        # Calculate net bonus/penalty (they cancel each other)
        net_bonus = self.bonus_dice - self.penalty_dice

        # Determine how many dice to roll (minimum 2)
        dice_count = 2 + abs(net_bonus)

        # Roll all dice
        all_rolls = [random.randint(1, 6) for _ in range(dice_count)]

        # Sort to determine which dice to keep
        sorted_rolls = sorted(all_rolls, reverse=True)

        # Take highest 2 (if net bonus) or lowest 2 (if net penalty)
        if net_bonus >= 0:
            # Bonus or neutral: take highest 2
            kept_rolls = sorted_rolls[:2]
            dropped_rolls = sorted_rolls[2:]
            is_bonus = net_bonus > 0
            is_penalty = False
        else:
            # Penalty: take lowest 2
            kept_rolls = sorted_rolls[-2:]
            dropped_rolls = sorted_rolls[:-2]
            is_bonus = False
            is_penalty = True

        # Sort kept_rolls in descending order for display consistency
        kept_rolls = sorted(kept_rolls, reverse=True)

        # Calculate total
        dice_sum = sum(kept_rolls)
        total = dice_sum + self.modifier

        return DiceResult(
            all_rolls=all_rolls,
            kept_rolls=kept_rolls,
            dropped_rolls=dropped_rolls,
            modifier=self.modifier,
            total=total,
            outcome=self._determine_outcome(total),
            is_bonus=is_bonus,
            is_penalty=is_penalty,
        )

    @staticmethod
    def _determine_outcome(total: int) -> Outcome:
        """Determine the outcome based on the roll total."""
        if total >= 12:
            return Outcome.CRITICAL
        elif total >= 10:
            return Outcome.SUCCESS
        elif total >= 7:
            return Outcome.PARTIAL
        else:
            return Outcome.FAILURE

    def get_dice_formula(self) -> str:
        """
        Get the dice formula notation for this pool.

        Returns:
            String like "2d6", "3d6kh2" (keep highest 2), or "3d6kl2" (keep lowest 2)

        Examples:
            >>> DicePool().get_dice_formula()
            '2d6'
            >>> DicePool(bonus_dice=1).get_dice_formula()
            '3d6kh2'
            >>> DicePool(penalty_dice=1).get_dice_formula()
            '3d6kl2'
        """
        net_bonus = self.bonus_dice - self.penalty_dice
        dice_count = 2 + abs(net_bonus)

        if net_bonus > 0:
            return f"{dice_count}d6kh2"  # Keep highest 2
        elif net_bonus < 0:
            return f"{dice_count}d6kl2"  # Keep lowest 2
        else:
            return "2d6"  # Base roll
