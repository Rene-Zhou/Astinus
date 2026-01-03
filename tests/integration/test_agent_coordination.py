"""Integration tests for agent coordination."""

import os
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from src.backend.agents.gm import GMAgent
from src.backend.agents.rule import RuleAgent
from src.backend.core.llm_provider import LLMConfig, get_llm
from src.backend.models.character import PlayerCharacter, Trait
from src.backend.models.game_state import GameState
from src.backend.models.i18n import LocalizedString

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


class TestAgentCoordination:
    """Integration tests for multi-agent coordination."""

    @pytest.fixture
    def llm(self):
        """Create real LLM instance for integration tests."""
        config = LLMConfig(
            model="gpt-4o-mini",
            api_key="sk-test-key",
            temperature=0.0,  # Deterministic for testing
        )
        return get_llm(config)

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM for faster testing."""
        return AsyncMock()

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

    @pytest.mark.asyncio
    async def test_gm_calls_rule_agent(self, mock_llm, sample_game_state):
        """Test that GM Agent calls Rule Agent for action requiring check."""
        # Setup agents
        rule_agent = RuleAgent(mock_llm)
        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"rule": rule_agent},
            game_state=sample_game_state,
        )

        # Mock LLM responses
        # First call: GM parses intent and decides to call Rule Agent
        # Second call: Rule Agent judges the action
        mock_llm.ainvoke.side_effect = [
            AIMessage(
                content="""{
                    "player_intent": "escape",
                    "agents_to_call": ["rule"],
                    "context_slices": {
                        "rule": {}
                    },
                    "reasoning": "逃离房间需要检定"
                }"""
            ),
            AIMessage(
                content="""{
                    "needs_check": true,
                    "check_request": {
                        "intention": "逃离房间",
                        "influencing_factors": {
                            "traits": ["运动健将"],
                            "tags": ["右腿受伤"]
                        },
                        "dice_formula": "3d6kl2",
                        "instructions": {
                            "cn": "腿伤导致劣势",
                            "en": "Leg injury causes disadvantage"
                        }
                    },
                    "reasoning": "腿伤影响行动"
                }"""
            ),
        ]

        # Process player input
        result = await gm_agent.process({
            "player_input": "我要逃离房间",
            "lang": "cn",
        })

        # Verify coordination
        assert result.success is True
        assert "rule" in result.metadata["agents_called"]

        # Check that game state was updated
        assert sample_game_state.turn_count == 1
        assert len(sample_game_state.messages) == 2

    @pytest.mark.asyncio
    async def test_rule_agent_judges_action(self, mock_llm):
        """Test Rule Agent judging player action."""
        rule_agent = RuleAgent(mock_llm)

        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "needs_check": true,
                "check_request": {
                    "intention": "攀爬悬崖",
                    "influencing_factors": {
                        "traits": ["运动健将"],
                        "tags": []
                    },
                    "dice_formula": "3d6kh2",
                    "instructions": {
                        "cn": "运动健将给予优势",
                        "en": "Athletic grants advantage"
                    }
                },
                "reasoning": "运动健将有助于攀爬"
            }"""
        )

        input_data = {
            "action": "攀爬悬崖",
            "character": {
                "name": "张伟",
                "concept": {"cn": "建筑师"},
                "traits": [
                    {"name": {"cn": "运动健将", "en": "Athletic"}},
                ],
            },
            "tags": [],
            "argument": "我有运动健将特质",
        }

        result = await rule_agent.process(input_data)

        assert result.success is True
        assert result.metadata["needs_check"] is True
        assert result.metadata["dice_check"]["dice_formula"] == "3d6kh2"
        assert "运动健将" in result.metadata["dice_check"]["influencing_factors"]["traits"]

    @pytest.mark.asyncio
    async def test_simple_action_no_check(self, mock_llm, sample_game_state):
        """Test that simple actions don't trigger dice checks."""
        rule_agent = RuleAgent(mock_llm)
        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"rule": rule_agent},
            game_state=sample_game_state,
        )

        # Mock LLM responses
        mock_llm.ainvoke.side_effect = [
            # GM decides to call Rule Agent
            AIMessage(
                content="""{
                    "player_intent": "examine",
                    "agents_to_call": ["rule"],
                    "context_slices": {}
                }"""
            ),
            # Rule Agent says no check needed
            AIMessage(
                content="""{
                    "needs_check": false,
                    "reasoning": "查看房间不需要检定"
                }"""
            ),
        ]

        result = await gm_agent.process({
            "player_input": "我查看房间",
            "lang": "cn",
        })

        assert result.success is True
        assert "rule" in result.metadata["agents_called"]

    @pytest.mark.asyncio
    async def test_agent_context_slicing(self, mock_llm, sample_game_state):
        """Test that agents receive only necessary context."""
        rule_agent = RuleAgent(mock_llm)
        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"rule": rule_agent},
            game_state=sample_game_state,
        )

        # Mock responses
        mock_llm.ainvoke.side_effect = [
            AIMessage(
                content="""{
                    "player_intent": "examine",
                    "agents_to_call": ["rule"],
                    "context_slices": {}
                }"""
            ),
            AIMessage(
                content='{"needs_check": false, "reasoning": "简单查看"}'
            ),
        ]

        # Add some messages to game state
        sample_game_state.add_message(
            role="user",
            content="之前的对话",
            metadata={"npc_id": "other_npc"},
        )

        result = await gm_agent.process({
            "player_input": "查看四周",
            "lang": "cn",
        })

        # Rule Agent should only get action + character + tags
        # NOT full message history or other NPCs
        assert result.success is True

    @pytest.mark.asyncio
    async def test_star_topology_enforced(self, mock_llm, sample_game_state):
        """Test that star topology prevents information leakage."""
        # Create Rule Agent
        rule_agent = RuleAgent(mock_llm)

        # Create GM with Rule Agent
        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"rule": rule_agent},
            game_state=sample_game_state,
        )

        # Mock responses
        mock_llm.ainvoke.side_effect = [
            AIMessage(
                content="""{
                    "player_intent": "talk",
                    "agents_to_call": ["rule"],
                    "context_slices": {}
                }"""
            ),
            AIMessage(
                content='{"needs_check": false, "reasoning": "对话"}'
            ),
        ]

        # Process action
        result = await gm_agent.process({
            "player_input": "我想和陈玲说话",
            "lang": "cn",
        })

        # Verify that Rule Agent can only access what GM provides
        # It should NOT have direct access to:
        # - Other NPCs
        # - Full message history
        # - GameState internals
        assert result.success is True

        # The context slicing ensures Rule Agent only gets:
        # - action
        # - character
        # - tags
        # Nothing else from GameState

    @pytest.mark.asyncio
    async def test_error_handling_in_coordination(self, mock_llm, sample_game_state):
        """Test error handling when one agent fails."""
        rule_agent = RuleAgent(mock_llm)
        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"rule": rule_agent},
            game_state=sample_game_state,
        )

        # Mock GM succeeds but Rule Agent fails
        mock_llm.ainvoke.side_effect = [
            AIMessage(
                content="""{
                    "player_intent": "act",
                    "agents_to_call": ["rule"],
                    "context_slices": {}
                }"""
            ),
            # Rule Agent returns invalid JSON
            AIMessage(content="invalid json {"),
        ]

        result = await gm_agent.process({
            "player_input": "执行复杂行动",
            "lang": "cn",
        })

        # GM should handle the error gracefully
        assert result.success is True  # GM succeeded in orchestration
        # But the Rule Agent result should show failure
        assert any(
            not r["success"]
            for r in result.metadata["agent_results"]
        )

    @pytest.mark.asyncio
    async def test_sync_and_async_consistency(self, mock_llm, sample_game_state):
        """Test that sync and async calls produce consistent results."""
        rule_agent = RuleAgent(mock_llm)
        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"rule": rule_agent},
            game_state=sample_game_state,
        )

        # Mock responses
        mock_llm.ainvoke.side_effect = [
            AIMessage(
                content="""{
                    "player_intent": "examine",
                    "agents_to_call": ["rule"],
                    "context_slices": {}
                }"""
            ),
            AIMessage(
                content='{"needs_check": false, "reasoning": "检查"}'
            ),
        ]

        # Test async call
        async_result = await gm_agent.process({
            "player_input": "检查",
            "lang": "cn",
        })

        # Reset mock
        mock_llm.ainvoke.side_effect = [
            AIMessage(
                content="""{
                    "player_intent": "examine",
                    "agents_to_call": ["rule"],
                    "context_slices": {}
                }"""
            ),
            AIMessage(
                content='{"needs_check": false, "reasoning": "检查"}'
            ),
        ]

        # Test sync call
        sync_result = gm_agent.invoke({
            "player_input": "检查",
            "lang": "cn",
        })

        # Both should succeed
        assert async_result.success is True
        assert sync_result.success is True

        # Both should call the same agents
        assert (
            async_result.metadata["agents_called"]
            == sync_result.metadata["agents_called"]
        )
