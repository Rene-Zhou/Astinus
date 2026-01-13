"""Tests for GM Agent roleplay direction generation."""

import os
from unittest.mock import MagicMock

import pytest

from src.backend.agents.gm import GMAgent
from src.backend.models.character import PlayerCharacter, Trait
from src.backend.models.game_state import GameState
from src.backend.models.i18n import LocalizedString

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


def create_mock_gm_agent():
    """Create a GM agent with minimal mock dependencies for testing."""
    character = PlayerCharacter(
        name="测试玩家",
        concept=LocalizedString(cn="测试角色", en="Test Character"),
        traits=[
            Trait(
                name=LocalizedString(cn="测试特质", en="Test Trait"),
                description=LocalizedString(cn="测试描述", en="Test Description"),
                positive_aspect=LocalizedString(cn="正面效果", en="Positive Effect"),
                negative_aspect=LocalizedString(cn="负面效果", en="Negative Effect"),
            )
        ],
        tags=[],
    )
    game_state = GameState(
        session_id="test",
        player=character,
        world_pack_id="test_world",
        current_location="test_location",
    )
    return GMAgent(llm=MagicMock(), sub_agents={}, game_state=game_state)


class TestGenerateRoleplayDirection:
    """Test _generate_roleplay_direction method."""

    @pytest.fixture
    def gm_agent(self):
        """Create a GM agent for testing."""
        return create_mock_gm_agent()

    @pytest.mark.parametrize(
        "outcome,lang,expected_substring",
        [
            ("critical_success", "cn", "非常积极"),
            ("critical_success", "en", "very positively"),
            ("success", "cn", "积极回应"),
            ("success", "en", "respond positively"),
            ("partial", "cn", "有所松动"),
            ("partial", "en", "soften somewhat"),
            ("failure", "cn", "拒绝"),
            ("failure", "en", "refuse"),
            ("critical_failure", "cn", "强烈拒绝"),
            ("critical_failure", "en", "strongly refuse"),
        ],
    )
    def test_generate_roleplay_direction_outcomes(
        self, gm_agent, outcome, lang, expected_substring
    ):
        """Test that correct direction is generated for each outcome."""
        dice_result = {"outcome": outcome}

        direction = gm_agent._generate_roleplay_direction(dice_result, lang)

        assert expected_substring in direction

    def test_empty_outcome_returns_empty_string(self, gm_agent):
        """Test that empty outcome returns empty direction."""
        dice_result = {"outcome": ""}

        direction = gm_agent._generate_roleplay_direction(dice_result, "cn")

        assert direction == ""

    def test_missing_outcome_returns_empty_string(self, gm_agent):
        """Test that missing outcome returns empty direction."""
        dice_result = {}

        direction = gm_agent._generate_roleplay_direction(dice_result, "cn")

        assert direction == ""

    def test_unknown_outcome_returns_empty_string(self, gm_agent):
        """Test that unknown outcome returns empty direction."""
        dice_result = {"outcome": "unknown_outcome"}

        direction = gm_agent._generate_roleplay_direction(dice_result, "cn")

        assert direction == ""

    def test_unknown_lang_falls_back_to_english(self, gm_agent):
        """Test that unknown language falls back to English."""
        dice_result = {"outcome": "success"}

        direction = gm_agent._generate_roleplay_direction(dice_result, "fr")

        assert "positively" in direction


class TestSliceContextForNpcWithDiceResult:
    """Test _slice_context_for_npc includes roleplay_direction."""

    @pytest.fixture
    def gm_agent(self):
        """Create a GM agent for testing."""
        return create_mock_gm_agent()

    def test_context_includes_roleplay_direction_when_dice_result_present(
        self, gm_agent
    ):
        """Test that roleplay_direction is included when dice_result is provided."""
        dice_result = {"outcome": "partial"}

        context = gm_agent._slice_context_for_npc(
            npc_id="old_guard",
            player_input="请告诉我更多信息",
            lang="cn",
            dice_result=dice_result,
        )

        assert "roleplay_direction" in context
        assert "有所松动" in context["roleplay_direction"]

    def test_context_excludes_dice_result_details(self, gm_agent):
        """Test that raw dice_result is NOT passed to NPC (information isolation)."""
        dice_result = {"outcome": "partial", "total": 7, "intention": "说服"}

        context = gm_agent._slice_context_for_npc(
            npc_id="old_guard",
            player_input="请告诉我更多信息",
            lang="cn",
            dice_result=dice_result,
        )

        # dice_result should NOT be in context
        assert "dice_result" not in context
        # But roleplay_direction should be
        assert "roleplay_direction" in context

    def test_context_no_roleplay_direction_when_no_dice_result(self, gm_agent):
        """Test that roleplay_direction is not included when no dice_result."""
        context = gm_agent._slice_context_for_npc(
            npc_id="old_guard",
            player_input="你好",
            lang="cn",
            dice_result=None,
        )

        assert "roleplay_direction" not in context

    def test_roleplay_direction_english(self, gm_agent):
        """Test that English roleplay direction is correctly generated."""
        dice_result = {"outcome": "success"}

        context = gm_agent._slice_context_for_npc(
            npc_id="old_guard",
            player_input="Tell me more",
            lang="en",
            dice_result=dice_result,
        )

        assert "roleplay_direction" in context
        assert "positively" in context["roleplay_direction"]

    def test_roleplay_direction_critical_success(self, gm_agent):
        """Test critical success direction in Chinese."""
        dice_result = {"outcome": "critical_success"}

        context = gm_agent._slice_context_for_npc(
            npc_id="old_guard",
            player_input="请帮帮我",
            lang="cn",
            dice_result=dice_result,
        )

        assert "roleplay_direction" in context
        assert "非常积极" in context["roleplay_direction"]

    def test_roleplay_direction_critical_failure(self, gm_agent):
        """Test critical failure direction in English."""
        dice_result = {"outcome": "critical_failure"}

        context = gm_agent._slice_context_for_npc(
            npc_id="old_guard",
            player_input="Tell me your secret",
            lang="en",
            dice_result=dice_result,
        )

        assert "roleplay_direction" in context
        assert "strongly refuse" in context["roleplay_direction"]
