"""Tests for GameClient connection management and reconnection.

Tests the complete connection lifecycle:
1. Connection establishment
2. Disconnection handling
3. Reconnection logic
4. Connection state management
5. Error handling during connection
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from src.frontend.client import GameClient, create_client


class TestGameClientInit:
    """Test GameClient initialization."""

    def test_default_urls(self):
        """Test default URL configuration."""
        client = GameClient()

        assert client.base_url == "http://localhost:8000"
        assert client.ws_url == "ws://localhost:8000"

    def test_custom_urls(self):
        """Test custom URL configuration."""
        client = GameClient(
            base_url="http://custom:9000",
            ws_url="ws://custom:9000",
        )

        assert client.base_url == "http://custom:9000"
        assert client.ws_url == "ws://custom:9000"

    def test_initial_state(self):
        """Test initial client state."""
        client = GameClient()

        assert client.session_id is None
        assert client.player_name is None
        assert client.player_data is None
        assert client.game_state is None
        assert client._http_client is None
        assert client._ws_connection is None
        assert client._message_handlers == []


class TestGameClientConnection:
    """Test GameClient connection methods."""

    @pytest.fixture
    def client(self):
        """Create a GameClient instance."""
        return GameClient()

    @pytest.mark.asyncio
    async def test_connect_creates_http_client(self, client):
        """Test connect creates HTTP client."""
        await client.connect()

        assert client._http_client is not None

        # Cleanup
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_connect_idempotent(self, client):
        """Test multiple connects don't create multiple clients."""
        await client.connect()
        first_client = client._http_client

        await client.connect()
        second_client = client._http_client

        assert first_client is second_client

        # Cleanup
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_closes_http_client(self, client):
        """Test disconnect closes HTTP client."""
        await client.connect()
        assert client._http_client is not None

        await client.disconnect()
        assert client._http_client is None

    @pytest.mark.asyncio
    async def test_disconnect_without_connection(self, client):
        """Test disconnect without prior connection doesn't error."""
        # Should not raise
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_closes_websocket(self, client):
        """Test disconnect closes WebSocket connection."""
        mock_ws = AsyncMock()
        client._ws_connection = mock_ws

        await client.disconnect()

        # Verify close was called before connection was set to None
        mock_ws.close.assert_called_once()
        assert client._ws_connection is None


class TestGameClientMessageHandlers:
    """Test message handler registration."""

    @pytest.fixture
    def client(self):
        """Create a GameClient instance."""
        return GameClient()

    def test_add_message_handler(self, client):
        """Test adding a message handler."""
        handler = MagicMock()

        client.add_message_handler(handler)

        assert handler in client._message_handlers

    def test_add_multiple_handlers(self, client):
        """Test adding multiple handlers."""
        handler1 = MagicMock()
        handler2 = MagicMock()

        client.add_message_handler(handler1)
        client.add_message_handler(handler2)

        assert len(client._message_handlers) == 2
        assert handler1 in client._message_handlers
        assert handler2 in client._message_handlers

    def test_remove_message_handler(self, client):
        """Test removing a message handler."""
        handler = MagicMock()
        client.add_message_handler(handler)

        client.remove_message_handler(handler)

        assert handler not in client._message_handlers

    def test_remove_nonexistent_handler(self, client):
        """Test removing non-existent handler doesn't error."""
        handler = MagicMock()

        # Should not raise
        client.remove_message_handler(handler)


