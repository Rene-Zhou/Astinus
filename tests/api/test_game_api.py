"""Tests for game API endpoints."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from src.backend.main import app

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


class TestGameAPI:
    """Test suite for game API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_gm_agent(self):
        """Mock GM Agent for testing."""
        from src.backend.agents.base import AgentResponse

        mock_agent = AsyncMock()
        mock_agent.process = AsyncMock(
            return_value=AgentResponse(
                content="测试响应",
                metadata={"agent": "gm_agent", "test": True},
                success=True,
            )
        )
        return mock_agent

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "Astinus TTRPG Engine" in data["name"]
        assert data["status"] == "running"
        assert "docs" in data

    def test_health_check(self, client):
        """Test health check endpoint."""
        # In test environment, lifespan doesn't run so gm_agent is None
        # This is expected behavior - returns 503
        response = client.get("/health")
        assert response.status_code == 503

        data = response.json()
        assert "status" in data
        assert "agents" in data
        # Agents should not be initialized in test environment
        assert data["status"] == "unhealthy"
        assert data["agents"]["gm_agent"] is False

    @pytest.mark.skip(reason="Requires real LLM initialization")
    def test_process_player_action(self, client):
        """Test processing player action."""
        action_data = {
            "player_input": "我要查看房间",
            "lang": "cn",
        }

        response = client.post("/api/v1/game/action", json=action_data)
        assert response.status_code == 200

        data = response.json()
        assert "success" in data
        assert "content" in data

    @pytest.mark.skip(reason="Requires gm_agent mock - validation happens after agent check")
    def test_process_player_action_missing_input(self, client):
        """Test error when player input is missing."""
        action_data = {
            "lang": "cn",
        }

        response = client.post("/api/v1/game/action", json=action_data)
        assert response.status_code == 400
        assert "player_input is required" in response.json()["detail"]

    @pytest.mark.skip(reason="Requires real LLM initialization")
    def test_get_game_state(self, client):
        """Test getting game state."""
        response = client.get("/api/v1/game/state")
        assert response.status_code == 200

        data = response.json()
        assert "session_id" in data
        assert "player" in data
        assert "current_location" in data

    @pytest.mark.skip(reason="Requires real LLM initialization")
    def test_submit_dice_result(self, client):
        """Test submitting dice result."""
        dice_data = {
            "total": 10,
            "all_rolls": [6, 4],
            "kept_rolls": [6, 4],
            "outcome": "success",
        }

        response = client.post("/api/v1/game/dice-result", json=dice_data)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "Dice result recorded" in data["message"]

    @pytest.mark.skip(reason="Requires gm_agent mock - validation happens after agent check")
    def test_submit_dice_result_missing_fields(self, client):
        """Test error when required dice fields are missing."""
        dice_data = {
            "total": 10,
        }

        response = client.post("/api/v1/game/dice-result", json=dice_data)
        assert response.status_code == 400
        assert "Missing required field" in response.json()["detail"]

    @pytest.mark.skip(reason="Requires real LLM initialization")
    def test_get_recent_messages(self, client):
        """Test getting recent messages."""
        response = client.get("/api/v1/game/messages?count=5")
        assert response.status_code == 200

        data = response.json()
        assert "messages" in data
        assert "count" in data

    @pytest.mark.skip(reason="Requires real LLM initialization")
    def test_reset_game_state(self, client):
        """Test resetting game state."""
        response = client.post("/api/v1/game/reset")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "Game state reset" in data["message"]

    def test_404_endpoint(self, client):
        """Test 404 for non-existent endpoint."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
