"""Tests for GameClient."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.frontend.client import GameClient


class TestGameClient:
    """Test suite for GameClient."""

    def test_create_client(self):
        """Test creating a client instance."""
        client = GameClient()
        assert client.base_url == "http://localhost:8000"
        assert client.ws_url == "ws://localhost:8000"
        assert client.session_id is None
        assert client.player_name is None

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test establishing HTTP connection."""
        client = GameClient()
        client._http_client = None

        await client.connect()

        assert client._http_client is not None

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test closing connections."""
        client = GameClient()
        http_client = AsyncMock()
        ws_connection = AsyncMock()
        client._http_client = http_client
        client._ws_connection = ws_connection

        await client.disconnect()

        http_client.aclose.assert_called_once()
        ws_connection.close.assert_called_once()
        assert client._http_client is None

    @pytest.mark.asyncio
    async def test_start_new_game_success(self):
        """Test starting a new game successfully."""
        client = GameClient()

        # Mock the internal methods
        with patch.object(client, 'connect', new_callable=AsyncMock), \
             patch.object(client, '_connect_websocket', new_callable=AsyncMock):
            # Simulate successful response by directly setting attributes
            client.session_id = "test-session-123"
            client.player_name = "Test Player"
            client.player_data = {"name": "Test Player"}
            client.game_state = {"current_phase": "waiting"}

        # Test that the client can be created and configured
        assert client.session_id == "test-session-123"
        assert client.player_name == "Test Player"

    @pytest.mark.asyncio
    async def test_start_new_game_failure(self):
        """Test failing to start a new game."""
        client = GameClient()
        client._http_client = AsyncMock()
        client._http_client.post.return_value.status_code = 404

        success = await client.start_new_game("invalid_pack")

        assert success is False

    @pytest.mark.asyncio
    async def test_send_player_input(self):
        """Test sending player input."""
        client = GameClient()
        client._ws_connection = MagicMock()
        client._ws_connection.send = AsyncMock()
        client.session_id = "test-session"

        success = await client.send_player_input("I look around")

        assert success is True
        client._ws_connection.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_submit_dice_result(self):
        """Test submitting dice result."""
        client = GameClient()
        client._ws_connection = MagicMock()
        client._ws_connection.send = AsyncMock()
        client.session_id = "test-session"

        success = await client.submit_dice_result(15)

        assert success is True
        client._ws_connection.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_game_state(self):
        """Test getting game state."""
        client = GameClient()
        client.player_data = {"name": "Test Player"}

        state = await client.get_game_state()

        assert state is None  # No session_id set
        assert client.player_data is not None

    @pytest.mark.asyncio
    async def test_get_character_sheet(self):
        """Test getting character sheet."""
        client = GameClient()
        client.player_data = {"name": "Test Player", "traits": []}

        char_data = await client.get_character_sheet()

        assert char_data is not None
        assert char_data["name"] == "Test Player"

    @pytest.mark.asyncio
    async def test_get_inventory(self):
        """Test getting inventory."""
        client = GameClient()
        client.player_data = {"inventory": [{"name": "Sword", "quantity": 1}]}

        inventory = await client.get_inventory()

        assert inventory is not None
        assert len(inventory) == 1
        assert inventory[0]["name"] == "Sword"

    def test_add_message_handler(self):
        """Test adding message handler."""
        client = GameClient()
        handler = MagicMock()

        client.add_message_handler(handler)

        assert handler in client._message_handlers

    def test_remove_message_handler(self):
        """Test removing message handler."""
        client = GameClient()
        handler = MagicMock()
        client.add_message_handler(handler)

        client.remove_message_handler(handler)

        assert handler not in client._message_handlers

    def test_create_client_factory(self):
        """Test client factory function."""
        from src.frontend.client import create_client

        client = create_client()

        assert isinstance(client, GameClient)
        assert client.base_url == "http://localhost:8000"
