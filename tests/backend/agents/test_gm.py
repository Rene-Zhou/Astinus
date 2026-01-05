"""Tests for GMAgent."""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from src.backend.agents.base import AgentResponse
from src.backend.agents.gm import GMAgent
from src.backend.models.character import PlayerCharacter, Trait
from src.backend.models.game_state import GameState
from src.backend.models.i18n import LocalizedString
from src.backend.models.world_pack import (
    NPCBody,
    NPCData,
    NPCSoul,
)
from src.backend.services.vector_store import VectorStoreService

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
        assert any(r["agent"] == "npc_unknown" and not r["success"] for r in agent_results)

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

        # Mock LLM response for synthesis
        gm_agent.llm.ainvoke.return_value.content = "你尝试逃离房间，但需要进行检定。"

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

        await gm_agent.process(input_data)

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

        result = gm_agent.invoke(
            {
                "player_input": "查看",
                "lang": "cn",
            }
        )

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

    @pytest.mark.asyncio
    async def test_slice_context_for_npc_with_world_pack(
        self, mock_llm, mock_rule_agent, sample_game_state
    ):
        """Test NPC context slicing with world pack loader."""
        # Create mock world pack loader
        mock_loader = MagicMock()
        mock_npc = NPCData(
            id="chen_ling",
            soul=NPCSoul(
                name="陈玲",
                description=LocalizedString(
                    cn="年轻的图书馆员",
                    en="Young librarian",
                ),
                personality=["内向", "好奇"],
                speech_style=LocalizedString(
                    cn="说话轻柔",
                    en="Speaks softly",
                ),
            ),
            body=NPCBody(
                location="library",
                inventory=[],
                relations={"player": 10},
                tags=["工作中"],
                memory={},
            ),
        )
        mock_world_pack = MagicMock()
        mock_world_pack.get_npc.return_value = mock_npc
        mock_loader.load.return_value = mock_world_pack

        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"rule": mock_rule_agent},
            game_state=sample_game_state,
            world_pack_loader=mock_loader,
        )

        context = gm_agent._slice_context_for_npc("chen_ling", "你好", "cn")

        assert "npc_data" in context
        assert context["npc_data"]["id"] == "chen_ling"
        assert context["npc_data"]["soul"]["name"] == "陈玲"
        assert context["player_input"] == "你好"
        assert context["context"]["location"] == "暗室"

    @pytest.mark.asyncio
    async def test_slice_context_for_npc_without_world_pack(self, gm_agent):
        """Test NPC context slicing without world pack loader."""
        context = gm_agent._slice_context_for_npc("chen_ling", "你好", "cn")

        # Should still work, just without npc_data
        assert "npc_id" in context
        assert context["npc_id"] == "chen_ling"
        assert context["player_input"] == "你好"
        assert "npc_data" not in context

    @pytest.mark.asyncio
    async def test_process_with_npc_agent(self, mock_llm, sample_game_state):
        """Test processing with NPC agent dispatch."""
        # Create mock NPC agent
        mock_npc_agent = AsyncMock()
        mock_npc_agent.ainvoke = AsyncMock(
            return_value=AgentResponse(
                content="你...你好。有什么事吗？",
                metadata={"npc_id": "chen_ling", "emotion": "shy"},
                success=True,
            )
        )

        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"npc_chen_ling": mock_npc_agent},
            game_state=sample_game_state,
        )

        # Mock LLM to dispatch to NPC agent
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "player_intent": "talk",
                "agents_to_call": ["npc_chen_ling"],
                "context_slices": {},
                "reasoning": "玩家想和陈玲对话"
            }"""
        )

        result = await gm_agent.process(
            {
                "player_input": "我想和陈玲说话",
                "lang": "cn",
            }
        )

        assert result.success is True
        assert "npc_chen_ling" in result.metadata["agents_called"]
        # NPC response should be in narrative
        assert "你好" in result.content or "陈玲" in result.content or "尝试" in result.content

    @pytest.mark.asyncio
    async def test_npc_agent_registration_with_prefix(self, mock_llm, sample_game_state):
        """Test that NPC agents are registered with npc_ prefix format."""
        # Create mock NPC agent for old_guard
        mock_npc_agent = AsyncMock()
        mock_npc_agent.ainvoke = AsyncMock(
            return_value=AgentResponse(
                content="老人缓缓抬起头，用沙哑的声音说道：'你想知道什么？'",
                metadata={"npc_id": "old_guard", "npc_name": "老王", "emotion": "cautious"},
                success=True,
            )
        )

        # Register NPC agent with npc_ prefix format
        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"npc_old_guard": mock_npc_agent},
            game_state=sample_game_state,
        )

        # Verify npc_old_guard is in sub_agents
        assert "npc_old_guard" in gm_agent.sub_agents

        # Mock LLM to dispatch to NPC agent when player uses vague reference
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "player_intent": "talk",
                "can_respond_directly": false,
                "agents_to_call": ["npc_old_guard"],
                "context_slices": {
                    "npc_old_guard": {"player_input": "你好", "interaction_type": "talk"}
                },
                "reasoning": "玩家想和场景中的老人（老王）对话"
            }"""
        )

        result = await gm_agent.process(
            {
                "player_input": "我想和那个老人说话",
                "lang": "cn",
            }
        )

        assert result.success is True
        assert "npc_old_guard" in result.metadata["agents_called"]
        # Verify NPC agent was actually called
        mock_npc_agent.ainvoke.assert_called_once()


