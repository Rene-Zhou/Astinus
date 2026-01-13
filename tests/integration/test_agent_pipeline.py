"""Integration tests for Agent pipeline collaboration."""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from src.backend.agents.base import AgentResponse
from src.backend.agents.gm import GMAgent
from src.backend.agents.npc import NPCAgent
from src.backend.agents.rule import RuleAgent
from src.backend.models.character import PlayerCharacter, Trait
from src.backend.models.game_state import GamePhase, GameState
from src.backend.models.i18n import LocalizedString
from src.backend.models.world_pack import (
    NPCBody,
    NPCData,
    NPCSoul,
)

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


class TestAgentPipeline:
    """Test suite for multi-agent pipeline integration."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def sample_character(self):
        """Create sample player character."""
        return PlayerCharacter(
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

    @pytest.fixture
    def sample_game_state(self, sample_character):
        """Create sample game state."""
        return GameState(
            session_id="test-session",
            world_pack_id="demo_pack",
            player=sample_character,
            current_location="library_main_hall",
            active_npc_ids=["chen_ling"],
        )

    @pytest.fixture
    def sample_npc_data(self):
        """Create sample NPC data."""
        return NPCData(
            id="chen_ling",
            soul=NPCSoul(
                name="陈玲",
                description=LocalizedString(
                    cn="图书馆的年轻女馆员，戴着圆框眼镜。",
                    en="A young female librarian wearing round glasses.",
                ),
                personality=["内向", "细心", "好奇"],
                speech_style=LocalizedString(
                    cn="说话轻柔，紧张时会结巴。",
                    en="Speaks softly, stutters when nervous.",
                ),
                example_dialogue=[],
            ),
            body=NPCBody(
                location="library_main_hall",
                inventory=["钥匙串"],
                relations={"player": 0},
                tags=["工作中"],
                memory={},
            ),
        )

    @pytest.fixture
    def mock_world_pack_loader(self, sample_npc_data):
        """Create mock world pack loader."""
        mock_loader = MagicMock()
        mock_pack = MagicMock()
        mock_pack.get_npc.return_value = sample_npc_data
        mock_loader.load.return_value = mock_pack
        return mock_loader

    @pytest.mark.asyncio
    async def test_gm_to_rule_pipeline(self, mock_llm, sample_game_state):
        """Test GM dispatching to Rule Agent."""
        # Create Rule Agent with mock LLM
        rule_llm = AsyncMock()
        rule_llm.ainvoke.return_value = AIMessage(
            content='{"needs_check": true, "check_request": '
            '{"intention": "翻找书架", '
            '"influencing_factors": {"traits": [], "tags": ["右腿受伤"]}, '
            '"dice_formula": "3d6kl2", '
            '"instructions": {"cn": "受伤导致劣势", "en": "Injury causes disadvantage"}}, '
            '"reasoning": "翻找书架需要检定，受伤影响"}'
        )
        rule_agent = RuleAgent(rule_llm)

        # Create GM Agent
        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"rule": rule_agent},
            game_state=sample_game_state,
        )

        # Mock GM LLM response - ReAct loop calls rule agent
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "action": "CALL_AGENT",
                "agent_name": "rule",
                "agent_context": {},
                "reasoning": "翻找需要规则判定"
            }"""
        )

        result = await gm_agent.process(
            {
                "player_input": "我要翻找书架",
                "lang": "cn",
            }
        )

        assert result.success is True
        assert "rule" in result.metadata["agents_called"]
        # Game phase should be DICE_CHECK after rule agent
        assert sample_game_state.current_phase == GamePhase.DICE_CHECK
        # Verify needs_check and dice_check are propagated to GM response metadata
        assert result.metadata.get("needs_check") is True
        assert result.metadata.get("dice_check") is not None
        dice_check = result.metadata["dice_check"]
        assert dice_check["intention"] == "翻找书架"
        assert dice_check["dice_formula"] == "3d6kl2"

    @pytest.mark.asyncio
    async def test_gm_to_npc_pipeline(
        self, mock_llm, sample_game_state, sample_npc_data, mock_world_pack_loader
    ):
        """Test GM dispatching to NPC Agent."""
        # Create NPC Agent with mock LLM
        npc_llm = AsyncMock()
        npc_llm.ainvoke.return_value = AIMessage(
            content='{"response": "你...你好。需要找什么书吗？", '
            '"emotion": "shy", "action": "推了推眼镜", '
            '"relation_change": 0}'
        )
        npc_agent = NPCAgent(npc_llm)

        # Create GM Agent with world pack loader
        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"npc_chen_ling": npc_agent},
            game_state=sample_game_state,
            world_pack_loader=mock_world_pack_loader,
        )

        # Mock GM LLM responses:
        # 1st call: ReAct decides to call NPC agent
        # 2nd call: ReAct RESPOND with narrative after NPC result
        mock_llm.ainvoke.side_effect = [
            AIMessage(
                content="""{
                    "action": "CALL_AGENT",
                    "agent_name": "npc_chen_ling",
                    "agent_context": {},
                    "reasoning": "玩家想和陈玲对话"
                }"""
            ),
            AIMessage(
                content="""{
                    "action": "RESPOND",
                    "narrative": "你走向陈玲，礼貌地打了个招呼。她推了推眼镜，略显害羞地回应道：\\"你...你好。需要找什么书吗？\\"",
                    "reasoning": "整合NPC响应完成"
                }"""
            ),
        ]

        result = await gm_agent.process(
            {
                "player_input": "你好，能帮我找本书吗？",
                "lang": "cn",
            }
        )

        assert result.success is True
        assert "npc_chen_ling" in result.metadata["agents_called"]
        # Check synthesized narrative contains NPC response
        assert "你好" in result.content or "书" in result.content

    @pytest.mark.asyncio
    async def test_gm_to_rule_and_npc_pipeline(
        self, mock_llm, sample_game_state, mock_world_pack_loader
    ):
        """Test GM dispatching to both Rule and NPC agents."""
        # Create Rule Agent
        rule_llm = AsyncMock()
        rule_llm.ainvoke.return_value = AIMessage(
            content='{"needs_check": false, "reasoning": "简单对话不需要检定"}'
        )
        rule_agent = RuleAgent(rule_llm)

        # Create NPC Agent
        npc_llm = AsyncMock()
        npc_llm.ainvoke.return_value = AIMessage(
            content='{"response": "古籍区在二楼...", "emotion": "helpful", "action": "指向楼梯"}'
        )
        npc_agent = NPCAgent(npc_llm)

        # Create GM Agent
        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"rule": rule_agent, "npc_chen_ling": npc_agent},
            game_state=sample_game_state,
            world_pack_loader=mock_world_pack_loader,
        )

        # Mock GM LLM responses:
        # 1st call: ReAct decides to call Rule Agent
        # 2nd call: ReAct decides to call NPC Agent
        # 3rd call: ReAct RESPOND with narrative
        mock_llm.ainvoke.side_effect = [
            AIMessage(
                content="""{
                    "action": "CALL_AGENT",
                    "agent_name": "rule",
                    "agent_context": {},
                    "reasoning": "询问NPC先检查规则"
                }"""
            ),
            AIMessage(
                content="""{
                    "action": "CALL_AGENT",
                    "agent_name": "npc_chen_ling",
                    "agent_context": {},
                    "reasoning": "继续调用NPC Agent"
                }"""
            ),
            AIMessage(
                content="""{
                    "action": "RESPOND",
                    "narrative": "你礼貌地询问古籍区的位置。陈玲微笑着指向楼梯，说道：\\"古籍区在二楼...\\"",
                    "reasoning": "整合所有响应完成"
                }"""
            ),
        ]

        result = await gm_agent.process(
            {
                "player_input": "请问古籍区在哪里？",
                "lang": "cn",
            }
        )

        assert result.success is True
        assert "rule" in result.metadata["agents_called"]
        assert "npc_chen_ling" in result.metadata["agents_called"]

    @pytest.mark.asyncio
    async def test_agent_pipeline_error_handling(self, mock_llm, sample_game_state):
        """Test pipeline handles agent errors gracefully."""
        # Create failing Rule Agent
        failing_agent = AsyncMock()
        failing_agent.ainvoke.return_value = AgentResponse(
            content="",
            success=False,
            error="Agent internal error",
        )

        # Create GM Agent
        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"rule": failing_agent},
            game_state=sample_game_state,
        )

        # Mock GM LLM response - ReAct calls rule agent then responds
        mock_llm.ainvoke.side_effect = [
            AIMessage(
                content="""{
                    "action": "CALL_AGENT",
                    "agent_name": "rule",
                    "agent_context": {},
                    "reasoning": "需要规则判定"
                }"""
            ),
            AIMessage(
                content="""{
                    "action": "RESPOND",
                    "narrative": "你尝试做某事。",
                    "reasoning": "规则代理失败后的回退"
                }"""
            ),
        ]

        result = await gm_agent.process(
            {
                "player_input": "尝试做某事",
                "lang": "cn",
            }
        )

        # GM should still succeed even if sub-agent fails
        assert result.success is True
        # GM still calls rule agent even if it fails
        assert "rule" in result.metadata.get("agents_called", [])

    @pytest.mark.asyncio
    async def test_context_isolation_between_npcs(
        self, mock_llm, sample_game_state, mock_world_pack_loader
    ):
        """Test that NPC context slices are properly isolated."""
        # Create two NPC agents
        npc1_llm = AsyncMock()
        npc1_llm.ainvoke.return_value = AIMessage(
            content='{"response": "陈玲的回复", "emotion": "neutral"}'
        )
        npc1_agent = NPCAgent(npc1_llm)

        npc2_llm = AsyncMock()
        npc2_llm.ainvoke.return_value = AIMessage(
            content='{"response": "李明的回复", "emotion": "neutral"}'
        )
        npc2_agent = NPCAgent(npc2_llm)

        # Create GM Agent
        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={
                "npc_chen_ling": npc1_agent,
                "npc_li_ming": npc2_agent,
            },
            game_state=sample_game_state,
            world_pack_loader=mock_world_pack_loader,
        )

        # Verify context slices are isolated
        chen_ling_context = gm_agent._slice_context_for_npc("chen_ling", "你好", "cn")
        li_ming_context = gm_agent._slice_context_for_npc("li_ming", "你好", "cn")

        # Each NPC should only have their own ID
        assert chen_ling_context["npc_id"] == "chen_ling"
        assert li_ming_context["npc_id"] == "li_ming"

        # NPC contexts should not contain info about other NPCs
        assert "li_ming" not in str(chen_ling_context.get("npc_data", {}))

    @pytest.mark.asyncio
    async def test_game_state_message_history(self, mock_llm, sample_character):
        """Test that game state correctly tracks message history."""
        # Create fresh game state to avoid test pollution
        fresh_game_state = GameState(
            session_id="test-session-msg-history",
            world_pack_id="demo_pack",
            player=sample_character,
            current_location="library_main_hall",
            active_npc_ids=["chen_ling"],
        )
        initial_message_count = len(fresh_game_state.messages)

        # Create simple mock agent
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = AgentResponse(
            content="Action result",
            success=True,
        )

        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"rule": mock_agent},
            game_state=fresh_game_state,
        )

        # Mock GM LLM response - ReAct RESPOND directly
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "action": "RESPOND",
                "narrative": "你的动作完成了。",
                "reasoning": "简单动作"
            }"""
        )

        await gm_agent.process(
            {
                "player_input": "第一个动作",
                "lang": "cn",
            }
        )

        await gm_agent.process(
            {
                "player_input": "第二个动作",
                "lang": "cn",
            }
        )

        # Should have added 4 messages (2 player + 2 assistant)
        assert len(fresh_game_state.messages) == initial_message_count + 4

        # Verify message content
        messages = fresh_game_state.messages
        assert "第一个动作" in messages[-4]["content"]
        assert "第二个动作" in messages[-2]["content"]

    @pytest.mark.asyncio
    async def test_turn_count_increment(self, mock_llm, sample_game_state):
        """Test that turn count increments correctly."""
        initial_turn = sample_game_state.turn_count

        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={},
            game_state=sample_game_state,
        )

        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "action": "RESPOND",
                "narrative": "你的动作完成了。",
                "reasoning": "简单动作"
            }"""
        )

        await gm_agent.process({"player_input": "动作1", "lang": "cn"})
        await gm_agent.process({"player_input": "动作2", "lang": "cn"})
        await gm_agent.process({"player_input": "动作3", "lang": "cn"})

        assert sample_game_state.turn_count == initial_turn + 3
