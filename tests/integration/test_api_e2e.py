"""
End-to-end integration tests for REST API and WebSocket flows.

Tests the complete game flow through the API layer:
- Game creation and session management
- Player action processing
- Dice check workflow
- WebSocket streaming
- State persistence

These tests use mocked agents to isolate API behavior from LLM dependencies.
"""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set fake API key before imports
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"

from src.backend.agents.base import AgentResponse
from src.backend.api.websockets import (
    ConnectionManager,
    MessageType,
    StreamMessage,
    manager,
    stream_content,
)
from src.backend.models.character import PlayerCharacter, Trait
from src.backend.models.game_state import GamePhase, GameState
from src.backend.models.i18n import LocalizedString


class TestConnectionManagerIntegration:
    """Integration tests for WebSocket connection manager."""

    @pytest.fixture
    def connection_manager(self):
        """Create a fresh connection manager."""
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.send_text = AsyncMock()
        ws.receive_text = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self, connection_manager, mock_websocket):
        """Test complete WebSocket session lifecycle."""
        session_id = "lifecycle-test-session"

        # 1. Connect
        await connection_manager.connect(session_id, mock_websocket)
        assert session_id in connection_manager.active_connections
        mock_websocket.accept.assert_called_once()

        # 2. Send status
        await connection_manager.send_status(session_id, "processing", "Analyzing...")
        mock_websocket.send_json.assert_called()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "status"
        assert call_args["data"]["phase"] == "processing"

        # 3. Send content chunks
        mock_websocket.send_json.reset_mock()
        await connection_manager.send_content_chunk(
            session_id, "Hello ", is_partial=True, chunk_index=0
        )
        await connection_manager.send_content_chunk(
            session_id, "World!", is_partial=False, chunk_index=1
        )
        assert mock_websocket.send_json.call_count == 2

        # 4. Send complete
        mock_websocket.send_json.reset_mock()
        await connection_manager.send_complete(
            session_id,
            content="Full narrative here",
            metadata={"turn": 1},
            success=True,
        )
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "complete"
        assert call_args["data"]["success"] is True

        # 5. Disconnect
        connection_manager.disconnect(session_id)
        assert session_id not in connection_manager.active_connections

    @pytest.mark.asyncio
    async def test_dice_check_flow(self, connection_manager, mock_websocket):
        """Test dice check request/response flow."""
        session_id = "dice-test-session"

        await connection_manager.connect(session_id, mock_websocket)

        # Send dice check request
        check_request = {
            "intention": "搜索房间",
            "influencing_factors": {"traits": ["敏锐"], "tags": ["专注"]},
            "dice_formula": "3d6kh2",
            "instructions": {"cn": "敏锐特质给予优势", "en": "Perceptive grants advantage"},
        }
        await connection_manager.send_dice_check(session_id, check_request)

        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "dice_check"
        assert call_args["data"]["check_request"]["intention"] == "搜索房间"
        assert call_args["data"]["check_request"]["dice_formula"] == "3d6kh2"

    @pytest.mark.asyncio
    async def test_error_handling(self, connection_manager, mock_websocket):
        """Test error message sending."""
        session_id = "error-test-session"

        await connection_manager.connect(session_id, mock_websocket)
        await connection_manager.send_error(session_id, "Something went wrong")

        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert call_args["data"]["error"] == "Something went wrong"

    @pytest.mark.asyncio
    async def test_phase_change_notification(self, connection_manager, mock_websocket):
        """Test phase change notifications."""
        session_id = "phase-test-session"

        await connection_manager.connect(session_id, mock_websocket)

        # Test all phases
        phases = ["waiting_input", "processing", "narrating", "dice_check"]
        for phase in phases:
            mock_websocket.send_json.reset_mock()
            await connection_manager.send_phase_change(session_id, phase)
            call_args = mock_websocket.send_json.call_args[0][0]
            assert call_args["type"] == "phase"
            assert call_args["data"]["phase"] == phase

    @pytest.mark.asyncio
    async def test_send_to_disconnected_session(self, connection_manager):
        """Test that sending to a disconnected session doesn't raise."""
        # Should not raise even if session doesn't exist
        await connection_manager.send_status("nonexistent", "test")
        await connection_manager.send_error("nonexistent", "test")
        await connection_manager.send_phase_change("nonexistent", "test")

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, connection_manager):
        """Test managing multiple concurrent sessions."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        # Connect both
        await connection_manager.connect("session1", ws1)
        await connection_manager.connect("session2", ws2)

        assert len(connection_manager.active_connections) == 2

        # Send to session1 only
        await connection_manager.send_status("session1", "processing")
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()

        # Disconnect session1
        connection_manager.disconnect("session1")
        assert "session1" not in connection_manager.active_connections
        assert "session2" in connection_manager.active_connections


class TestStreamContentFunction:
    """Tests for the stream_content utility function."""

    @pytest.fixture
    def connection_manager_with_mock(self):
        """Set up connection manager with a mocked session."""
        cm = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()
        return cm, mock_ws

    @pytest.mark.asyncio
    async def test_stream_content_chunks(self, connection_manager_with_mock):
        """Test streaming content in chunks."""
        cm, mock_ws = connection_manager_with_mock
        session_id = "stream-test"

        # Connect
        await cm.connect(session_id, mock_ws)

        # Temporarily replace global manager
        original_active = manager.active_connections
        manager.active_connections = cm.active_connections

        try:
            # Stream content with small chunks and no delay
            content = "Hello World!"
            await stream_content(session_id, content, chunk_size=5, delay=0)

            # Should have sent 3 chunks: "Hello", " Worl", "d!"
            assert mock_ws.send_json.call_count == 3

            # Check first chunk (partial)
            first_call = mock_ws.send_json.call_args_list[0][0][0]
            assert first_call["type"] == "content"
            assert first_call["data"]["chunk"] == "Hello"
            assert first_call["data"]["is_partial"] is True
            assert first_call["data"]["chunk_index"] == 0

            # Check last chunk (not partial)
            last_call = mock_ws.send_json.call_args_list[-1][0][0]
            assert last_call["data"]["is_partial"] is False
        finally:
            manager.active_connections = original_active

    @pytest.mark.asyncio
    async def test_stream_short_content(self, connection_manager_with_mock):
        """Test streaming content shorter than chunk size."""
        cm, mock_ws = connection_manager_with_mock
        session_id = "stream-short-test"

        await cm.connect(session_id, mock_ws)

        original_active = manager.active_connections
        manager.active_connections = cm.active_connections

        try:
            # Content shorter than chunk size
            content = "Hi"
            await stream_content(session_id, content, chunk_size=10, delay=0)

            # Should have sent 1 chunk
            assert mock_ws.send_json.call_count == 1

            call = mock_ws.send_json.call_args[0][0]
            assert call["data"]["chunk"] == "Hi"
            assert call["data"]["is_partial"] is False
        finally:
            manager.active_connections = original_active


class TestMessageProtocol:
    """Tests for WebSocket message protocol compliance."""

    def test_all_message_types_have_correct_format(self):
        """Verify all message types follow the protocol."""
        # Test each message type
        for msg_type in MessageType:
            message = StreamMessage(
                type=msg_type,
                data={"test": "data"},
            )
            serialized = message.model_dump()
            assert "type" in serialized
            assert "data" in serialized
            assert serialized["type"] == msg_type.value

    def test_status_message_format(self):
        """Test status message has correct structure."""
        message = StreamMessage(
            type=MessageType.STATUS,
            data={"phase": "processing", "message": "Thinking..."},
        )
        data = message.model_dump()
        assert data["type"] == "status"
        assert "phase" in data["data"]
        assert "message" in data["data"]

    def test_content_message_format(self):
        """Test content chunk message has correct structure."""
        message = StreamMessage(
            type=MessageType.CONTENT,
            data={"chunk": "Hello", "is_partial": True, "chunk_index": 0},
        )
        data = message.model_dump()
        assert data["type"] == "content"
        assert "chunk" in data["data"]
        assert "is_partial" in data["data"]
        assert "chunk_index" in data["data"]

    def test_dice_check_message_format(self):
        """Test dice check message has correct structure."""
        message = StreamMessage(
            type=MessageType.DICE_CHECK,
            data={
                "check_request": {
                    "intention": "test",
                    "dice_formula": "2d6",
                    "influencing_factors": {},
                    "instructions": {"cn": "测试", "en": "test"},
                }
            },
        )
        data = message.model_dump()
        assert data["type"] == "dice_check"
        assert "check_request" in data["data"]
        assert "intention" in data["data"]["check_request"]
        assert "dice_formula" in data["data"]["check_request"]

    def test_complete_message_format(self):
        """Test complete message has correct structure."""
        message = StreamMessage(
            type=MessageType.COMPLETE,
            data={
                "content": "Full response",
                "metadata": {"turn": 1},
                "success": True,
            },
        )
        data = message.model_dump()
        assert data["type"] == "complete"
        assert "content" in data["data"]
        assert "metadata" in data["data"]
        assert "success" in data["data"]

    def test_error_message_format(self):
        """Test error message has correct structure."""
        message = StreamMessage(
            type=MessageType.ERROR,
            data={"error": "Something went wrong"},
        )
        data = message.model_dump()
        assert data["type"] == "error"
        assert "error" in data["data"]

    def test_phase_message_format(self):
        """Test phase change message has correct structure."""
        message = StreamMessage(
            type=MessageType.PHASE,
            data={"phase": "narrating"},
        )
        data = message.model_dump()
        assert data["type"] == "phase"
        assert "phase" in data["data"]

    def test_dice_result_message_format(self):
        """Test dice result message type exists and can be used."""
        message = StreamMessage(
            type=MessageType.DICE_RESULT,
            data={
                "total": 10,
                "all_rolls": [6, 4],
                "outcome": "success",
            },
        )
        data = message.model_dump()
        assert data["type"] == "dice_result"


class TestGameStateIntegration:
    """Integration tests for game state management."""

    @pytest.fixture
    def game_state(self):
        """Create a test game state."""
        player = PlayerCharacter(
            name="测试玩家",
            concept=LocalizedString(cn="勇敢的探险者", en="Brave Explorer"),
            traits=[
                Trait(
                    name=LocalizedString(cn="敏锐", en="Perceptive"),
                    description=LocalizedString(cn="善于观察细节", en="Good at noticing details"),
                    positive_aspect=LocalizedString(cn="注意力强", en="Strong attention"),
                    negative_aspect=LocalizedString(cn="可能多疑", en="May be suspicious"),
                )
            ],
            tags=["新手冒险者"],
        )
        return GameState(
            session_id="test-session-123",
            world_pack_id="demo_pack",
            player=player,
            current_location="study",
            active_npc_ids=["chen_ling"],
        )

    def test_game_state_creation(self, game_state):
        """Test game state is created correctly."""
        assert game_state.session_id == "test-session-123"
        assert game_state.world_pack_id == "demo_pack"
        assert game_state.current_location == "study"
        assert game_state.player.name == "测试玩家"
        assert len(game_state.player.traits) == 1
        assert "chen_ling" in game_state.active_npc_ids

    def test_game_state_phase_transitions(self, game_state):
        """Test phase transitions work correctly."""
        from src.backend.models.game_state import GamePhase

        # Initial phase
        assert game_state.current_phase == GamePhase.WAITING_INPUT

        # Transition to processing
        game_state.set_phase(GamePhase.PROCESSING)
        assert game_state.current_phase == GamePhase.PROCESSING

        # Transition to dice check
        game_state.set_phase(GamePhase.DICE_CHECK)
        assert game_state.current_phase == GamePhase.DICE_CHECK

        # Transition to narrating
        game_state.set_phase(GamePhase.NARRATING)
        assert game_state.current_phase == GamePhase.NARRATING

        # Back to waiting
        game_state.set_phase(GamePhase.WAITING_INPUT)
        assert game_state.current_phase == GamePhase.WAITING_INPUT

    def test_game_state_message_history(self, game_state):
        """Test message history management."""
        # Add messages
        game_state.add_message("player", "我查看房间")
        game_state.add_message("gm", "你看到了一间古老的书房...")

        assert len(game_state.messages) == 2
        assert game_state.messages[0]["role"] == "player"
        assert game_state.messages[1]["role"] == "gm"

        # Get recent messages
        recent = game_state.get_recent_messages(count=1)
        assert len(recent) == 1
        assert recent[0]["role"] == "gm"

    def test_game_state_location_change(self, game_state):
        """Test location changes."""
        assert game_state.current_location == "study"

        game_state.update_location("secret_room")
        assert game_state.current_location == "secret_room"

    def test_game_state_turn_tracking(self, game_state):
        """Test turn counter."""
        assert game_state.turn_count == 0

        game_state.turn_count += 1
        assert game_state.turn_count == 1

        game_state.turn_count += 1
        assert game_state.turn_count == 2

    def test_game_state_dice_result_storage(self, game_state):
        """Test storing dice check results."""
        assert game_state.last_check_result is None

        dice_result = {
            "total": 10,
            "all_rolls": [6, 4],
            "kept_rolls": [6, 4],
            "outcome": "success",
        }
        game_state.last_check_result = dice_result

        assert game_state.last_check_result is not None
        assert game_state.last_check_result["total"] == 10
        assert game_state.last_check_result["outcome"] == "success"


class TestAgentResponseIntegration:
    """Integration tests for agent response handling."""

    def test_agent_response_success(self):
        """Test successful agent response."""
        response = AgentResponse(
            content="你仔细查看了房间，发现书架后似乎有什么东西。",
            metadata={
                "agent": "gm_agent",
                "phase": "narrating",
                "needs_check": False,
            },
            success=True,
        )

        assert response.success is True
        assert response.error is None
        assert "书架" in response.content
        assert response.metadata["needs_check"] is False

    def test_agent_response_with_dice_check(self):
        """Test agent response that triggers dice check."""
        response = AgentResponse(
            content="这需要一次检定",
            metadata={
                "needs_check": True,
                "dice_check": {
                    "intention": "翻找书架寻找秘密",
                    "influencing_factors": {"traits": ["敏锐"], "tags": []},
                    "dice_formula": "3d6kh2",
                    "instructions": {
                        "cn": "敏锐特质给予优势",
                        "en": "Perceptive trait grants advantage",
                    },
                },
            },
            success=True,
        )

        assert response.metadata["needs_check"] is True
        assert "dice_check" in response.metadata
        assert response.metadata["dice_check"]["dice_formula"] == "3d6kh2"

    def test_agent_response_failure(self):
        """Test failed agent response."""
        response = AgentResponse(
            content="",
            metadata={},
            success=False,
            error="LLM connection failed",
        )

        assert response.success is False
        assert response.error == "LLM connection failed"

    def test_agent_response_with_npc_interaction(self):
        """Test agent response for NPC interaction."""
        response = AgentResponse(
            content="陈玲转向你，目光锐利：'你是谁？为什么来这里？'",
            metadata={
                "npc_id": "chen_ling",
                "needs_check": False,
                "relation_change": 0,
                "emotion": "suspicious",
            },
            success=True,
        )

        assert response.metadata["npc_id"] == "chen_ling"
        assert response.metadata["emotion"] == "suspicious"
        assert "陈玲" in response.content


class TestDiceCheckIntegration:
    """Integration tests for dice check system."""

    def test_dice_check_request_creation(self):
        """Test creating a dice check request."""
        from src.backend.models.dice_check import DiceCheckRequest

        check = DiceCheckRequest(
            intention="搜索房间寻找线索",
            influencing_factors={"traits": ["敏锐"], "tags": []},
            dice_formula="3d6kh2",
            instructions=LocalizedString(
                cn="敏锐特质给予优势，投3d6取最高2个",
                en="Perceptive trait grants advantage, roll 3d6 keep highest 2",
            ),
        )

        assert check.intention == "搜索房间寻找线索"
        assert check.dice_formula == "3d6kh2"
        assert check.has_advantage() is True
        assert check.has_disadvantage() is False
        assert check.get_dice_count() == 3

    def test_dice_check_disadvantage(self):
        """Test dice check with disadvantage."""
        from src.backend.models.dice_check import DiceCheckRequest

        check = DiceCheckRequest(
            intention="在黑暗中搜索",
            influencing_factors={"traits": [], "tags": ["黑暗中"]},
            dice_formula="3d6kl2",
            instructions=LocalizedString(
                cn="黑暗环境带来劣势",
                en="Darkness grants disadvantage",
            ),
        )

        assert check.has_advantage() is False
        assert check.has_disadvantage() is True

    def test_dice_check_display_format(self):
        """Test dice check display formatting."""
        from src.backend.models.dice_check import DiceCheckRequest

        check = DiceCheckRequest(
            intention="翻找书架",
            influencing_factors={"traits": [], "tags": []},
            dice_formula="2d6",
            instructions=LocalizedString(
                cn="标准搜索检定",
                en="Standard search check",
            ),
        )

        # Test Chinese display
        display_cn = check.to_display("cn")
        assert display_cn["intention"] == "翻找书架"
        assert display_cn["dice"] == "2d6"
        assert display_cn["explanation"] == "标准搜索检定"

        # Test English display
        display_en = check.to_display("en")
        assert display_en["explanation"] == "Standard search check"

    @pytest.mark.asyncio
    async def test_dice_result_processing_with_rule_agent(self):
        """Test that dice result is processed through Rule Agent for narrative."""
        from src.backend.api.websockets import _generate_fallback_narrative, _handle_dice_result

        # Create mock GM agent with Rule Agent
        mock_rule_agent = AsyncMock()
        mock_rule_agent.process_result = AsyncMock(
            return_value=AgentResponse(
                content="你迅速地翻越障碍物，成功逃出了房间。门在身后砰然关上。",
                metadata={
                    "agent": "rule_agent",
                    "narrative": "你迅速地翻越障碍物，成功逃出了房间。",
                    "outcome_type": "success",
                    "consequences": [],
                    "suggested_tags": [],
                },
                success=True,
            )
        )

        # Create mock game state (no need for real PlayerCharacter)
        mock_game_state = MagicMock()
        mock_game_state.current_location = "test_room"
        mock_game_state.active_npc_ids = []
        mock_game_state.temp_context = {
            "pending_dice_check": {
                "intention": "逃离房间",
                "influencing_factors": {"traits": [], "tags": []},
                "dice_formula": "2d6",
            }
        }
        mock_game_state.set_phase = MagicMock()
        mock_game_state.add_message = MagicMock()

        # Create mock GM agent
        mock_gm_agent = MagicMock()
        mock_gm_agent.game_state = mock_game_state
        mock_gm_agent.sub_agents = {"rule": mock_rule_agent}

        # Create mock connection manager
        with patch("src.backend.api.websockets.manager") as mock_manager:
            mock_manager.send_status = AsyncMock()
            mock_manager.send_phase_change = AsyncMock()
            mock_manager.send_complete = AsyncMock()

            # Process dice result
            dice_data = {
                "type": "dice_result",
                "result": 8,
                "all_rolls": [3, 5],
                "kept_rolls": [3, 5],
                "outcome": "success",
            }

            await _handle_dice_result("test-session", dice_data, mock_gm_agent)

            # Verify Rule Agent was called
            mock_rule_agent.process_result.assert_called_once()
            call_args = mock_rule_agent.process_result.call_args

            # Verify result_data was passed correctly
            result_data = call_args.kwargs.get("result_data") or call_args[1].get("result_data")
            assert result_data["intention"] == "逃离房间"
            assert result_data["total"] == 8
            assert result_data["success"] is True

            # Verify complete message was sent with narrative
            mock_manager.send_complete.assert_called_once()
            complete_call = mock_manager.send_complete.call_args
            assert "你迅速地翻越障碍物" in complete_call.kwargs.get(
                "content", complete_call[1].get("content", "")
            )

    def test_fallback_narrative_generation(self):
        """Test fallback narrative when Rule Agent is unavailable."""
        from src.backend.api.websockets import _generate_fallback_narrative

        # Test all outcome types
        critical = _generate_fallback_narrative(12, "critical")
        assert "大成功" in critical
        assert "12" in critical

        success = _generate_fallback_narrative(9, "success")
        assert "成功" in success
        assert "9" in success

        partial = _generate_fallback_narrative(7, "partial")
        assert "部分成功" in partial or "代价" in partial

        failure = _generate_fallback_narrative(5, "failure")
        assert "失败" in failure
        assert "5" in failure


class TestE2EScenarios:
    """End-to-end scenario tests without requiring real API."""

    @pytest.fixture
    def game_state(self):
        """Create a game state for scenarios."""
        player = PlayerCharacter(
            name="林风",
            concept=LocalizedString(cn="失忆的旅人", en="Amnesiac Traveler"),
            traits=[
                Trait(
                    name=LocalizedString(cn="直觉敏锐", en="Sharp Intuition"),
                    description=LocalizedString(
                        cn="能感知到常人忽略的细节", en="Can perceive details others miss"
                    ),
                    positive_aspect=LocalizedString(cn="发现隐藏事物", en="Find hidden things"),
                    negative_aspect=LocalizedString(cn="过度敏感", en="Oversensitive"),
                )
            ],
            tags=[],
            fate_points=3,
        )
        return GameState(
            session_id="scenario-test",
            world_pack_id="demo_pack",
            player=player,
            current_location="manor_entrance",
            active_npc_ids=["chen_ling"],
        )

    def test_exploration_scenario_state_changes(self, game_state):
        """Test state changes during exploration."""
        from src.backend.models.game_state import GamePhase

        # Player enters and looks around
        game_state.add_message("player", "我观察庄园入口")
        game_state.set_phase(GamePhase.PROCESSING)

        # GM responds (no check needed)
        game_state.add_message("gm", "你看到古老的木门半掩着，周围杂草丛生。")
        game_state.set_phase(GamePhase.WAITING_INPUT)
        game_state.turn_count += 1

        assert game_state.turn_count == 1
        assert len(game_state.messages) == 2

    def test_dice_check_scenario_state_changes(self, game_state):
        """Test state changes during dice check."""
        from src.backend.models.game_state import GamePhase

        # Player tries to search
        game_state.add_message("player", "我仔细搜索入口附近")
        game_state.set_phase(GamePhase.PROCESSING)

        # Rule Agent determines check is needed
        game_state.set_phase(GamePhase.DICE_CHECK)

        # Player rolls
        game_state.last_check_result = {
            "total": 10,
            "all_rolls": [6, 4, 2],
            "kept_rolls": [6, 4],
            "outcome": "success",
        }

        # GM narrates result
        game_state.set_phase(GamePhase.NARRATING)
        game_state.add_message("gm", "你的细心观察发现了一个隐藏的暗门！")
        game_state.turn_count += 1

        # Back to waiting
        game_state.set_phase(GamePhase.WAITING_INPUT)

        assert game_state.turn_count == 1
        assert game_state.last_check_result["outcome"] == "success"
        assert game_state.current_phase == GamePhase.WAITING_INPUT

    def test_npc_interaction_scenario(self, game_state):
        """Test NPC interaction scenario."""
        from src.backend.models.game_state import GamePhase

        # Player talks to NPC
        game_state.add_message("player", "我向陈玲打招呼")
        game_state.set_phase(GamePhase.PROCESSING)

        # NPC responds
        game_state.add_message("npc:chen_ling", "陈玲警惕地看着你：'你是谁？'")
        game_state.set_phase(GamePhase.WAITING_INPUT)
        game_state.turn_count += 1

        # Verify NPC is active
        assert "chen_ling" in game_state.active_npc_ids
        assert any("chen_ling" in msg["role"] for msg in game_state.messages)


class TestMessageTypeEnum:
    """Tests for MessageType enum values."""

    def test_all_expected_types_exist(self):
        """Verify all expected message types are defined."""
        expected_types = [
            "status",
            "content",
            "complete",
            "error",
            "phase",
            "dice_check",
            "dice_result",
        ]

        actual_types = [mt.value for mt in MessageType]
        for expected in expected_types:
            assert expected in actual_types, f"Missing message type: {expected}"

    def test_message_type_values_are_strings(self):
        """Verify all message type values are strings."""
        for mt in MessageType:
            assert isinstance(mt.value, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
