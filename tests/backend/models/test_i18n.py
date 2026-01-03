"""Tests for LocalizedString."""

import pytest

from src.backend.models.i18n import LocalizedString


class TestLocalizedString:
    """Test suite for LocalizedString class."""

    def test_create_localized_string(self):
        """Test creating a LocalizedString with both languages."""
        text = LocalizedString(cn="你好", en="Hello")
        assert text.cn == "你好"
        assert text.en == "Hello"

    def test_get_chinese(self):
        """Test getting Chinese text."""
        text = LocalizedString(cn="你好", en="Hello")
        assert text.get("cn") == "你好"

    def test_get_english(self):
        """Test getting English text."""
        text = LocalizedString(cn="你好", en="Hello")
        assert text.get("en") == "Hello"

    def test_fallback_to_chinese(self):
        """Test fallback to Chinese for unsupported language."""
        text = LocalizedString(cn="你好", en="Hello")
        assert text.get("fr") == "你好"  # Falls back to cn

    def test_default_language_is_chinese(self):
        """Test that default language is Chinese."""
        text = LocalizedString(cn="你好", en="Hello")
        assert text.get() == "你好"

    def test_str_returns_chinese(self):
        """Test __str__ returns Chinese version."""
        text = LocalizedString(cn="你好", en="Hello")
        assert str(text) == "你好"

    def test_repr_shows_both_languages(self):
        """Test __repr__ shows both language versions."""
        text = LocalizedString(cn="你好", en="Hello")
        repr_str = repr(text)
        assert "你好" in repr_str
        assert "Hello" in repr_str

    def test_validation_requires_both_languages(self):
        """Test that both cn and en are required."""
        with pytest.raises(ValueError):
            LocalizedString(cn="你好")  # Missing en

        with pytest.raises(ValueError):
            LocalizedString(en="Hello")  # Missing cn
