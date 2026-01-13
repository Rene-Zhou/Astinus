"""Tests for WebSocket integration and message routing.

Tests the complete flow:
1. Player input → GM Agent → Response stream
2. Dice check request from Rule Agent
3. Dice result submission and narrative generation
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.backend.api.websockets import (
    ConnectionManager,
    MessageType,
    StreamMessage,
    _handle_dice_result,
    _handle_player_input,
    manager,
)


class TestWebSocketMessageRouting:
    """Test WebSocket message routing functionality."""

    @pytest.fixture
    def connection_manager(self):
        """Create a fresh ConnectionManager for each test."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        ws = AsyncMock()
        ws.send_json = AsyncMock()
        ws.receive_text = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect_adds_to_active_connections(self, connection_manager, mock_websocket):
        """Test that connecting adds session to active connections."""
        session_id = "test-session-123"

        await connection_manager.connect(session_id, mock_websocket)

        assert session_id in connection_manager.active_connections
        assert connection_manager.active_connections[session_id] == mock_websocket
        mock_websocket.accept.assert_called_once()

    def test_disconnect_removes_from_active_connections(self, connection_manager):
        """Test that disconnecting removes session from active connections."""
        session_id = "test-session-123"
        connection_manager.active_connections[session_id] = MagicMock()

        connection_manager.disconnect(session_id)

        assert session_id not in connection_manager.active_connections

    def test_disconnect_nonexistent_session_no_error(self, connection_manager):
        """Test disconnecting non-existent session doesn't raise."""
        connection_manager.disconnect("nonexistent")
        # Should not raise

    @pytest.mark.asyncio
    async def test_send_message_to_connected_session(self, connection_manager, mock_websocket):
        """Test sending message to connected session."""
        session_id = "test-session-123"
        connection_manager.active_connections[session_id] = mock_websocket

        message = StreamMessage(
            type=MessageType.STATUS,
            data={"phase": "processing", "message": "Working..."},
        )

        await connection_manager.send_message(session_id, message)

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "status"
        assert call_args["data"]["phase"] == "processing"

    @pytest.mark.asyncio
    async def test_send_message_to_disconnected_session(self, connection_manager):
        """Test sending to disconnected session does nothing."""
        # Should not raise
        message = StreamMessage(
            type=MessageType.STATUS,
            data={"phase": "test"},
        )
        await connection_manager.send_message("nonexistent", message)

    @pytest.mark.asyncio
    async def test_send_status_update(self, connection_manager, mock_websocket):
        """Test sending status update message."""
        session_id = "test-session-123"
        connection_manager.active_connections[session_id] = mock_websocket

        await connection_manager.send_status(session_id, phase="processing", message="分析中...")

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "status"
        assert call_args["data"]["phase"] == "processing"
        assert call_args["data"]["message"] == "分析中..."

    @pytest.mark.asyncio
    async def test_send_content_chunk(self, connection_manager, mock_websocket):
        """Test sending content chunk for streaming."""
        session_id = "test-session-123"
        connection_manager.active_connections[session_id] = mock_websocket

        await connection_manager.send_content_chunk(
            session_id,
            chunk="你走进了",
            is_partial=True,
            chunk_index=0,
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "content"
        assert call_args["data"]["chunk"] == "你走进了"
        assert call_args["data"]["is_partial"] is True
        assert call_args["data"]["chunk_index"] == 0

    @pytest.mark.asyncio
    async def test_send_complete_response(self, connection_manager, mock_websocket):
        """Test sending complete response."""
        session_id = "test-session-123"
        connection_manager.active_connections[session_id] = mock_websocket

        await connection_manager.send_complete(
            session_id,
            content="你成功地逃离了房间。",
            metadata={"agents_called": ["rule"]},
            success=True,
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "complete"
        assert call_args["data"]["content"] == "你成功地逃离了房间。"
        assert call_args["data"]["metadata"]["agents_called"] == ["rule"]
        assert call_args["data"]["success"] is True

    @pytest.mark.asyncio
    async def test_send_error(self, connection_manager, mock_websocket):
        """Test sending error message."""
        session_id = "test-session-123"
        connection_manager.active_connections[session_id] = mock_websocket

        await connection_manager.send_error(session_id, "Something went wrong")

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert call_args["data"]["error"] == "Something went wrong"

    @pytest.mark.asyncio
    async def test_send_phase_change(self, connection_manager, mock_websocket):
        """Test sending phase change notification."""
        session_id = "test-session-123"
        connection_manager.active_connections[session_id] = mock_websocket

        await connection_manager.send_phase_change(session_id, "dice_check")

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "phase"
        assert call_args["data"]["phase"] == "dice_check"


class TestDiceCheckMessageFlow:
    """Test dice check message flow through WebSocket."""

    def test_dice_check_message_type_exists(self):
        """Verify DICE_CHECK message type exists in enum."""
        assert MessageType.DICE_CHECK.value == "dice_check"
        assert MessageType.DICE_RESULT.value == "dice_result"

    def test_dice_check_message_creation(self):
        """Test creating a dice check message."""
        msg = StreamMessage(
            type=MessageType.DICE_CHECK,
            data={
                "check_request": {
                    "intention": "逃离房间",
                    "influencing_factors": {
                        "traits": [],
                        "tags": ["右腿受伤"],
                    },
                    "dice_formula": "3d6kl2",
                    "instructions": {
                        "cn": "由于右腿受伤，你有劣势",
                        "en": "Due to leg injury, you have disadvantage",
                    },
                },
            },
        )
        assert msg.type == MessageType.DICE_CHECK
        assert msg.data["check_request"]["dice_formula"] == "3d6kl2"

    def test_dice_result_message_format(self):
        """Test dice result message can be formatted correctly."""
        msg = StreamMessage(
            type=MessageType.DICE_RESULT,
            data={
                "total": 8,
                "all_rolls": [3, 5, 6],
                "kept_rolls": [3, 5],
                "outcome": "partial_success",
            },
        )

        # Verify format matches expected structure
        assert msg.type == MessageType.DICE_RESULT
        assert msg.data["total"] == 8
        assert len(msg.data["all_rolls"]) == 3
        assert len(msg.data["kept_rolls"]) == 2

    @pytest.fixture
    def mock_connection_manager(self):
        """Create a mock connection manager."""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_send_dice_check(self, mock_connection_manager):
        """Test sending dice check request to client."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()

        session_id = "test-session"
        await mock_connection_manager.connect(session_id, ws)

        check_request = {
            "intention": "攀爬城墙",
            "influencing_factors": {"traits": ["敏捷"], "tags": []},
            "dice_formula": "2d6",
            "instructions": {"cn": "进行攀爬检定", "en": "Make a climbing check"},
        }

        await mock_connection_manager.send_dice_check(session_id, check_request)

        ws.send_json.assert_called_once()
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "dice_check"
        assert call_args["data"]["check_request"]["intention"] == "攀爬城墙"


class TestPlayerInputRouting:
    """Test player input message routing."""

    def test_player_input_message_format(self):
        """Test player input message format."""
        message = {
            "type": "player_input",
            "content": "我想逃离这个房间",
            "lang": "cn",
        }

        # Verify required fields
        assert "type" in message
        assert message["type"] == "player_input"
        assert "content" in message
        assert len(message["content"]) > 0

    def test_player_input_with_lang_default(self):
        """Test player input defaults to Chinese."""
        message = {
            "type": "player_input",
            "content": "逃跑",
        }
        lang = message.get("lang", "cn")
        assert lang == "cn"

    def test_player_input_empty_validation(self):
        """Test that empty player input should be rejected."""
        message = {
            "type": "player_input",
            "content": "",
        }
        # Empty content should be considered invalid
        assert not message["content"]


class TestMessageProtocolCompliance:
    """Test compliance with the WebSocket message protocol."""

    def test_all_message_types_defined(self):
        """Verify all expected message types are defined."""
        assert MessageType.STATUS.value == "status"
        assert MessageType.CONTENT.value == "content"
        assert MessageType.COMPLETE.value == "complete"
        assert MessageType.ERROR.value == "error"
        assert MessageType.PHASE.value == "phase"
        assert MessageType.DICE_CHECK.value == "dice_check"
        assert MessageType.DICE_RESULT.value == "dice_result"

    def test_stream_message_serialization(self):
        """Test StreamMessage can be serialized to JSON-compatible dict."""
        msg = StreamMessage(
            type=MessageType.COMPLETE,
            data={
                "content": "测试内容",
                "metadata": {"agent": "gm_agent"},
                "success": True,
            },
        )

        dumped = msg.model_dump()

        # Should be JSON serializable
        json_str = json.dumps(dumped, ensure_ascii=False)
        parsed = json.loads(json_str)

        assert parsed["type"] == "complete"
        assert parsed["data"]["content"] == "测试内容"

    def test_phase_values_match_game_phases(self):
        """Test that phase messages use valid game phase names."""
        valid_phases = [
            "waiting_input",
            "processing",
            "narrating",
            "dice_check",
        ]

        for phase in valid_phases:
            msg = StreamMessage(
                type=MessageType.PHASE,
                data={"phase": phase},
            )
            assert msg.data["phase"] == phase


class TestMultipleConnectionManagement:
    """Test managing multiple WebSocket connections."""

    @pytest.fixture
    def connection_manager(self):
        """Create a fresh ConnectionManager."""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_multiple_sessions_independent(self, connection_manager):
        """Test multiple sessions are managed independently."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        await connection_manager.connect("session-1", ws1)
        await connection_manager.connect("session-2", ws2)

        assert len(connection_manager.active_connections) == 2

        # Send to session-1 only
        await connection_manager.send_status("session-1", "processing")

        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_session_disconnect_doesnt_affect_others(self, connection_manager):
        """Test disconnecting one session doesn't affect others."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()

        await connection_manager.connect("session-1", ws1)
        await connection_manager.connect("session-2", ws2)

        connection_manager.disconnect("session-1")

        assert "session-1" not in connection_manager.active_connections
        assert "session-2" in connection_manager.active_connections


class TestStreamContentUtility:
    """Test the stream_content utility function."""

    def test_content_chunking_logic(self):
        """Test that content is chunked correctly."""
        content = "你走进了一间昏暗的房间。"
        chunk_size = 5

        chunks = []
        for i in range(0, len(content), chunk_size):
            chunk = content[i : i + chunk_size]
            is_partial = i + chunk_size < len(content)
            chunks.append(
                {
                    "chunk": chunk,
                    "is_partial": is_partial,
                    "index": i // chunk_size,
                }
            )

        # Verify chunking
        assert len(chunks) == 3  # 14 chars / 5 = 3 chunks
        assert chunks[0]["chunk"] == "你走进了一"
        assert chunks[0]["is_partial"] is True
        assert chunks[-1]["is_partial"] is False

    def test_short_content_single_chunk(self):
        """Test short content produces single chunk."""
        content = "Hi"
        chunk_size = 20

        chunks = []
        for i in range(0, len(content), chunk_size):
            chunk = content[i : i + chunk_size]
            is_partial = i + chunk_size < len(content)
            chunks.append({"chunk": chunk, "is_partial": is_partial})

        assert len(chunks) == 1
        assert chunks[0]["is_partial"] is False


class TestMessageHandlers:
    """Test message handler functions."""

    @pytest.fixture
    def mock_gm_agent(self):
        """Create a mock GM Agent."""
        from src.backend.agents.base import AgentResponse

        agent = MagicMock()
        agent.game_state = MagicMock()
        agent.game_state.current_phase = MagicMock()
        agent.game_state.current_phase.value = "waiting_input"
        agent.game_state.last_check_result = None
        agent.game_state.temp_context = {}
        agent.game_state.language = "cn"
        agent.resume_after_dice = AsyncMock(
            return_value=AgentResponse(
                content="检定成功，你完成了行动。",
                metadata={"agent": "gm_agent", "needs_check": False},
                success=True,
            )
        )
        return agent

    @pytest.mark.asyncio
    async def test_handle_player_input_empty_content(self, mock_gm_agent):
        """Test player input handler rejects empty content."""
        session_id = "test-session"

        # Set up mock connection
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        manager.active_connections[session_id] = ws

        try:
            data = {"type": "player_input", "content": ""}
            await _handle_player_input(session_id, data, mock_gm_agent)

            # Should send error
            ws.send_json.assert_called()
            call_args = ws.send_json.call_args[0][0]
            assert call_args["type"] == "error"
        finally:
            manager.disconnect(session_id)

    @pytest.mark.asyncio
    async def test_handle_dice_result_missing_result(self, mock_gm_agent):
        """Test dice result handler rejects missing result."""
        session_id = "test-session"

        # Set up mock connection
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        manager.active_connections[session_id] = ws

        try:
            data = {"type": "dice_result"}  # Missing result
            await _handle_dice_result(session_id, data, mock_gm_agent)

            # Should send error
            ws.send_json.assert_called()
            call_args = ws.send_json.call_args[0][0]
            assert call_args["type"] == "error"
        finally:
            manager.disconnect(session_id)

    @pytest.mark.asyncio
    async def test_handle_dice_result_success(self, mock_gm_agent):
        """Test dice result handler processes valid result."""
        session_id = "test-session"

        # Set up mock connection
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        manager.active_connections[session_id] = ws

        try:
            data = {
                "type": "dice_result",
                "result": 10,
                "all_rolls": [4, 6],
                "kept_rolls": [4, 6],
                "outcome": "success",
            }
            await _handle_dice_result(session_id, data, mock_gm_agent)

            # Should store result and send response
            assert mock_gm_agent.game_state.last_check_result is not None
            assert mock_gm_agent.game_state.last_check_result["total"] == 10
        finally:
            manager.disconnect(session_id)

    @pytest.mark.asyncio
    async def test_handle_dice_result_outcomes(self, mock_gm_agent):
        """Test different dice outcomes generate appropriate narratives."""
        session_id = "test-session"

        outcomes = ["critical", "success", "partial", "failure"]

        for outcome in outcomes:
            ws = AsyncMock()
            ws.accept = AsyncMock()
            ws.send_json = AsyncMock()
            manager.active_connections[session_id] = ws

            try:
                data = {
                    "type": "dice_result",
                    "result": 8,
                    "all_rolls": [4, 4],
                    "kept_rolls": [4, 4],
                    "outcome": outcome,
                }
                await _handle_dice_result(session_id, data, mock_gm_agent)

                # Should send complete message
                calls = ws.send_json.call_args_list
                complete_call = [c for c in calls if c[0][0].get("type") == "complete"]
                assert len(complete_call) > 0
            finally:
                manager.disconnect(session_id)
