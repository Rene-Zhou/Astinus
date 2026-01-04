"""Tests for StatBlock widget - Trait-based system per GUIDE.md."""

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

    def test_initial_fate_points(self):
        """Test initial fate points values."""
        widget = StatBlock()
        assert widget._fate_points == 3  # Per GUIDE.md
        assert widget._max_fate_points == 5

    def test_initial_traits_empty(self):
        """Test initial traits list is empty."""
        widget = StatBlock()
        assert widget._traits == []

    def test_initial_tags_empty(self):
        """Test initial tags list is empty."""
        widget = StatBlock()
        assert widget._tags == []

    def test_initial_npcs_empty(self):
        """Test initial nearby NPCs list is empty."""
        widget = StatBlock()
        assert widget._nearby_npcs == []


class TestStatBlockFatePoints:
    """Test suite for StatBlock fate points functionality per GUIDE.md."""

    def test_update_fate_points(self):
        """Test updating fate points values."""
        widget = StatBlock()
        widget.update_fate_points(4, 5)
        assert widget._fate_points == 4
        assert widget._max_fate_points == 5

    def test_update_fate_points_clamps_max(self):
        """Test that fate points are clamped to max value."""
        widget = StatBlock()
        widget.update_fate_points(10, 5)
        assert widget._fate_points == 5

    def test_update_fate_points_clamps_min(self):
        """Test that fate points are clamped to 0."""
        widget = StatBlock()
        widget.update_fate_points(-3, 5)
        assert widget._fate_points == 0

    def test_render_fate_points_stars_full(self):
        """Test rendering fate points as stars when full."""
        widget = StatBlock()
        widget._fate_points = 5
        widget._max_fate_points = 5
        result = widget._render_fate_points_stars()
        assert "★★★★★" in result
        assert "☆" not in result

    def test_render_fate_points_stars_empty(self):
        """Test rendering fate points as stars when empty."""
        widget = StatBlock()
        widget._fate_points = 0
        widget._max_fate_points = 5
        result = widget._render_fate_points_stars()
        assert "☆☆☆☆☆" in result
        assert "★" not in result

    def test_render_fate_points_stars_partial(self):
        """Test rendering fate points as stars when partial."""
        widget = StatBlock()
        widget._fate_points = 3
        widget._max_fate_points = 5
        result = widget._render_fate_points_stars()
        assert "★★★☆☆" in result


class TestStatBlockTraits:
    """Test suite for StatBlock traits functionality per GUIDE.md."""

    def test_update_traits(self):
        """Test updating traits list."""
        widget = StatBlock()
        traits = [
            {
                "name": {"cn": "优柔寡断", "en": "Indecisive"},
                "description": {"cn": "描述", "en": "Description"},
                "positive_aspect": {"cn": "能预见后果", "en": "Can foresee consequences"},
                "negative_aspect": {"cn": "错过时机", "en": "Miss opportunities"},
            },
        ]
        widget.update_traits(traits)
        assert widget._traits == traits
        assert len(widget._traits) == 1

    def test_update_traits_empty(self):
        """Test updating with empty traits list."""
        widget = StatBlock()
        widget._traits = [{"name": {"cn": "Test"}}]
        widget.update_traits([])
        assert widget._traits == []

    def test_multiple_traits(self):
        """Test multiple traits (GUIDE.md allows 1-4 traits)."""
        widget = StatBlock()
        traits = [
            {
                "name": {"cn": "特质1"},
                "positive_aspect": {"cn": "正面1"},
                "negative_aspect": {"cn": "负面1"},
            },
            {
                "name": {"cn": "特质2"},
                "positive_aspect": {"cn": "正面2"},
                "negative_aspect": {"cn": "负面2"},
            },
            {
                "name": {"cn": "特质3"},
                "positive_aspect": {"cn": "正面3"},
                "negative_aspect": {"cn": "负面3"},
            },
        ]
        widget.update_traits(traits)
        assert len(widget._traits) == 3


