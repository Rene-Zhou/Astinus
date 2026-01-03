"""
Pytest configuration and shared fixtures.
"""

import pytest


@pytest.fixture
def sample_game_state():
    """Sample game state for testing."""
    return {
        "messages": [],
        "world_state": {
            "current_scene": "test_scene",
            "time": "day",
            "active_npcs": [],
        },
        "player_profile": {
            "name": "Test Player",
            "concept": "Test Concept",
            "traits": [],
            "tags": [],
        },
        "current_phase": "Waiting_Input",
        "next_agent": "gm",
    }
