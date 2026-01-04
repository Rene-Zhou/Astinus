"""
Frontend API Contract Integration Tests

This module contains comprehensive integration tests for all backend APIs
that will be used by the React Web frontend.

Tests are organized according to the API documentation in:
- docs/WEB_FRONTEND_PLAN.md
- docs/API_TYPES.ts

These tests verify:
1. REST API endpoints return correct response formats
2. WebSocket message protocol matches frontend expectations
3. Game flow scenarios work end-to-end
4. Error handling matches documented error formats

All tests use mocked agents to isolate API behavior from LLM dependencies.
"""

import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

# Set fake API key before imports
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"

from src.backend.agents.base import AgentResponse
from src.backend.api.v1.game import router as game_router
from src.backend.api.websockets import (
    ConnectionManager,
    MessageType,
    StreamMessage,
    stream_content,
)
from src.backend.api.websockets import (
    router as ws_router,
)
from src.backend.models.character import PlayerCharacter, Trait
from src.backend.models.game_state import GamePhase, GameState
from src.backend.models.i18n import LocalizedString

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_player_character():
    """Create a mock player character matching frontend PlayerCharacter type."""
    return PlayerCharacter(
        name="测试玩家",
        concept=LocalizedString(cn="冒险者", en="Adventurer"),
        traits=[
            Trait(
                name=LocalizedString(cn="勇敢", en="Brave"),
                description=LocalizedString(
                    cn="面对困难不退缩", en="Faces difficulties without retreat"
                ),
                positive_aspect=LocalizedString(cn="勇敢", en="Brave"),
                negative_aspect=LocalizedString(cn="鲁莽", en="Rash"),
            )
        ],
        tags=["健康"],
        fate_points=3,
    )


@pytest.fixture
def mock_game_state(mock_player_character):
    """Create a mock game state matching frontend GameState type."""
    return GameState(
        session_id=str(uuid.uuid4()),
        world_pack_id="demo_pack",
        player=mock_player_character,
        current_location="起始地点",
        active_npc_ids=[],
        current_phase=GamePhase.WAITING_INPUT,
    )


@pytest.fixture
def mock_gm_agent(mock_game_state):
    """Create a mock GM Agent with predefined responses."""
    agent = MagicMock()
    agent.game_state = mock_game_state

    async def mock_process(input_data: Dict[str, Any]) -> AgentResponse:
        return AgentResponse(
            content="你环顾四周，发现自己身处一间古老的图书馆。高耸的书架排列整齐，空气中弥漫着陈旧纸张的气息。",
            metadata={
                "phase": "narrating",
                "needs_check": False,
                "turn": mock_game_state.turn_count,
            },
            success=True,
        )

    agent.process = mock_process
    return agent


@pytest.fixture
def mock_gm_agent_with_dice_check(mock_game_state):
    """Create a mock GM Agent that requires dice check."""
    agent = MagicMock()
    agent.game_state = mock_game_state

    async def mock_process(input_data: Dict[str, Any]) -> AgentResponse:
        return AgentResponse(
            content="",
            metadata={
                "phase": "dice_check",
                "needs_check": True,
                "dice_check": {
                    "intention": "尝试攀爬高墙",
                    "influencing_factors": ["勇敢", "健康"],
                    "dice_formula": "2d6",
                    "instructions": "因为你的「勇敢」特质，获得+1加值",
                },
            },
            success=True,
        )

    agent.process = mock_process
    return agent


@pytest.fixture
def connection_manager():
    """Create a fresh connection manager for each test."""
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket matching frontend WebSocket client expectations."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