class TestGameClientStartNewGame:
    """Test starting new game sessions."""

    @pytest.fixture
    def client(self):
        """Create a GameClient instance."""
        return GameClient()

    @pytest.mark.asyncio
    async def test_start_new_game_success(self, client):
        """Test successful game start."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "session_id": "test-session-123",
            "player": {
                "name": "测试玩家",
                "concept": {"cn": "冒险者"},
            },
            "game_state": {"phase": "waiting_input"},
        }

        with patch.object(client, "_connect_websocket", new_callable=AsyncMock):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_http = AsyncMock()
                mock_http.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value = mock_http

                await client.connect()
                client._http_client = mock_http

                success = await client.start_new_game("demo_pack")

        assert success is True
        assert client.session_id == "test-session-123"
        assert client.player_name == "测试玩家"

    @pytest.mark.asyncio
    async def test_start_new_game_failure(self, client):
        """Test failed game start."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_http

            await client.connect()
            client._http_client = mock_http

            success = await client.start_new_game("demo_pack")

        assert success is False
        assert client.session_id is None

    @pytest.mark.asyncio
    async def test_start_new_game_exception(self, client):
        """Test game start with exception."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(side_effect=Exception("Connection error"))
            mock_client_class.return_value = mock_http

            await client.connect()
            client._http_client = mock_http

            success = await client.start_new_game("demo_pack")

        assert success is False


class TestGameClientSendInput:
    """Test sending player input."""

    @pytest.fixture
    def client(self):
        """Create a GameClient instance with mock WebSocket."""
        client = GameClient()
        client.session_id = "test-session-123"
        client._ws_connection = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_send_player_input_success(self, client):
        """Test successful input send."""
        success = await client.send_player_input("我想逃跑")

        assert success is True
        client._ws_connection.send.assert_called_once()

        # Verify message format
        import json

        call_args = client._ws_connection.send.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == "player_input"
        assert message["content"] == "我想逃跑"

    @pytest.mark.asyncio
    async def test_send_player_input_no_connection(self):
        """Test send fails without WebSocket."""
        client = GameClient()

        success = await client.send_player_input("test")

        assert success is False

    @pytest.mark.asyncio
    async def test_send_player_input_no_session(self, client):
        """Test send fails without session."""
        client.session_id = None

        success = await client.send_player_input("test")

        assert success is False

    @pytest.mark.asyncio
    async def test_send_player_input_exception(self, client):
        """Test send handles exceptions."""
        client._ws_connection.send = AsyncMock(side_effect=Exception("Send error"))

        success = await client.send_player_input("test")

        assert success is False


class TestGameClientDiceResult:
    """Test submitting dice results."""

    @pytest.fixture
    def client(self):
        """Create a GameClient instance with mock WebSocket."""
        client = GameClient()
        client.session_id = "test-session-123"
        client._ws_connection = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_submit_dice_result_success(self, client):
        """Test successful dice result submission."""
        success = await client.submit_dice_result(8)

        assert success is True
        client._ws_connection.send.assert_called_once()

        # Verify message format
        import json

        call_args = client._ws_connection.send.call_args[0][0]
        message = json.loads(call_args)
        assert message["type"] == "dice_result"
        assert message["result"] == 8

    @pytest.mark.asyncio
    async def test_submit_dice_result_no_connection(self):
        """Test submit fails without WebSocket."""
        client = GameClient()

        success = await client.submit_dice_result(10)

        assert success is False


class TestGameClientGetState:
    """Test getting game state."""

    @pytest.fixture
    def client(self):
        """Create a GameClient instance."""
        client = GameClient()
        client.session_id = "test-session-123"
        return client

    @pytest.mark.asyncio
    async def test_get_game_state_success(self, client):
        """Test successful state retrieval."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "session_id": "test-session-123",
            "current_location": "起始地点",
            "current_phase": "waiting_input",
        }

        client._http_client = AsyncMock()
        client._http_client.get = AsyncMock(return_value=mock_response)

        state = await client.get_game_state()

        assert state is not None
        assert state["current_location"] == "起始地点"

    @pytest.mark.asyncio
    async def test_get_game_state_no_client(self):
        """Test get state fails without HTTP client."""
        client = GameClient()
        client.session_id = "test"

        state = await client.get_game_state()

        assert state is None

    @pytest.mark.asyncio
    async def test_get_game_state_no_session(self, client):
        """Test get state fails without session."""
        client.session_id = None

        state = await client.get_game_state()

        assert state is None


class TestGameClientCharacterSheet:
    """Test character sheet retrieval."""

    @pytest.mark.asyncio
    async def test_get_character_sheet_with_data(self):
        """Test getting character sheet with player data."""
        client = GameClient()
        client.player_data = {
            "name": "测试玩家",
            "concept": {"cn": "冒险者"},
            "traits": [],
        }

        result = await client.get_character_sheet()

        assert result is not None
        assert result["name"] == "测试玩家"

    @pytest.mark.asyncio
    async def test_get_character_sheet_no_data(self):
        """Test getting character sheet without player data."""
        client = GameClient()

        result = await client.get_character_sheet()

        assert result is None


class TestGameClientInventory:
    """Test inventory retrieval."""

    @pytest.mark.asyncio
    async def test_get_inventory_with_items(self):
        """Test getting inventory with items."""
        client = GameClient()
        client.player_data = {
            "inventory": [
                {"name": "短剑", "quantity": 1},
                {"name": "火把", "quantity": 3},
            ]
        }

        result = await client.get_inventory()

        assert result is not None
        assert len(result) == 2
        assert result[0]["name"] == "短剑"

    @pytest.mark.asyncio
    async def test_get_inventory_empty(self):
        """Test getting empty inventory."""
        client = GameClient()
        client.player_data = {"inventory": []}

        result = await client.get_inventory()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_inventory_no_data(self):
        """Test getting inventory without player data."""
        client = GameClient()

        result = await client.get_inventory()

        assert result is None


class TestCreateClientFactory:
    """Test the create_client factory function."""

    def test_create_client_returns_game_client(self):
        """Test factory returns GameClient instance."""
        client = create_client()

        assert isinstance(client, GameClient)

    def test_create_client_default_config(self):
        """Test factory uses default configuration."""
        client = create_client()

        assert client.base_url == "http://localhost:8000"
        assert client.ws_url == "ws://localhost:8000"


