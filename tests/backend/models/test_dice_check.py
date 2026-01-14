"""Tests for DiceCheckRequest and DiceCheckResponse models."""

import pytest

from src.backend.models.dice_check import DiceCheckRequest, DiceCheckResponse, DiceCheckResult
from src.backend.models.i18n import LocalizedString


class TestDiceCheckRequest:
    """Test suite for DiceCheckRequest class."""

    @pytest.fixture
    def sample_check_request(self):
        """Create a sample dice check request."""
        return DiceCheckRequest(
            intention="逃离这个房间",
            influencing_factors={
                "traits": [],
                "tags": ["右腿受伤"]
            },
            dice_formula="3d6kl2",
            instructions=LocalizedString(
                cn="由于右腿受伤，你在逃离这个房间的检定上有劣势",
                en="Due to leg injury, you have disadvantage on escaping"
            )
        )

    def test_create_dice_check_request(self, sample_check_request):
        """Test creating a DiceCheckRequest."""
        assert sample_check_request.intention == "逃离这个房间"
        assert "右腿受伤" in sample_check_request.influencing_factors["tags"]
        assert sample_check_request.dice_formula == "3d6kl2"

    def test_to_display_chinese(self, sample_check_request):
        """Test to_display() with Chinese language."""
        display = sample_check_request.to_display("cn")
        assert display["intention"] == "逃离这个房间"
        assert display["dice"] == "3d6kl2"
        assert "劣势" in display["explanation"]

    def test_to_display_english(self, sample_check_request):
        """Test to_display() with English language."""
        display = sample_check_request.to_display("en")
        assert display["intention"] == "逃离这个房间"
        assert display["dice"] == "3d6kl2"
        assert "disadvantage" in display["explanation"]

    def test_has_advantage(self):
        """Test has_advantage() detects advantage rolls."""
        check_advantage = DiceCheckRequest(
            intention="攀爬墙壁",
            influencing_factors={"traits": ["运动健将"], "tags": []},
            dice_formula="3d6kh2",
            instructions=LocalizedString(cn="优势", en="Advantage")
        )
        check_normal = DiceCheckRequest(
            intention="观察",
            influencing_factors={"traits": [], "tags": []},
            dice_formula="2d6",
            instructions=LocalizedString(cn="普通", en="Normal")
        )

        assert check_advantage.has_advantage() is True
        assert check_normal.has_advantage() is False

    def test_has_disadvantage(self, sample_check_request):
        """Test has_disadvantage() detects disadvantage rolls."""
        check_normal = DiceCheckRequest(
            intention="观察",
            influencing_factors={"traits": [], "tags": []},
            dice_formula="2d6",
            instructions=LocalizedString(cn="普通", en="Normal")
        )

        assert sample_check_request.has_disadvantage() is True
        assert check_normal.has_disadvantage() is False

    def test_get_dice_count(self, sample_check_request):
        """Test get_dice_count() extracts correct number."""
        assert sample_check_request.get_dice_count() == 3

        check_2d6 = DiceCheckRequest(
            intention="测试",
            influencing_factors={"traits": [], "tags": []},
            dice_formula="2d6",
            instructions=LocalizedString(cn="普通", en="Normal")
        )
        assert check_2d6.get_dice_count() == 2

        check_4d6 = DiceCheckRequest(
            intention="测试",
            influencing_factors={"traits": ["A", "B"], "tags": []},
            dice_formula="4d6kh2",
            instructions=LocalizedString(cn="双优势", en="Double advantage")
        )
        assert check_4d6.get_dice_count() == 4

    def test_str_returns_chinese(self, sample_check_request):
        """Test __str__ returns Chinese representation."""
        result = str(sample_check_request)
        assert "逃离这个房间" in result
        assert "3d6kl2" in result

    def test_repr_shows_key_info(self, sample_check_request):
        """Test __repr__ contains key information."""
        result = repr(sample_check_request)
        assert "逃离这个房间" in result
        assert "3d6kl2" in result

    def test_check_with_trait_advantage(self):
        """Test check request with trait-based advantage."""
        check = DiceCheckRequest(
            intention="说服守卫",
            influencing_factors={
                "traits": ["三寸不烂之舌"],
                "tags": []
            },
            dice_formula="3d6kh2",
            instructions=LocalizedString(
                cn="玩家的'三寸不烂之舌'特质给予优势",
                en="Player's 'Silver Tongue' trait grants advantage"
            )
        )
        assert check.has_advantage()
        assert "三寸不烂之舌" in check.influencing_factors["traits"]

    def test_check_with_multiple_tags(self):
        """Test check with multiple status tags."""
        check = DiceCheckRequest(
            intention="战斗",
            influencing_factors={
                "traits": [],
                "tags": ["右腿受伤", "疲惫", "饥饿"]
            },
            dice_formula="5d6kl2",  # Multiple penalties stack
            instructions=LocalizedString(
                cn="多个负面状态叠加",
                en="Multiple negative conditions stack"
            )
        )
        assert len(check.influencing_factors["tags"]) == 3
        assert check.get_dice_count() == 5