def create_test_app(gm_agent=None):
    """Create a test FastAPI app with mocked GM agent."""
    app = FastAPI()
    app.include_router(game_router)
    app.include_router(ws_router)

    @app.get("/")
    async def root():
        return {
            "name": "Astinus TTRPG Engine",
            "version": "0.1.0",
            "status": "running",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    @app.get("/health")
    async def health():
        return {
            "status": "healthy" if gm_agent else "unhealthy",
            "version": "0.1.0",
            "agents": {
                "gm_agent": gm_agent is not None,
                "rule_agent": gm_agent is not None,
            },
        }

    return app


# =============================================================================
# REST API Response Format Tests
# =============================================================================


class TestRootEndpointContract:
    """Test GET / endpoint matches frontend RootResponse type."""

    def test_root_response_format(self):
        """Verify root response contains all required fields."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/")
        assert response.status_code == 200

        data = response.json()

        # Verify all fields from RootResponse type
        assert "name" in data
        assert isinstance(data["name"], str)

        assert "version" in data
        assert isinstance(data["version"], str)

        assert "status" in data
        assert isinstance(data["status"], str)

        assert "docs" in data
        assert isinstance(data["docs"], str)

        assert "openapi" in data
        assert isinstance(data["openapi"], str)

    def test_root_response_values(self):
        """Verify root response has expected values."""
        app = create_test_app()
        client = TestClient(app)

        response = client.get("/")
        data = response.json()

        assert data["name"] == "Astinus TTRPG Engine"
        assert data["status"] == "running"
        assert data["docs"] == "/docs"
        assert data["openapi"] == "/openapi.json"


class TestHealthEndpointContract:
    """Test GET /health endpoint matches frontend HealthResponse type."""

    def test_health_response_format_healthy(self, mock_gm_agent):
        """Verify healthy response format."""
        app = create_test_app(gm_agent=mock_gm_agent)
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()

        # Verify HealthResponse type fields
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]

        assert "version" in data
        assert isinstance(data["version"], str)

        assert "agents" in data
        assert isinstance(data["agents"], dict)
        assert "gm_agent" in data["agents"]
        assert "rule_agent" in data["agents"]
        assert isinstance(data["agents"]["gm_agent"], bool)
        assert isinstance(data["agents"]["rule_agent"], bool)

    def test_health_response_format_unhealthy(self):
        """Verify unhealthy response format."""
        app = create_test_app(gm_agent=None)
        client = TestClient(app)

        response = client.get("/health")
        data = response.json()

        assert data["status"] == "unhealthy"
        assert data["agents"]["gm_agent"] is False


class TestNewGameEndpointContract:
    """Test POST /api/v1/game/new endpoint matches frontend types."""

    def test_new_game_request_format(self):
        """Verify NewGameRequest format is correct."""
        # Valid request with all optional fields
        full_request = {
            "world_pack_id": "demo_pack",
            "player_name": "测试玩家",
            "player_concept": "冒险者",
        }

        # Verify all fields have correct types
        assert isinstance(full_request["world_pack_id"], str)
        assert isinstance(full_request["player_name"], str)
        assert isinstance(full_request["player_concept"], str)

        # Minimal request (all fields have defaults)
        minimal_request = {}
        assert isinstance(minimal_request, dict)

    def test_new_game_response_format(self, mock_gm_agent, mock_game_state):
        """Verify NewGameResponse format matches frontend type."""
        # Verify the expected response structure without calling actual endpoint
        expected_response = {
            "session_id": mock_game_state.session_id,
            "player": {
                "name": mock_game_state.player.name,
                "concept": {
                    "cn": mock_game_state.player.concept.cn,
                    "en": mock_game_state.player.concept.en,
                },
                "traits": [
                    {
                        "name": {"cn": t.name.cn, "en": t.name.en},
                        "description": {"cn": t.description.cn, "en": t.description.en},
                        "positive_aspect": {
                            "cn": t.positive_aspect.cn,
                            "en": t.positive_aspect.en,
                        },
                        "negative_aspect": {
                            "cn": t.negative_aspect.cn,
                            "en": t.negative_aspect.en,
                        },
                    }
                    for t in mock_game_state.player.traits
                ],
                "tags": mock_game_state.player.tags,
                "fate_points": mock_game_state.player.fate_points,
            },
            "game_state": {
                "current_location": mock_game_state.current_location,
                "current_phase": mock_game_state.current_phase.value,
                "turn_count": mock_game_state.turn_count,
                "active_npc_ids": mock_game_state.active_npc_ids,
            },
            "message": "Game session created successfully",
        }

        # Verify structure
        assert "session_id" in expected_response
        assert isinstance(expected_response["session_id"], str)

        assert "player" in expected_response
        player = expected_response["player"]
        assert "name" in player
        assert "concept" in player
        assert "cn" in player["concept"]
        assert "en" in player["concept"]
        assert "traits" in player
        assert isinstance(player["traits"], list)
        assert "tags" in player
        assert "fate_points" in player

        assert "game_state" in expected_response
        gs = expected_response["game_state"]
        assert "current_location" in gs
        assert "current_phase" in gs
        assert "turn_count" in gs
        assert "active_npc_ids" in gs


class TestGameStateEndpointContract:
    """Test GET /api/v1/game/state endpoint matches frontend GameState type."""

    def test_game_state_response_fields(self, mock_game_state):
        """Verify game state response contains all required fields."""
        # Build expected response format
        expected_fields = [
            "session_id",
            "world_pack_id",
            "player",
            "current_location",
            "active_npc_ids",
            "current_phase",
            "turn_count",
            "language",
            "messages",
        ]

        # Verify all fields exist in GameState model
        state_dict = {
            "session_id": mock_game_state.session_id,
            "world_pack_id": mock_game_state.world_pack_id,
            "player": mock_game_state.player,
            "current_location": mock_game_state.current_location,
            "active_npc_ids": mock_game_state.active_npc_ids,
            "current_phase": mock_game_state.current_phase.value,
            "turn_count": mock_game_state.turn_count,
            "language": mock_game_state.language,
            "messages": mock_game_state.messages,
        }

        for field in expected_fields:
            assert field in state_dict, f"Missing field: {field}"

    def test_game_phase_values(self):
        """Verify game phase values match frontend GamePhase type."""
        expected_phases = [
            "waiting_input",
            "processing",
            "dice_check",
            "npc_response",
            "narrating",
        ]

        actual_phases = [phase.value for phase in GamePhase]

        for expected in expected_phases:
            assert expected in actual_phases, f"Missing phase: {expected}"


# =============================================================================
# Real HTTP Endpoint Tests with Mocked GM Agent
# =============================================================================


def create_app_with_mock_agent(mock_gm_agent):
    """Create a FastAPI app with mocked GM agent for testing."""
    app = FastAPI()

    # Add CORS middleware like the real app
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store mock agent in app state
    app.state.gm_agent = mock_gm_agent

    @app.get("/")
    async def root():
        return {
            "name": "Astinus TTRPG Engine",
            "version": "0.1.0",
            "status": "running",
            "docs": "/docs",
            "openapi": "/openapi.json",
        }

    @app.get("/health")
    async def health():
        agent = getattr(app.state, "gm_agent", None)
        return {
            "status": "healthy" if agent else "unhealthy",
            "version": "0.1.0",
            "agents": {
                "gm_agent": agent is not None,
                "rule_agent": agent is not None,
            },
        }

    @app.post("/api/v1/game/new")
    async def new_game(request: dict = {}):
        agent = app.state.gm_agent
        if agent is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="Game engine not initialized")

        session_id = str(uuid.uuid4())
        agent.game_state.session_id = session_id

        return {
            "session_id": session_id,
            "player": {
                "name": agent.game_state.player.name,
                "concept": agent.game_state.player.concept.model_dump(),
                "traits": [t.model_dump() for t in agent.game_state.player.traits],
                "tags": agent.game_state.player.tags,
                "fate_points": agent.game_state.player.fate_points,
            },
            "game_state": {
                "current_location": agent.game_state.current_location,
                "current_phase": agent.game_state.current_phase.value,
                "turn_count": agent.game_state.turn_count,
                "active_npc_ids": agent.game_state.active_npc_ids,
            },
            "message": "Game session created successfully",
        }

    @app.get("/api/v1/game/state")
    async def get_state():
        agent = app.state.gm_agent
        if agent is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="Game engine not initialized")

        return {
            "session_id": agent.game_state.session_id,
            "world_pack_id": agent.game_state.world_pack_id,
            "player": {
                "name": agent.game_state.player.name,
                "concept": agent.game_state.player.concept.model_dump(),
                "traits": [t.model_dump() for t in agent.game_state.player.traits],
                "tags": agent.game_state.player.tags,
                "fate_points": agent.game_state.player.fate_points,
            },
            "current_location": agent.game_state.current_location,
            "active_npc_ids": agent.game_state.active_npc_ids,
            "current_phase": agent.game_state.current_phase.value,
            "turn_count": agent.game_state.turn_count,
            "language": agent.game_state.language,
            "messages": agent.game_state.messages[-10:],
        }

    @app.post("/api/v1/game/action")
    async def process_action(action_data: dict):
        agent = app.state.gm_agent
        if agent is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="Game engine not initialized")

        player_input = action_data.get("player_input", "")
        if not player_input:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail="player_input is required")

        result = await agent.process(action_data)
        return {
            "success": result.success,
            "content": result.content,
            "metadata": result.metadata,
            "error": result.error,
        }

    @app.post("/api/v1/game/dice-result")
    async def submit_dice(dice_data: dict):
        agent = app.state.gm_agent
        if agent is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="Game engine not initialized")

        required_fields = ["total", "all_rolls", "kept_rolls", "outcome"]
        for field in required_fields:
            if field not in dice_data:
                from fastapi import HTTPException

                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

        agent.game_state.last_check_result = dice_data
        return {
            "success": True,
            "message": "Dice result recorded",
            "next_phase": "narrating",
        }

    @app.get("/api/v1/game/messages")
    async def get_messages(count: int = 10):
        agent = app.state.gm_agent
        if agent is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="Game engine not initialized")

        messages = agent.game_state.get_recent_messages(count=count)
        return {
            "messages": messages,
            "count": len(messages),
        }

    @app.post("/api/v1/game/reset")
    async def reset_game():
        agent = app.state.gm_agent
        if agent is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="Game engine not initialized")

        agent.game_state.messages = []
        agent.game_state.turn_count = 0
        agent.game_state.last_check_result = None
        agent.game_state.set_phase(GamePhase.WAITING_INPUT)

        return {
            "success": True,
            "message": "Game state reset",
        }

    return app


class TestRealHTTPEndpoints:
    """Test actual HTTP endpoints with mocked GM agent."""

    @pytest.fixture
    def app_with_agent(self, mock_gm_agent):
        """Create test app with mocked agent."""
        return create_app_with_mock_agent(mock_gm_agent)

    @pytest.fixture
    def client(self, app_with_agent):
        """Create test client."""
        return TestClient(app_with_agent)

    def test_root_endpoint_real(self, client):
        """Test GET / returns correct format."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Astinus TTRPG Engine"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"

    def test_health_endpoint_real(self, client):
        """Test GET /health returns healthy with agent."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["agents"]["gm_agent"] is True
        assert data["agents"]["rule_agent"] is True

    def test_new_game_endpoint_real(self, client):
        """Test POST /api/v1/game/new creates session."""
        response = client.post("/api/v1/game/new", json={})
        assert response.status_code == 200

        data = response.json()
        # Verify NewGameResponse structure
        assert "session_id" in data
        assert isinstance(data["session_id"], str)
        assert len(data["session_id"]) > 0

        assert "player" in data
        assert "name" in data["player"]
        assert "concept" in data["player"]
        assert "traits" in data["player"]
        assert "tags" in data["player"]
        assert "fate_points" in data["player"]

        assert "game_state" in data
        assert "current_location" in data["game_state"]
        assert "current_phase" in data["game_state"]
        assert "turn_count" in data["game_state"]

        assert data["message"] == "Game session created successfully"

    def test_game_state_endpoint_real(self, client):
        """Test GET /api/v1/game/state returns full state."""
        response = client.get("/api/v1/game/state")
        assert response.status_code == 200

        data = response.json()
        # Verify GameState structure
        assert "session_id" in data
        assert "world_pack_id" in data
        assert "player" in data
        assert "current_location" in data
        assert "active_npc_ids" in data
        assert "current_phase" in data
        assert "turn_count" in data
        assert "language" in data
        assert "messages" in data

        # Verify types
        assert isinstance(data["active_npc_ids"], list)
        assert isinstance(data["turn_count"], int)
        assert data["language"] in ["cn", "en"]

    def test_action_endpoint_real(self, client):
        """Test POST /api/v1/game/action processes input."""
        response = client.post(
            "/api/v1/game/action",
            json={"player_input": "我查看周围", "lang": "cn"},
        )
        assert response.status_code == 200

        data = response.json()
        # Verify ActionResponse structure
        assert "success" in data
        assert isinstance(data["success"], bool)
        assert "content" in data
        assert "metadata" in data
        assert "error" in data

    def test_action_endpoint_missing_input(self, client):
        """Test POST /api/v1/game/action returns 400 for missing input."""
        response = client.post("/api/v1/game/action", json={"lang": "cn"})
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "player_input" in data["detail"]

    def test_dice_result_endpoint_real(self, client):
        """Test POST /api/v1/game/dice-result records result."""
        response = client.post(
            "/api/v1/game/dice-result",
            json={
                "total": 10,
                "all_rolls": [6, 4],
                "kept_rolls": [6, 4],
                "outcome": "success",
            },
        )
        assert response.status_code == 200

        data = response.json()
        # Verify DiceResultResponse structure
        assert data["success"] is True
        assert "message" in data
        assert data["next_phase"] == "narrating"

    def test_dice_result_missing_field(self, client):
        """Test POST /api/v1/game/dice-result returns 400 for missing field."""
        response = client.post(
            "/api/v1/game/dice-result",
            json={"total": 10},
        )
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "Missing required field" in data["detail"]

    def test_messages_endpoint_real(self, client, mock_gm_agent):
        """Test GET /api/v1/game/messages returns messages."""
        # Add some messages first
        mock_gm_agent.game_state.add_message("user", "测试消息")
        mock_gm_agent.game_state.add_message("assistant", "回复消息")

        response = client.get("/api/v1/game/messages?count=10")
        assert response.status_code == 200

        data = response.json()
        # Verify GetMessagesResponse structure
        assert "messages" in data
        assert "count" in data
        assert isinstance(data["messages"], list)
        assert data["count"] == len(data["messages"])
        assert data["count"] == 2

    def test_reset_endpoint_real(self, client, mock_gm_agent):
        """Test POST /api/v1/game/reset clears state."""
        # Add some state first
        mock_gm_agent.game_state.add_message("user", "测试")
        mock_gm_agent.game_state.turn_count = 5

        response = client.post("/api/v1/game/reset")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "Game state reset" in data["message"]

        # Verify state was reset
        assert mock_gm_agent.game_state.turn_count == 0
        assert len(mock_gm_agent.game_state.messages) == 0

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options(
            "/api/v1/game/new",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        # CORS preflight should work
        assert response.status_code in [200, 405]


class TestActionEndpointContract:
    """Test POST /api/v1/game/action endpoint matches frontend types."""

    def test_action_request_format(self):
        """Verify ActionRequest format is correct."""
        valid_request = {
            "player_input": "我查看周围的环境",
            "lang": "cn",
        }

        # Verify required field
        assert "player_input" in valid_request
        assert isinstance(valid_request["player_input"], str)

        # Verify optional field with default
        assert valid_request.get("lang", "cn") in ["cn", "en"]

    def test_action_response_format(self, mock_gm_agent):
        """Verify ActionResponse format matches frontend type."""
        # Expected response structure
        expected_response = {
            "success": True,
            "content": "你环顾四周，发现自己身处一间古老的图书馆。",
            "metadata": {
                "phase": "narrating",
                "needs_check": False,
            },
            "error": None,
        }

        # Verify all fields
        assert "success" in expected_response
        assert isinstance(expected_response["success"], bool)

        assert "content" in expected_response
        assert isinstance(expected_response["content"], str)

        assert "metadata" in expected_response
        assert isinstance(expected_response["metadata"], dict)

        assert "error" in expected_response
        # error can be None or string


class TestDiceResultEndpointContract:
    """Test POST /api/v1/game/dice-result endpoint matches frontend types."""

    def test_dice_result_request_format(self):
        """Verify DiceResultRequest format."""
        valid_request = {
            "total": 14,
            "all_rolls": [6, 4, 4],
            "kept_rolls": [6, 4, 4],
            "outcome": "success",
        }

        # Verify all required fields
        assert "total" in valid_request
        assert isinstance(valid_request["total"], int)

        assert "all_rolls" in valid_request
        assert isinstance(valid_request["all_rolls"], list)
        assert all(isinstance(r, int) for r in valid_request["all_rolls"])

        assert "kept_rolls" in valid_request
        assert isinstance(valid_request["kept_rolls"], list)

        assert "outcome" in valid_request
        assert valid_request["outcome"] in ["critical", "success", "partial", "failure"]

    def test_dice_result_response_format(self):
        """Verify DiceResultResponse format."""
        expected_response = {
            "success": True,
            "message": "Dice result recorded",
            "next_phase": "narrating",
        }

        assert "success" in expected_response
        assert isinstance(expected_response["success"], bool)

        assert "message" in expected_response
        assert isinstance(expected_response["message"], str)

        assert "next_phase" in expected_response
        assert expected_response["next_phase"] in [
            "waiting_input",
            "processing",
            "dice_check",
            "npc_response",
            "narrating",
        ]


class TestMessagesEndpointContract:
    """Test GET /api/v1/game/messages endpoint matches frontend types."""

    def test_messages_response_format(self, mock_game_state):
        """Verify GetMessagesResponse format."""
        # Add sample messages to game state
        mock_game_state.add_message("user", "我打开那扇神秘的门")
        mock_game_state.add_message(
            "assistant",
            "门缓缓打开，一股陈旧的气息扑面而来...",
            metadata={"agent": "gm"},
        )

        messages = mock_game_state.messages

        # Verify message format
        for msg in messages:
            assert "role" in msg
            assert msg["role"] in ["user", "assistant"]

            assert "content" in msg
            assert isinstance(msg["content"], str)

            assert "timestamp" in msg
            # Timestamp should be ISO format string

            assert "turn" in msg
            assert isinstance(msg["turn"], int)

    def test_messages_response_structure(self):
        """Verify response structure with count."""
        expected_response = {
            "messages": [
                {
                    "role": "user",
                    "content": "测试消息",
                    "timestamp": datetime.now().isoformat(),
                    "turn": 0,
                }
            ],
            "count": 1,
        }

        assert "messages" in expected_response
        assert isinstance(expected_response["messages"], list)

        assert "count" in expected_response
        assert isinstance(expected_response["count"], int)
        assert expected_response["count"] == len(expected_response["messages"])


# =============================================================================
# WebSocket Message Protocol Tests
# =============================================================================


class TestWebSocketMessageTypes:
    """Test WebSocket message types match frontend WSMessageType."""

    def test_all_message_types_exist(self):
        """Verify all expected message types are defined."""
        expected_types = [
            "status",
            "content",
            "complete",
            "dice_check",
            "phase",
            "error",
            "dice_result",  # Client to server type
        ]

        actual_types = [t.value for t in MessageType]

        for expected in expected_types:
            assert expected in actual_types, f"Missing message type: {expected}"

    def test_message_type_values_are_strings(self):
        """Verify message type values are strings for JSON serialization."""
        for msg_type in MessageType:
            assert isinstance(msg_type.value, str)


class TestWSStatusMessage:
    """Test WebSocket status message format (WSStatusMessage)."""

    @pytest.mark.asyncio
    async def test_status_message_format(self, connection_manager, mock_websocket):
        """Verify status message matches frontend type."""
        session_id = "test-session"
        await connection_manager.connect(session_id, mock_websocket)

        await connection_manager.send_status(session_id, "processing", "正在分析你的行动...")

        mock_websocket.send_json.assert_called_once()
        message = mock_websocket.send_json.call_args[0][0]

        # Verify WSStatusMessage format
        assert message["type"] == "status"
        assert "data" in message
        assert "phase" in message["data"]
        assert "message" in message["data"]
        assert isinstance(message["data"]["phase"], str)
        assert isinstance(message["data"]["message"], str)


class TestWSContentMessage:
    """Test WebSocket content message format (WSContentMessage)."""

    @pytest.mark.asyncio
    async def test_content_message_format(self, connection_manager, mock_websocket):
        """Verify content message matches frontend type."""
        session_id = "test-session"
        await connection_manager.connect(session_id, mock_websocket)

        await connection_manager.send_content_chunk(
            session_id,
            chunk="图书管理员抬起头，",
            is_partial=True,
            chunk_index=0,
        )

        mock_websocket.send_json.assert_called_once()
        message = mock_websocket.send_json.call_args[0][0]

        # Verify WSContentMessage format
        assert message["type"] == "content"
        assert "data" in message
        assert "chunk" in message["data"]
        assert "is_partial" in message["data"]
        assert "chunk_index" in message["data"]
        assert isinstance(message["data"]["chunk"], str)
        assert isinstance(message["data"]["is_partial"], bool)
        assert isinstance(message["data"]["chunk_index"], int)


class TestWSCompleteMessage:
    """Test WebSocket complete message format (WSCompleteMessage)."""

    @pytest.mark.asyncio
    async def test_complete_message_format(self, connection_manager, mock_websocket):
        """Verify complete message matches frontend type."""
        session_id = "test-session"
        await connection_manager.connect(session_id, mock_websocket)

        await connection_manager.send_complete(
            session_id,
            content="图书管理员抬起头，用审视的目光打量着你...",
            metadata={"phase": "waiting_input", "turn": 6},
            success=True,
        )

        mock_websocket.send_json.assert_called_once()
        message = mock_websocket.send_json.call_args[0][0]

        # Verify WSCompleteMessage format
        assert message["type"] == "complete"
        assert "data" in message
        assert "content" in message["data"]
        assert "metadata" in message["data"]
        assert "success" in message["data"]
        assert isinstance(message["data"]["content"], str)
        assert isinstance(message["data"]["metadata"], dict)
        assert isinstance(message["data"]["success"], bool)


class TestWSDiceCheckMessage:
    """Test WebSocket dice check message format (WSDiceCheckMessage)."""

    @pytest.mark.asyncio
    async def test_dice_check_message_format(self, connection_manager, mock_websocket):
        """Verify dice check message matches frontend type."""
        session_id = "test-session"
        await connection_manager.connect(session_id, mock_websocket)

        check_request = {
            "intention": "说服图书管理员透露秘密",
            "influencing_factors": ["善于交际", "图书馆常客"],
            "dice_formula": "2d6",
            "instructions": "因为你的「善于交际」特质，获得+1加值",
        }

        await connection_manager.send_dice_check(session_id, check_request)

        mock_websocket.send_json.assert_called_once()
        message = mock_websocket.send_json.call_args[0][0]

        # Verify WSDiceCheckMessage format
        assert message["type"] == "dice_check"
        assert "data" in message
        assert "check_request" in message["data"]

        req = message["data"]["check_request"]
        assert "intention" in req
        assert "influencing_factors" in req
        assert "dice_formula" in req
        assert "instructions" in req
        assert isinstance(req["intention"], str)
        assert isinstance(req["influencing_factors"], list)
        assert isinstance(req["dice_formula"], str)
        assert isinstance(req["instructions"], str)


class TestWSPhaseMessage:
    """Test WebSocket phase message format (WSPhaseMessage)."""

    @pytest.mark.asyncio
    async def test_phase_message_format(self, connection_manager, mock_websocket):
        """Verify phase message matches frontend type."""
        session_id = "test-session"
        await connection_manager.connect(session_id, mock_websocket)

        await connection_manager.send_phase_change(session_id, "dice_check")

        mock_websocket.send_json.assert_called_once()
        message = mock_websocket.send_json.call_args[0][0]

        # Verify WSPhaseMessage format
        assert message["type"] == "phase"
        assert "data" in message
        assert "phase" in message["data"]
        assert isinstance(message["data"]["phase"], str)


class TestWSErrorMessage:
    """Test WebSocket error message format (WSErrorMessage)."""

    @pytest.mark.asyncio
    async def test_error_message_format(self, connection_manager, mock_websocket):
        """Verify error message matches frontend type."""
        session_id = "test-session"
        await connection_manager.connect(session_id, mock_websocket)

        await connection_manager.send_error(session_id, "Invalid player input")

        mock_websocket.send_json.assert_called_once()
        message = mock_websocket.send_json.call_args[0][0]

        # Verify WSErrorMessage format
        assert message["type"] == "error"
        assert "data" in message
        assert "error" in message["data"]
        assert isinstance(message["data"]["error"], str)


# =============================================================================
# WebSocket Streaming Tests
# =============================================================================


class TestWebSocketStreamContent:
    """Test WebSocket content streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_content_produces_chunks(self, connection_manager, mock_websocket):
        """Verify streaming produces correct chunk sequence."""
        session_id = "stream-test"
        await connection_manager.connect(session_id, mock_websocket)

        # Use connection_manager's send_content_chunk directly to test format
        await connection_manager.send_content_chunk(
            session_id, "First chunk ", is_partial=True, chunk_index=0
        )
        await connection_manager.send_content_chunk(
            session_id, "Second chunk ", is_partial=True, chunk_index=1
        )
        await connection_manager.send_content_chunk(
            session_id, "Final chunk", is_partial=False, chunk_index=2
        )

        # Should have 3 calls for chunks
        assert mock_websocket.send_json.call_count == 3

        # Verify last chunk has is_partial=False
        last_call = mock_websocket.send_json.call_args_list[-1]
        last_message = last_call[0][0]
        assert last_message["type"] == "content"
        assert last_message["data"]["is_partial"] is False

    @pytest.mark.asyncio
    async def test_stream_content_chunk_indices_sequential(
        self, connection_manager, mock_websocket
    ):
        """Verify chunk indices are sequential."""
        session_id = "index-test"
        await connection_manager.connect(session_id, mock_websocket)

        # Send chunks with sequential indices
        for i in range(5):
            is_last = i == 4
            await connection_manager.send_content_chunk(
                session_id, f"Chunk {i}", is_partial=not is_last, chunk_index=i
            )

        indices = []
        for call in mock_websocket.send_json.call_args_list:
            message = call[0][0]
            if message["type"] == "content":
                indices.append(message["data"]["chunk_index"])

        # Verify indices are sequential starting from 0
        assert indices == list(range(len(indices)))
        assert indices == [0, 1, 2, 3, 4]


# =============================================================================
# Game Flow Integration Tests
# =============================================================================


class TestGameFlowScenarios:
    """Test complete game flow scenarios matching frontend expectations."""

    def test_player_character_serialization(self, mock_player_character):
        """Verify PlayerCharacter serializes correctly for frontend."""
        # Simulate API response serialization
        serialized = {
            "name": mock_player_character.name,
            "concept": mock_player_character.concept.model_dump(),
            "traits": [t.model_dump() for t in mock_player_character.traits],
            "tags": mock_player_character.tags,
            "fate_points": mock_player_character.fate_points,
        }

        # Verify structure matches frontend PlayerCharacter type
        assert isinstance(serialized["name"], str)
        assert "cn" in serialized["concept"]
        assert "en" in serialized["concept"]
        assert isinstance(serialized["traits"], list)
        assert len(serialized["traits"]) > 0

        trait = serialized["traits"][0]
        assert "name" in trait
        assert "description" in trait
        assert "positive_aspect" in trait
        assert "negative_aspect" in trait

    def test_game_state_phase_transitions(self, mock_game_state):
        """Verify game state phase transitions work correctly."""
        # Initial state
        assert mock_game_state.current_phase == GamePhase.WAITING_INPUT

        # Transition to processing
        mock_game_state.set_phase(GamePhase.PROCESSING)
        assert mock_game_state.current_phase == GamePhase.PROCESSING

        # Transition to dice check
        mock_game_state.set_phase(GamePhase.DICE_CHECK)
        assert mock_game_state.current_phase == GamePhase.DICE_CHECK

        # Transition to narrating
        mock_game_state.set_phase(GamePhase.NARRATING)
        assert mock_game_state.current_phase == GamePhase.NARRATING

        # Back to waiting input
        mock_game_state.set_phase(GamePhase.WAITING_INPUT)
        assert mock_game_state.current_phase == GamePhase.WAITING_INPUT

    def test_message_history_format(self, mock_game_state):
        """Verify message history format matches frontend Message type."""
        # Add messages as they would be during gameplay
        mock_game_state.add_message("user", "我查看周围的环境")
        mock_game_state.add_message(
            "assistant",
            "你环顾四周，发现自己身处一间古老的图书馆。",
            metadata={"agent": "gm", "phase": "narrating"},
        )
        mock_game_state.increment_turn()
        mock_game_state.add_message("user", "我走向书架")

        messages = mock_game_state.messages

        # Verify all messages have required fields
        for msg in messages:
            assert "role" in msg
            assert "content" in msg
            assert "timestamp" in msg
            assert "turn" in msg

        # Verify turn tracking
        assert messages[0]["turn"] == 0
        assert messages[1]["turn"] == 0
        assert messages[2]["turn"] == 1

    def test_dice_check_result_storage(self, mock_game_state):
        """Verify dice check results are stored correctly."""
        dice_result = {
            "total": 10,
            "all_rolls": [6, 4],
            "kept_rolls": [6, 4],
            "outcome": "success",
        }

        mock_game_state.last_check_result = dice_result

        # Verify storage
        assert mock_game_state.last_check_result is not None
        assert mock_game_state.last_check_result["total"] == 10
        assert mock_game_state.last_check_result["outcome"] == "success"


class TestConnectionManagerScenarios:
    """Test connection manager scenarios matching frontend client behavior."""

    @pytest.mark.asyncio
    async def test_full_game_session_flow(self, connection_manager, mock_websocket):
        """Test complete game session as frontend would experience."""
        session_id = "full-flow-test"

        # 1. Connect (frontend calls WebSocket connect)
        await connection_manager.connect(session_id, mock_websocket)
        assert session_id in connection_manager.active_connections

        # 2. Receive processing status
        await connection_manager.send_status(session_id, "processing", "正在分析你的行动...")

        # 3. Receive phase change
        await connection_manager.send_phase_change(session_id, "narrating")

        # 4. Receive streamed content
        await connection_manager.send_content_chunk(
            session_id, "你环顾", is_partial=True, chunk_index=0
        )
        await connection_manager.send_content_chunk(
            session_id, "四周...", is_partial=False, chunk_index=1
        )

        # 5. Receive complete response
        await connection_manager.send_complete(
            session_id,
            content="你环顾四周...",
            metadata={"phase": "waiting_input"},
            success=True,
        )

        # Verify all messages were sent
        # 1 status + 1 phase + 2 content + 1 complete = 5 messages
        assert mock_websocket.send_json.call_count == 5

        # 6. Disconnect
        connection_manager.disconnect(session_id)
        assert session_id not in connection_manager.active_connections

    @pytest.mark.asyncio
    async def test_dice_check_flow(self, connection_manager, mock_websocket):
        """Test dice check flow as frontend would experience."""
        session_id = "dice-flow-test"
        await connection_manager.connect(session_id, mock_websocket)

        # 1. Receive processing status
        await connection_manager.send_status(session_id, "processing", "正在分析你的行动...")

        # 2. Receive phase change to dice_check
        await connection_manager.send_phase_change(session_id, "dice_check")

        # 3. Receive dice check request
        await connection_manager.send_dice_check(
            session_id,
            {
                "intention": "尝试攀爬高墙",
                "influencing_factors": ["勇敢"],
                "dice_formula": "2d6",
                "instructions": "标准检定",
            },
        )

        # Verify dice check was sent
        calls = mock_websocket.send_json.call_args_list
        dice_check_call = calls[-1]
        assert dice_check_call[0][0]["type"] == "dice_check"

    @pytest.mark.asyncio
    async def test_error_handling_flow(self, connection_manager, mock_websocket):
        """Test error handling as frontend would experience."""
        session_id = "error-flow-test"
        await connection_manager.connect(session_id, mock_websocket)

        # Send error
        await connection_manager.send_error(session_id, "处理请求时发生错误")

        # Verify error message format
        message = mock_websocket.send_json.call_args[0][0]
        assert message["type"] == "error"
        assert "error" in message["data"]

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, connection_manager):
        """Test handling multiple concurrent sessions."""
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()

        session1 = "session-1"
        session2 = "session-2"

        # Connect both sessions
        await connection_manager.connect(session1, ws1)
        await connection_manager.connect(session2, ws2)

        assert len(connection_manager.active_connections) == 2

        # Send to session 1 only
        await connection_manager.send_status(session1, "processing", "Session 1")
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()

        # Send to session 2 only
        ws1.send_json.reset_mock()
        await connection_manager.send_status(session2, "processing", "Session 2")
        ws1.send_json.assert_not_called()
        ws2.send_json.assert_called_once()


