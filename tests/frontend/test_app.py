"""Tests for AstinusApp."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.frontend.app import AstinusApp


class TestAstinusApp:
    """Test suite for AstinusApp."""

    def test_create_app(self):
        """Test creating the TUI app."""
        app = AstinusApp()
        assert app is not None
        assert app.current_screen == "game"
        assert app.player_name == ""
        assert app.game_state == ""

    def test_app_css_defined(self):
        """Test that app has CSS styles defined."""
        app = AstinusApp()
        assert app.CSS is not None
        assert "main-container" in app.CSS
        assert "header" in app.CSS
        assert "footer" in app.CSS

    @pytest.mark.asyncio
    async def test_start_new_game_success(self):
        """Test starting a new game successfully."""
        app = AstinusApp()
        app.client = MagicMock()
        app.client.connect = AsyncMock()
        app.client.start_new_game = AsyncMock(return_value=True)
        app.client.session_id = "test-session"
        app.client.player_name = "Test Player"

        success = await app.start_new_game("demo_pack")

        assert success is True
        assert app.game_session_id == "test-session"
        assert app.player_name == "Test Player"

    @pytest.mark.asyncio
    async def test_start_new_game_failure(self):
        """Test failing to start a new game."""
        app = AstinusApp()
        app.client = None

        success = await app.start_new_game("demo_pack")

        assert success is False

    @pytest.mark.asyncio
    async def test_send_player_input_success(self):
        """Test sending player input successfully."""
        app = AstinusApp()
        app.client = MagicMock()
        app.client.send_player_input = AsyncMock(return_value=True)
        app.game_session_id = "test-session"

        success = await app.send_player_input("I look around")

        assert success is True
        app.client.send_player_input.assert_called_once_with("I look around")

    @pytest.mark.asyncio
    async def test_send_player_input_no_session(self):
        """Test sending input without a session."""
        app = AstinusApp()
        app.client = None

        success = await app.send_player_input("I look around")

        assert success is False

    @pytest.mark.asyncio
    async def test_submit_dice_result_success(self):
        """Test submitting dice result successfully."""
        app = AstinusApp()
        app.client = MagicMock()
        app.client.submit_dice_result = AsyncMock(return_value=True)
        app.game_session_id = "test-session"

        success = await app.submit_dice_result(15)

        assert success is True
        app.client.submit_dice_result.assert_called_once_with(15)

    @pytest.mark.asyncio
    async def test_submit_dice_result_no_session(self):
        """Test submitting dice result without a session."""
        app = AstinusApp()
        app.client = None

        success = await app.submit_dice_result(15)

        assert success is False

    def test_action_switch_to_game(self):
        """Test switching to game screen."""
        app = AstinusApp()
        app.push_screen = MagicMock()

        app.action_switch_to_game()

        assert app.current_screen == "game"
        app.push_screen.assert_called_once_with("game")

    def test_action_switch_to_character(self):
        """Test switching to character screen."""
        app = AstinusApp()
        app.push_screen = MagicMock()

        app.action_switch_to_character()

        assert app.current_screen == "character"
        app.push_screen.assert_called_once_with("character")

    def test_action_switch_to_inventory(self):
        """Test switching to inventory screen."""
        app = AstinusApp()
        app.push_screen = MagicMock()

        app.action_switch_to_inventory()

        assert app.current_screen == "inventory"
        app.push_screen.assert_called_once_with("inventory")

    def test_key_bindings(self):
        """Test key binding functions."""
        app = AstinusApp()
        app.action_switch_to_game = MagicMock()
        app.action_switch_to_character = MagicMock()
        app.action_switch_to_inventory = MagicMock()
        app.action_quit = MagicMock()

        app.key_g()
        app.action_switch_to_game.assert_called_once()

        app.key_c()
        app.action_switch_to_character.assert_called_once()

        app.key_i()
        app.action_switch_to_inventory.assert_called_once()

        app.key_q()
        app.action_quit.assert_called_once()
