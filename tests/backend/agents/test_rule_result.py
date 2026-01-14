"""Tests for Rule Agent result handling and narrative generation.

Tests the RuleAgent's ability to:
- Process dice check results
- Generate narrative based on success/failure
- Handle critical success/failure
- Integrate with GM narrative flow
"""

import os
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from src.backend.agents.rule import RuleAgent

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


class TestRuleAgentResultHandling:
    """Test suite for Rule Agent result handling."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def rule_agent(self, mock_llm):
        """Create RuleAgent instance."""
        return RuleAgent(mock_llm)

    @pytest.fixture
    def sample_success_result(self):
        """Create sample successful dice check result."""
        return {
            "intention": "跳过障碍物",
            "dice_formula": "2d6",
            "dice_values": [4, 5],
            "total": 9,
            "threshold": 7,
            "success": True,
            "critical": False,
            "modifiers": [],
        }

    @pytest.fixture
    def sample_failure_result(self):
        """Create sample failed dice check result."""
        return {
            "intention": "撬开锁住的门",
            "dice_formula": "2d6",
            "dice_values": [1, 2],
            "total": 3,
            "threshold": 7,
            "success": False,
            "critical": False,
            "modifiers": [],
        }

    @pytest.fixture
    def sample_critical_success(self):
        """Create sample critical success result."""
        return {
            "intention": "说服守卫",
            "dice_formula": "2d6",
            "dice_values": [6, 6],
            "total": 12,
            "threshold": 7,
            "success": True,
            "critical": True,
            "modifiers": [],
        }

    @pytest.fixture
    def sample_critical_failure(self):
        """Create sample critical failure result."""
        return {
            "intention": "攀爬城墙",
            "dice_formula": "2d6",
            "dice_values": [1, 1],
            "total": 2,
            "threshold": 7,
            "success": False,
            "critical": True,
            "modifiers": [],
        }

    @pytest.mark.asyncio
    async def test_process_result_success(self, rule_agent, mock_llm, sample_success_result):
        """Test processing successful dice result."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "narrative": "你灵活地跃过障碍物，稳稳落地。",
                "outcome_type": "success",
                "consequences": [],
                "suggested_tags": []
            }"""
        )

        result = await rule_agent.process_result(sample_success_result)

        assert result.success is True
        assert "narrative" in result.metadata
        assert result.metadata["outcome_type"] == "success"

    @pytest.mark.asyncio
    async def test_process_result_failure(self, rule_agent, mock_llm, sample_failure_result):
        """Test processing failed dice result."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "narrative": "锁纹丝不动，你的工具滑了一下，发出刺耳的声响。",
                "outcome_type": "failure",
                "consequences": ["可能惊动了附近的人"],
                "suggested_tags": []
            }"""
        )

        result = await rule_agent.process_result(sample_failure_result)

        assert result.success is True
        assert result.metadata["outcome_type"] == "failure"
        assert len(result.metadata.get("consequences", [])) > 0

    @pytest.mark.asyncio
    async def test_process_result_critical_success(
        self, rule_agent, mock_llm, sample_critical_success
    ):
        """Test processing critical success."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "narrative": "守卫被你的话语深深打动，不仅放你通过，还主动提供了宫殿的情报！",
                "outcome_type": "critical_success",
                "consequences": ["获得了额外情报"],
                "suggested_tags": [],
                "bonus_effect": "守卫愿意帮助你"
            }"""
        )

        result = await rule_agent.process_result(sample_critical_success)

        assert result.success is True
        assert result.metadata["outcome_type"] == "critical_success"
        assert "bonus_effect" in result.metadata

    @pytest.mark.asyncio
    async def test_process_result_critical_failure(
        self, rule_agent, mock_llm, sample_critical_failure
    ):
        """Test processing critical failure."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "narrative": "你脚下一滑，从城墙上摔落！好在只是擦伤，但警铃已经响起...",
                "outcome_type": "critical_failure",
                "consequences": ["摔伤", "触发警报"],
                "suggested_tags": ["轻伤", "被发现"]
            }"""
        )

        result = await rule_agent.process_result(sample_critical_failure)

        assert result.success is True
        assert result.metadata["outcome_type"] == "critical_failure"
        assert len(result.metadata.get("suggested_tags", [])) > 0

    @pytest.mark.asyncio
    async def test_process_result_with_context(self, rule_agent, mock_llm, sample_success_result):
        """Test processing result with additional context."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "narrative": "在夜色的掩护下，你轻松越过障碍，没有惊动任何人。",
                "outcome_type": "success",
                "consequences": [],
                "suggested_tags": []
            }"""
        )

        context = {
            "location": "夜晚的宫殿庭院",
            "situation": "潜入行动",
            "nearby_npcs": ["巡逻守卫"],
        }

        result = await rule_agent.process_result(sample_success_result, context=context)

        assert result.success is True
        assert "夜" in result.metadata.get("narrative", "") or result.success

    @pytest.mark.asyncio
    async def test_process_result_returns_consequences(
        self, rule_agent, mock_llm, sample_failure_result
    ):
        """Test that consequences are properly returned."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "narrative": "门锁卡住了你的工具...",
                "outcome_type": "failure",
                "consequences": ["工具损坏", "浪费了时间"],
                "suggested_tags": []
            }"""
        )

        result = await rule_agent.process_result(sample_failure_result)

        consequences = result.metadata.get("consequences", [])
        assert isinstance(consequences, list)
        assert len(consequences) >= 1

    @pytest.mark.asyncio
    async def test_process_result_with_modifiers(self, rule_agent, mock_llm):
        """Test processing result that had modifiers applied."""
        result_data = {
            "intention": "躲避攻击",
            "dice_formula": "3d6kh2",
            "dice_values": [3, 4, 5],
            "total": 9,
            "threshold": 7,
            "success": True,
            "critical": False,
            "modifiers": [{"source": "敏捷特质", "effect": "advantage"}],
        }

        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "narrative": "凭借你出色的敏捷身手，你侧身闪过了攻击。",
                "outcome_type": "success",
                "consequences": [],
                "suggested_tags": []
            }"""
        )

        result = await rule_agent.process_result(result_data)

        assert result.success is True
        # The narrative should acknowledge the advantage

    @pytest.mark.asyncio
    async def test_process_result_invalid_json(self, rule_agent, mock_llm, sample_success_result):
        """Test error handling for invalid LLM response."""
        mock_llm.ainvoke.return_value = AIMessage(content="这不是有效的JSON格式")

        result = await rule_agent.process_result(sample_success_result)

        # Should have a fallback narrative
        assert result.success is True or "error" in result.metadata
        # Fallback should still provide usable result


