"""
Sample test file for dice service.

This is a placeholder test that will be expanded as the dice service is implemented.
"""

import pytest


class TestDiceService:
    """Test suite for dice rolling service."""

    def test_placeholder(self):
        """Placeholder test to ensure pytest is working."""
        assert True

    def test_dice_range(self):
        """Test that dice roll results are within valid range."""
        # TODO: Implement actual dice service test
        # For now, just a placeholder
        min_result = 2  # 2d6 minimum
        max_result = 12  # 2d6 maximum
        assert min_result <= max_result

    @pytest.mark.parametrize(
        "dice_notation,expected_min,expected_max",
        [
            ("2d6", 2, 12),
            ("3d6kh2", 2, 12),  # advantage: keep highest 2
            ("3d6kl2", 2, 12),  # disadvantage: keep lowest 2
        ],
    )
    def test_dice_notation_parsing(self, dice_notation, expected_min, expected_max):
        """Test that various dice notations are understood."""
        # TODO: Implement dice notation parser test
        assert expected_min <= expected_max
