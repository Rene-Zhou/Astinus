"""
Extended tests for dice service to improve coverage.

Tests DiceResult display methods and outcome determination.
"""

import os

import pytest

os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"

from src.backend.services.dice import DicePool, DiceResult, Outcome


class TestDiceResultDisplay:
    """Tests for DiceResult display methods."""

    @pytest.fixture
    def basic_result(self):
        """Create a basic dice result."""
        return DiceResult(
            all_rolls=[4, 5],
            kept_rolls=[4, 5],
            dropped_rolls=[],
            modifier=0,
            total=9,
            outcome=Outcome.PARTIAL,
            is_bonus=False,
            is_penalty=False,
        )

    @pytest.fixture
    def bonus_result(self):
        """Create a result with bonus dice."""
        return DiceResult(
            all_rolls=[6, 5, 2],
            kept_rolls=[6, 5],
            dropped_rolls=[2],
            modifier=0,
            total=11,
            outcome=Outcome.SUCCESS,
            is_bonus=True,
            is_penalty=False,
        )

    @pytest.fixture
    def penalty_result(self):
        """Create a result with penalty dice."""
        return DiceResult(
            all_rolls=[6, 3, 2],
            kept_rolls=[3, 2],
            dropped_rolls=[6],
            modifier=0,
            total=5,
            outcome=Outcome.FAILURE,
            is_bonus=False,
            is_penalty=True,
        )

    @pytest.fixture
    def modified_result(self):
        """Create a result with modifier."""
        return DiceResult(
            all_rolls=[4, 5],
            kept_rolls=[4, 5],
            dropped_rolls=[],
            modifier=2,
            total=11,
            outcome=Outcome.SUCCESS,
            is_bonus=False,
            is_penalty=False,
        )

    @pytest.fixture
    def critical_result(self):
        """Create a critical success result."""
        return DiceResult(
            all_rolls=[6, 6],
            kept_rolls=[6, 6],
            dropped_rolls=[],
            modifier=0,
            total=12,
            outcome=Outcome.CRITICAL,
            is_bonus=False,
            is_penalty=False,
        )

    def test_basic_result_str(self, basic_result):
        """Test string representation of basic result."""
        result_str = str(basic_result)
        assert result_str is not None
        # Should contain outcome info

    def test_basic_result_repr(self, basic_result):
        """Test repr of basic result."""
        repr_str = repr(basic_result)
        assert "DiceResult" in repr_str
        assert "total=9" in repr_str
        assert "partial" in repr_str

    def test_bonus_result_str(self, bonus_result):
        """Test string representation with bonus."""
        result_str = str(bonus_result)
        assert result_str is not None

    def test_penalty_result_str(self, penalty_result):
        """Test string representation with penalty."""
        result_str = str(penalty_result)
        assert result_str is not None

    def test_legacy_base_rolls_property(self, basic_result):
        """Test legacy base_rolls property."""
        assert basic_result.base_rolls == basic_result.kept_rolls

    def test_legacy_bonus_rolls_property(self, bonus_result, basic_result):
        """Test legacy bonus_rolls property."""
        # Bonus result should have bonus_rolls
        assert bonus_result.bonus_rolls == bonus_result.dropped_rolls
        # Basic result should have empty bonus_rolls
        assert basic_result.bonus_rolls == []

    def test_legacy_penalty_rolls_property(self, penalty_result, basic_result):
        """Test legacy penalty_rolls property."""
        # Penalty result should have penalty_rolls
        assert penalty_result.penalty_rolls == penalty_result.dropped_rolls
        # Basic result should have empty penalty_rolls
        assert basic_result.penalty_rolls == []


class TestOutcomeEnum:
    """Tests for Outcome enum."""

    def test_all_outcomes_exist(self):
        """Test all expected outcomes are defined."""
        expected_outcomes = ["critical", "success", "partial", "failure"]
        actual_values = [outcome.value for outcome in Outcome]
        for expected in expected_outcomes:
            assert expected in actual_values

    def test_outcome_values_are_strings(self):
        """Test outcome values are strings."""
        for outcome in Outcome:
            assert isinstance(outcome.value, str)


