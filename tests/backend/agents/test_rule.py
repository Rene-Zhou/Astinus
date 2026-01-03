"""Tests for RuleAgent."""

import os
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from src.backend.agents.rule import RuleAgent

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


class TestRuleAgent:
    """Test suite for RuleAgent class."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def rule_agent(self, mock_llm):
        """Create RuleAgent instance."""
        return RuleAgent(mock_llm)

    @pytest.fixture
    def sample_character(self):
        """Create sample character."""
        return {
            "name": "张伟",
            "concept": {
                "cn": "失业的建筑师",
                "en": "Unemployed Architect",
            },
            "traits": [
                {
                    "name": {"cn": "运动健将", "en": "Athletic"},
                    "description": {"cn": "擅长各种运动", "en": "Good at sports"},
                    "positive_aspect": {"cn": "行动敏捷", "en": "Agile"},
                    "negative_aspect": {"cn": "容易鲁莽", "en": "Rash"},
                }
            ],
            "tags": ["右腿受伤"],
        }

    def test_create_rule_agent(self, rule_agent):
        """Test creating RuleAgent."""
        assert rule_agent.agent_name == "rule_agent"
        assert rule_agent.i18n is not None
        assert rule_agent.prompt_loader is not None

    def test_rule_agent_repr(self, rule_agent):
        """Test RuleAgent string representation."""
        assert repr(rule_agent) == "RuleAgent()"

    @pytest.mark.asyncio
    async def test_process_simple_action_no_check(self, rule_agent, mock_llm):
        """Test processing simple action that doesn't need check."""
        # Mock LLM response for simple action
        mock_llm.ainvoke.return_value = AIMessage(
            content='{"needs_check": false, "reasoning": "正常行走不需要检定"}'
        )

        input_data = {
            "action": "正常行走",
            "character": {"name": "张伟"},
            "tags": [],
        }

        result = await rule_agent.process(input_data)

        assert result.success is True
        assert result.metadata["needs_check"] is False
        assert result.content != ""
        assert "正常行走" in result.content

    @pytest.mark.asyncio
    async def test_process_action_needs_check(self, rule_agent, mock_llm):
        """Test processing action that needs dice check."""
        # Mock LLM response for action needing check
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "needs_check": true,
                "check_request": {
                    "intention": "逃离房间",
                    "influencing_factors": {
                        "traits": [],
                        "tags": ["右腿受伤"]
                    },
                    "dice_formula": "3d6kl2",
                    "instructions": {
                        "cn": "腿伤导致劣势",
                        "en": "Leg injury causes disadvantage"
                    }
                },
                "reasoning": "腿伤影响跑步，需要劣势检定"
            }"""
        )

        input_data = {
            "action": "逃离房间",
            "character": {
                "name": "张伟",
                "traits": [
                    {
                        "name": {"cn": "运动健将", "en": "Athletic"},
                    }
                ],
            },
            "tags": ["右腿受伤"],
        }

        result = await rule_agent.process(input_data)

        assert result.success is True
        assert result.metadata["needs_check"] is True
        assert "dice_check" in result.metadata

        # Verify DiceCheckRequest structure
        dice_check_data = result.metadata["dice_check"]
        assert dice_check_data["intention"] == "逃离房间"
        assert "右腿受伤" in dice_check_data["influencing_factors"]["tags"]
        assert dice_check_data["dice_formula"] == "3d6kl2"

    @pytest.mark.asyncio
    async def test_process_with_player_argument(self, rule_agent, mock_llm):
        """Test processing action with player argument for advantage."""
        # Mock LLM response granting advantage
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "needs_check": true,
                "check_request": {
                    "intention": "攀爬墙壁",
                    "influencing_factors": {
                        "traits": ["运动健将"],
                        "tags": []
                    },
                    "dice_formula": "3d6kh2",
                    "instructions": {
                        "cn": "运动健将特质给予优势",
                        "en": "Athletic trait grants advantage"
                    }
                },
                "reasoning": "玩家的优势论证合理，运动健将确实有助于攀爬"
            }"""
        )

        input_data = {
            "action": "攀爬墙壁",
            "character": {
                "name": "张伟",
                "traits": [
                    {
                        "name": {"cn": "运动健将", "en": "Athletic"},
                    }
                ],
            },
            "tags": [],
            "argument": "我有运动健将特质，攀爬应该更容易",
        }

        result = await rule_agent.process(input_data)

        assert result.success is True
        assert result.metadata["needs_check"] is True

        dice_check_data = result.metadata["dice_check"]
        assert dice_check_data["dice_formula"] == "3d6kh2"
        assert "运动健将" in dice_check_data["influencing_factors"]["traits"]

    @pytest.mark.asyncio
    async def test_process_no_action_provided(self, rule_agent):
        """Test error when no action provided."""
        input_data = {
            "character": {"name": "张伟"},
            "tags": [],
        }

        result = await rule_agent.process(input_data)

        assert result.success is False
        assert "No action provided" in result.error

    @pytest.mark.asyncio
    async def test_process_invalid_json_response(self, rule_agent, mock_llm):
        """Test error handling for invalid JSON from LLM."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="这不是有效的JSON {"
        )

        input_data = {
            "action": "测试行动",
            "character": {"name": "张伟"},
            "tags": [],
        }

        result = await rule_agent.process(input_data)

        assert result.success is False
        assert "Failed to parse" in result.error

    @pytest.mark.asyncio
    async def test_process_non_dict_response(self, rule_agent, mock_llm):
        """Test error when LLM returns non-dict JSON."""
        mock_llm.ainvoke.return_value = AIMessage(content='"just a string"')

        input_data = {
            "action": "测试行动",
            "character": {"name": "张伟"},
            "tags": [],
        }

        result = await rule_agent.process(input_data)

        assert result.success is False
        assert "Expected dict" in result.error

    @pytest.mark.asyncio
    async def test_build_prompt(self, rule_agent, sample_character):
        """Test prompt building."""
        messages = rule_agent._build_prompt(
            input_data={},
            character=sample_character,
            tags=["右腿受伤"],
            action="逃离房间",
            argument="我有运动健将特质",
        )

        assert len(messages) == 2
        assert messages[0].content is not None  # System message
        assert messages[1].content is not None  # Human message

        # Check that prompt contains character info
        prompt_text = messages[0].content + "\n" + messages[1].content
        assert "张伟" in prompt_text
        assert "运动健将" in prompt_text
        assert "右腿受伤" in prompt_text
        assert "逃离房间" in prompt_text

    @pytest.mark.asyncio
    async def test_build_prompt_minimal_data(self, rule_agent):
        """Test prompt building with minimal data."""
        messages = rule_agent._build_prompt(
            input_data={},
            character={"name": "Test"},
            tags=[],
            action="简单行动",
            argument="",
        )

        assert len(messages) == 2
        assert "简单行动" in messages[1].content

    @pytest.mark.asyncio
    async def test_process_with_bonus_and_penalty(self, rule_agent, mock_llm):
        """Test that both bonus and penalty tags are handled."""
        # Mock response with neutral (cancels out)
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "needs_check": true,
                "check_request": {
                    "intention": "复杂行动",
                    "influencing_factors": {
                        "traits": ["相关特质"],
                        "tags": ["负面标签", "正面标签"]
                    },
                    "dice_formula": "2d6",
                    "instructions": {
                        "cn": "正负标签相互抵消",
                        "en": "Positive and negative tags cancel out"
                    }
                },
                "reasoning": "正负影响相互抵消"
            }"""
        )

        input_data = {
            "action": "复杂行动",
            "character": {
                "name": "张伟",
                "traits": [{"name": {"cn": "相关特质", "en": "Relevant"}}],
            },
            "tags": ["负面标签", "正面标签"],
        }

        result = await rule_agent.process(input_data)

        assert result.success is True
        assert result.metadata["needs_check"] is True
        assert result.metadata["dice_check"]["dice_formula"] == "2d6"

    @pytest.mark.asyncio
    async def test_sync_invoke(self, rule_agent, mock_llm):
        """Test synchronous invocation."""
        mock_llm.ainvoke.return_value = AIMessage(
            content='{"needs_check": false, "reasoning": "简单行动"}'
        )

        result = rule_agent.invoke({
            "action": "简单行动",
            "character": {"name": "张伟"},
            "tags": [],
        })

        assert result.success is True
        assert result.metadata["needs_check"] is False
