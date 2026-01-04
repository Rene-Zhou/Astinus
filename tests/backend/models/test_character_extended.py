"""
Extended tests for character model and game state.

These tests cover additional methods and edge cases to improve coverage.
"""

import os

import pytest

os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"

from src.backend.models.character import PlayerCharacter, Trait
from src.backend.models.game_state import GamePhase, GameState
from src.backend.models.i18n import LocalizedString


class TestPlayerCharacterExtended:
    """Extended tests for PlayerCharacter model."""

    @pytest.fixture
    def player(self):
        """Create a test player character."""
        return PlayerCharacter(
            name="测试角色",
            concept=LocalizedString(cn="勇敢的冒险者", en="Brave Adventurer"),
            traits=[
                Trait(
                    name=LocalizedString(cn="敏锐", en="Perceptive"),
                    description=LocalizedString(cn="善于观察", en="Good at observing"),
                    positive_aspect=LocalizedString(cn="注意力强", en="Strong attention"),
                    negative_aspect=LocalizedString(cn="多疑", en="Suspicious"),
                )
            ],
            tags=["新手"],
            fate_points=3,
        )

    def test_add_tag(self, player):
        """Test adding a tag to player."""
        player.add_tag("受伤")
        assert "受伤" in player.tags

    def test_add_duplicate_tag(self, player):
        """Test that duplicate tags are not added."""
        initial_count = len(player.tags)
        player.add_tag("新手")  # Already exists
        assert len(player.tags) == initial_count

    def test_remove_tag(self, player):
        """Test removing a tag from player."""
        player.add_tag("临时标签")
        assert "临时标签" in player.tags
        player.remove_tag("临时标签")
        assert "临时标签" not in player.tags

    def test_remove_nonexistent_tag(self, player):
        """Test removing a tag that doesn't exist."""
        # Should not raise
        player.remove_tag("不存在的标签")

    def test_has_tag(self, player):
        """Test checking if player has a tag."""
        assert player.has_tag("新手") is True
        assert player.has_tag("不存在") is False

    def test_fate_points_operations(self, player):
        """Test fate point operations."""
        assert player.fate_points == 3

        # Spend fate point
        result = player.spend_fate_point()
        assert result is True
        assert player.fate_points == 2

        # Gain fate point
        result = player.gain_fate_point()
        assert result is True
        assert player.fate_points == 3

    def test_spend_fate_point_at_zero(self, player):
        """Test that spending fate point at zero returns False."""
        player.fate_points = 0
        result = player.spend_fate_point()
        assert result is False
        assert player.fate_points == 0

    def test_gain_fate_point_at_max(self, player):
        """Test that gaining fate point at max returns False."""
        player.fate_points = 5
        result = player.gain_fate_point()
        assert result is False
        assert player.fate_points == 5

    def test_get_concept(self, player):
        """Test getting character concept in different languages."""
        assert player.get_concept("cn") == "勇敢的冒险者"
        assert player.get_concept("en") == "Brave Adventurer"

    def test_player_str(self, player):
        """Test string representation."""
        assert str(player) == "测试角色"

    def test_player_repr(self, player):
        """Test repr representation."""
        repr_str = repr(player)
        assert "测试角色" in repr_str
        assert "traits=1" in repr_str
        assert "fate=3" in repr_str

    def test_trait_positive_negative_aspects(self, player):
        """Test trait positive and negative aspects."""
        trait = player.traits[0]
        assert trait.positive_aspect.get("cn") == "注意力强"
        assert trait.negative_aspect.get("cn") == "多疑"


