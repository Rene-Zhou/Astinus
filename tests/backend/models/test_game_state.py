"""Tests for GameState model."""

from datetime import datetime

import pytest

from src.backend.models.character import PlayerCharacter
from src.backend.models.game_state import GamePhase, GameState
from src.backend.models.i18n import LocalizedString
from src.backend.models.trait import Trait


class TestGameState:
    """Test suite for GameState class."""

    @pytest.fixture
    def sample_character(self):
        """Create a sample character for testing."""
        return PlayerCharacter(
            name="测试角色",
            concept=LocalizedString(cn="测试概念", en="Test Concept"),
            traits=[
                Trait(
                    name=LocalizedString(cn="特质", en="Trait"),
                    description=LocalizedString(cn="描述", en="Description"),
                    positive_aspect=LocalizedString(cn="正面", en="Positive"),
                    negative_aspect=LocalizedString(cn="负面", en="Negative")
                )
            ],
            fate_points=3
        )

    @pytest.fixture
    def sample_game_state(self, sample_character):
        """Create a sample game state for testing."""
        return GameState(
            session_id="test-session-123",
            player=sample_character,
            world_pack_id="demo_pack",
            current_location="living_room"
        )

    def test_create_game_state(self, sample_game_state):
        """Test creating a game state with required fields."""
        assert sample_game_state.session_id == "test-session-123"
        assert sample_game_state.player.name == "测试角色"
        assert sample_game_state.world_pack_id == "demo_pack"
        assert sample_game_state.current_location == "living_room"

    def test_default_phase_is_waiting_input(self, sample_game_state):
        """Test that default phase is WAITING_INPUT."""
        assert sample_game_state.current_phase == GamePhase.WAITING_INPUT

    def test_default_turn_count_is_zero(self, sample_game_state):
        """Test that default turn count is 0."""
        assert sample_game_state.turn_count == 0

    def test_default_language_is_chinese(self, sample_game_state):
        """Test that default language is cn."""
        assert sample_game_state.language == "cn"

    def test_add_message(self, sample_game_state):
        """Test adding a message to conversation history."""
        sample_game_state.add_message("user", "我要翻找书架")
        assert len(sample_game_state.messages) == 1
        message = sample_game_state.messages[0]
        assert message["role"] == "user"
        assert message["content"] == "我要翻找书架"
        assert "timestamp" in message

    def test_add_message_with_metadata(self, sample_game_state):
        """Test adding a message with metadata."""
        sample_game_state.add_message(
            "assistant",
            "你开始翻找书架...",
            metadata={"agent": "narrator", "phase": "narrating"}
        )
        message = sample_game_state.messages[0]
        assert message["metadata"]["agent"] == "narrator"

    def test_get_recent_messages(self, sample_game_state):
        """Test getting recent messages."""
        # Add 10 messages
        for i in range(10):
            sample_game_state.add_message("user", f"Message {i}")

        recent = sample_game_state.get_recent_messages(5)
        assert len(recent) == 5
        assert recent[-1]["content"] == "Message 9"  # Most recent

    def test_get_recent_messages_when_fewer_exist(self, sample_game_state):
        """Test getting recent messages when fewer than requested exist."""
        sample_game_state.add_message("user", "First message")
        recent = sample_game_state.get_recent_messages(5)
        assert len(recent) == 1

    def test_update_location(self, sample_game_state):
        """Test updating current location."""
        sample_game_state.update_location("kitchen", npc_ids=["chen_ling"])
        assert sample_game_state.current_location == "kitchen"
        assert "chen_ling" in sample_game_state.active_npc_ids

    def test_add_flag(self, sample_game_state):
        """Test adding a story flag."""
        sample_game_state.add_flag("found_key")
        assert "found_key" in sample_game_state.flags

    def test_has_flag(self, sample_game_state):
        """Test checking if flag exists."""
        sample_game_state.add_flag("found_key")
        assert sample_game_state.has_flag("found_key")
        assert not sample_game_state.has_flag("not_set")

    def test_add_discovered_item(self, sample_game_state):
        """Test adding a discovered item."""
        sample_game_state.add_discovered_item("ancient_book")
        assert "ancient_book" in sample_game_state.discovered_items

    def test_has_discovered_item(self, sample_game_state):
        """Test checking if item has been discovered."""
        sample_game_state.add_discovered_item("ancient_book")
        assert sample_game_state.has_discovered_item("ancient_book")
        assert not sample_game_state.has_discovered_item("not_found")

    def test_increment_turn(self, sample_game_state):
        """Test incrementing turn counter."""
        assert sample_game_state.turn_count == 0
        sample_game_state.increment_turn()
        assert sample_game_state.turn_count == 1

    def test_set_phase(self, sample_game_state):
        """Test setting game phase."""
        sample_game_state.set_phase(GamePhase.DICE_CHECK, next_agent="rule")
        assert sample_game_state.current_phase == GamePhase.DICE_CHECK
        assert sample_game_state.next_agent == "rule"

    def test_updated_at_changes_on_modification(self, sample_game_state):
        """Test that updated_at changes when state is modified."""
        original_time = sample_game_state.updated_at
        # Wait a tiny bit to ensure timestamp changes
        import time
        time.sleep(0.01)
        sample_game_state.add_message("user", "test")
        assert sample_game_state.updated_at > original_time

    def test_temp_context_for_agent_communication(self, sample_game_state):
        """Test using temp_context for passing data to agents."""
        sample_game_state.temp_context = {
            "check_request": {"dice_formula": "3d6kl2"}
        }
        assert sample_game_state.temp_context["check_request"]["dice_formula"] == "3d6kl2"

    def test_last_check_result_storage(self, sample_game_state):
        """Test storing last dice check result."""
        sample_game_state.last_check_result = {
            "total": 11,
            "outcome": "success"
        }
        assert sample_game_state.last_check_result["outcome"] == "success"

    def test_repr_shows_key_info(self, sample_game_state):
        """Test __repr__ contains key information."""
        repr_str = repr(sample_game_state)
        assert "test-session-123" in repr_str
        assert "测试角色" in repr_str
        assert "living_room" in repr_str
