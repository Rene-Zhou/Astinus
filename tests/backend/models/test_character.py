"""Tests for PlayerCharacter model."""

import pytest
from pydantic import ValidationError

from src.backend.models.character import PlayerCharacter
from src.backend.models.i18n import LocalizedString
from src.backend.models.trait import Trait


class TestPlayerCharacter:
    """Test suite for PlayerCharacter class."""

    @pytest.fixture
    def sample_trait(self):
        """Create a sample trait."""
        return Trait(
            name=LocalizedString(cn="运动健将", en="Athletic"),
            description=LocalizedString(
                cn="多年的体育训练让你拥有出色的身体素质",
                en="Years of training gave you excellent physical condition",
            ),
            positive_aspect=LocalizedString(
                cn="在需要体力和敏捷的场合表现出色",
                en="Excel in situations requiring strength and agility",
            ),
            negative_aspect=LocalizedString(
                cn="倾向于用蛮力解决问题而非思考", en="Tend to use brute force instead of thinking"
            ),
        )

    @pytest.fixture
    def sample_character(self, sample_trait):
        """Create a sample character for testing."""
        return PlayerCharacter(
            name="张伟",
            concept=LocalizedString(cn="失业的建筑师", en="Unemployed Architect"),
            traits=[sample_trait],
            fate_points=3,
            tags=[],
        )

    def test_create_character(self, sample_character):
        """Test creating a character with required fields."""
        assert sample_character.name == "张伟"
        assert sample_character.concept.cn == "失业的建筑师"
        assert len(sample_character.traits) == 1
        assert sample_character.fate_points == 3

    def test_character_must_have_at_least_one_trait(self):
        """Test that character must have at least one trait."""
        with pytest.raises(ValidationError):
            PlayerCharacter(
                name="测试",
                concept=LocalizedString(cn="测试", en="Test"),
                traits=[],  # Empty traits list
                fate_points=3,
            )

    def test_character_cannot_have_more_than_four_traits(self, sample_trait):
        """Test that character cannot have more than 4 traits."""
        with pytest.raises(ValidationError):
            PlayerCharacter(
                name="测试",
                concept=LocalizedString(cn="测试", en="Test"),
                traits=[sample_trait] * 5,  # 5 traits
                fate_points=3,
            )

    def test_add_tag(self, sample_character):
        """Test adding a tag to character."""
        sample_character.add_tag("右腿受伤")
        assert "右腿受伤" in sample_character.tags

    def test_add_tag_does_not_duplicate(self, sample_character):
        """Test that adding the same tag twice doesn't duplicate."""
        sample_character.add_tag("右腿受伤")
        sample_character.add_tag("右腿受伤")
        assert sample_character.tags.count("右腿受伤") == 1

    def test_remove_tag(self, sample_character):
        """Test removing a tag from character."""
        sample_character.add_tag("右腿受伤")
        sample_character.remove_tag("右腿受伤")
        assert "右腿受伤" not in sample_character.tags

    def test_remove_nonexistent_tag_does_not_error(self, sample_character):
        """Test that removing a non-existent tag doesn't error."""
        sample_character.remove_tag("不存在的标签")  # Should not raise

    def test_has_tag(self, sample_character):
        """Test checking if character has a tag."""
        sample_character.add_tag("右腿受伤")
        assert sample_character.has_tag("右腿受伤")
        assert not sample_character.has_tag("不存在的标签")

    def test_spend_fate_point(self, sample_character):
        """Test spending a fate point."""
        assert sample_character.fate_points == 3
        result = sample_character.spend_fate_point()
        assert result is True
        assert sample_character.fate_points == 2

    def test_cannot_spend_fate_point_when_zero(self, sample_character):
        """Test that cannot spend fate point when at zero."""
        sample_character.fate_points = 0
        result = sample_character.spend_fate_point()
        assert result is False
        assert sample_character.fate_points == 0

    def test_gain_fate_point(self, sample_character):
        """Test gaining a fate point."""
        assert sample_character.fate_points == 3
        result = sample_character.gain_fate_point()
        assert result is True
        assert sample_character.fate_points == 4

    def test_cannot_gain_fate_point_at_max(self, sample_character):
        """Test that cannot gain fate point when at max (5)."""
        sample_character.fate_points = 5
        result = sample_character.gain_fate_point()
        assert result is False
        assert sample_character.fate_points == 5

    def test_get_concept(self, sample_character):
        """Test getting character concept in different languages."""
        assert sample_character.get_concept("cn") == "失业的建筑师"
        assert sample_character.get_concept("en") == "Unemployed Architect"

    def test_str_returns_name(self, sample_character):
        """Test __str__ returns character name."""
        assert str(sample_character) == "张伟"

    def test_repr_shows_stats(self, sample_character):
        """Test __repr__ contains character stats."""
        repr_str = repr(sample_character)
        assert "张伟" in repr_str
        assert "traits=1" in repr_str
        assert "fate=3" in repr_str

    def test_fate_points_bounded(self):
        """Test that fate points are bounded between 0 and 5."""
        # This is enforced by Pydantic validation
        with pytest.raises(ValueError):
            PlayerCharacter(
                name="测试",
                concept=LocalizedString(cn="测试", en="Test"),
                traits=[
                    Trait(
                        name=LocalizedString(cn="特质", en="Trait"),
                        description=LocalizedString(cn="描述", en="Desc"),
                        positive_aspect=LocalizedString(cn="正", en="Pos"),
                        negative_aspect=LocalizedString(cn="负", en="Neg"),
                    )
                ],
                fate_points=10,  # Over max
            )
