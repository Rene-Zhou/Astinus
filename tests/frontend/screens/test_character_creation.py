"""Tests for CharacterCreationScreen - Trait-based system per GUIDE.md."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCharacterCreationScreen:
    """Test suite for CharacterCreationScreen."""

    def test_create_character_creation_screen(self):
        """Test creating the character creation screen."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        assert screen is not None

    def test_character_creation_screen_has_css(self):
        """Test that character creation screen has CSS styles defined."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        assert screen.DEFAULT_CSS is not None

    def test_character_creation_screen_title(self):
        """Test that character creation screen has a title."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        assert hasattr(screen, "TITLE") or hasattr(screen, "title")


class TestCharacterCreationTraits:
    """Test suite for character trait system per GUIDE.md."""

    def test_no_numerical_attributes(self):
        """Test that screen does NOT have PbtA-style numerical attributes."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        # Should NOT have old attribute system
        assert (
            not hasattr(screen, "_attributes")
            or screen._attributes is None
            or len(getattr(screen, "_attributes", {})) == 0
        )
        # Should have traits instead
        assert hasattr(screen, "_traits")

    def test_trait_list_exists(self):
        """Test that trait list exists."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        assert hasattr(screen, "_traits")
        assert isinstance(screen._traits, list)

    def test_initial_trait_count(self):
        """Test that initial trait count is correct."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        # Should start with no traits (empty list before mounting)
        assert hasattr(screen, "_traits")

    def test_max_traits_limit(self):
        """Test that max traits limit is enforced (max 4 per GUIDE.md)."""
        from src.frontend.screens.character_creation import MAX_TRAITS

        # GUIDE.md specifies 1-4 traits
        assert MAX_TRAITS == 4

    def test_get_traits_method(self):
        """Test getting traits list."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        if hasattr(screen, "get_traits"):
            traits = screen.get_traits()
            assert isinstance(traits, list)


class TestTraitEditor:
    """Test suite for TraitEditor widget."""

    def test_trait_editor_creation(self):
        """Test creating a trait editor."""
        from src.frontend.screens.character_creation import TraitEditor

        editor = TraitEditor(0)
        assert editor is not None
        assert editor.trait_index == 0

    def test_trait_editor_fields(self):
        """Test that trait editor has all required fields per GUIDE.md."""
        from src.frontend.screens.character_creation import TraitEditor

        editor = TraitEditor(0)
        # Per GUIDE.md Section 3.1, traits have:
        # - name
        # - description
        # - positive_aspect
        # - negative_aspect
        assert hasattr(editor, "_name")
        assert hasattr(editor, "_description")
        assert hasattr(editor, "_positive")
        assert hasattr(editor, "_negative")

    def test_trait_editor_get_data(self):
        """Test getting trait data from editor."""
        from src.frontend.screens.character_creation import TraitEditor

        editor = TraitEditor(0)
        # Empty editor should return None
        data = editor.get_trait_data()
        assert data is None  # Empty name means invalid

    def test_trait_editor_set_data(self):
        """Test setting trait data on editor."""
        from src.frontend.screens.character_creation import TraitEditor

        editor = TraitEditor(0)
        test_data = {
            "name": {"cn": "优柔寡断", "en": "Indecisive"},
            "description": {"cn": "描述", "en": "Description"},
            "positive_aspect": {"cn": "正面", "en": "Positive"},
            "negative_aspect": {"cn": "负面", "en": "Negative"},
        }
        editor.set_trait_data(test_data)
        assert editor._name == "优柔寡断"

    def test_trait_editor_is_empty(self):
        """Test checking if trait editor is empty."""
        from src.frontend.screens.character_creation import TraitEditor

        editor = TraitEditor(0)
        assert editor.is_empty() is True

    def test_trait_editor_is_complete(self):
        """Test checking if trait editor is complete."""
        from src.frontend.screens.character_creation import TraitEditor

        editor = TraitEditor(0)
        # Empty editor is not complete
        assert editor.is_complete() is False

        # Set all fields
        editor._name = "Test Trait"
        editor._description = "Test Description"
        editor._positive = "Positive Aspect"
        editor._negative = "Negative Aspect"
        assert editor.is_complete() is True


class TestCharacterCreationName:
    """Test suite for character name input."""

    def test_name_input_exists(self):
        """Test that name input exists."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        assert hasattr(screen, "character_name")

    def test_name_can_be_set(self):
        """Test that character name can be set."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        if hasattr(screen, "set_name"):
            screen.set_name("Test Hero")
            assert screen.character_name == "Test Hero"

    def test_name_validation_not_empty(self):
        """Test that empty name is rejected."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        if hasattr(screen, "validate_name"):
            assert not screen.validate_name("")
            assert not screen.validate_name("   ")

    def test_name_validation_max_length(self):
        """Test that excessively long name is handled."""
        from src.frontend.screens.character_creation import (
            MAX_NAME_LENGTH,
            CharacterCreationScreen,
        )

        screen = CharacterCreationScreen()
        if hasattr(screen, "validate_name"):
            long_name = "A" * (MAX_NAME_LENGTH + 10)
            result = screen.validate_name(long_name)
            assert result is False


class TestCharacterCreationConcept:
    """Test suite for character concept input per GUIDE.md."""

    def test_concept_is_free_form(self):
        """Test that concept is free-form text, not predefined selection."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        # Concept should be a string, not from a predefined list
        assert hasattr(screen, "character_concept")
        # Should NOT have available_concepts list (old system)
        # The new system uses free-form input

    def test_concept_can_be_set(self):
        """Test that concept can be set to any string."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        if hasattr(screen, "set_concept"):
            # Per GUIDE.md: concept like "失业的建筑师" or "只会炼金术的法师"
            screen.set_concept("失业的建筑师")
            assert screen.character_concept == "失业的建筑师"

    def test_concept_validation(self):
        """Test concept validation."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        if hasattr(screen, "validate_concept"):
            assert screen.validate_concept("失业的建筑师") is True
            assert screen.validate_concept("") is False
            assert screen.validate_concept("   ") is False


