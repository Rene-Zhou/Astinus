"""
Extended tests for DiceCheckResult model to improve coverage.
"""

import os

import pytest

os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"

from src.backend.models.dice_check import DiceCheckRequest, DiceCheckResponse, DiceCheckResult
from src.backend.models.i18n import LocalizedString


class TestDiceCheckResultExtended:
    """Extended tests for DiceCheckResult model."""

    @pytest.fixture
    def success_result(self):
        """Create a successful dice check result."""
        return DiceCheckResult(
            intention="搜索房间",
            dice_formula="2d6",
            dice_values=[5, 4],
            total=9,
            threshold=7,
            success=True,
            critical=False,
            modifiers=[],
        )

    @pytest.fixture
    def critical_success_result(self):
        """Create a critical success result."""
        return DiceCheckResult(
            intention="逃离陷阱",
            dice_formula="2d6",
            dice_values=[6, 6],
            total=12,
            threshold=7,
            success=True,
            critical=True,
            modifiers=[{"source": "敏锐", "effect": "advantage"}],
        )

    @pytest.fixture
    def failure_result(self):
        """Create a failure result."""
        return DiceCheckResult(
            intention="说服守卫",
            dice_formula="2d6",
            dice_values=[2, 3],
            total=5,
            threshold=7,
            success=False,
            critical=False,
            modifiers=[],
        )

    @pytest.fixture
    def critical_failure_result(self):
        """Create a critical failure result."""
        return DiceCheckResult(
            intention="攀爬城墙",
            dice_formula="2d6",
            dice_values=[1, 1],
            total=2,
            threshold=7,
            success=False,
            critical=True,
            modifiers=[{"source": "受伤", "effect": "disadvantage"}],
        )

    def test_is_critical_success(self, critical_success_result):
        """Test critical success detection."""
        assert critical_success_result.is_critical_success() is True

    def test_is_not_critical_success(self, success_result):
        """Test non-critical success."""
        assert success_result.is_critical_success() is False

    def test_is_critical_failure(self, critical_failure_result):
        """Test critical failure detection."""
        assert critical_failure_result.is_critical_failure() is True

    def test_is_not_critical_failure(self, failure_result):
        """Test non-critical failure."""
        assert failure_result.is_critical_failure() is False

    def test_get_margin_success(self, success_result):
        """Test success margin calculation."""
        margin = success_result.get_margin()
        assert margin == 2  # 9 - 7 = 2

    def test_get_margin_failure(self, failure_result):
        """Test failure margin calculation (negative)."""
        margin = failure_result.get_margin()
        assert margin == -2  # 5 - 7 = -2

    def test_str_success(self, success_result):
        """Test string representation for success."""
        str_repr = str(success_result)
        assert "搜索房间" in str_repr
        assert "9" in str_repr
        assert "成功" in str_repr

    def test_str_critical_success(self, critical_success_result):
        """Test string representation for critical success."""
        str_repr = str(critical_success_result)
        assert "大成功" in str_repr

    def test_str_failure(self, failure_result):
        """Test string representation for failure."""
        str_repr = str(failure_result)
        assert "失败" in str_repr

    def test_str_critical_failure(self, critical_failure_result):
        """Test string representation for critical failure."""
        str_repr = str(critical_failure_result)
        assert "大失败" in str_repr

    def test_repr(self, success_result):
        """Test developer representation."""
        repr_str = repr(success_result)
        assert "DiceCheckResult" in repr_str
        assert "搜索房间" in repr_str
        assert "total=9" in repr_str
        assert "success=True" in repr_str


class TestDiceCheckRequestExtended:
    """Extended tests for DiceCheckRequest model."""

    @pytest.fixture
    def basic_request(self):
        """Create a basic dice check request."""
        return DiceCheckRequest(
            intention="打开上锁的门",
            influencing_factors={"traits": [], "tags": []},
            dice_formula="2d6",
            instructions=LocalizedString(
                cn="标准开锁检定",
                en="Standard lockpicking check",
            ),
        )

    @pytest.fixture
    def advantage_request(self):
        """Create a dice check with advantage."""
        return DiceCheckRequest(
            intention="搜索书架",
            influencing_factors={"traits": ["敏锐"], "tags": []},
            dice_formula="3d6kh2",
            instructions=LocalizedString(
                cn="敏锐特质给予优势",
                en="Perceptive trait grants advantage",
            ),
        )

    @pytest.fixture
    def disadvantage_request(self):
        """Create a dice check with disadvantage."""
        return DiceCheckRequest(
            intention="在黑暗中搜索",
            influencing_factors={"traits": [], "tags": ["黑暗中"]},
            dice_formula="3d6kl2",
            instructions=LocalizedString(
                cn="黑暗环境带来劣势",
                en="Darkness brings disadvantage",
            ),
        )

    def test_to_display_cn(self, basic_request):
        """Test display format in Chinese."""
        display = basic_request.to_display("cn")
        assert display["intention"] == "打开上锁的门"
        assert display["dice"] == "2d6"
        assert display["explanation"] == "标准开锁检定"

    def test_to_display_en(self, basic_request):
        """Test display format in English."""
        display = basic_request.to_display("en")
        assert display["explanation"] == "Standard lockpicking check"

    def test_has_advantage_true(self, advantage_request):
        """Test advantage detection."""
        assert advantage_request.has_advantage() is True
        assert advantage_request.has_disadvantage() is False

    def test_has_disadvantage_true(self, disadvantage_request):
        """Test disadvantage detection."""
        assert disadvantage_request.has_disadvantage() is True
        assert disadvantage_request.has_advantage() is False

    def test_no_advantage_or_disadvantage(self, basic_request):
        """Test basic roll has neither advantage nor disadvantage."""
        assert basic_request.has_advantage() is False
        assert basic_request.has_disadvantage() is False

    def test_get_dice_count_basic(self, basic_request):
        """Test dice count for basic roll."""
        assert basic_request.get_dice_count() == 2

    def test_get_dice_count_advantage(self, advantage_request):
        """Test dice count for advantage roll."""
        assert advantage_request.get_dice_count() == 3

    def test_get_dice_count_disadvantage(self, disadvantage_request):
        """Test dice count for disadvantage roll."""
        assert disadvantage_request.get_dice_count() == 3

    def test_str_representation(self, basic_request):
        """Test string representation."""
        str_repr = str(basic_request)
        assert "打开上锁的门" in str_repr or "2d6" in str_repr

    def test_repr_representation(self, basic_request):
        """Test developer representation."""
        repr_str = repr(basic_request)
        assert "DiceCheckRequest" in repr_str


class TestDiceCheckResponse:
    """Tests for DiceCheckResponse model."""

    def test_roll_response(self):
        """Test response for a roll action."""
        response = DiceCheckResponse(
            action="roll",
            dice_result={
                "all_rolls": [5, 4],
                "kept_rolls": [5, 4],
                "total": 9,
                "outcome": "success",
            },
        )
        assert response.action == "roll"
        assert response.dice_result is not None
        assert response.dice_result["total"] == 9

    def test_argue_response(self):
        """Test response for an argue action."""
        response = DiceCheckResponse(
            action="argue",
            argument="我的敏锐特质让我能更好地发现隐藏的东西",
            trait_claimed="敏锐",
        )
        assert response.action == "argue"
        assert response.argument is not None
        assert response.trait_claimed == "敏锐"

    def test_cancel_response(self):
        """Test response for a cancel action."""
        response = DiceCheckResponse(action="cancel")
        assert response.action == "cancel"
        assert response.dice_result is None
        assert response.argument is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
