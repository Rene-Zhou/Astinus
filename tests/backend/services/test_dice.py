"""
Tests for the dice rolling system.

Ported from weave with additions for i18n support.
"""

import pytest

from src.backend.services.dice import DicePool, DiceResult, Outcome


class TestOutcome:
    """Tests for the Outcome enum."""

    def test_outcome_values(self):
        """Test that all outcome values are defined."""
        assert Outcome.CRITICAL.value == "critical"
        assert Outcome.SUCCESS.value == "success"
        assert Outcome.PARTIAL.value == "partial"
        assert Outcome.FAILURE.value == "failure"


class TestDiceResult:
    """Tests for the DiceResult class."""

    def test_dice_result_creation(self):
        """Test creating a DiceResult."""
        result = DiceResult(
            all_rolls=[3, 4],
            kept_rolls=[4, 3],
            dropped_rolls=[],
            modifier=1,
            total=8,
            outcome=Outcome.PARTIAL,
        )
        assert result.kept_rolls == [4, 3]
        assert result.modifier == 1
        assert result.total == 8
        assert result.outcome == Outcome.PARTIAL

    def test_dice_result_str_basic(self):
        """Test string representation of basic roll."""
        result = DiceResult(
            all_rolls=[4, 3],
            kept_rolls=[4, 3],
            dropped_rolls=[],
            modifier=1,
            total=8,
            outcome=Outcome.PARTIAL,
        )
        result_str = str(result)
        assert "4" in result_str
        assert "3" in result_str
        assert "+1" in result_str
        assert "= 8" in result_str

    def test_dice_result_str_with_bonus(self):
        """Test string representation with bonus dice."""
        result = DiceResult(
            all_rolls=[5, 4, 3, 2],
            kept_rolls=[5, 4],
            dropped_rolls=[3, 2],
            modifier=1,
            total=10,
            outcome=Outcome.SUCCESS,
            is_bonus=True,
        )
        result_str = str(result)
        # Should show arrow indicating selection and up arrow for bonus
        assert "→" in result_str
        assert "↑" in result_str

    def test_dice_result_str_with_penalty(self):
        """Test string representation with penalty dice."""
        result = DiceResult(
            all_rolls=[6, 5, 4, 3],
            kept_rolls=[4, 3],
            dropped_rolls=[6, 5],
            modifier=0,
            total=7,
            outcome=Outcome.PARTIAL,
            is_penalty=True,
        )
        result_str = str(result)
        # Should show arrow indicating selection and down arrow for penalty
        assert "→" in result_str
        assert "↓" in result_str

    def test_to_display_chinese(self):
        """Test to_display() returns Chinese text."""
        result = DiceResult(
            all_rolls=[6, 5],
            kept_rolls=[6, 5],
            dropped_rolls=[],
            modifier=0,
            total=11,
            outcome=Outcome.SUCCESS,
        )
        display = result.to_display("cn")
        assert display["outcome"] == "成功"
        assert "= 11" in display["roll_detail"]

    def test_to_display_english(self):
        """Test to_display() returns English text."""
        result = DiceResult(
            all_rolls=[6, 5],
            kept_rolls=[6, 5],
            dropped_rolls=[],
            modifier=0,
            total=11,
            outcome=Outcome.SUCCESS,
        )
        display = result.to_display("en")
        assert display["outcome"] == "Success"
        assert "= 11" in display["roll_detail"]

    def test_to_display_with_bonus_shows_advantage_text(self):
        """Test that bonus rolls show 'advantage' text."""
        result = DiceResult(
            all_rolls=[6, 5, 2],
            kept_rolls=[6, 5],
            dropped_rolls=[2],
            modifier=0,
            total=11,
            outcome=Outcome.SUCCESS,
            is_bonus=True,
        )
        display_cn = result.to_display("cn")
        display_en = result.to_display("en")

        assert display_cn["modifier_text"] == "优势"
        assert display_en["modifier_text"] == "Advantage"

    def test_to_display_with_penalty_shows_disadvantage_text(self):
        """Test that penalty rolls show 'disadvantage' text."""
        result = DiceResult(
            all_rolls=[6, 5, 2],
            kept_rolls=[5, 2],
            dropped_rolls=[6],
            modifier=0,
            total=7,
            outcome=Outcome.PARTIAL,
            is_penalty=True,
        )
        display_cn = result.to_display("cn")
        display_en = result.to_display("en")

        assert display_cn["modifier_text"] == "劣势"
        assert display_en["modifier_text"] == "Disadvantage"

    def test_legacy_compatibility_properties(self):
        """Test backward compatibility properties from weave."""
        result = DiceResult(
            all_rolls=[6, 5, 2],
            kept_rolls=[6, 5],
            dropped_rolls=[2],
            modifier=0,
            total=11,
            outcome=Outcome.SUCCESS,
            is_bonus=True,
        )
        assert result.base_rolls == [6, 5]
        assert result.bonus_rolls == [2]
        assert result.penalty_rolls == []


