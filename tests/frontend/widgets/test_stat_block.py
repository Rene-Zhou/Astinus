"""Tests for StatBlock widget."""

import pytest

from src.frontend.widgets.stat_block import StatBlock


class TestStatBlock:
    """Test suite for StatBlock widget."""

    def test_create_stat_block(self):
        """Test creating the stat block widget."""
        widget = StatBlock()
        assert widget is not None

    def test_stat_block_has_css(self):
        """Test that stat block has CSS styles defined."""
        widget = StatBlock()
        assert widget.DEFAULT_CSS is not None
        assert "stat-label" in widget.DEFAULT_CSS
        assert "stat-value" in widget.DEFAULT_CSS

    def test_initial_hp_values(self):
        """Test initial HP values."""
        widget = StatBlock()
        assert widget._hp_current == 10
        assert widget._hp_max == 10

    def test_initial_mp_values(self):
        """Test initial MP values."""
        widget = StatBlock()
        assert widget._mp_current == 5
        assert widget._mp_max == 5

    def test_initial_effects_empty(self):
        """Test initial effects list is empty."""
        widget = StatBlock()
        assert widget._effects == []

    def test_initial_npcs_empty(self):
        """Test initial nearby NPCs list is empty."""
        widget = StatBlock()
        assert widget._nearby_npcs == []


class TestStatBlockHPMP:
    """Test suite for StatBlock HP/MP functionality."""

    def test_update_hp(self):
        """Test updating HP values."""
        widget = StatBlock()
        widget.update_hp(5, 10)
        assert widget._hp_current == 5
        assert widget._hp_max == 10

    def test_update_hp_clamps_max(self):
        """Test that HP is clamped to max value."""
        widget = StatBlock()
        widget.update_hp(15, 10)
        assert widget._hp_current == 10

    def test_update_hp_clamps_min(self):
        """Test that HP is clamped to 0."""
        widget = StatBlock()
        widget.update_hp(-5, 10)
        assert widget._hp_current == 0

    def test_update_mp(self):
        """Test updating MP values."""
        widget = StatBlock()
        widget.update_mp(3, 8)
        assert widget._mp_current == 3
        assert widget._mp_max == 8

    def test_update_mp_clamps_max(self):
        """Test that MP is clamped to max value."""
        widget = StatBlock()
        widget.update_mp(20, 5)
        assert widget._mp_current == 5

    def test_update_mp_clamps_min(self):
        """Test that MP is clamped to 0."""
        widget = StatBlock()
        widget.update_mp(-3, 5)
        assert widget._mp_current == 0


class TestStatBlockEffects:
    """Test suite for StatBlock effects functionality."""

    def test_update_effects(self):
        """Test updating effects list."""
        widget = StatBlock()
        effects = [
            {"name": "Poison", "type": "debuff", "duration": 3},
            {"name": "Shield", "type": "buff", "duration": 5},
        ]
        widget.update_effects(effects)
        assert widget._effects == effects
        assert len(widget._effects) == 2

    def test_update_effects_empty(self):
        """Test updating with empty effects list."""
        widget = StatBlock()
        widget._effects = [{"name": "Test", "type": "buff"}]
        widget.update_effects([])
        assert widget._effects == []

    def test_effects_types(self):
        """Test various effect types."""
        widget = StatBlock()
        effects = [
            {"name": "Buff Effect", "type": "buff"},
            {"name": "Debuff Effect", "type": "debuff"},
            {"name": "Neutral Effect", "type": "neutral"},
        ]
        widget.update_effects(effects)
        assert len(widget._effects) == 3


class TestStatBlockNPCs:
    """Test suite for StatBlock NPC functionality."""

    def test_update_nearby_npcs(self):
        """Test updating nearby NPCs list."""
        widget = StatBlock()
        npcs = [
            {"name": "Friendly Guard", "disposition": "friendly"},
            {"name": "Angry Orc", "disposition": "hostile"},
        ]
        widget.update_nearby_npcs(npcs)
        assert widget._nearby_npcs == npcs
        assert len(widget._nearby_npcs) == 2

    def test_update_npcs_empty(self):
        """Test updating with empty NPCs list."""
        widget = StatBlock()
        widget._nearby_npcs = [{"name": "Test NPC"}]
        widget.update_nearby_npcs([])
        assert widget._nearby_npcs == []

    def test_npc_dispositions(self):
        """Test various NPC dispositions."""
        widget = StatBlock()
        npcs = [
            {"name": "Friend", "disposition": "friendly"},
            {"name": "Enemy", "disposition": "hostile"},
            {"name": "Stranger", "disposition": "neutral"},
        ]
        widget.update_nearby_npcs(npcs)
        assert len(widget._nearby_npcs) == 3