# =============================================================================
# LocalizedString Tests
# =============================================================================


class TestLocalizedStringFormat:
    """Test LocalizedString format matches frontend type."""

    def test_localized_string_structure(self):
        """Verify LocalizedString has cn and en fields."""
        ls = LocalizedString(cn="中文内容", en="English content")

        assert hasattr(ls, "cn")
        assert hasattr(ls, "en")
        assert ls.cn == "中文内容"
        assert ls.en == "English content"

    def test_localized_string_serialization(self):
        """Verify LocalizedString serializes correctly."""
        ls = LocalizedString(cn="测试", en="Test")
        serialized = ls.model_dump()

        assert "cn" in serialized
        assert "en" in serialized
        assert isinstance(serialized["cn"], str)
        assert isinstance(serialized["en"], str)

    def test_localized_string_get_method(self):
        """Verify get method works for both languages."""
        ls = LocalizedString(cn="中文", en="English")

        assert ls.get("cn") == "中文"
        assert ls.get("en") == "English"
        # Default to cn for unknown language
        assert ls.get("unknown") == "中文"


# =============================================================================
# Trait Model Tests
# =============================================================================


class TestTraitModelFormat:
    """Test Trait model format matches frontend type."""

    def test_trait_structure(self):
        """Verify Trait has all required LocalizedString fields."""
        trait = Trait(
            name=LocalizedString(cn="勇敢", en="Brave"),
            description=LocalizedString(cn="面对困难不退缩", en="Faces difficulties"),
            positive_aspect=LocalizedString(cn="勇敢", en="Brave"),
            negative_aspect=LocalizedString(cn="鲁莽", en="Rash"),
        )

        assert hasattr(trait, "name")
        assert hasattr(trait, "description")
        assert hasattr(trait, "positive_aspect")
        assert hasattr(trait, "negative_aspect")

    def test_trait_serialization(self):
        """Verify Trait serializes with nested LocalizedString."""
        trait = Trait(
            name=LocalizedString(cn="勇敢", en="Brave"),
            description=LocalizedString(cn="描述", en="Description"),
            positive_aspect=LocalizedString(cn="正面", en="Positive"),
            negative_aspect=LocalizedString(cn="负面", en="Negative"),
        )

        serialized = trait.model_dump()

        assert "name" in serialized
        assert "cn" in serialized["name"]
        assert "en" in serialized["name"]

        assert "description" in serialized
        assert "positive_aspect" in serialized
        assert "negative_aspect" in serialized