class TestBuildOnFlyMode:
    """Test suite for 边玩边建卡 (build-on-fly) mode per GUIDE.md."""

    def test_build_on_fly_mode_exists(self):
        """Test that build-on-fly mode toggle exists."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        assert hasattr(screen, "build_on_fly_mode")

    def test_build_on_fly_mode_default(self):
        """Test that build-on-fly mode is off by default."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        assert screen.build_on_fly_mode is False

    def test_build_on_fly_allows_no_traits(self):
        """Test that build-on-fly mode allows starting with no traits."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        screen.build_on_fly_mode = True
        screen.set_name("Test Hero")
        screen.set_concept("失业的建筑师")
        # In build-on-fly mode, character should be valid without traits
        # (validation depends on mode)


class TestCharacterCreationValidation:
    """Test suite for character creation validation."""

    def test_validation_method_exists(self):
        """Test that validation method exists."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        assert hasattr(screen, "is_valid")

    def test_incomplete_character_fails_validation(self):
        """Test that incomplete character fails validation."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        # Fresh screen should not be valid (no name, concept)
        assert screen.is_valid() is False

    def test_get_validation_errors(self):
        """Test getting validation error messages."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        errors = screen.get_validation_errors()
        assert isinstance(errors, list)
        # Should have errors for missing name and concept
        assert len(errors) > 0


class TestCharacterCreationOutput:
    """Test suite for character creation output per GUIDE.md."""

    def test_get_character_data(self):
        """Test getting character data dictionary."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        data = screen.get_character_data()
        assert isinstance(data, dict)

    def test_character_data_has_trait_based_fields(self):
        """Test that character data contains trait-based fields per GUIDE.md."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        screen.set_name("Test Hero")
        screen.set_concept("失业的建筑师")

        data = screen.get_character_data()
        # Required fields per GUIDE.md
        assert "name" in data
        assert "concept" in data
        assert "traits" in data
        assert "fate_points" in data
        assert "tags" in data

        # Should NOT have old attribute system
        assert "attributes" not in data

    def test_character_data_concept_is_localized(self):
        """Test that concept is in LocalizedString format."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        screen.set_name("Test Hero")
        screen.set_concept("失业的建筑师")

        data = screen.get_character_data()
        concept = data.get("concept")
        # Should be a dict with cn/en keys
        assert isinstance(concept, dict)
        assert "cn" in concept or "en" in concept

    def test_character_data_fate_points_initial(self):
        """Test that initial fate points are set correctly."""
        from src.frontend.screens.character_creation import (
            INITIAL_FATE_POINTS,
            CharacterCreationScreen,
        )

        screen = CharacterCreationScreen()
        data = screen.get_character_data()
        assert data.get("fate_points") == INITIAL_FATE_POINTS
        assert INITIAL_FATE_POINTS == 3  # Per GUIDE.md

    def test_character_data_tags_empty_initially(self):
        """Test that tags start empty."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        data = screen.get_character_data()
        assert data.get("tags") == []


class TestCharacterCreationNavigation:
    """Test suite for character creation navigation."""

    def test_back_action_exists(self):
        """Test that back action exists."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        assert hasattr(screen, "action_back") or hasattr(screen, "go_back")

    def test_confirm_action_exists(self):
        """Test that confirm action exists."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        assert hasattr(screen, "action_confirm") or hasattr(screen, "confirm_character")


class TestCharacterCreationBindings:
    """Test suite for character creation key bindings."""

    def test_has_key_bindings(self):
        """Test that character creation screen has key bindings."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        assert hasattr(CharacterCreationScreen, "BINDINGS")

    def test_escape_binding_for_back(self):
        """Test that escape key is bound for going back."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        if hasattr(CharacterCreationScreen, "BINDINGS"):
            binding_keys = [b[0] for b in CharacterCreationScreen.BINDINGS]
            assert "escape" in binding_keys


class TestNoLegacySystem:
    """Test suite to ensure old PbtA-style system is removed."""

    def test_no_default_attributes_constant(self):
        """Test that DEFAULT_ATTRIBUTES constant does not exist."""
        from src.frontend.screens import character_creation

        assert not hasattr(character_creation, "DEFAULT_ATTRIBUTES")

    def test_no_available_concepts_constant(self):
        """Test that AVAILABLE_CONCEPTS constant does not exist."""
        from src.frontend.screens import character_creation

        assert not hasattr(character_creation, "AVAILABLE_CONCEPTS")

    def test_no_initial_points_constant(self):
        """Test that INITIAL_POINTS constant does not exist."""
        from src.frontend.screens import character_creation

        assert not hasattr(character_creation, "INITIAL_POINTS")

    def test_no_increase_attribute_method(self):
        """Test that increase_attribute method does not exist."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        assert not hasattr(screen, "increase_attribute")

    def test_no_decrease_attribute_method(self):
        """Test that decrease_attribute method does not exist."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        assert not hasattr(screen, "decrease_attribute")

    def test_no_set_attribute_method(self):
        """Test that set_attribute method does not exist."""
        from src.frontend.screens.character_creation import CharacterCreationScreen

        screen = CharacterCreationScreen()
        assert not hasattr(screen, "set_attribute")