class TestDiceCheckResponse:
    """Test suite for DiceCheckResponse class."""

    def test_create_roll_response(self):
        """Test creating a response with roll action."""
        response = DiceCheckResponse(
            action="roll",
            dice_result={
                "all_rolls": [6, 5],
                "kept_rolls": [6, 5],
                "total": 11,
                "outcome": "success"
            }
        )
        assert response.action == "roll"
        assert response.dice_result["total"] == 11

    def test_create_argue_response(self):
        """Test creating a response with argue action."""
        response = DiceCheckResponse(
            action="argue",
            argument="我的运动健将特质应该抵消腿伤的影响",
            trait_claimed="运动健将"
        )
        assert response.action == "argue"
        assert response.trait_claimed == "运动健将"
        assert response.dice_result is None

    def test_create_cancel_response(self):
        """Test creating a response with cancel action."""
        response = DiceCheckResponse(action="cancel")
        assert response.action == "cancel"
        assert response.dice_result is None
        assert response.argument is None

    def test_response_validation(self):
        """Test that DiceCheckResponse validates required fields."""
        # action is required
        with pytest.raises(ValueError):
            DiceCheckResponse()


class TestDiceCheckResult:
    @pytest.fixture
    def success_result(self):
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
        assert critical_success_result.is_critical_success() is True

    def test_is_not_critical_success(self, success_result):
        assert success_result.is_critical_success() is False

    def test_is_critical_failure(self, critical_failure_result):
        assert critical_failure_result.is_critical_failure() is True

    def test_is_not_critical_failure(self, failure_result):
        assert failure_result.is_critical_failure() is False

    def test_get_margin_success(self, success_result):
        margin = success_result.get_margin()
        assert margin == 2

    def test_get_margin_failure(self, failure_result):
        margin = failure_result.get_margin()
        assert margin == -2

    def test_str_success(self, success_result):
        str_repr = str(success_result)
        assert "搜索房间" in str_repr
        assert "9" in str_repr
        assert "成功" in str_repr

    def test_str_critical_success(self, critical_success_result):
        str_repr = str(critical_success_result)
        assert "大成功" in str_repr

    def test_str_failure(self, failure_result):
        str_repr = str(failure_result)
        assert "失败" in str_repr

    def test_str_critical_failure(self, critical_failure_result):
        str_repr = str(critical_failure_result)
        assert "大失败" in str_repr

    def test_repr(self, success_result):
        repr_str = repr(success_result)
        assert "DiceCheckResult" in repr_str
        assert "搜索房间" in repr_str
        assert "total=9" in repr_str
        assert "success=True" in repr_str



class TestDiceCheckResult:
    """Tests for DiceCheckResult model."""

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