class TestGameStateExtended:
    """Extended tests for GameState model."""

    @pytest.fixture
    def player(self):
        """Create a test player."""
        return PlayerCharacter(
            name="测试角色",
            concept=LocalizedString(cn="冒险者", en="Adventurer"),
            traits=[
                Trait(
                    name=LocalizedString(cn="勇敢", en="Brave"),
                    description=LocalizedString(cn="无所畏惧", en="Fearless"),
                    positive_aspect=LocalizedString(cn="勇气", en="Courage"),
                    negative_aspect=LocalizedString(cn="鲁莽", en="Reckless"),
                )
            ],
            tags=[],
        )

    @pytest.fixture
    def game_state(self, player):
        """Create a test game state."""
        return GameState(
            session_id="test-extended-session",
            world_pack_id="demo_pack",
            player=player,
            current_location="start",
            active_npc_ids=[],
        )

    def test_add_flag(self, game_state):
        """Test adding a story flag."""
        game_state.add_flag("found_key")
        assert game_state.has_flag("found_key") is True
        assert game_state.has_flag("other_flag") is False

    def test_add_duplicate_flag(self, game_state):
        """Test adding duplicate flags."""
        game_state.add_flag("flag1")
        game_state.add_flag("flag1")
        # Flags is a set, so duplicates won't be added
        assert "flag1" in game_state.flags

    def test_add_discovered_item(self, game_state):
        """Test adding discovered items."""
        game_state.add_discovered_item("ancient_book")
        assert game_state.has_discovered_item("ancient_book") is True
        assert game_state.has_discovered_item("other_item") is False

    def test_increment_turn(self, game_state):
        """Test turn counter increment."""
        assert game_state.turn_count == 0
        game_state.increment_turn()
        assert game_state.turn_count == 1
        game_state.increment_turn()
        assert game_state.turn_count == 2

    def test_update_location_with_npcs(self, game_state):
        """Test updating location with NPCs."""
        game_state.update_location("tavern", npc_ids=["bartender", "merchant"])
        assert game_state.current_location == "tavern"
        assert "bartender" in game_state.active_npc_ids
        assert "merchant" in game_state.active_npc_ids

    def test_update_location_without_npcs(self, game_state):
        """Test updating location without changing NPCs."""
        game_state.active_npc_ids = ["existing_npc"]
        game_state.update_location("forest")
        assert game_state.current_location == "forest"
        assert "existing_npc" in game_state.active_npc_ids

    def test_set_phase_with_next_agent(self, game_state):
        """Test setting phase with next agent."""
        game_state.set_phase(GamePhase.PROCESSING, next_agent="rule_agent")
        assert game_state.current_phase == GamePhase.PROCESSING
        assert game_state.next_agent == "rule_agent"

    def test_game_state_repr(self, game_state):
        """Test game state string representation."""
        repr_str = repr(game_state)
        assert "test-extended-session" in repr_str
        assert "测试角色" in repr_str

    def test_get_recent_messages_empty(self, game_state):
        """Test getting recent messages when history is empty."""
        messages = game_state.get_recent_messages(5)
        assert messages == []

    def test_get_recent_messages_overflow(self, game_state):
        """Test getting more messages than available."""
        game_state.add_message("player", "Hello")
        game_state.add_message("gm", "Hi there")
        messages = game_state.get_recent_messages(10)
        assert len(messages) == 2

    def test_message_metadata(self, game_state):
        """Test message with metadata."""
        game_state.add_message("gm", "Test message", metadata={"agent": "gm_agent"})
        messages = game_state.get_recent_messages(1)
        assert messages[0]["metadata"]["agent"] == "gm_agent"