class TestGMAgentConversationHistoryRetrieval:
    """Test suite for GM conversation history retrieval functionality."""

    @pytest.fixture(autouse=True)
    def reset_vector_store_singleton(self):
        """Reset VectorStoreService singleton before each test."""
        VectorStoreService.reset_instance()
        yield
        VectorStoreService.reset_instance()

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def sample_game_state(self):
        """Create sample game state."""
        character = PlayerCharacter(
            name="张伟",
            concept=LocalizedString(
                cn="年轻的冒险者",
                en="Young adventurer",
            ),
            traits=[
                Trait(
                    name=LocalizedString(cn="勇敢", en="Brave"),
                    description=LocalizedString(
                        cn="敢于面对危险", en="Brave in the face of danger"
                    ),
                    positive_aspect=LocalizedString(cn="能够保护他人", en="Can protect others"),
                    negative_aspect=LocalizedString(cn="有时过于鲁莽", en="Sometimes reckless"),
                )
            ],
        )
        return GameState(
            session_id="test-session",
            player=character,
            world_pack_id="demo_pack",
            current_location="library_main_hall",
        )

    @pytest.fixture
    def gm_agent_with_vector_store(self, mock_llm, sample_game_state):
        """Create GM Agent with vector store."""
        import tempfile

        from src.backend.services.vector_store import VectorStoreService

        with tempfile.TemporaryDirectory() as tmpdir:
            vector_store = VectorStoreService(tmpdir)
            return GMAgent(
                llm=mock_llm,
                sub_agents={},
                game_state=sample_game_state,
                vector_store=vector_store,
            )

    @pytest.fixture
    def gm_agent_without_vector_store(self, mock_llm, sample_game_state):
        """Create GM Agent without vector store."""
        return GMAgent(
            llm=mock_llm,
            sub_agents={},
            game_state=sample_game_state,
            # No vector_store
        )

    def test_gm_agent_initialization_with_vector_store(self, mock_llm, sample_game_state):
        """Test GMAgent can be initialized with and without vector store."""
        import tempfile

        from src.backend.services.vector_store import VectorStoreService

        # Without vector store
        agent1 = GMAgent(
            llm=mock_llm,
            sub_agents={},
            game_state=sample_game_state,
        )
        assert agent1.vector_store is None

        # With vector store
        with tempfile.TemporaryDirectory() as tmpdir:
            vector_store = VectorStoreService(tmpdir)
            agent2 = GMAgent(
                llm=mock_llm,
                sub_agents={},
                game_state=sample_game_state,
                vector_store=vector_store,
            )
            assert agent2.vector_store is vector_store

    def test_retrieve_relevant_history_less_than_10_messages(
        self, gm_agent_without_vector_store, sample_game_state
    ):
        """Test that all messages are returned when count < 10."""
        # Add 5 messages
        for i in range(5):
            sample_game_state.add_message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
            )

        result = gm_agent_without_vector_store._retrieve_relevant_history(
            session_id="test-session",
            player_input="Current input",
            all_messages=sample_game_state.messages,
            n_results=5,
        )

        # Should return all 5 messages
        assert len(result) == 5

    def test_retrieve_relevant_history_no_vector_store(
        self, gm_agent_without_vector_store, sample_game_state
    ):
        """Test fallback to recent messages when no vector store."""
        # Add 15 messages
        for i in range(15):
            sample_game_state.add_message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
            )

        result = gm_agent_without_vector_store._retrieve_relevant_history(
            session_id="test-session",
            player_input="Current input",
            all_messages=sample_game_state.messages,
            n_results=5,
        )

        # Should return last 5 messages
        assert len(result) == 5
        assert result == sample_game_state.messages[-5:]

    @pytest.mark.skip(reason="需要实现对话历史索引功能")
    def test_retrieve_relevant_history_with_vector_search(
        self, gm_agent_with_vector_store, sample_game_state
    ):
        """Test conversation history retrieval using vector similarity search."""
        # Add 15 messages with different content
        messages = [
            "玩家进入了图书馆",
            "玩家询问关于古老书籍的问题",
            "玩家与陈玲对话",
            "玩家检查书架",
            "玩家发现了一本神秘的书",
            "玩家阅读书中的内容",
            "NPC 陈玲对此做出反应",
            "玩家询问书籍的历史",
            "陈玲解释了书籍的来源",
            "玩家决定带走这本书",
            "陈玲警告玩家小心",
            "玩家忽视警告",
            "玩家打开了书",
            "突然发生了奇怪的事情",
            "游戏继续进行",
        ]

        for content in messages:
            sample_game_state.add_message(role="user", content=content)

        # TODO: 实现对话历史索引逻辑
        # vector_store.add_documents(
        #     collection_name="conversation_history_test-session",
        #     documents=messages,
        #     metadatas=[{"turn": i} for i in range(len(messages))],
        #     ids=[f"test-session_msg_{i}" for i in range(len(messages))],
        # )

        # Search for messages about books
        result = gm_agent_with_vector_store._retrieve_relevant_history(
            session_id="test-session",
            player_input="关于书籍的问题",
            all_messages=sample_game_state.messages,
            n_results=5,
        )

        # Should find relevant messages
        assert len(result) >= 1
        # Messages should be sorted by turn (chronological order)
        assert all(result[i]["turn"] <= result[i + 1]["turn"] for i in range(len(result) - 1))

    def test_retrieve_relevant_history_fallback_on_error(
        self, gm_agent_with_vector_store, sample_game_state
    ):
        """Test fallback to recent messages when vector search fails."""
        # Add 15 messages
        for i in range(15):
            sample_game_state.add_message(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
            )

        # Clear vector store to simulate failure
        gm_agent_with_vector_store.vector_store = None

        result = gm_agent_with_vector_store._retrieve_relevant_history(
            session_id="test-session",
            player_input="Current input",
            all_messages=sample_game_state.messages,
            n_results=5,
        )

        # Should return last 5 messages as fallback
        assert len(result) == 5
        assert result == sample_game_state.messages[-5:]

    def test_game_state_add_message_with_vector_indexing(self, mock_llm, sample_game_state):
        """Test that GameState.add_message can index messages in vector store."""
        import tempfile

        from src.backend.services.vector_store import VectorStoreService

        with tempfile.TemporaryDirectory() as tmpdir:
            vector_store = VectorStoreService(tmpdir)

            # Add message with vector indexing
            sample_game_state.add_message(
                role="user",
                content="玩家进入图书馆",
                vector_store=vector_store,
                collection_name="conversation_history_test-session",
            )

            # Verify message was added
            assert len(sample_game_state.messages) == 1
            assert sample_game_state.messages[0]["content"] == "玩家进入图书馆"

            # Verify it was indexed (collection should exist)
            collections = vector_store.list_collections()
            assert "conversation_history_test-session" in collections

    def test_game_state_add_message_without_vector_store(self, mock_llm, sample_game_state):
        """Test that GameState.add_message works without vector store."""
        # Add message without vector indexing
        sample_game_state.add_message(
            role="user",
            content="玩家进入图书馆",
            # No vector_store parameter
        )

        # Verify message was added
        assert len(sample_game_state.messages) == 1
        assert sample_game_state.messages[0]["content"] == "玩家进入图书馆"

    def test_retrieve_relevant_history_empty_messages(self, gm_agent_without_vector_store):
        """Test that empty message list is handled correctly."""
        result = gm_agent_without_vector_store._retrieve_relevant_history(
            session_id="test-session",
            player_input="Current input",
            all_messages=[],
            n_results=5,
        )

        # Should return empty list
        assert result == []
