"""Tests for Director Agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.backend.agents.base import AgentResponse
from src.backend.agents.director import (
    DirectorAgent,
    NarrativeBeat,
    PacingSuggestion,
)


class TestDirectorAgentInit:
    """Test suite for DirectorAgent initialization."""

    def test_create_director_agent(self):
        """Test creating the director agent."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)
        assert agent is not None
        assert agent.agent_name == "director_agent"

    def test_initial_state(self):
        """Test initial agent state."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)
        assert agent.current_beat == NarrativeBeat.SETUP
        assert agent.tension_level == 3
        assert agent._turns_in_beat == 0
        assert agent._recent_beat_history == []
        assert agent._action_dialogue_ratio == 0.5


class TestNarrativeBeat:
    """Test suite for NarrativeBeat enum."""

    def test_all_beats_defined(self):
        """Test that all narrative beats are defined."""
        expected_beats = [
            "hook",
            "setup",
            "rising_action",
            "climax",
            "falling_action",
            "resolution",
            "transition",
            "breather",
        ]
        for beat in expected_beats:
            assert hasattr(NarrativeBeat, beat.upper())

    def test_beat_values(self):
        """Test narrative beat values."""
        assert NarrativeBeat.HOOK.value == "hook"
        assert NarrativeBeat.CLIMAX.value == "climax"
        assert NarrativeBeat.RESOLUTION.value == "resolution"


class TestPacingSuggestion:
    """Test suite for PacingSuggestion enum."""

    def test_all_suggestions_defined(self):
        """Test that all pacing suggestions are defined."""
        expected_suggestions = [
            "speed_up",
            "slow_down",
            "maintain",
            "build_tension",
            "release_tension",
            "introduce_complication",
            "allow_rest",
        ]
        for suggestion in expected_suggestions:
            assert hasattr(PacingSuggestion, suggestion.upper())

    def test_suggestion_values(self):
        """Test pacing suggestion values."""
        assert PacingSuggestion.SPEED_UP.value == "speed_up"
        assert PacingSuggestion.MAINTAIN.value == "maintain"
        assert PacingSuggestion.BUILD_TENSION.value == "build_tension"


class TestDirectorBeatManagement:
    """Test suite for Director Agent beat management."""

    def test_set_beat(self):
        """Test setting narrative beat."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent.set_beat(NarrativeBeat.RISING_ACTION)
        assert agent.current_beat == NarrativeBeat.RISING_ACTION
        assert NarrativeBeat.SETUP in agent._recent_beat_history

    def test_set_same_beat_no_history(self):
        """Test that setting same beat doesn't add to history."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent.set_beat(NarrativeBeat.SETUP)  # Same as initial
        assert len(agent._recent_beat_history) == 0

    def test_beat_history_limit(self):
        """Test that beat history is limited to 10 entries."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        # Set many different beats
        beats = [
            NarrativeBeat.HOOK,
            NarrativeBeat.SETUP,
            NarrativeBeat.RISING_ACTION,
            NarrativeBeat.CLIMAX,
            NarrativeBeat.FALLING_ACTION,
            NarrativeBeat.RESOLUTION,
            NarrativeBeat.TRANSITION,
            NarrativeBeat.BREATHER,
            NarrativeBeat.HOOK,
            NarrativeBeat.SETUP,
            NarrativeBeat.RISING_ACTION,
            NarrativeBeat.CLIMAX,
        ]

        for beat in beats:
            agent.set_beat(beat)

        assert len(agent._recent_beat_history) <= 10

    def test_turns_in_beat_reset_on_change(self):
        """Test that turns in beat resets when beat changes."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._turns_in_beat = 5
        agent.set_beat(NarrativeBeat.RISING_ACTION)
        assert agent._turns_in_beat == 0


class TestDirectorTensionManagement:
    """Test suite for Director Agent tension management."""

    def test_adjust_tension_increase(self):
        """Test increasing tension."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        initial = agent.tension_level
        agent.adjust_tension(2)
        assert agent.tension_level == initial + 2

    def test_adjust_tension_decrease(self):
        """Test decreasing tension."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._tension_level = 5
        agent.adjust_tension(-2)
        assert agent.tension_level == 3

    def test_tension_clamp_max(self):
        """Test tension is clamped at maximum 10."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._tension_level = 8
        agent.adjust_tension(5)
        assert agent.tension_level == 10

    def test_tension_clamp_min(self):
        """Test tension is clamped at minimum 1."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._tension_level = 2
        agent.adjust_tension(-5)
        assert agent.tension_level == 1


class TestDirectorActionDialogueRatio:
    """Test suite for action/dialogue ratio tracking."""

    def test_dialogue_decreases_ratio(self):
        """Test that dialogue input decreases action ratio."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        initial = agent._action_dialogue_ratio
        agent._update_action_dialogue_ratio("dialogue")
        assert agent._action_dialogue_ratio < initial

    def test_action_increases_ratio(self):
        """Test that action input increases action ratio."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._action_dialogue_ratio = 0.3
        agent._update_action_dialogue_ratio("action")
        assert agent._action_dialogue_ratio > 0.3

    def test_combat_increases_ratio(self):
        """Test that combat input increases action ratio."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._action_dialogue_ratio = 0.3
        agent._update_action_dialogue_ratio("combat")
        assert agent._action_dialogue_ratio > 0.3

    def test_explore_maintains_ratio(self):
        """Test that explore input maintains ratio."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        initial = agent._action_dialogue_ratio
        agent._update_action_dialogue_ratio("explore")
        assert agent._action_dialogue_ratio == initial


class TestDirectorStateSummary:
    """Test suite for Director Agent state summary."""

    def test_get_state_summary(self):
        """Test getting state summary."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        summary = agent.get_state_summary()

        assert "current_beat" in summary
        assert "tension_level" in summary
        assert "turns_in_beat" in summary
        assert "action_dialogue_ratio" in summary
        assert "recent_beats" in summary

    def test_state_summary_values(self):
        """Test state summary values are correct."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent.set_beat(NarrativeBeat.RISING_ACTION)
        agent._tension_level = 7
        agent._turns_in_beat = 3

        summary = agent.get_state_summary()

        assert summary["current_beat"] == "rising_action"
        assert summary["tension_level"] == 7
        assert summary["turns_in_beat"] == 3


class TestDirectorSuggestNextBeat:
    """Test suite for Director Agent beat suggestions."""

    def test_suggest_next_beat_from_setup(self):
        """Test suggesting next beat from setup."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._current_beat = NarrativeBeat.SETUP
        suggested = agent.suggest_next_beat()
        assert suggested == NarrativeBeat.RISING_ACTION

    def test_suggest_next_beat_from_rising_action(self):
        """Test suggesting next beat from rising action."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._current_beat = NarrativeBeat.RISING_ACTION
        suggested = agent.suggest_next_beat()
        assert suggested == NarrativeBeat.CLIMAX

    def test_suggest_next_beat_from_climax(self):
        """Test suggesting next beat from climax."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._current_beat = NarrativeBeat.CLIMAX
        suggested = agent.suggest_next_beat()
        assert suggested == NarrativeBeat.FALLING_ACTION

    def test_suggest_breather_after_high_tension_resolution(self):
        """Test that breather is suggested after high tension resolution."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._current_beat = NarrativeBeat.RESOLUTION
        agent._tension_level = 7
        suggested = agent.suggest_next_beat()
        assert suggested == NarrativeBeat.BREATHER


class TestDirectorHeuristicAnalysis:
    """Test suite for Director Agent heuristic analysis."""

    def test_heuristic_long_setup(self):
        """Test heuristic for long setup beat."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._current_beat = NarrativeBeat.SETUP
        result = agent._heuristic_analysis(turn_count=15, turns_in_beat=12)

        assert result["success"] is True
        assert result["pacing"] == PacingSuggestion.BUILD_TENSION.value

    def test_heuristic_long_climax(self):
        """Test heuristic for long climax beat."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._current_beat = NarrativeBeat.CLIMAX
        result = agent._heuristic_analysis(turn_count=20, turns_in_beat=12)

        assert result["success"] is True
        assert result["pacing"] == PacingSuggestion.RELEASE_TENSION.value

    def test_heuristic_high_tension_extended(self):
        """Test heuristic for extended high tension."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._tension_level = 9
        result = agent._heuristic_analysis(turn_count=15, turns_in_beat=7)

        assert result["success"] is True
        assert result["pacing"] == PacingSuggestion.RELEASE_TENSION.value

    def test_heuristic_low_tension_long_game(self):
        """Test heuristic for low tension in long game."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._tension_level = 2
        result = agent._heuristic_analysis(turn_count=15, turns_in_beat=3)

        assert result["success"] is True
        assert result["pacing"] == PacingSuggestion.BUILD_TENSION.value

    def test_heuristic_action_heavy(self):
        """Test heuristic suggests dialogue when action-heavy."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._action_dialogue_ratio = 0.9
        result = agent._heuristic_analysis(turn_count=10, turns_in_beat=3)

        assert "dialogue scene" in result["recommended_elements"]

    def test_heuristic_dialogue_heavy(self):
        """Test heuristic suggests action when dialogue-heavy."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        agent._action_dialogue_ratio = 0.1
        result = agent._heuristic_analysis(turn_count=10, turns_in_beat=3)

        assert "action sequence" in result["recommended_elements"]


class TestDirectorProcess:
    """Test suite for Director Agent process method."""

    @pytest.mark.asyncio
    async def test_process_success(self):
        """Test successful process call."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="""{
                    "suggested_beat": "rising_action",
                    "pacing": "build_tension",
                    "tension_change": 1,
                    "suggestion": "Add a complication",
                    "scene_suggestion": "",
                    "recommended_elements": ["conflict"]
                }"""
            )
        )

        agent = DirectorAgent(mock_llm)
        result = await agent.process(
            {
                "recent_events": [{"description": "Player entered the tavern"}],
                "current_location": "Tavern",
                "turn_count": 5,
                "player_input_type": "dialogue",
                "npcs_present": ["Bartender"],
                "lang": "en",
            }
        )

        assert result.success is True
        assert "current_beat" in result.metadata
        assert "tension_level" in result.metadata
        assert "pacing_suggestion" in result.metadata

    @pytest.mark.asyncio
    async def test_process_updates_turns(self):
        """Test that process updates turns in beat."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="""{
                    "suggested_beat": null,
                    "pacing": "maintain",
                    "tension_change": 0,
                    "suggestion": "Continue",
                    "scene_suggestion": "",
                    "recommended_elements": []
                }"""
            )
        )

        agent = DirectorAgent(mock_llm)
        initial_turns = agent._turns_in_beat

        await agent.process(
            {
                "recent_events": [],
                "current_location": "Forest",
                "turn_count": 1,
            }
        )

        assert agent._turns_in_beat == initial_turns + 1

    @pytest.mark.asyncio
    async def test_process_fallback_to_heuristic(self):
        """Test fallback to heuristic when LLM fails."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Not valid JSON"))

        agent = DirectorAgent(mock_llm)
        result = await agent.process(
            {
                "recent_events": [],
                "current_location": "Castle",
                "turn_count": 10,
            }
        )

        # Should still succeed with heuristic fallback
        assert result.success is True


class TestDirectorRepr:
    """Test suite for Director Agent representation."""

    def test_repr(self):
        """Test string representation."""
        mock_llm = MagicMock()
        agent = DirectorAgent(mock_llm)

        repr_str = repr(agent)
        assert "DirectorAgent" in repr_str
        assert "beat=" in repr_str
        assert "tension=" in repr_str
