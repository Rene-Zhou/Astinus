"""
Integration tests for services and WebSocket handlers.

Tests the backend services and WebSocket message handling flows
to increase coverage for:
- WebSocket handlers (_handle_player_input, _handle_dice_result)
- Database service operations
- Narrative service
- World pack loading
- Dice rolling
"""

import asyncio
import os
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set fake API key before imports
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"

from src.backend.agents.base import AgentResponse
from src.backend.api.websockets import (
    ConnectionManager,
    MessageType,
    StreamMessage,
    _handle_dice_result,
    _handle_player_input,
    manager,
)
from src.backend.models.character import PlayerCharacter, Trait
from src.backend.models.game_state import GamePhase, GameState
from src.backend.models.i18n import LocalizedString


class TestWebSocketHandlers:
    """Tests for WebSocket message handlers."""

    @pytest.fixture
    def mock_game_state(self):
        """Create a mock game state."""
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
            session_id="ws-test-session",
            world_pack_id="demo_pack",
            player=player,
            current_location="study",
            active_npc_ids=["chen_ling"],
        )

    @pytest.fixture
    def mock_gm_agent(self, mock_game_state):
        """Create a mock GM agent."""
        agent = MagicMock()
        agent.game_state = mock_game_state
        agent.process = AsyncMock(
            return_value=AgentResponse(
                content="你仔细查看了房间，发现书架后似乎有什么东西。",
                metadata={
                    "agent": "gm_agent",
                    "phase": "narrating",
                    "needs_check": False,
                },
                success=True,
            )
        )
        return agent

    @pytest.fixture
    def mock_gm_agent_with_dice_check(self, mock_game_state):
        """Create a mock GM agent that returns a dice check request."""
        agent = MagicMock()
        agent.game_state = mock_game_state
        agent.process = AsyncMock(
            return_value=AgentResponse(
                content="你需要进行一次检定",
                metadata={
                    "agent": "gm_agent",
                    "phase": "processing",
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
        )
        return agent

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
        ws.receive_text = AsyncMock()
        ws.close = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_handle_player_input_success(
        self, connection_manager, mock_websocket, mock_gm_agent
    ):
        """Test handling player input successfully."""
        session_id = "input-test"

        # Connect
        await connection_manager.connect(session_id, mock_websocket)

        # Replace global manager
        original_active = manager.active_connections
        manager.active_connections = connection_manager.active_connections

        try:
            data = {
                "content": "我查看书架",
                "lang": "cn",
                "stream": False,
            }

            await _handle_player_input(session_id, data, mock_gm_agent)

            # Verify agent was called
            mock_gm_agent.process.assert_called_once()
            call_args = mock_gm_agent.process.call_args[0][0]
            assert call_args["player_input"] == "我查看书架"
            assert call_args["lang"] == "cn"

            # Verify messages were sent (status, phase, complete)
            assert mock_websocket.send_json.call_count >= 2
        finally:
            manager.active_connections = original_active

    @pytest.mark.asyncio
    async def test_handle_player_input_empty_content(
        self, connection_manager, mock_websocket, mock_gm_agent
    ):
        """Test handling player input with empty content."""
        session_id = "empty-input-test"

        await connection_manager.connect(session_id, mock_websocket)

        original_active = manager.active_connections
        manager.active_connections = connection_manager.active_connections

        try:
            data = {
                "content": "",
                "lang": "cn",
            }

            await _handle_player_input(session_id, data, mock_gm_agent)

            # Verify error was sent
            calls = mock_websocket.send_json.call_args_list
            error_sent = any(call[0][0].get("type") == "error" for call in calls)
            assert error_sent
        finally:
            manager.active_connections = original_active

    @pytest.mark.asyncio
    async def test_handle_player_input_with_dice_check(
        self, connection_manager, mock_websocket, mock_gm_agent_with_dice_check
    ):
        """Test handling player input that triggers dice check."""
        session_id = "dice-check-test"

        await connection_manager.connect(session_id, mock_websocket)

        original_active = manager.active_connections
        manager.active_connections = connection_manager.active_connections

        try:
            data = {
                "content": "我翻找书架",
                "lang": "cn",
            }

            await _handle_player_input(session_id, data, mock_gm_agent_with_dice_check)

            # Verify dice check message was sent
            calls = mock_websocket.send_json.call_args_list
            dice_check_sent = any(call[0][0].get("type") == "dice_check" for call in calls)
            assert dice_check_sent
        finally:
            manager.active_connections = original_active

    @pytest.mark.asyncio
    async def test_handle_dice_result_success(
        self, connection_manager, mock_websocket, mock_gm_agent
    ):
        """Test handling dice result - success outcome."""
        session_id = "dice-result-test"

        await connection_manager.connect(session_id, mock_websocket)

        original_active = manager.active_connections
        manager.active_connections = connection_manager.active_connections

        try:
            data = {
                "result": 10,
                "all_rolls": [6, 4],
                "kept_rolls": [6, 4],
                "outcome": "success",
            }

            await _handle_dice_result(session_id, data, mock_gm_agent)

            # Verify dice result was stored
            assert mock_gm_agent.game_state.last_check_result is not None
            assert mock_gm_agent.game_state.last_check_result["total"] == 10
            assert mock_gm_agent.game_state.last_check_result["outcome"] == "success"

            # Verify phase change and complete messages sent
            calls = mock_websocket.send_json.call_args_list
            phase_sent = any(call[0][0].get("type") == "phase" for call in calls)
            complete_sent = any(call[0][0].get("type") == "complete" for call in calls)
            assert phase_sent
            assert complete_sent
        finally:
            manager.active_connections = original_active

    @pytest.mark.asyncio
    async def test_handle_dice_result_critical(
        self, connection_manager, mock_websocket, mock_gm_agent
    ):
        """Test handling dice result - critical success."""
        session_id = "dice-critical-test"

        await connection_manager.connect(session_id, mock_websocket)

        original_active = manager.active_connections
        manager.active_connections = connection_manager.active_connections

        try:
            data = {
                "result": 12,
                "all_rolls": [6, 6],
                "kept_rolls": [6, 6],
                "outcome": "critical",
            }

            await _handle_dice_result(session_id, data, mock_gm_agent)

            # Verify critical narrative was generated
            calls = mock_websocket.send_json.call_args_list
            complete_call = next(call for call in calls if call[0][0].get("type") == "complete")
            content = complete_call[0][0]["data"]["content"]
            assert "大成功" in content or "12" in content
        finally:
            manager.active_connections = original_active

    @pytest.mark.asyncio
    async def test_handle_dice_result_failure(
        self, connection_manager, mock_websocket, mock_gm_agent
    ):
        """Test handling dice result - failure outcome."""
        session_id = "dice-fail-test"

        await connection_manager.connect(session_id, mock_websocket)

        original_active = manager.active_connections
        manager.active_connections = connection_manager.active_connections

        try:
            data = {
                "result": 4,
                "all_rolls": [2, 2],
                "kept_rolls": [2, 2],
                "outcome": "failure",
            }

            await _handle_dice_result(session_id, data, mock_gm_agent)

            # Verify failure narrative was generated
            calls = mock_websocket.send_json.call_args_list
            complete_call = next(call for call in calls if call[0][0].get("type") == "complete")
            content = complete_call[0][0]["data"]["content"]
            assert "失败" in content or "4" in content
        finally:
            manager.active_connections = original_active

    @pytest.mark.asyncio
    async def test_handle_dice_result_partial(
        self, connection_manager, mock_websocket, mock_gm_agent
    ):
        """Test handling dice result - partial success."""
        session_id = "dice-partial-test"

        await connection_manager.connect(session_id, mock_websocket)

        original_active = manager.active_connections
        manager.active_connections = connection_manager.active_connections

        try:
            data = {
                "result": 7,
                "all_rolls": [4, 3],
                "kept_rolls": [4, 3],
                "outcome": "partial",
            }

            await _handle_dice_result(session_id, data, mock_gm_agent)

            # Verify partial success narrative
            calls = mock_websocket.send_json.call_args_list
            complete_call = next(call for call in calls if call[0][0].get("type") == "complete")
            content = complete_call[0][0]["data"]["content"]
            assert "部分成功" in content or "代价" in content or "7" in content
        finally:
            manager.active_connections = original_active

    @pytest.mark.asyncio
    async def test_handle_dice_result_missing_result(
        self, connection_manager, mock_websocket, mock_gm_agent
    ):
        """Test handling dice result with missing result field."""
        session_id = "missing-result-test"

        await connection_manager.connect(session_id, mock_websocket)

        original_active = manager.active_connections
        manager.active_connections = connection_manager.active_connections

        try:
            data = {
                "all_rolls": [3, 4],
                "kept_rolls": [3, 4],
                "outcome": "failure",
            }

            await _handle_dice_result(session_id, data, mock_gm_agent)

            # Verify error was sent
            calls = mock_websocket.send_json.call_args_list
            error_sent = any(call[0][0].get("type") == "error" for call in calls)
            assert error_sent
        finally:
            manager.active_connections = original_active

    @pytest.mark.asyncio
    async def test_phase_returns_to_waiting_input_after_player_input(
        self, connection_manager, mock_websocket, mock_gm_agent
    ):
        """Test that phase returns to waiting_input after player input processing completes."""
        session_id = "phase-return-test"

        await connection_manager.connect(session_id, mock_websocket)

        original_active = manager.active_connections
        manager.active_connections = connection_manager.active_connections

        try:
            data = {
                "content": "我查看书架",
                "lang": "cn",
                "stream": False,
            }

            await _handle_player_input(session_id, data, mock_gm_agent)

            # Verify phase was set to waiting_input at the end
            assert mock_gm_agent.game_state.current_phase == GamePhase.WAITING_INPUT

            # Verify waiting_input phase message was sent
            calls = mock_websocket.send_json.call_args_list
            phase_messages = [call[0][0] for call in calls if call[0][0].get("type") == "phase"]
            # The last phase message should be waiting_input
            assert len(phase_messages) >= 1
            last_phase_msg = phase_messages[-1]
            assert last_phase_msg["data"]["phase"] == "waiting_input"
        finally:
            manager.active_connections = original_active

    @pytest.mark.asyncio
    async def test_phase_returns_to_waiting_input_after_dice_result(
        self, connection_manager, mock_websocket, mock_gm_agent
    ):
        """Test that phase returns to waiting_input after dice result processing completes."""
        session_id = "phase-dice-return-test"

        await connection_manager.connect(session_id, mock_websocket)

        original_active = manager.active_connections
        manager.active_connections = connection_manager.active_connections

        try:
            data = {
                "result": 8,
                "all_rolls": [5, 3],
                "kept_rolls": [5, 3],
                "outcome": "success",
            }

            await _handle_dice_result(session_id, data, mock_gm_agent)

            # Verify phase was set to waiting_input at the end
            assert mock_gm_agent.game_state.current_phase == GamePhase.WAITING_INPUT

            # Verify waiting_input phase message was sent as the last phase
            calls = mock_websocket.send_json.call_args_list
            phase_messages = [call[0][0] for call in calls if call[0][0].get("type") == "phase"]
            # The last phase message should be waiting_input
            assert len(phase_messages) >= 1
            last_phase_msg = phase_messages[-1]
            assert last_phase_msg["data"]["phase"] == "waiting_input"
        finally:
            manager.active_connections = original_active

    @pytest.mark.asyncio
    async def test_phase_stays_dice_check_when_check_needed(
        self, connection_manager, mock_websocket, mock_gm_agent_with_dice_check
    ):
        """Test that phase stays at dice_check when a dice check is needed."""
        session_id = "phase-dice-check-test"

        await connection_manager.connect(session_id, mock_websocket)

        original_active = manager.active_connections
        manager.active_connections = connection_manager.active_connections

        try:
            data = {
                "content": "我翻找书架",
                "lang": "cn",
            }

            await _handle_player_input(session_id, data, mock_gm_agent_with_dice_check)

            # Verify phase is dice_check (should NOT go back to waiting_input)
            assert mock_gm_agent_with_dice_check.game_state.current_phase == GamePhase.DICE_CHECK

            # Verify dice_check phase message was sent
            calls = mock_websocket.send_json.call_args_list
            phase_messages = [call[0][0] for call in calls if call[0][0].get("type") == "phase"]
            # The last phase message should be dice_check, not waiting_input
            assert len(phase_messages) >= 1
            last_phase_msg = phase_messages[-1]
            assert last_phase_msg["data"]["phase"] == "dice_check"
        finally:
            manager.active_connections = original_active


class TestDatabaseServiceIntegration:
    """Integration tests for database service."""

    @pytest.fixture
    def temp_db_url(self, tmp_path):
        """Create a temporary database URL."""
        return f"sqlite+aiosqlite:///{tmp_path}/test_game.db"

    @pytest.mark.asyncio
    async def test_database_service_lifecycle(self, temp_db_url):
        """Test database service initialization and cleanup."""
        from src.backend.services.database import DatabaseService

        service = DatabaseService(db_url=temp_db_url)

        # Initialize
        await service.initialize()
        assert service._engine is not None
        assert service.is_connected is True

        # Close
        await service.close()

    @pytest.mark.asyncio
    async def test_create_and_get_game_session(self, temp_db_url):
        """Test creating and retrieving a game session."""
        from src.backend.services.database import DatabaseService

        service = DatabaseService(db_url=temp_db_url)
        await service.initialize()

        try:
            # Create session
            session_id = str(uuid.uuid4())
            session = await service.create_game_session(
                session_id=session_id,
                world_pack_id="demo_pack",
                player_name="测试玩家",
                player_data={"name": "测试玩家", "traits": []},
                current_location="start",
            )
            assert session is not None
            assert session.world_pack_id == "demo_pack"
            assert session.session_id == session_id

            # Get session
            retrieved = await service.get_game_session(session_id)
            assert retrieved is not None
            assert retrieved.session_id == session_id
            assert retrieved.world_pack_id == "demo_pack"
        finally:
            await service.close()

    @pytest.mark.asyncio
    async def test_list_game_sessions(self, temp_db_url):
        """Test listing game sessions."""
        from src.backend.services.database import DatabaseService

        service = DatabaseService(db_url=temp_db_url)
        await service.initialize()

        try:
            # Create multiple sessions
            for i in range(3):
                await service.create_game_session(
                    session_id=str(uuid.uuid4()),
                    world_pack_id=f"pack_{i}",
                    player_name=f"Player {i}",
                    player_data={},
                    current_location="start",
                )

            # List sessions
            sessions = await service.list_game_sessions()
            assert len(sessions) >= 3
        finally:
            await service.close()

    @pytest.mark.asyncio
    async def test_update_game_session(self, temp_db_url):
        """Test updating a game session."""
        from src.backend.services.database import DatabaseService

        service = DatabaseService(db_url=temp_db_url)
        await service.initialize()

        try:
            # Create session
            session_id = str(uuid.uuid4())
            session = await service.create_game_session(
                session_id=session_id,
                world_pack_id="demo_pack",
                player_name="测试玩家",
                player_data={},
                current_location="start",
            )

            # Update session
            updated = await service.update_game_session(
                session_id, current_location="new_location", turn_count=5
            )
            assert updated is not None

            # Verify update
            retrieved = await service.get_game_session(session_id)
            assert retrieved.current_location == "new_location"
            assert retrieved.turn_count == 5
        finally:
            await service.close()

    @pytest.mark.asyncio
    async def test_delete_game_session(self, temp_db_url):
        """Test deleting a game session."""
        from src.backend.services.database import DatabaseService

        service = DatabaseService(db_url=temp_db_url)
        await service.initialize()

        try:
            # Create session
            session_id = str(uuid.uuid4())
            session = await service.create_game_session(
                session_id=session_id,
                world_pack_id="demo_pack",
                player_name="测试玩家",
                player_data={},
                current_location="start",
            )

            # Delete session
            result = await service.delete_game_session(session_id)
            assert result is True

            # Verify deletion
            retrieved = await service.get_game_session(session_id)
            assert retrieved is None
        finally:
            await service.close()


class TestWorldPackServiceIntegration:
    """Integration tests for world pack service."""

    @pytest.fixture
    def world_packs_dir(self):
        """Get the test world packs directory."""
        # Use the test data packs directory
        test_dir = Path(__file__).parent.parent / "data" / "packs"
        if test_dir.exists():
            return test_dir
        # Fall back to main data directory
        main_dir = Path(__file__).parent.parent.parent / "data" / "packs"
        if main_dir.exists():
            return main_dir
        return None

    def test_load_demo_pack(self, world_packs_dir):
        """Test loading the demo world pack."""
        if world_packs_dir is None or not (world_packs_dir / "demo_pack.json").exists():
            pytest.skip("Demo pack not available")

        from src.backend.services.world import WorldPackLoader

        loader = WorldPackLoader(world_packs_dir)
        pack = loader.load("demo_pack")

        assert pack is not None
        assert pack.info.name.get("cn") is not None

    def test_get_npc_from_pack(self, world_packs_dir):
        """Test getting NPC from world pack."""
        if world_packs_dir is None or not (world_packs_dir / "demo_pack.json").exists():
            pytest.skip("Demo pack not available")

        from src.backend.services.world import WorldPackLoader

        loader = WorldPackLoader(world_packs_dir)
        pack = loader.load("demo_pack")

        # Try to get an NPC (assuming chen_ling exists in demo pack)
        npc = pack.get_npc("chen_ling")
        if npc is not None:
            assert npc.soul.name is not None

    def test_get_location_from_pack(self, world_packs_dir):
        """Test getting location from world pack."""
        if world_packs_dir is None or not (world_packs_dir / "demo_pack.json").exists():
            pytest.skip("Demo pack not available")

        from src.backend.services.world import WorldPackLoader

        loader = WorldPackLoader(world_packs_dir)
        pack = loader.load("demo_pack")

        # Try to get a location
        location = pack.get_location("study")
        if location is not None:
            assert location.name is not None


class TestDiceServiceIntegration:
    """Integration tests for dice rolling using DicePool."""

    def test_roll_2d6(self):
        """Test rolling 2d6 (base roll)."""
        from src.backend.services.dice import DicePool

        pool = DicePool()
        result = pool.roll()

        assert len(result.all_rolls) == 2
        assert len(result.kept_rolls) == 2
        assert all(1 <= r <= 6 for r in result.all_rolls)
        assert 2 <= result.total <= 12

    def test_roll_3d6_keep_highest_2(self):
        """Test rolling 3d6 and keeping highest 2 (advantage)."""
        from src.backend.services.dice import DicePool

        pool = DicePool(bonus_dice=1)
        result = pool.roll()

        assert len(result.all_rolls) == 3
        assert len(result.kept_rolls) == 2
        assert result.is_bonus is True
        assert result.is_penalty is False
        # Verify highest were kept
        sorted_rolls = sorted(result.all_rolls, reverse=True)
        assert sorted(result.kept_rolls, reverse=True) == sorted_rolls[:2]

    def test_roll_3d6_keep_lowest_2(self):
        """Test rolling 3d6 and keeping lowest 2 (disadvantage)."""
        from src.backend.services.dice import DicePool

        pool = DicePool(penalty_dice=1)
        result = pool.roll()

        assert len(result.all_rolls) == 3
        assert len(result.kept_rolls) == 2
        assert result.is_bonus is False
        assert result.is_penalty is True
        # Verify lowest were kept
        sorted_rolls = sorted(result.all_rolls)
        assert sorted(result.kept_rolls) == sorted_rolls[:2]

    def test_roll_with_modifier(self):
        """Test rolling with modifier."""
        from src.backend.services.dice import DicePool

        pool = DicePool(modifier=3)
        result = pool.roll()

        assert len(result.kept_rolls) == 2
        assert result.modifier == 3
        assert result.total == sum(result.kept_rolls) + 3

    def test_bonus_and_penalty_cancel(self):
        """Test that bonus and penalty dice cancel each other."""
        from src.backend.services.dice import DicePool

        pool = DicePool(bonus_dice=2, penalty_dice=2)
        result = pool.roll()

        # Should be a base 2d6 roll
        assert len(result.all_rolls) == 2
        assert result.is_bonus is False
        assert result.is_penalty is False

    def test_dice_formula_generation(self):
        """Test dice formula string generation."""
        from src.backend.services.dice import DicePool

        # Base roll
        assert DicePool().get_dice_formula() == "2d6"

        # Bonus dice
        assert DicePool(bonus_dice=1).get_dice_formula() == "3d6kh2"
        assert DicePool(bonus_dice=2).get_dice_formula() == "4d6kh2"

        # Penalty dice
        assert DicePool(penalty_dice=1).get_dice_formula() == "3d6kl2"
        assert DicePool(penalty_dice=2).get_dice_formula() == "4d6kl2"

    def test_multiple_rolls_randomness(self):
        """Test that multiple rolls produce different results."""
        from src.backend.services.dice import DicePool

        pool = DicePool()
        results = [pool.roll().total for _ in range(100)]

        # Should have some variety in 100 rolls
        unique_results = set(results)
        assert len(unique_results) > 1

    def test_outcome_determination(self):
        """Test outcome determination based on total."""
        from src.backend.services.dice import DicePool, Outcome

        pool = DicePool()

        # Test outcome determination logic
        assert pool._determine_outcome(12) == Outcome.CRITICAL
        assert pool._determine_outcome(15) == Outcome.CRITICAL
        assert pool._determine_outcome(10) == Outcome.SUCCESS
        assert pool._determine_outcome(11) == Outcome.SUCCESS
        assert pool._determine_outcome(7) == Outcome.PARTIAL
        assert pool._determine_outcome(8) == Outcome.PARTIAL
        assert pool._determine_outcome(9) == Outcome.PARTIAL
        assert pool._determine_outcome(6) == Outcome.FAILURE
        assert pool._determine_outcome(2) == Outcome.FAILURE


class TestNarrativeModelsIntegration:
    """Integration tests for narrative models."""

    def test_narrative_scene_creation(self):
        """Test creating a narrative scene."""
        from src.backend.models.narrative import Scene, SceneType

        scene = Scene(
            id="test_scene",
            name="测试场景",
            description="这是一个测试场景",
            type=SceneType.LOCATION,
            active_npcs=["npc_1", "npc_2"],
        )

        assert scene.id == "test_scene"
        assert scene.name == "测试场景"
        assert scene.type == SceneType.LOCATION
        assert "npc_1" in scene.active_npcs

    def test_narrative_graph_operations(self):
        """Test narrative graph operations."""
        from src.backend.models.narrative import NarrativeGraph, Scene, SceneType

        graph = NarrativeGraph(world_pack_id="test_pack")

        # Add scenes
        scene1 = Scene(
            id="scene_1",
            name="场景1",
            description="第一个场景",
            type=SceneType.LOCATION,
        )
        scene2 = Scene(
            id="scene_2",
            name="场景2",
            description="第二个场景",
            type=SceneType.LOCATION,
        )

        graph.add_scene(scene1)
        graph.add_scene(scene2)

        # Retrieve scenes
        retrieved = graph.get_scene("scene_1")
        assert retrieved is not None
        assert retrieved.id == "scene_1"

        # Set current scene
        graph.current_scene_id = "scene_1"
        current = graph.get_current_scene()
        assert current is not None
        assert current.id == "scene_1"


class TestPersistenceModelsIntegration:
    """Integration tests for persistence models."""

    def test_game_session_model_creation(self):
        """Test creating a game session model."""
        from src.backend.models.persistence import GameSessionModel

        session = GameSessionModel(
            session_id=str(uuid.uuid4()),
            world_pack_id="demo_pack",
            player_name="测试玩家",
            player_data={"name": "测试玩家", "traits": []},
            current_location="start",
        )

        assert session.world_pack_id == "demo_pack"
        assert session.player_name == "测试玩家"
        assert session.current_location == "start"

    def test_save_slot_model_creation(self):
        """Test creating a save slot model."""
        from src.backend.models.persistence import SaveSlotModel

        save = SaveSlotModel(
            session_id=str(uuid.uuid4()),
            slot_name="测试存档",
            game_state_json='{"location": "saved_location", "turn": 10}',
        )

        assert save.slot_name == "测试存档"
        assert save.game_state["location"] == "saved_location"
        assert save.game_state["turn"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