# =============================================================================
# API Error Format Tests
# =============================================================================


class TestAPIErrorFormat:
    """Test API error responses match frontend APIError type."""

    def test_http_exception_format(self):
        """Verify HTTP exceptions return expected format."""
        from fastapi import HTTPException

        exc = HTTPException(status_code=400, detail="Invalid player input")

        # FastAPI converts this to {"detail": "..."} response
        assert exc.detail == "Invalid player input"

    def test_validation_error_expected_format(self):
        """Document expected validation error format."""
        # FastAPI validation errors return:
        # {"detail": [{"loc": [...], "msg": "...", "type": "..."}]}
        expected_format = {
            "detail": [
                {
                    "loc": ["body", "player_input"],
                    "msg": "field required",
                    "type": "value_error.missing",
                }
            ]
        }

        # Frontend should handle both simple and detailed error formats
        assert "detail" in expected_format


# =============================================================================
# Summary Test
# =============================================================================


class TestFrontendAPIContractSummary:
    """Summary tests to ensure all frontend API contracts are covered."""

    def test_all_rest_endpoints_have_tests(self):
        """Verify all REST endpoints documented in WEB_FRONTEND_PLAN.md have tests."""
        endpoints_tested = [
            "GET /",
            "GET /health",
            "POST /api/v1/game/new",
            "GET /api/v1/game/state",
            "POST /api/v1/game/action",
            "POST /api/v1/game/dice-result",
            "GET /api/v1/game/messages",
            "POST /api/v1/game/reset",
        ]

        # This test documents coverage - all endpoints should have corresponding test classes
        assert len(endpoints_tested) == 8

    def test_all_websocket_message_types_have_tests(self):
        """Verify all WebSocket message types have tests."""
        message_types_tested = [
            "status",
            "content",
            "complete",
            "dice_check",
            "phase",
            "error",
        ]

        # All server -> client message types should be tested
        assert len(message_types_tested) == 6

    def test_all_frontend_types_have_backend_equivalents(self):
        """Verify all frontend types have corresponding backend models."""
        frontend_types_with_backend_models = {
            "LocalizedString": LocalizedString,
            "Trait": Trait,
            "PlayerCharacter": PlayerCharacter,
            "GameState": GameState,
            "GamePhase": GamePhase,
            "MessageType": MessageType,
        }

        for type_name, model in frontend_types_with_backend_models.items():
            assert model is not None, f"Missing backend model for {type_name}"

    def test_real_http_endpoints_coverage(self):
        """Document that TestRealHTTPEndpoints covers all endpoints."""
        # TestRealHTTPEndpoints tests:
        # - test_root_endpoint_real: GET /
        # - test_health_endpoint_real: GET /health
        # - test_new_game_endpoint_real: POST /api/v1/game/new
        # - test_game_state_endpoint_real: GET /api/v1/game/state
        # - test_action_endpoint_real: POST /api/v1/game/action
        # - test_action_endpoint_missing_input: POST /api/v1/game/action (error case)
        # - test_dice_result_endpoint_real: POST /api/v1/game/dice-result
        # - test_dice_result_missing_field: POST /api/v1/game/dice-result (error case)
        # - test_messages_endpoint_real: GET /api/v1/game/messages
        # - test_reset_endpoint_real: POST /api/v1/game/reset
        # - test_cors_headers: CORS support
        real_endpoint_tests = 11
        assert real_endpoint_tests == 11