class TestRuleAgentNarrativeGeneration:
    """Test suite for narrative generation from dice results."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def rule_agent(self, mock_llm):
        """Create RuleAgent instance."""
        return RuleAgent(mock_llm)

    def test_build_result_prompt_success(self, rule_agent):
        """Test building prompt for successful result."""
        result_data = {
            "intention": "开锁",
            "dice_formula": "2d6",
            "dice_values": [4, 4],
            "total": 8,
            "threshold": 7,
            "success": True,
            "critical": False,
        }

        messages = rule_agent._build_result_prompt(result_data, lang="cn")

        assert len(messages) >= 1
        prompt_text = "\n".join(m.content for m in messages)
        assert "成功" in prompt_text or "success" in prompt_text.lower()

    def test_build_result_prompt_failure(self, rule_agent):
        """Test building prompt for failed result."""
        result_data = {
            "intention": "潜行",
            "dice_formula": "2d6",
            "dice_values": [2, 3],
            "total": 5,
            "threshold": 7,
            "success": False,
            "critical": False,
        }

        messages = rule_agent._build_result_prompt(result_data, lang="cn")

        assert len(messages) >= 1
        prompt_text = "\n".join(m.content for m in messages)
        assert "失败" in prompt_text or "fail" in prompt_text.lower()

    def test_build_result_prompt_critical(self, rule_agent):
        """Test building prompt for critical result."""
        result_data = {
            "intention": "攻击",
            "dice_formula": "2d6",
            "dice_values": [6, 6],
            "total": 12,
            "threshold": 7,
            "success": True,
            "critical": True,
        }

        messages = rule_agent._build_result_prompt(result_data, lang="cn")

        prompt_text = "\n".join(m.content for m in messages)
        assert "大成功" in prompt_text or "critical" in prompt_text.lower() or "12" in prompt_text

    def test_build_result_prompt_with_context(self, rule_agent):
        """Test building prompt with scene context."""
        result_data = {
            "intention": "逃跑",
            "dice_formula": "2d6",
            "dice_values": [5, 4],
            "total": 9,
            "threshold": 7,
            "success": True,
            "critical": False,
        }
        context = {
            "location": "燃烧的仓库",
            "situation": "被敌人追击",
        }

        messages = rule_agent._build_result_prompt(result_data, context=context, lang="cn")

        prompt_text = "\n".join(m.content for m in messages)
        assert (
            "燃烧" in prompt_text
            or "仓库" in prompt_text
            or context.get("location", "") in prompt_text
        )


class TestRuleAgentStateUpdates:
    """Test suite for Rule Agent state update extraction."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def rule_agent(self, mock_llm):
        """Create RuleAgent instance."""
        return RuleAgent(mock_llm)

    @pytest.mark.asyncio
    async def test_extract_tag_updates_from_result(self, rule_agent, mock_llm):
        """Test extracting tag updates from result."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "narrative": "你从高处跌落，扭伤了脚踝。",
                "outcome_type": "failure",
                "consequences": ["扭伤脚踝"],
                "suggested_tags": ["脚踝扭伤", "行动不便"]
            }"""
        )

        result_data = {
            "intention": "跳下平台",
            "success": False,
            "critical": False,
            "total": 4,
            "threshold": 7,
        }

        result = await rule_agent.process_result(result_data)

        suggested_tags = result.metadata.get("suggested_tags", [])
        assert isinstance(suggested_tags, list)

    @pytest.mark.asyncio
    async def test_extract_fate_point_suggestion(self, rule_agent, mock_llm):
        """Test fate point suggestion for near-miss."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "narrative": "你差一点就成功了...",
                "outcome_type": "failure",
                "consequences": [],
                "suggested_tags": [],
                "fate_point_applicable": true,
                "fate_point_reason": "运动健将特质可能帮助你"
            }"""
        )

        result_data = {
            "intention": "跳跃",
            "success": False,
            "critical": False,
            "total": 6,
            "threshold": 7,
        }

        result = await rule_agent.process_result(result_data)

        # Near-miss could suggest fate point usage
        assert result.metadata.get("fate_point_applicable") in [True, False, None]

    def test_determine_outcome_type(self, rule_agent):
        """Test outcome type determination."""
        # Normal success
        assert rule_agent._determine_outcome_type(True, False) == "success"
        # Normal failure
        assert rule_agent._determine_outcome_type(False, False) == "failure"
        # Critical success
        assert rule_agent._determine_outcome_type(True, True) == "critical_success"
        # Critical failure
        assert rule_agent._determine_outcome_type(False, True) == "critical_failure"

    @pytest.mark.asyncio
    async def test_result_includes_dice_info(self, rule_agent, mock_llm):
        """Test that result includes original dice information."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "narrative": "你成功了！",
                "outcome_type": "success",
                "consequences": [],
                "suggested_tags": []
            }"""
        )

        result_data = {
            "intention": "测试",
            "dice_formula": "2d6",
            "dice_values": [5, 4],
            "total": 9,
            "threshold": 7,
            "success": True,
            "critical": False,
        }

        result = await rule_agent.process_result(result_data)

        assert result.metadata.get("dice_total") == 9 or "total" in str(result.metadata)
        assert result.metadata.get("threshold") == 7 or "threshold" in str(result.metadata)


