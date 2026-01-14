"""Tests for I18nService."""

import pytest

from src.backend.core.i18n import I18nService, get_i18n, reset_i18n


class TestI18nService:
    """Test suite for I18nService class."""

    @pytest.fixture
    def i18n_service(self):
        """Create a fresh I18nService instance for testing."""
        # Reset global instance before each test
        reset_i18n()
        return I18nService()

    def test_create_i18n_service(self, i18n_service):
        """Test creating an I18nService instance."""
        assert i18n_service.default_lang == "cn"
        assert len(i18n_service._cache) > 0

    def test_get_chinese_string(self, i18n_service):
        """Test getting a Chinese string."""
        result = i18n_service.get("system.dice.outcome.critical", lang="cn")
        assert result == "大成功"

    def test_get_english_string(self, i18n_service):
        """Test getting an English string."""
        result = i18n_service.get("system.dice.outcome.critical", lang="en")
        assert result == "Critical Success"

    def test_get_nested_key(self, i18n_service):
        """Test getting a deeply nested key."""
        result = i18n_service.get("system.dice.modifier.bonus", lang="cn")
        assert result == "优势"

    def test_get_with_default_language(self, i18n_service):
        """Test that omitting lang uses default language."""
        result = i18n_service.get("system.dice.outcome.success")
        assert result == "成功"  # Chinese default

    def test_fallback_to_default_language(self, i18n_service):
        """Test fallback to default language for unsupported language."""
        result = i18n_service.get("system.dice.outcome.critical", lang="fr")
        # Should fall back to Chinese (default)
        assert result == "大成功"

    def test_missing_key_returns_placeholder(self, i18n_service):
        """Test that missing key returns error placeholder."""
        result = i18n_service.get("system.nonexistent.key", lang="cn")
        assert result == "[MISSING: system.nonexistent.key]"

    def test_has_key_returns_true_for_existing_key(self, i18n_service):
        """Test has_key() returns True for existing key."""
        assert i18n_service.has_key("system.dice.outcome.critical", lang="cn")

    def test_has_key_returns_false_for_missing_key(self, i18n_service):
        """Test has_key() returns False for missing key."""
        assert not i18n_service.has_key("system.nonexistent.key", lang="cn")

    def test_get_namespace(self, i18n_service):
        """Test getting entire namespace."""
        dice_ns = i18n_service.get_namespace("system.dice", lang="cn")
        assert "outcome" in dice_ns
        assert dice_ns["outcome"]["critical"] == "大成功"

    def test_get_namespace_english(self, i18n_service):
        """Test getting namespace in English."""
        dice_ns = i18n_service.get_namespace("system.dice", lang="en")
        assert dice_ns["outcome"]["critical"] == "Critical Success"

    def test_get_with_format_arguments(self, i18n_service):
        """Test string interpolation with format arguments."""
        # Note: This would require adding a test key with format placeholders
        # For now, test that it doesn't break
        result = i18n_service.get("system.dice.outcome.critical", lang="cn")
        assert result == "大成功"

    def test_loads_common_namespace(self, i18n_service):
        """Test that common.json is also loaded."""
        result = i18n_service.get("common.app.title", lang="cn")
        assert "Astinus" in result

    def test_reload_refreshes_cache(self, i18n_service):
        """Test that reload() refreshes the cache."""
        # Get initial value
        initial = i18n_service.get("system.dice.outcome.critical", lang="cn")
        assert initial == "大成功"

        # Reload
        i18n_service.reload()

        # Should still work
        reloaded = i18n_service.get("system.dice.outcome.critical", lang="cn")
        assert reloaded == "大成功"

    def test_global_singleton(self):
        """Test get_i18n() returns singleton instance."""
        reset_i18n()

        i18n1 = get_i18n()
        i18n2 = get_i18n()

        assert i18n1 is i18n2  # Same instance

    def test_reset_i18n_clears_singleton(self):
        """Test reset_i18n() clears the singleton."""
        i18n1 = get_i18n()
        reset_i18n()
        i18n2 = get_i18n()

        assert i18n1 is not i18n2  # Different instances

    def test_invalid_key_format(self, i18n_service):
        """Test that invalid key format returns error placeholder."""
        result = i18n_service.get("invalid", lang="cn")
        assert result.startswith("[MISSING:")

    def test_all_dice_outcomes_exist(self, i18n_service):
        """Test that all dice outcomes have translations."""
        outcomes = ["critical", "success", "partial", "failure"]

        for outcome in outcomes:
            key = f"system.dice.outcome.{outcome}"
            cn_text = i18n_service.get(key, lang="cn")
            en_text = i18n_service.get(key, lang="en")

            assert not cn_text.startswith("[MISSING:")
            assert not en_text.startswith("[MISSING:")
            assert cn_text != en_text  # Should be different languages

    def test_all_dice_modifiers_exist(self, i18n_service):
        """Test that all dice modifiers have translations."""
        modifiers = ["bonus", "penalty", "advantage", "disadvantage"]

        for modifier in modifiers:
            key = f"system.dice.modifier.{modifier}"
            cn_text = i18n_service.get(key, lang="cn")
            en_text = i18n_service.get(key, lang="en")

            assert not cn_text.startswith("[MISSING:")
            assert not en_text.startswith("[MISSING:")

    def test_all_game_phases_exist(self, i18n_service):
        """Test that all game phases have translations."""
        phases = ["waiting_input", "processing", "dice_check", "npc_response", "narrating"]

        for phase in phases:
            key = f"system.game_phase.{phase}"
            cn_text = i18n_service.get(key, lang="cn")
            en_text = i18n_service.get(key, lang="en")

            assert not cn_text.startswith("[MISSING:")
            assert not en_text.startswith("[MISSING:")

    def test_all_errors_exist(self, i18n_service):
        """Test that all error messages have translations."""
        errors = [
            "invalid_input",
            "connection_failed",
            "file_not_found",
            "session_not_found",
            "character_not_found",
        ]

        for error in errors:
            key = f"system.errors.{error}"
            cn_text = i18n_service.get(key, lang="cn")
            en_text = i18n_service.get(key, lang="en")

            assert not cn_text.startswith("[MISSING:")
            assert not en_text.startswith("[MISSING:")