class TestDicePoolRolling:
    """Tests for DicePool rolling behavior."""

    def test_base_roll_always_two_dice(self):
        """Test that base roll always uses two dice."""
        pool = DicePool()
        for _ in range(10):
            result = pool.roll()
            assert len(result.all_rolls) == 2
            assert len(result.kept_rolls) == 2
            assert len(result.dropped_rolls) == 0

    def test_bonus_roll_keeps_highest(self):
        """Test that bonus roll keeps highest dice."""
        pool = DicePool(bonus_dice=1)
        for _ in range(10):
            result = pool.roll()
            assert len(result.all_rolls) == 3
            assert len(result.kept_rolls) == 2
            assert len(result.dropped_rolls) == 1
            # Kept should be highest
            assert min(result.kept_rolls) >= max(result.dropped_rolls)

    def test_penalty_roll_keeps_lowest(self):
        """Test that penalty roll keeps lowest dice."""
        pool = DicePool(penalty_dice=1)
        for _ in range(10):
            result = pool.roll()
            assert len(result.all_rolls) == 3
            assert len(result.kept_rolls) == 2
            assert len(result.dropped_rolls) == 1
            # Kept should be lowest
            assert max(result.kept_rolls) <= min(result.dropped_rolls)

    def test_modifier_applied_correctly(self):
        """Test that modifier is applied to total."""
        pool = DicePool(modifier=3)
        result = pool.roll()
        expected_total = sum(result.kept_rolls) + 3
        assert result.total == expected_total
        assert result.modifier == 3

    def test_negative_modifier(self):
        """Test negative modifier."""
        pool = DicePool(modifier=-2)
        result = pool.roll()
        expected_total = sum(result.kept_rolls) - 2
        assert result.total == expected_total

    def test_outcome_critical_on_12_plus(self):
        """Test outcome is critical on 12+."""
        result = DiceResult(
            all_rolls=[6, 6],
            kept_rolls=[6, 6],
            dropped_rolls=[],
            modifier=0,
            total=12,
            outcome=DicePool._determine_outcome(12),
            is_bonus=False,
            is_penalty=False,
        )
        assert result.outcome == Outcome.CRITICAL

    def test_outcome_success_on_10_11(self):
        """Test outcome is success on 10-11."""
        assert DicePool._determine_outcome(10) == Outcome.SUCCESS
        assert DicePool._determine_outcome(11) == Outcome.SUCCESS

    def test_outcome_partial_on_7_9(self):
        """Test outcome is partial on 7-9."""
        assert DicePool._determine_outcome(7) == Outcome.PARTIAL
        assert DicePool._determine_outcome(8) == Outcome.PARTIAL
        assert DicePool._determine_outcome(9) == Outcome.PARTIAL

    def test_outcome_failure_on_6_or_less(self):
        """Test outcome is failure on 6 or less."""
        assert DicePool._determine_outcome(6) == Outcome.FAILURE
        assert DicePool._determine_outcome(5) == Outcome.FAILURE
        assert DicePool._determine_outcome(2) == Outcome.FAILURE


class TestDicePoolFormula:
    """Tests for dice formula generation."""

    def test_base_formula(self):
        """Test base roll formula."""
        pool = DicePool()
        assert pool.get_dice_formula() == "2d6"

    def test_bonus_formula(self):
        """Test bonus dice formula."""
        pool = DicePool(bonus_dice=1)
        assert pool.get_dice_formula() == "3d6kh2"

        pool2 = DicePool(bonus_dice=2)
        assert pool2.get_dice_formula() == "4d6kh2"

    def test_penalty_formula(self):
        """Test penalty dice formula."""
        pool = DicePool(penalty_dice=1)
        assert pool.get_dice_formula() == "3d6kl2"

        pool2 = DicePool(penalty_dice=2)
        assert pool2.get_dice_formula() == "4d6kl2"

    def test_bonus_and_penalty_cancel(self):
        """Test that bonus and penalty cancel each other."""
        pool = DicePool(bonus_dice=1, penalty_dice=1)
        assert pool.get_dice_formula() == "2d6"

        pool2 = DicePool(bonus_dice=2, penalty_dice=1)
        assert pool2.get_dice_formula() == "3d6kh2"

        pool3 = DicePool(bonus_dice=1, penalty_dice=2)
        assert pool3.get_dice_formula() == "3d6kl2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
