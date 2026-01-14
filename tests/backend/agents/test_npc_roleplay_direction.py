"""Tests for NPC Agent roleplay direction handling."""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.agents.npc import NPCAgent
from src.backend.models.world_pack import NPCData

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


class TestNpcRoleplayDirection:
    """Test NPC Agent handles roleplay_direction correctly."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM that returns valid NPC response."""
        llm = MagicMock()
        llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"response": "好吧，我告诉你一点...", "emotion": "reluctant", "action": "叹了口气", "relation_change": 1}'
            )
        )
        return llm

    @pytest.fixture
    def npc_agent(self, mock_llm):
        """Create NPC agent with mock LLM."""
        return NPCAgent(llm=mock_llm)

    @pytest.fixture
    def sample_npc_data(self):
        """Sample NPC data for testing."""
        return {
            "id": "old_guard",
            "soul": {
                "name": "老王",
                "description": {"cn": "村子的守夜人", "en": "Village night watchman"},
                "personality": ["沉默", "警惕"],
                "speech_style": {"cn": "话很少", "en": "Few words"},
                "example_dialogue": [],
            },
            "body": {
                "location": "village",
                "tags": [],
                "relations": {"player": -20},
                "memory": {},
                "location_knowledge": {},
            },
        }

    def test_build_system_prompt_includes_roleplay_direction_cn(self, npc_agent, sample_npc_data):
        """Test that Chinese prompt includes roleplay direction when provided."""

        npc = NPCData(**sample_npc_data)
        roleplay_direction = "NPC 的态度应有所松动，但仍保持一定警惕。"

        prompt = npc_agent._build_system_prompt(
            npc=npc,
            player_input="请告诉我更多",
            context={"location": "village"},
            lang="cn",
            narrative_style="detailed",
            roleplay_direction=roleplay_direction,
        )

        assert "## 扮演方向指示（重要）" in prompt
        assert roleplay_direction in prompt

    def test_build_system_prompt_includes_roleplay_direction_en(self, npc_agent, sample_npc_data):
        """Test that English prompt includes roleplay direction when provided."""

        npc = NPCData(**sample_npc_data)
        roleplay_direction = "The NPC's attitude should soften somewhat."

        prompt = npc_agent._build_system_prompt(
            npc=npc,
            player_input="Tell me more",
            context={"location": "village"},
            lang="en",
            narrative_style="detailed",
            roleplay_direction=roleplay_direction,
        )

        assert "## Roleplay Direction (IMPORTANT)" in prompt
        assert roleplay_direction in prompt

    def test_build_system_prompt_no_direction_section_when_none(self, npc_agent, sample_npc_data):
        """Test that prompt doesn't include direction section when None."""

        npc = NPCData(**sample_npc_data)

        prompt = npc_agent._build_system_prompt(
            npc=npc,
            player_input="你好",
            context={"location": "village"},
            lang="cn",
            narrative_style="detailed",
            roleplay_direction=None,
        )

        assert "扮演方向指示" not in prompt

    def test_build_system_prompt_no_direction_section_when_empty(self, npc_agent, sample_npc_data):
        """Test that prompt doesn't include direction section when empty string."""

        npc = NPCData(**sample_npc_data)

        prompt = npc_agent._build_system_prompt(
            npc=npc,
            player_input="你好",
            context={"location": "village"},
            lang="cn",
            narrative_style="detailed",
            roleplay_direction="",
        )

        assert "扮演方向指示" not in prompt

    @pytest.mark.asyncio
    async def test_process_passes_roleplay_direction_to_prompt(
        self, npc_agent, sample_npc_data, mock_llm
    ):
        """Test that process() correctly passes roleplay_direction to prompt building."""
        input_data = {
            "npc_data": sample_npc_data,
            "player_input": "请告诉我更多信息",
            "context": {"location": "village"},
            "lang": "cn",
            "roleplay_direction": "NPC 的态度应有所松动。",
        }

        result = await npc_agent.process(input_data)

        assert result.success
        # Verify LLM was called
        mock_llm.ainvoke.assert_called_once()
        # Check that the system message contains roleplay direction
        call_args = mock_llm.ainvoke.call_args[0][0]
        system_message = call_args[0]
        assert "扮演方向指示" in system_message.content
        assert "态度应有所松动" in system_message.content

    @pytest.mark.asyncio
    async def test_process_works_without_roleplay_direction(
        self, npc_agent, sample_npc_data, mock_llm
    ):
        """Test that process() works correctly without roleplay_direction."""
        input_data = {
            "npc_data": sample_npc_data,
            "player_input": "你好",
            "context": {"location": "village"},
            "lang": "cn",
            # No roleplay_direction
        }

        result = await npc_agent.process(input_data)

        assert result.success
        mock_llm.ainvoke.assert_called_once()
        call_args = mock_llm.ainvoke.call_args[0][0]
        system_message = call_args[0]
        assert "扮演方向指示" not in system_message.content

    @pytest.mark.asyncio
    async def test_process_passes_english_roleplay_direction(
        self, npc_agent, sample_npc_data, mock_llm
    ):
        """Test that process() correctly passes English roleplay_direction."""
        input_data = {
            "npc_data": sample_npc_data,
            "player_input": "Tell me more",
            "context": {"location": "village"},
            "lang": "en",
            "roleplay_direction": "The NPC should respond positively.",
        }

        result = await npc_agent.process(input_data)

        assert result.success
        mock_llm.ainvoke.assert_called_once()
        call_args = mock_llm.ainvoke.call_args[0][0]
        system_message = call_args[0]
        assert "## Roleplay Direction (IMPORTANT)" in system_message.content
        assert "respond positively" in system_message.content