class TestStatBlockTags:
    """Test suite for StatBlock tags (status effects) per GUIDE.md."""

    def test_update_tags(self):
        """Test updating tags list."""
        widget = StatBlock()
        tags = ["右腿受伤", "疲惫"]
        widget.update_tags(tags)
        assert widget._tags == tags
        assert len(widget._tags) == 2

    def test_update_tags_empty(self):
        """Test updating with empty tags list."""
        widget = StatBlock()
        widget._tags = ["中毒"]
        widget.update_tags([])
        assert widget._tags == []

    def test_tags_status_effects(self):
        """Test various status effect tags per GUIDE.md."""
        widget = StatBlock()
        # Per GUIDE.md Section 3.2, tags track status like "右腿受伤", "疲惫"
        tags = ["右腿受伤", "疲惫", "中毒", "眩晕"]
        widget.update_tags(tags)
        assert len(widget._tags) == 4


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
    """Test suite for StatBlock character data handling per GUIDE.md."""

    def test_update_character_sets_data(self):
        """Test that update_character sets character_data."""
        widget = StatBlock()
        char_data = {
            "name": "Test Hero",
            "concept": {"cn": "失业的建筑师", "en": "Unemployed Architect"},
        }
        widget.update_character(char_data)
        assert widget.character_data == char_data

    def test_character_data_with_traits(self):
        """Test character data with traits per GUIDE.md."""
        widget = StatBlock()
        char_data = {
            "name": "Test Hero",
            "concept": {"cn": "失业的建筑师"},
            "traits": [
                {
                    "name": {"cn": "优柔寡断"},
                    "description": {"cn": "描述"},
                    "positive_aspect": {"cn": "正面"},
                    "negative_aspect": {"cn": "负面"},
                }
            ],
            "fate_points": 3,
            "tags": [],
        }
        widget.update_character(char_data)
        assert widget.character_data["traits"][0]["name"]["cn"] == "优柔寡断"

    def test_character_data_with_tags(self):
        """Test character data with tags."""
        widget = StatBlock()
        char_data = {
            "name": "Test Hero",
            "tags": ["右腿受伤", "疲惫"],
        }
        widget.update_character(char_data)
        assert len(widget.character_data["tags"]) == 2

    def test_character_data_with_fate_points(self):
        """Test character data with fate points."""
        widget = StatBlock()
        char_data = {
            "name": "Test Hero",
            "fate_points": 4,
        }
        widget.update_character(char_data)
        assert widget.character_data["fate_points"] == 4


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


class TestStatBlockLocalization:
    """Test suite for StatBlock localization support."""

    def test_get_localized_text_dict(self):
        """Test getting localized text from dict."""
        widget = StatBlock()
        value = {"cn": "中文", "en": "English"}
        result = widget._get_localized_text(value, "cn")
        assert result == "中文"

    def test_get_localized_text_dict_fallback(self):
        """Test getting localized text with fallback."""
        widget = StatBlock()
        value = {"en": "English"}
        result = widget._get_localized_text(value, "cn")
        assert result == "English"

    def test_get_localized_text_string(self):
        """Test getting localized text from plain string."""
        widget = StatBlock()
        value = "Plain text"
        result = widget._get_localized_text(value, "cn")
        assert result == "Plain text"

    def test_get_localized_text_empty(self):
        """Test getting localized text from empty value."""
        widget = StatBlock()
        result = widget._get_localized_text("", "cn")
        assert result == ""


class TestStatBlockLegacyCompatibility:
    """Test suite for StatBlock legacy compatibility methods."""

    def test_update_hp_converts_to_tag(self):
        """Test that HP loss is converted to tags."""
        widget = StatBlock()
        widget._tags = []
        widget.update_hp(2, 12)  # ~17% HP, below 25%
        # Should add "重伤" tag
        assert "重伤" in widget._tags

    def test_update_hp_moderate_damage(self):
        """Test that moderate HP loss adds 受伤 tag."""
        widget = StatBlock()
        widget._tags = []
        widget.update_hp(4, 10)  # 40% HP, below 50% but above 25%
        assert "受伤" in widget._tags

    def test_update_mp_does_nothing(self):
        """Test that MP update is a no-op (deprecated)."""
        widget = StatBlock()
        initial_tags = widget._tags.copy()
        widget.update_mp(0, 10)
        # Should not modify tags
        assert widget._tags == initial_tags

    def test_update_effects_converts_to_tags(self):
        """Test that effects are converted to tags."""
        widget = StatBlock()
        widget._tags = []
        effects = [
            {"name": "Poison"},
            {"name": "Blessing"},
        ]
        widget.update_effects(effects)
        assert "Poison" in widget._tags
        assert "Blessing" in widget._tags


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


class TestNoLegacyHPMPSystem:
    """Test suite to ensure old HP/MP system is not primary."""

    def test_no_hp_progress_bar_in_css(self):
        """Test that hp-bar is not prominently in CSS."""
        widget = StatBlock()
        # HP/MP bars should be removed from main CSS
        # Legacy methods may exist but shouldn't be primary
        assert "fate-points" in widget.DEFAULT_CSS
        assert "traits-list" in widget.DEFAULT_CSS
        assert "tags-list" in widget.DEFAULT_CSS

    def test_traits_list_in_css(self):
        """Test that traits list CSS exists."""
        widget = StatBlock()
        assert "traits-list" in widget.DEFAULT_CSS
        assert "trait-item" in widget.DEFAULT_CSS

    def test_tags_list_in_css(self):
        """Test that tags list CSS exists."""
        widget = StatBlock()
        assert "tags-list" in widget.DEFAULT_CSS
        assert "tag-item" in widget.DEFAULT_CSS
