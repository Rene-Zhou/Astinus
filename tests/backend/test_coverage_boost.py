"""
Tests to boost coverage over 70%.

These tests cover additional edge cases and methods across the backend
to push overall coverage above the 70% threshold.
"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"

from src.backend.agents.base import AgentResponse
from src.backend.models.character import PlayerCharacter, Trait
from src.backend.models.dice_check import DiceCheckRequest, DiceCheckResult
from src.backend.models.game_state import GamePhase, GameState
from src.backend.models.i18n import LocalizedString
from src.backend.models.narrative import NarrativeGraph, Scene, SceneTransition, SceneType
from src.backend.models.persistence import GameSessionModel, MessageModel, SaveSlotModel
from src.backend.services.dice import DicePool, DiceResult, Outcome


class TestAgentResponse:
    """Tests for AgentResponse model."""

    def test_successful_response(self):
        """Test creating a successful response."""
        response = AgentResponse(
            content="成功的响应内容",
            metadata={"key": "value"},
            success=True,
        )
        assert response.success is True
        assert response.error is None
        assert response.content == "成功的响应内容"

    def test_failed_response(self):
        """Test creating a failed response."""
        response = AgentResponse(
            content="",
            metadata={},
            success=False,
            error="Something went wrong",
        )
        assert response.success is False
        assert response.error == "Something went wrong"

    def test_response_with_complex_metadata(self):
        """Test response with complex metadata."""
        response = AgentResponse(
            content="Test",
            metadata={
                "needs_check": True,
                "dice_check": {"formula": "2d6"},
                "agents_called": ["rule", "npc"],
            },
            success=True,
        )
        assert response.metadata["needs_check"] is True
        assert "dice_check" in response.metadata


class TestNarrativeModels:
    """Tests for narrative models."""

    def test_scene_creation(self):
        """Test creating a scene."""
        scene = Scene(
            id="test_scene",
            name="测试场景",
            type=SceneType.LOCATION,
            description="这是一个测试场景",
            active_npcs=["npc_1"],
            available_actions=["look", "search"],
        )
        assert scene.id == "test_scene"
        assert scene.type == SceneType.LOCATION
        assert "npc_1" in scene.active_npcs

    def test_scene_types(self):
        """Test all scene types."""
        types = [
            SceneType.LOCATION,
            SceneType.ENCOUNTER,
            SceneType.DIALOGUE,
            SceneType.CUTSCENE,
            SceneType.PUZZLE,
            SceneType.COMBAT,
        ]
        for scene_type in types:
            scene = Scene(
                id=f"scene_{scene_type.value}",
                name=f"Scene {scene_type.value}",
                type=scene_type,
            )
            assert scene.type == scene_type

    def test_narrative_graph_creation(self):
        """Test creating a narrative graph."""
        graph = NarrativeGraph(world_pack_id="test_pack")
        assert graph.world_pack_id == "test_pack"
        assert graph.scenes == {}

    def test_narrative_graph_add_scene(self):
        """Test adding scenes to graph."""
        graph = NarrativeGraph(world_pack_id="test_pack")
        scene = Scene(id="scene_1", name="Scene 1")
        graph.add_scene(scene)
        assert "scene_1" in graph.scenes

    def test_narrative_graph_get_scene(self):
        """Test getting a scene from graph."""
        graph = NarrativeGraph(world_pack_id="test_pack")
        scene = Scene(id="scene_1", name="Scene 1")
        graph.add_scene(scene)

        retrieved = graph.get_scene("scene_1")
        assert retrieved is not None
        assert retrieved.id == "scene_1"

        not_found = graph.get_scene("nonexistent")
        assert not_found is None

    def test_narrative_graph_current_scene(self):
        """Test current scene tracking."""
        graph = NarrativeGraph(world_pack_id="test_pack")
        scene = Scene(id="scene_1", name="Scene 1")
        graph.add_scene(scene)
        graph.current_scene_id = "scene_1"

        current = graph.get_current_scene()
        assert current is not None
        assert current.id == "scene_1"

    def test_scene_transition(self):
        """Test scene transition model."""
        transition = SceneTransition(
            target_scene_id="next_scene",
            description="You walk to the next room",
        )
        assert transition.target_scene_id == "next_scene"
        assert transition.condition is None


class TestPersistenceModelsExtended:
    """Extended tests for persistence models."""

    def test_game_session_model_properties(self):
        """Test GameSessionModel properties."""
        session = GameSessionModel(
            session_id="test-session",
            world_pack_id="demo_pack",
            player_name="测试玩家",
            player_data={"traits": ["brave"]},
            current_location="start",
            current_phase="waiting_input",
            turn_count=5,
            active_npc_ids=["npc_1", "npc_2"],
        )

        # Test player_data property
        assert session.player_data is not None
        assert "traits" in session.player_data

        # Test active_npc_ids property
        assert len(session.active_npc_ids) == 2
        assert "npc_1" in session.active_npc_ids

    def test_game_session_model_to_dict(self):
        """Test GameSessionModel to_dict method."""
        session = GameSessionModel(
            session_id="test-session",
            world_pack_id="demo_pack",
            player_name="测试玩家",
            player_data=None,
            current_location="start",
        )

        data = session.to_dict()
        assert data["session_id"] == "test-session"
        assert data["world_pack_id"] == "demo_pack"
        assert data["player_name"] == "测试玩家"

    def test_game_session_model_repr(self):
        """Test GameSessionModel repr."""
        session = GameSessionModel(
            session_id="test-session",
            world_pack_id="demo_pack",
            player_name="测试",
            player_data=None,
            current_location="start",
        )
        repr_str = repr(session)
        assert "GameSessionModel" in repr_str
        assert "test-session" in repr_str

    def test_save_slot_model_properties(self):
        """Test SaveSlotModel properties."""
        save = SaveSlotModel(
            session_id="test-session",
            slot_name="Save 1",
            game_state_json='{"location": "cave", "turn": 10}',
            description="In the cave",
        )

        # Test game_state property getter
        state = save.game_state
        assert state["location"] == "cave"
        assert state["turn"] == 10

        # Test game_state property setter
        save.game_state = {"location": "forest", "turn": 15}
        assert save.game_state["location"] == "forest"

    def test_save_slot_model_to_dict(self):
        """Test SaveSlotModel to_dict method."""
        save = SaveSlotModel(
            session_id="test-session",
            slot_name="Save 1",
            game_state_json='{"turn": 5}',
        )

        data = save.to_dict()
        assert data["slot_name"] == "Save 1"
        assert data["game_state"]["turn"] == 5

    def test_save_slot_model_repr(self):
        """Test SaveSlotModel repr."""
        save = SaveSlotModel(
            session_id="test-session",
            slot_name="Auto Save",
            game_state_json="{}",
            is_auto_save=True,
        )
        repr_str = repr(save)
        assert "SaveSlotModel" in repr_str
        assert "Auto Save" in repr_str


class TestDiceResultToDisplay:
    """Test DiceResult to_display method."""

    def test_basic_roll_display(self):
        """Test display for basic roll."""
        result = DiceResult(
            all_rolls=[4, 5],
            kept_rolls=[4, 5],
            dropped_rolls=[],
            modifier=0,
            total=9,
            outcome=Outcome.PARTIAL,
            is_bonus=False,
            is_penalty=False,
        )
        # to_display should return a dict with roll_detail, outcome, modifier_text
        # We just verify it doesn't raise and returns something
        display = result.to_display("cn")
        assert "roll_detail" in display
        assert "outcome" in display

    def test_bonus_roll_display(self):
        """Test display for bonus roll."""
        result = DiceResult(
            all_rolls=[6, 5, 2],
            kept_rolls=[6, 5],
            dropped_rolls=[2],
            modifier=0,
            total=11,
            outcome=Outcome.SUCCESS,
            is_bonus=True,
            is_penalty=False,
        )
        display = result.to_display("cn")
        assert display["modifier_text"] is not None  # Should show bonus indicator

    def test_penalty_roll_display(self):
        """Test display for penalty roll."""
        result = DiceResult(
            all_rolls=[6, 3, 2],
            kept_rolls=[3, 2],
            dropped_rolls=[6],
            modifier=0,
            total=5,
            outcome=Outcome.FAILURE,
            is_bonus=False,
            is_penalty=True,
        )
        display = result.to_display("en")
        assert display["modifier_text"] is not None  # Should show penalty indicator

    def test_modified_roll_display(self):
        """Test display for roll with modifier."""
        result = DiceResult(
            all_rolls=[4, 5],
            kept_rolls=[4, 5],
            dropped_rolls=[],
            modifier=2,
            total=11,
            outcome=Outcome.SUCCESS,
            is_bonus=False,
            is_penalty=False,
        )
        display = result.to_display("cn")
        # roll_detail should contain the modifier
        assert "+2" in display["roll_detail"] or "2" in display["roll_detail"]


class TestGameStateMessages:
    """Test GameState message operations."""

    @pytest.fixture
    def player(self):
        """Create test player."""
        return PlayerCharacter(
            name="测试",
            concept=LocalizedString(cn="冒险者", en="Adventurer"),
            traits=[
                Trait(
                    name=LocalizedString(cn="勇敢", en="Brave"),
                    description=LocalizedString(cn="无畏", en="Fearless"),
                    positive_aspect=LocalizedString(cn="勇气", en="Courage"),
                    negative_aspect=LocalizedString(cn="鲁莽", en="Reckless"),
                )
            ],
            tags=[],
        )

    @pytest.fixture
    def game_state(self, player):
        """Create test game state."""
        return GameState(
            session_id="test-messages",
            world_pack_id="demo_pack",
            player=player,
            current_location="start",
            active_npc_ids=[],
        )

    def test_add_message_with_metadata(self, game_state):
        """Test adding message with metadata."""
        game_state.add_message(
            role="gm",
            content="Test message",
            metadata={"agent": "gm_agent", "phase": "narrating"},
        )

        messages = game_state.get_recent_messages(1)
        assert len(messages) == 1
        assert messages[0]["role"] == "gm"
        assert messages[0]["metadata"]["agent"] == "gm_agent"

    def test_message_turn_tracking(self, game_state):
        """Test that messages track turn number."""
        game_state.turn_count = 5
        game_state.add_message("player", "Action")

        messages = game_state.get_recent_messages(1)
        assert messages[0]["turn"] == 5


class TestDiceCheckRequestStr:
    """Test DiceCheckRequest string methods."""

    def test_str_representation(self):
        """Test __str__ method."""
        request = DiceCheckRequest(
            intention="测试意图",
            influencing_factors={"traits": [], "tags": []},
            dice_formula="2d6",
            instructions=LocalizedString(cn="测试说明", en="Test instructions"),
        )
        str_repr = str(request)
        # Should contain some meaningful info
        assert str_repr is not None
        assert len(str_repr) > 0

    def test_repr_representation(self):
        """Test __repr__ method."""
        request = DiceCheckRequest(
            intention="测试",
            influencing_factors={},
            dice_formula="3d6kh2",
            instructions=LocalizedString(cn="说明", en="Instructions"),
        )
        repr_str = repr(request)
        assert "DiceCheckRequest" in repr_str


class TestWorldPackModels:
    """Tests for world pack models."""

    def test_location_data(self):
        """Test LocationData model."""
        from src.backend.models.world_pack import LocationData

        location = LocationData(
            id="tavern",
            name=LocalizedString(cn="酒馆", en="Tavern"),
            description=LocalizedString(cn="热闹的酒馆", en="A lively tavern"),
        )
        assert location.id == "tavern"
        assert location.name.get("cn") == "酒馆"

    def test_world_pack_info(self):
        """Test WorldPackInfo model."""
        from src.backend.models.world_pack import WorldPackInfo

        info = WorldPackInfo(
            name=LocalizedString(cn="测试包", en="Test Pack"),
            description=LocalizedString(cn="测试", en="Test"),
            version="1.0.0",
            author="Test Author",
        )
        assert info.version == "1.0.0"
        assert info.author == "Test Author"


class TestI18nService:
    """Tests for I18n service."""

    def test_localized_string_empty_en(self):
        """Test localized string with empty English falls back to Chinese."""
        ls = LocalizedString(cn="中文", en="")
        # When en is empty string, should still return it (not fallback)
        result = ls.get("en")
        # Empty string is falsy so should fallback
        assert result == "中文"

    def test_localized_string_with_both(self):
        """Test localized string with both languages."""
        ls = LocalizedString(cn="中文", en="English")
        assert ls.get("cn") == "中文"
        assert ls.get("en") == "English"
        assert ls.get() == "中文"  # Default is cn


class TestDiceCheckResultMethods:
    """Additional tests for DiceCheckResult."""

    def test_result_with_modifiers(self):
        """Test result with modifiers list."""
        result = DiceCheckResult(
            intention="测试",
            dice_formula="3d6kh2",
            dice_values=[6, 5, 2],
            total=11,
            threshold=7,
            success=True,
            critical=False,
            modifiers=[
                {"source": "敏锐", "effect": "advantage"},
                {"source": "受伤", "effect": "-1"},
            ],
        )
        assert len(result.modifiers) == 2
        assert result.modifiers[0]["source"] == "敏锐"


class TestMessageModel:
    """Tests for MessageModel."""

    def test_message_model_creation(self):
        """Test creating a message model."""
        msg = MessageModel(
            session_id="test-session",
            role="player",
            content="我查看房间",
            turn=1,
        )
        assert msg.role == "player"
        assert msg.content == "我查看房间"
        assert msg.turn == 1

    def test_message_model_with_metadata(self):
        """Test message model with metadata."""
        msg = MessageModel(
            session_id="test-session",
            role="gm",
            content="房间里很黑",
            turn=1,
            metadata={"agent": "gm_agent"},
        )
        assert msg.extra_data is not None
        assert msg.extra_data["agent"] == "gm_agent"

    def test_message_model_to_dict(self):
        """Test message model to_dict method."""
        msg = MessageModel(
            session_id="test-session",
            role="player",
            content="测试内容",
            turn=2,
        )
        data = msg.to_dict()
        assert data["role"] == "player"
        assert data["content"] == "测试内容"
        assert data["turn"] == 2

    def test_message_model_repr(self):
        """Test message model repr."""
        msg = MessageModel(
            session_id="test-session",
            role="assistant",
            content="Test",
            turn=3,
        )
        repr_str = repr(msg)
        assert "MessageModel" in repr_str
        assert "assistant" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