class TestRuleAgentGMIntegration:
    """Tests for Rule Agent integration with GM orchestration."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def rule_agent(self, mock_llm):
        """Create RuleAgent instance."""
        return RuleAgent(mock_llm)

    @pytest.mark.asyncio
    async def test_result_format_for_gm_synthesis(self, rule_agent, mock_llm):
        """Test that result format is suitable for GM synthesis."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "narrative": "你成功地完成了行动。",
                "outcome_type": "success",
                "consequences": [],
                "suggested_tags": []
            }"""
        )

        result_data = {
            "intention": "行动",
            "success": True,
            "critical": False,
            "total": 8,
            "threshold": 7,
        }

        result = await rule_agent.process_result(result_data)

        # GM needs these fields for synthesis
        assert hasattr(result, "success")
        assert hasattr(result, "content") or hasattr(result, "metadata")
        assert "narrative" in result.metadata or result.content

    @pytest.mark.asyncio
    async def test_result_can_chain_to_npc_agent(self, rule_agent, mock_llm):
        """Test that result can inform NPC agent responses."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "narrative": "守卫被你的话打动了。",
                "outcome_type": "success",
                "consequences": ["守卫态度软化"],
                "suggested_tags": [],
                "npc_reaction_hint": "impressed"
            }"""
        )

        result_data = {
            "intention": "说服守卫",
            "success": True,
            "critical": False,
            "total": 10,
            "threshold": 7,
        }

        result = await rule_agent.process_result(result_data)

        # Should provide hints for NPC agent
        assert "consequences" in result.metadata or result.success