class TestDicePool:
    """Tests for the DicePool class."""

    def test_dice_pool_basic_roll(self):
        """Test basic 2d6 roll."""
        pool = DicePool(modifier=1)
        result = pool.roll()

        assert len(result.all_rolls) == 2
        assert len(result.kept_rolls) == 2
        assert all(1 <= d <= 6 for d in result.all_rolls)
        assert result.total == sum(result.kept_rolls) + 1

    def test_dice_pool_no_modifier(self):
        """Test roll without modifier."""
        pool = DicePool(modifier=0)
        result = pool.roll()

        assert len(result.all_rolls) == 2
        assert result.modifier == 0
        assert result.total == sum(result.kept_rolls)

    def test_dice_pool_with_bonus_dice(self):
        """Test roll with bonus dice (advantage)."""
        pool = DicePool(bonus_dice=1)
        result = pool.roll()

        # Should roll 3 dice total
        assert len(result.all_rolls) == 3
        # Should keep the highest 2
        assert len(result.kept_rolls) == 2
        assert len(result.dropped_rolls) == 1
        assert result.is_bonus is True
        assert result.is_penalty is False

        # Verify kept_rolls are the highest
        assert min(result.kept_rolls) >= max(result.dropped_rolls)

    def test_dice_pool_with_penalty_dice(self):
        """Test roll with penalty dice (disadvantage)."""
        pool = DicePool(penalty_dice=1)
        result = pool.roll()

        # Should roll 3 dice total
        assert len(result.all_rolls) == 3
        # Should keep the lowest 2
        assert len(result.kept_rolls) == 2
        assert len(result.dropped_rolls) == 1
        assert result.is_bonus is False
        assert result.is_penalty is True

        # Verify kept_rolls are the lowest
        assert max(result.kept_rolls) <= min(result.dropped_rolls)

    def test_dice_pool_bonus_and_penalty_cancel(self):
        """Test that bonus and penalty dice cancel each other."""
        pool = DicePool(bonus_dice=2, penalty_dice=1)
        result = pool.roll()

        # Net bonus = 2 - 1 = 1, so 3 dice total
        assert len(result.all_rolls) == 3
        assert result.is_bonus is True

    def test_dice_pool_penalty_exceeds_bonus(self):
        """Test when penalty dice exceed bonus dice."""
        pool = DicePool(bonus_dice=1, penalty_dice=2)
        result = pool.roll()

        # Net bonus = 1 - 2 = -1, so 3 dice total with penalty
        assert len(result.all_rolls) == 3
        assert result.is_penalty is True

    def test_dice_pool_multiple_bonus_dice(self):
        """Test with multiple bonus dice."""
        pool = DicePool(bonus_dice=2)
        result = pool.roll()

        # Should roll 4 dice (2 base + 2 bonus)
        assert len(result.all_rolls) == 4
        assert len(result.kept_rolls) == 2
        assert result.is_bonus is True

    def test_outcome_determination_critical(self):
        """Test critical success outcome (12+)."""
        # Total 12 should be critical
        assert DicePool._determine_outcome(12) == Outcome.CRITICAL
        assert DicePool._determine_outcome(13) == Outcome.CRITICAL

    def test_outcome_determination_success(self):
        """Test success outcome (10-11)."""
        assert DicePool._determine_outcome(10) == Outcome.SUCCESS
        assert DicePool._determine_outcome(11) == Outcome.SUCCESS

    def test_outcome_determination_partial(self):
        """Test partial success outcome (7-9)."""
        assert DicePool._determine_outcome(7) == Outcome.PARTIAL
        assert DicePool._determine_outcome(8) == Outcome.PARTIAL
        assert DicePool._determine_outcome(9) == Outcome.PARTIAL

    def test_outcome_determination_failure(self):
        """Test failure outcome (6-)."""
        assert DicePool._determine_outcome(2) == Outcome.FAILURE
        assert DicePool._determine_outcome(6) == Outcome.FAILURE

    def test_get_dice_formula_base(self):
        """Test dice formula for base roll."""
        pool = DicePool()
        assert pool.get_dice_formula() == "2d6"

    def test_get_dice_formula_with_bonus(self):
        """Test dice formula with bonus (advantage)."""
        pool = DicePool(bonus_dice=1)
        assert pool.get_dice_formula() == "3d6kh2"

    def test_get_dice_formula_with_penalty(self):
        """Test dice formula with penalty (disadvantage)."""
        pool = DicePool(penalty_dice=1)
        assert pool.get_dice_formula() == "3d6kl2"

    def test_get_dice_formula_with_multiple_bonus(self):
        """Test dice formula with multiple bonus dice."""
        pool = DicePool(bonus_dice=2)
        assert pool.get_dice_formula() == "4d6kh2"

    def test_dice_range_is_valid(self):
        """Test that all rolls are within valid range."""
        pool = DicePool()
        # Run multiple rolls to test randomness
        for _ in range(20):
            result = pool.roll()
            assert all(1 <= d <= 6 for d in result.all_rolls)
            # Total should be between 2 (two 1s) and 12 (two 6s)
            assert 2 <= result.total <= 12

    def test_bonus_increases_average(self):
        """Test that bonus dice increase average roll (statistical test)."""
        # This is a statistical test - run many rolls and compare averages
        base_rolls = [DicePool().roll().total for _ in range(100)]
        bonus_rolls = [DicePool(bonus_dice=1).roll().total for _ in range(100)]

        base_avg = sum(base_rolls) / len(base_rolls)
        bonus_avg = sum(bonus_rolls) / len(bonus_rolls)

        # With bonus, average should be higher
        # (Allow some variance due to randomness)
        assert bonus_avg > base_avg

    def test_penalty_decreases_average(self):
        """Test that penalty dice decrease average roll (statistical test)."""
        base_rolls = [DicePool().roll().total for _ in range(100)]
        penalty_rolls = [DicePool(penalty_dice=1).roll().total for _ in range(100)]

        base_avg = sum(base_rolls) / len(base_rolls)
        penalty_avg = sum(penalty_rolls) / len(penalty_rolls)

        # With penalty, average should be lower
        assert penalty_avg < base_avg