class TestTraitModel:
    """Tests for Trait model."""

    def test_trait_creation(self):
        """Test creating a trait."""
        trait = Trait(
            name=LocalizedString(cn="强壮", en="Strong"),
            description=LocalizedString(cn="体格强健", en="Physically fit"),
            positive_aspect=LocalizedString(cn="力量大", en="Great strength"),
            negative_aspect=LocalizedString(cn="笨重", en="Clumsy"),
        )
        assert trait.name.get("cn") == "强壮"
        assert trait.name.get("en") == "Strong"

    def test_trait_localized_fields(self):
        """Test all localized fields in trait."""
        trait = Trait(
            name=LocalizedString(cn="智慧", en="Wise"),
            description=LocalizedString(cn="博学多识", en="Knowledgeable"),
            positive_aspect=LocalizedString(cn="见多识广", en="Well-informed"),
            negative_aspect=LocalizedString(cn="傲慢", en="Arrogant"),
        )
        assert trait.description.get("cn") == "博学多识"
        assert trait.description.get("en") == "Knowledgeable"
        assert trait.positive_aspect.get("cn") == "见多识广"
        assert trait.negative_aspect.get("en") == "Arrogant"

    def test_trait_compatibility_properties(self):
        """Test backward compatibility properties."""
        trait = Trait(
            name=LocalizedString(cn="勇敢", en="Brave"),
            description=LocalizedString(cn="无畏", en="Fearless"),
            positive_aspect=LocalizedString(cn="勇气", en="Courage"),
            negative_aspect=LocalizedString(cn="鲁莽", en="Reckless"),
        )
        # Test name_cn and name_en properties
        assert trait.name_cn == "勇敢"
        assert trait.name_en == "Brave"

    def test_trait_get_methods(self):
        """Test trait get_* methods for all fields."""
        trait = Trait(
            name=LocalizedString(cn="聪明", en="Smart"),
            description=LocalizedString(cn="思维敏捷", en="Quick thinker"),
            positive_aspect=LocalizedString(cn="解决问题", en="Problem solver"),
            negative_aspect=LocalizedString(cn="自大", en="Arrogant"),
        )
        # Test get_name
        assert trait.get_name("cn") == "聪明"
        assert trait.get_name("en") == "Smart"

        # Test get_description
        assert trait.get_description("cn") == "思维敏捷"
        assert trait.get_description("en") == "Quick thinker"

        # Test get_positive
        assert trait.get_positive("cn") == "解决问题"
        assert trait.get_positive("en") == "Problem solver"

        # Test get_negative
        assert trait.get_negative("cn") == "自大"
        assert trait.get_negative("en") == "Arrogant"

    def test_trait_str_and_repr(self):
        """Test trait string representations."""
        trait = Trait(
            name=LocalizedString(cn="谨慎", en="Cautious"),
            description=LocalizedString(cn="小心行事", en="Acts carefully"),
            positive_aspect=LocalizedString(cn="避免风险", en="Avoids risks"),
            negative_aspect=LocalizedString(cn="犹豫不决", en="Hesitant"),
        )
        # Test __str__
        assert str(trait) == "谨慎"

        # Test __repr__
        repr_str = repr(trait)
        assert "Trait" in repr_str
        assert "谨慎" in repr_str


class TestLocalizedString:
    """Tests for LocalizedString model."""

    def test_localized_string_get_cn(self):
        """Test getting Chinese text."""
        ls = LocalizedString(cn="你好", en="Hello")
        assert ls.get("cn") == "你好"

    def test_localized_string_get_en(self):
        """Test getting English text."""
        ls = LocalizedString(cn="你好", en="Hello")
        assert ls.get("en") == "Hello"

    def test_localized_string_get_default(self):
        """Test getting default (Chinese) text."""
        ls = LocalizedString(cn="你好", en="Hello")
        assert ls.get() == "你好"

    def test_localized_string_fallback_to_cn(self):
        """Test fallback to Chinese for unknown language."""
        ls = LocalizedString(cn="你好", en="Hello")
        # Unknown language should fall back to cn
        assert ls.get("fr") == "你好"

    def test_localized_string_str(self):
        """Test string representation."""
        ls = LocalizedString(cn="你好", en="Hello")
        assert str(ls) == "你好"

    def test_localized_string_repr(self):
        """Test repr representation."""
        ls = LocalizedString(cn="你好", en="Hello")
        repr_str = repr(ls)
        assert "你好" in repr_str
        assert "Hello" in repr_str


class TestGamePhaseEnum:
    """Tests for GamePhase enum."""

    def test_all_phases_exist(self):
        """Test all expected phases are defined."""
        expected_phases = [
            "waiting_input",
            "processing",
            "dice_check",
            "npc_response",
            "narrating",
        ]
        actual_values = [phase.value for phase in GamePhase]
        for expected in expected_phases:
            assert expected in actual_values

    def test_phase_string_values(self):
        """Test phase values are strings."""
        for phase in GamePhase:
            assert isinstance(phase.value, str)

    def test_phase_comparison(self):
        """Test phase equality comparison."""
        assert GamePhase.WAITING_INPUT == GamePhase.WAITING_INPUT
        assert GamePhase.WAITING_INPUT != GamePhase.PROCESSING


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