class TestGameClientHandleMessage:
    """Test message handling in GameClient."""

    @pytest.fixture
    def client(self):
        """Create a GameClient instance."""
        return GameClient()

    @pytest.mark.asyncio
    async def test_handle_message_notifies_handlers(self, client):
        """Test that message handlers are notified."""
        handler = MagicMock()
        client.add_message_handler(handler)

        message = {"type": "status", "content": "Processing..."}
        await client._handle_message(message)

        handler.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_handle_message_handler_exception(self, client):
        """Test that handler exceptions don't break processing."""
        failing_handler = MagicMock(side_effect=Exception("Handler error"))
        working_handler = MagicMock()

        client.add_message_handler(failing_handler)
        client.add_message_handler(working_handler)

        message = {"type": "status", "content": "Test"}
        await client._handle_message(message)

        # Both handlers should be called even if first fails
        failing_handler.assert_called_once()
        working_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_dice_check_message(self, client):
        """Test handling dice check message."""
        handler = MagicMock()
        client.add_message_handler(handler)

        check_data = {
            "intention": "逃跑",
            "dice_formula": "2d6",
        }

        client._handle_dice_check(check_data)

        # Should notify handlers with dice_check type
        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert call_args["type"] == "dice_check"
        assert call_args["data"] == check_data


class TestGameClientReconnection:
    """Test GameClient reconnection functionality."""

    @pytest.fixture
    def client(self):
        """Create a GameClient instance."""
        return GameClient()

    @pytest.mark.asyncio
    async def test_reconnect_after_disconnect(self, client):
        """Test client can reconnect after disconnection."""
        # First connection
        await client.connect()
        assert client._http_client is not None

        # Disconnect
        await client.disconnect()
        assert client._http_client is None

        # Reconnect
        await client.connect()
        assert client._http_client is not None

        # Cleanup
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_is_connected_property(self, client):
        """Test is_connected property reflects connection state."""
        # Initially not connected
        assert client.is_connected is False

        # After connect
        await client.connect()
        assert client.is_connected is True

        # After disconnect
        await client.disconnect()
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_is_websocket_connected(self, client):
        """Test is_websocket_connected property."""
        # Initially not connected
        assert client.is_websocket_connected is False

        # Mock WebSocket connection
        client._ws_connection = AsyncMock()
        client._ws_connection.open = True
        assert client.is_websocket_connected is True

        # After close
        client._ws_connection = None
        assert client.is_websocket_connected is False

    @pytest.mark.asyncio
    async def test_reconnect_websocket(self, client):
        """Test WebSocket reconnection."""
        client.session_id = "test-session-123"
        client._ws_connection = None

        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value = mock_ws

            await client.reconnect_websocket()

            mock_connect.assert_called_once()
            assert "test-session-123" in str(mock_connect.call_args)

    @pytest.mark.asyncio
    async def test_reconnect_websocket_no_session(self, client):
        """Test reconnect fails without session."""
        client.session_id = None

        result = await client.reconnect_websocket()

        assert result is False

    @pytest.mark.asyncio
    async def test_auto_reconnect_on_connection_lost(self, client):
        """Test auto-reconnect behavior when connection is lost."""
        client.session_id = "test-session-123"
        client._auto_reconnect = True
        client._reconnect_attempts = 0
        client._max_reconnect_attempts = 3

        with patch.object(client, "reconnect_websocket", new_callable=AsyncMock) as mock_reconnect:
            mock_reconnect.return_value = True

            await client._on_connection_lost()

            mock_reconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_reconnect_attempts(self, client):
        """Test reconnection stops after max attempts."""
        client.session_id = "test-session-123"
        client._auto_reconnect = True
        client._reconnect_attempts = 3
        client._max_reconnect_attempts = 3

        with patch.object(client, "reconnect_websocket", new_callable=AsyncMock) as mock_reconnect:
            await client._on_connection_lost()

            # Should not attempt reconnect after max attempts
            mock_reconnect.assert_not_called()

    @pytest.mark.asyncio
    async def test_reconnect_resets_attempts_on_success(self, client):
        """Test successful reconnect resets attempt counter."""
        client.session_id = "test-session-123"
        client._reconnect_attempts = 2

        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_ws = AsyncMock()
            mock_connect.return_value = mock_ws

            await client.reconnect_websocket()

            assert client._reconnect_attempts == 0


class TestGameClientConnectionState:
    """Test connection state management."""

    @pytest.fixture
    def client(self):
        """Create a GameClient instance."""
        return GameClient()

    def test_connection_state_enum_values(self):
        """Test ConnectionState has expected values."""
        from src.frontend.client import ConnectionState

        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.RECONNECTING.value == "reconnecting"

    @pytest.mark.asyncio
    async def test_connection_state_transitions(self, client):
        """Test connection state transitions correctly."""
        from src.frontend.client import ConnectionState

        # Initial state
        assert client.connection_state == ConnectionState.DISCONNECTED

        # Connecting
        client._set_connection_state(ConnectionState.CONNECTING)
        assert client.connection_state == ConnectionState.CONNECTING

        # Connected
        client._set_connection_state(ConnectionState.CONNECTED)
        assert client.connection_state == ConnectionState.CONNECTED

    def test_connection_state_callback(self, client):
        """Test connection state change callback."""
        callback = MagicMock()
        client.on_connection_state_change = callback

        from src.frontend.client import ConnectionState

        client._set_connection_state(ConnectionState.CONNECTED)

        callback.assert_called_once_with(ConnectionState.CONNECTED)
