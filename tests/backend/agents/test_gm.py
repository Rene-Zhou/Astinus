"""Tests for GMAgent."""

import os
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from src.backend.agents.base import AgentResponse
from src.backend.agents.gm import GMAgent
from src.backend.models.character import PlayerCharacter, Trait
from src.backend.models.game_state import GameState
from src.backend.models.i18n import LocalizedString

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


class TestGMAgent:
    """Test suite for GMAgent class."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def mock_rule_agent(self):
        """Create mock Rule Agent."""
        agent = AsyncMock()
        agent.ainvoke = AsyncMock(
            return_value=AgentResponse(
                content="需要进行检定",
                metadata={"needs_check": True},
                success=True,
            )
        )
        return agent

    @pytest.fixture
    def sample_game_state(self):
        """Create sample game state."""
        character = PlayerCharacter(
            name="张伟",
            concept=LocalizedString(
                cn="失业的建筑师",
                en="Unemployed Architect",
            ),
            traits=[
                Trait(
                    name=LocalizedString(cn="运动健将", en="Athletic"),
                    description=LocalizedString(
                        cn="擅长各种运动",
                        en="Good at sports",
                    ),
                    positive_aspect=LocalizedString(cn="行动敏捷", en="Agile"),
                    negative_aspect=LocalizedString(cn="容易鲁莽", en="Rash"),
                )
            ],
            tags=["右腿受伤"],
        )

        return GameState(
            session_id="test-session",
            world_pack_id="demo-pack",
            player=character,
            current_location="暗室",
            active_npc_ids=["chen_ling"],
        )

    @pytest.fixture
    def gm_agent(self, mock_llm, mock_rule_agent, sample_game_state):
        """Create GM Agent instance."""
        return GMAgent(
            llm=mock_llm,
            sub_agents={"rule": mock_rule_agent},
            game_state=sample_game_state,
        )

    def test_create_gm_agent(self, gm_agent, sample_game_state):
        """Test creating GM Agent."""
        assert gm_agent.agent_name == "gm_agent"
        assert "rule" in gm_agent.sub_agents
        assert gm_agent.game_state == sample_game_state
        assert gm_agent.prompt_loader is not None

    def test_gm_agent_repr(self, gm_agent):
        """Test GM Agent string representation."""
        assert "GMAgent" in repr(gm_agent)
        assert "rule" in repr(gm_agent)

    @pytest.mark.asyncio
    async def test_process_simple_input(self, gm_agent, mock_llm):
        """Test processing simple player input."""
        # Mock LLM response
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "player_intent": "examine",
                "agents_to_call": ["rule"],
                "context_slices": {
                    "rule": {}
                },
                "reasoning": "需要判断是否检定"
            }"""
        )

        input_data = {
            "player_input": "我要查看房间",
            "lang": "cn",
        }

        result = await gm_agent.process(input_data)

        assert result.success is True
        assert result.content != ""
        assert result.metadata["player_intent"] == "examine"
        assert "rule" in result.metadata["agents_called"]

    @pytest.mark.asyncio
    async def test_process_no_input(self, gm_agent):
        """Test error when no player input provided."""
        input_data = {"lang": "cn"}

        result = await gm_agent.process(input_data)

        assert result.success is False
        assert "No player input" in result.error

    @pytest.mark.asyncio
    async def test_slice_context_for_rule(self, gm_agent, sample_game_state):
        """Test context slicing for Rule Agent."""
        context = gm_agent._slice_context_for_rule("逃离房间", "cn")

        assert "action" in context
        assert context["action"] == "逃离房间"
        assert "character" in context
        assert context["character"]["name"] == "张伟"
        assert "tags" in context
        assert "右腿受伤" in context["tags"]
        assert "lang" in context

        # Should NOT have access to full game state
        assert "messages" not in context
        assert "current_location" not in context

    @pytest.mark.asyncio
    async def test_slice_context_for_npc(self, gm_agent, sample_game_state):
        """Test context slicing for NPC Agent."""
        context = gm_agent._slice_context_for_npc("chen_ling", "我想和陳玲说话", "cn")

        assert "npc_id" in context
        assert context["npc_id"] == "chen_ling"
        assert "player_input" in context
        assert "recent_messages" in context
        assert "lang" in context

        # Should NOT have access to other NPCs
        assert "chen_ling" not in str(context) or context["npc_id"] == "chen_ling"

    @pytest.mark.asyncio
    async def test_process_invalid_json_response(self, gm_agent, mock_llm):
        """Test error handling for invalid JSON from LLM."""
        mock_llm.ainvoke.return_value = AIMessage(content="invalid json {")

        input_data = {
            "player_input": "测试",
            "lang": "cn",
        }

        result = await gm_agent.process(input_data)

        assert result.success is False
        assert "Failed to parse" in result.error

    @pytest.mark.asyncio
    async def test_agent_dispatch_with_missing_agent(self, gm_agent, mock_llm):
        """Test dispatch to non-existent agent."""
        # Mock LLM response requesting non-existent agent
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "player_intent": "talk",
                "agents_to_call": ["npc_unknown"],
                "context_slices": {},
                "reasoning": "和未知NPC对话"
            }"""
        )

        input_data = {
            "player_input": "我想和某人说话",
            "lang": "cn",
        }

        result = await gm_agent.process(input_data)

        assert result.success is True
        assert "npc_unknown" in result.metadata["agents_called"]
        # Check that error is recorded in results
        agent_results = result.metadata["agent_results"]
        assert any(
            r["agent"] == "npc_unknown" and not r["success"]
            for r in agent_results
        )

    @pytest.mark.asyncio
    async def test_synthesize_response(self, gm_agent):
        """Test response synthesis."""
        agent_results = [
            {
                "agent": "rule",
                "result": AgentResponse(
                    content="需要进行检定",
                    success=True,
                ),
            }
        ]

        narrative = await gm_agent._synthesize_response(
            player_input="逃离房间",
            player_intent="escape",
            agent_results=agent_results,
            lang="cn",
        )

        assert "逃离房间" in narrative or "尝试" in narrative
        assert "检定" in narrative

    @pytest.mark.asyncio
    async def test_synthesize_with_errors(self, gm_agent):
        """Test synthesis ignores agent errors."""
        agent_results = [
            {
                "agent": "npc_missing",
                "error": "Agent not found",
            }
        ]

        narrative = await gm_agent._synthesize_response(
            player_input="测试",
            player_intent="test",
            agent_results=agent_results,
            lang="cn",
        )

        # Should still produce narrative
        assert narrative != ""

    @pytest.mark.asyncio
    async def test_game_state_update(self, gm_agent, mock_llm, sample_game_state):
        """Test that game state is updated."""
        initial_turn = sample_game_state.turn_count

        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "player_intent": "examine",
                "agents_to_call": [],
                "context_slices": {},
                "reasoning": "简单观察"
            }"""
        )

        input_data = {
            "player_input": "查看四周",
            "lang": "cn",
        }

        result = await gm_agent.process(input_data)

        # Check turn incremented
        assert sample_game_state.turn_count == initial_turn + 1

        # Check messages added
        assert len(sample_game_state.messages) >= 2
        assert sample_game_state.messages[-2]["content"] == "查看四周"
        assert sample_game_state.messages[-1]["content"] != ""

    @pytest.mark.asyncio
    async def test_sync_invoke(self, gm_agent, mock_llm):
        """Test synchronous invocation."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "player_intent": "examine",
                "agents_to_call": [],
                "context_slices": {},
                "reasoning": "简单查看"
            }"""
        )

        result = gm_agent.invoke({
            "player_input": "查看",
            "lang": "cn",
        })

        assert result.success is True
        assert result.content != ""

    @pytest.mark.asyncio
    async def test_parse_intent_and_plan(self, gm_agent, mock_llm):
        """Test intent parsing and planning."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "player_intent": "move",
                "agents_to_call": ["rule"],
                "context_slices": {
                    "rule": {}
                },
                "reasoning": "移动需要规则判定"
            }"""
        )

        plan = await gm_agent._parse_intent_and_plan("走向门口", "cn")

        assert plan["success"] is True
        assert plan["player_intent"] == "move"
        assert "rule" in plan["agents_to_call"]
        assert "rule" in plan["context_slices"]

    @pytest.mark.asyncio
    async def test_parse_intent_invalid_json(self, gm_agent, mock_llm):
        """Test intent parsing with invalid JSON."""
        mock_llm.ainvoke.return_value = AIMessage(content="not json")

        plan = await gm_agent._parse_intent_and_plan("测试", "cn")

        assert plan["success"] is False
        assert "Failed to parse" in plan["error"]