class TestStatBlockCharacterData:
    """Test suite for StatBlock character data handling."""

    def test_update_character_sets_data(self):
        """Test that update_character sets character_data."""
        widget = StatBlock()
        char_data = {
            "name": "Test Hero",
            "concept": "warrior",
        }
        widget.update_character(char_data)
        assert widget.character_data == char_data

    def test_character_data_with_attributes(self):
        """Test character data with attributes."""
        widget = StatBlock()
        char_data = {
            "name": "Test Hero",
            "concept": "warrior",
            "attributes": {
                "strength": 2,
                "dexterity": 1,
                "intelligence": 0,
                "charisma": -1,
                "perception": 1,
            },
        }
        widget.update_character(char_data)
        assert widget.character_data["attributes"]["strength"] == 2

    def test_character_data_with_hp_mp(self):
        """Test character data with HP and MP."""
        widget = StatBlock()
        char_data = {
            "name": "Test Hero",
            "hp": {"current": 8, "max": 12},
            "mp": {"current": 3, "max": 6},
        }
        widget.update_character(char_data)
        # Note: _update_hp_bar and _update_mp_bar are called but may fail
        # without widget being mounted, so we just check the data is stored
        assert widget.character_data["hp"]["current"] == 8

    def test_character_data_with_effects(self):
        """Test character data with effects."""
        widget = StatBlock()
        char_data = {
            "name": "Test Hero",
            "effects": [
                {"name": "Blessing", "type": "buff", "duration": 3},
            ],
        }
        widget.update_character(char_data)
        assert len(widget.character_data["effects"]) == 1


class TestStatBlockGameState:
    """Test suite for StatBlock game state handling."""

    def test_update_game_state_sets_data(self):
        """Test that update_game_state sets game_state_data."""
        widget = StatBlock()
        game_state = {
            "current_location": "Town Square",
            "current_phase": "Exploration",
            "turn_count": 5,
        }
        widget.update_game_state(game_state)
        assert widget.game_state_data == game_state

    def test_game_state_with_npcs(self):
        """Test game state with nearby NPCs."""
        widget = StatBlock()
        game_state = {
            "current_location": "Tavern",
            "nearby_npcs": [
                {"name": "Bartender", "disposition": "friendly"},
            ],
        }
        widget.update_game_state(game_state)
        assert len(widget.game_state_data["nearby_npcs"]) == 1


class TestStatBlockFormatting:
    """Test suite for StatBlock formatting functions."""

    def test_format_attribute_positive(self):
        """Test formatting positive attribute value."""
        widget = StatBlock()
        result = widget._format_attribute_value(2)
        assert result == "+2"

    def test_format_attribute_negative(self):
        """Test formatting negative attribute value."""
        widget = StatBlock()
        result = widget._format_attribute_value(-1)
        assert result == "-1"

    def test_format_attribute_zero(self):
        """Test formatting zero attribute value."""
        widget = StatBlock()
        result = widget._format_attribute_value(0)
        assert result == "0"

    def test_format_attribute_large_positive(self):
        """Test formatting large positive attribute value."""
        widget = StatBlock()
        result = widget._format_attribute_value(3)
        assert result == "+3"

    def test_format_attribute_large_negative(self):
        """Test formatting large negative attribute value."""
        widget = StatBlock()
        result = widget._format_attribute_value(-2)
        assert result == "-2"


class TestStatBlockCompose:
    """Test suite for StatBlock compose method."""

    def test_compose_method_exists(self):
        """Test that compose method exists."""
        widget = StatBlock()
        assert hasattr(widget, "compose")
        assert callable(widget.compose)

    def test_compose_returns_generator(self):
        """Test that compose returns a generator."""
        widget = StatBlock()
        result = widget.compose()
        # ComposeResult is a generator
        assert hasattr(result, "__iter__")
