"""Tests for Trait model."""

import pytest

from src.backend.models.i18n import LocalizedString
from src.backend.models.trait import Trait


class TestTrait:
    """Test suite for Trait class."""

    @pytest.fixture
    def sample_trait(self):
        """Create a sample trait for testing."""
        return Trait(
            name=LocalizedString(cn="优柔寡断", en="Indecisive"),
            description=LocalizedString(
                cn="在行动前总是会思考许多，在脑内预演所能想象到的可能性",
                en="Always thinks through many scenarios before acting",
            ),
            positive_aspect=LocalizedString(
                cn="能预演各种可能性，从而做出更明智的决策",
                en="Can anticipate outcomes and make wiser decisions",
            ),
            negative_aspect=LocalizedString(
                cn="常常因为过度思考而错过最佳时机",
                en="Often misses opportunities due to overthinking",
            ),
        )

    def test_create_trait(self, sample_trait):
        """Test creating a trait with all fields."""
        assert sample_trait.name.cn == "优柔寡断"
        assert sample_trait.name.en == "Indecisive"

    def test_get_name_chinese(self, sample_trait):
        """Test getting trait name in Chinese."""
        assert sample_trait.get_name("cn") == "优柔寡断"

    def test_get_name_english(self, sample_trait):
        """Test getting trait name in English."""
        assert sample_trait.get_name("en") == "Indecisive"

    def test_get_description(self, sample_trait):
        """Test getting trait description."""
        desc_cn = sample_trait.get_description("cn")
        assert "思考" in desc_cn

        desc_en = sample_trait.get_description("en")
        assert "thinks" in desc_en

    def test_get_positive_aspect(self, sample_trait):
        """Test getting positive aspect."""
        positive_cn = sample_trait.get_positive("cn")
        assert "明智" in positive_cn

        positive_en = sample_trait.get_positive("en")
        assert "wiser" in positive_en

    def test_get_negative_aspect(self, sample_trait):
        """Test getting negative aspect."""
        negative_cn = sample_trait.get_negative("cn")
        assert "过度思考" in negative_cn

        negative_en = sample_trait.get_negative("en")
        assert "overthinking" in negative_en

    def test_backward_compatibility_properties(self, sample_trait):
        """Test backward compatibility properties for weave."""
        assert sample_trait.name_cn == "优柔寡断"
        assert sample_trait.name_en == "Indecisive"

    def test_str_returns_chinese_name(self, sample_trait):
        """Test __str__ returns Chinese name."""
        assert str(sample_trait) == "优柔寡断"

    def test_repr_shows_name(self, sample_trait):
        """Test __repr__ contains trait name."""
        repr_str = repr(sample_trait)
        assert "优柔寡断" in repr_str
        assert "Trait" in repr_str

    def test_trait_validation_requires_all_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValueError):
            Trait(
                name=LocalizedString(cn="测试", en="Test"),
                description=LocalizedString(cn="描述", en="Description"),
                positive_aspect=LocalizedString(cn="正面", en="Positive"),
                # Missing negative_aspect
            )
