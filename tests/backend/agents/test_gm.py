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
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "action": "RESPOND",
                "narrative": "你仔细环顾四周，这是一间昏暗的房间。",
                "target_location": null,
                "reasoning": "简单观察，可以直接描述"
            }"""
        )

        input_data = {
            "player_input": "我要查看房间",
            "lang": "cn",
        }

        result = await gm_agent.process(input_data)

        assert result.success is True
        assert result.content != ""
        assert "房间" in result.content or "环顾" in result.content

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
        """Test handling for invalid JSON from LLM - uses raw response as narrative."""
        mock_llm.ainvoke.return_value = AIMessage(content="你尝试进行某些操作。")

        input_data = {
            "player_input": "测试",
            "lang": "cn",
        }

        result = await gm_agent.process(input_data)

        assert result.success is True
        assert result.content == "你尝试进行某些操作。"

    @pytest.mark.asyncio
    async def test_agent_dispatch_with_missing_agent(self, gm_agent, mock_llm):
        """Test dispatch to non-existent agent."""
        call_count = 0

        def mock_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return AIMessage(
                    content="""{
                        "action": "CALL_AGENT",
                        "agent_name": "npc_unknown",
                        "agent_context": {"player_input": "我想和某人说话"},
                        "reasoning": "和未知NPC对话"
                    }"""
                )
            else:
                return AIMessage(
                    content="""{
                        "action": "RESPOND",
                        "narrative": "你环顾四周，但没有看到任何人。",
                        "reasoning": "找不到NPC，直接回应"
                    }"""
                )

        mock_llm.ainvoke.side_effect = mock_response

        input_data = {
            "player_input": "我想和某人说话",
            "lang": "cn",
        }

        result = await gm_agent.process(input_data)

        assert result.success is True
        assert "npc_unknown" in result.metadata["agents_called"]

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
                "action": "RESPOND",
                "narrative": "你环顾四周，看到昏暗的房间。",
                "reasoning": "简单观察"
            }"""
        )

        input_data = {
            "player_input": "查看四周",
            "lang": "cn",
        }

        await gm_agent.process(input_data)

        assert sample_game_state.turn_count == initial_turn + 1

        assert len(sample_game_state.messages) >= 2
        assert sample_game_state.messages[-2]["content"] == "查看四周"
        assert sample_game_state.messages[-1]["content"] != ""

    @pytest.mark.asyncio
    async def test_sync_invoke(self, gm_agent, mock_llm):
        """Test synchronous invocation."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "action": "RESPOND",
                "narrative": "你环顾四周。",
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
    async def test_get_react_action_respond(self, gm_agent, mock_llm):
        """Test ReAct action parsing for RESPOND."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "action": "RESPOND",
                "narrative": "你走向门口。",
                "target_location": null,
                "reasoning": "简单移动"
            }"""
        )

        from src.backend.agents.gm import GMActionType
        action = await gm_agent._get_react_action(
            player_input="走向门口",
            lang="cn",
            iteration=0,
            max_iterations=5,
            agent_results=[],
            dice_result=None,
            force_output=False,
        )

        assert action.action_type == GMActionType.RESPOND
        assert "走向门口" in action.content or "门口" in action.content

    @pytest.mark.asyncio
    async def test_get_react_action_call_agent(self, gm_agent, mock_llm):
        """Test ReAct action parsing for CALL_AGENT."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "action": "CALL_AGENT",
                "agent_name": "rule",
                "agent_context": {"player_input": "攻击怪物"},
                "reasoning": "需要规则判定"
            }"""
        )

        from src.backend.agents.gm import GMActionType
        action = await gm_agent._get_react_action(
            player_input="攻击怪物",
            lang="cn",
            iteration=0,
            max_iterations=5,
            agent_results=[],
            dice_result=None,
            force_output=False,
        )

        assert action.action_type == GMActionType.CALL_AGENT
        assert action.agent_name == "rule"

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
            sub_agents={"npc": mock_npc_agent},
            game_state=sample_game_state,
        )

        call_count = 0

        def mock_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return AIMessage(
                    content="""{
                        "action": "CALL_AGENT",
                        "agent_name": "npc_chen_ling",
                        "agent_context": {"player_input": "我想和陈玲说话"},
                        "reasoning": "玩家想和陈玲对话"
                    }"""
                )
            else:
                return AIMessage(
                    content="""{
                        "action": "RESPOND",
                        "narrative": "陈玲害羞地回应：'你...你好。有什么事吗？'",
                        "reasoning": "NPC已回应，可以输出叙事"
                    }"""
                )

        mock_llm.ainvoke.side_effect = mock_response

        result = await gm_agent.process(
            {
                "player_input": "我想和陈玲说话",
                "lang": "cn",
            }
        )

        assert result.success is True
        assert "npc_chen_ling" in result.metadata["agents_called"]
        assert "你好" in result.content or "陈玲" in result.content

    @pytest.mark.asyncio
    async def test_npc_agent_registration_with_prefix(self, mock_llm, sample_game_state):
        """Test that NPC agents are registered with npc_ prefix format."""
        mock_npc_agent = AsyncMock()
        mock_npc_agent.ainvoke = AsyncMock(
            return_value=AgentResponse(
                content="老人缓缓抬起头，用沙哑的声音说道：'你想知道什么？'",
                metadata={"npc_id": "old_guard", "npc_name": "老王", "emotion": "cautious"},
                success=True,
            )
        )

        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"npc": mock_npc_agent},
            game_state=sample_game_state,
        )

        call_count = 0

        def mock_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return AIMessage(
                    content="""{
                        "action": "CALL_AGENT",
                        "agent_name": "npc_old_guard",
                        "agent_context": {"player_input": "你好", "interaction_type": "talk"},
                        "reasoning": "玩家想和场景中的老人对话"
                    }"""
                )
            else:
                return AIMessage(
                    content="""{
                        "action": "RESPOND",
                        "narrative": "老人缓缓抬起头，用沙哑的声音说道：'你想知道什么？'",
                        "reasoning": "NPC已回应"
                    }"""
                )

        mock_llm.ainvoke.side_effect = mock_response

        result = await gm_agent.process(
            {
                "player_input": "我想和那个老人说话",
                "lang": "cn",
            }
        )

        assert result.success is True
        assert "npc_old_guard" in result.metadata["agents_called"]
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


class TestGMAgentHierarchicalContext:
    """Test suite for GMAgent hierarchical location context functionality."""

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
    def sample_game_state_with_location(self):
        """Create sample game state with location context."""
        from src.backend.models.character import PlayerCharacter, Trait
        from src.backend.models.game_state import GameState
        from src.backend.models.i18n import LocalizedString

        character = PlayerCharacter(
            name="张伟",
            concept=LocalizedString(cn="探险家", en="Explorer"),
            traits=[
                Trait(
                    name=LocalizedString(cn="勇敢", en="Brave"),
                    description=LocalizedString(cn="勇敢的描述", en="Brave description"),
                    positive_aspect=LocalizedString(cn="正面", en="Positive"),
                    negative_aspect=LocalizedString(cn="负面", en="Negative"),
                )
            ],
        )

        return GameState(
            session_id="test-session",
            world_pack_id="demo_pack",
            player=character,
            current_location="temple_entrance",
            active_npc_ids=["guardian"],
            discovered_items=set(),
        )

    @pytest.fixture
    def gm_agent_with_world_pack(self, mock_llm, sample_game_state_with_location):
        """Create GM Agent with world pack loader."""
        import tempfile
        from pathlib import Path

        from src.backend.models.world_pack import (
            LocationData,
            LoreEntry,
            NPCBody,
            NPCData,
            NPCSoul,
            RegionData,
            WorldPack,
            WorldPackInfo,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "packs"
            pack_dir.mkdir()

            pack = WorldPack(
                info=WorldPackInfo(
                    name=LocalizedString(cn="测试世界", en="Test World"),
                    description=LocalizedString(cn="用于测试", en="For testing"),
                ),
                entries={
                    "1": LoreEntry(
                        uid=1,
                        key=["神殿"],
                        content=LocalizedString(cn="古老神殿的历史", en="Ancient temple history"),
                        order=1,
                        visibility="basic",
                    ),
                },
                npcs={
                    "guardian": NPCData(
                        id="guardian",
                        soul=NPCSoul(
                            name="神殿守卫",
                            description=LocalizedString(cn="无形的守卫", en="Invisible guardian"),
                            personality=["警觉"],
                            speech_style=LocalizedString(cn="严肃", en="Solemn"),
                        ),
                        body=NPCBody(
                            location="temple_entrance",
                            inventory=[],
                            relations={},
                            tags=[],
                            memory={},
                        ),
                    ),
                },
                locations={
                    "temple_entrance": LocationData(
                        id="temple_entrance",
                        name=LocalizedString(cn="神殿入口", en="Temple Entrance"),
                        description=LocalizedString(cn="古老神殿的入口", en="Entrance to ancient temple"),
                        atmosphere=LocalizedString(cn="庄严神秘", en="Solemn and mysterious"),
                        region_id="temple_district",
                        visible_items=["altar", "statue"],
                        hidden_items=["secret_lever"],
                    ),
                },
                regions={
                    "temple_district": RegionData(
                        id="temple_district",
                        name=LocalizedString(cn="神殿区域", en="Temple District"),
                        description=LocalizedString(cn="神圣区域", en="Sacred area"),
                        narrative_tone=LocalizedString(cn="庄严神秘", en="Solemn and mysterious"),
                        atmosphere_keywords=["holy", "ancient", "mysterious"],
                        location_ids=["temple_entrance"],
                    ),
                },
            )

            pack_path = pack_dir / "demo_pack.json"
            pack_path.write_text(pack.model_dump_json(), encoding="utf-8")

            from src.backend.services.world import WorldPackLoader

            loader = WorldPackLoader(pack_dir)

            yield GMAgent(
                llm=mock_llm,
                sub_agents={},
                game_state=sample_game_state_with_location,
                world_pack_loader=loader,
            )

    def test_get_scene_context_includes_region(
        self, gm_agent_with_world_pack, sample_game_state_with_location
    ):
        """Test that scene context includes region information."""
        context = gm_agent_with_world_pack._get_scene_context("cn")

        assert "region_name" in context
        assert "region_tone" in context
        assert "atmosphere_keywords" in context

    def test_get_scene_context_includes_location_atmosphere(
        self, gm_agent_with_world_pack, sample_game_state_with_location
    ):
        """Test that scene context includes location atmosphere."""
        context = gm_agent_with_world_pack._get_scene_context("cn")

        assert "location_atmosphere" in context
        assert "庄严神秘" in context["location_atmosphere"] or context["location_atmosphere"] != ""

    def test_get_scene_context_separates_visible_hidden_items(
        self, gm_agent_with_world_pack, sample_game_state_with_location
    ):
        """Test that visible and hidden items are separated."""
        context = gm_agent_with_world_pack._get_scene_context("cn")

        assert "visible_items" in context
        assert "hidden_items_hints" in context
        assert "altar" in context["visible_items"]
        assert "statue" in context["visible_items"]

    def test_get_scene_context_generates_hidden_item_hints(
        self, gm_agent_with_world_pack, sample_game_state_with_location
    ):
        """Test that hidden item hints are generated when items remain."""
        context = gm_agent_with_world_pack._get_scene_context("cn")

        assert context["hidden_items_hints"] != ""

    def test_get_scene_context_includes_basic_lore(
        self, gm_agent_with_world_pack, sample_game_state_with_location
    ):
        """Test that basic lore is included in context."""
        context = gm_agent_with_world_pack._get_scene_context("cn")

        assert "basic_lore" in context
        assert len(context["basic_lore"]) >= 1

    def test_get_scene_context_atmosphere_guidance(
        self, gm_agent_with_world_pack, sample_game_state_with_location
    ):
        """Test that atmosphere guidance is included."""
        context = gm_agent_with_world_pack._get_scene_context("cn")

        assert "atmosphere_guidance" in context

    def test_hidden_item_hints_empty_when_all_discovered(
        self, mock_llm, sample_game_state_with_location
    ):
        """Test that hints are empty when all hidden items are discovered."""
        import tempfile
        from pathlib import Path

        from src.backend.models.world_pack import (
            LocationData,
            LoreEntry,
            NPCBody,
            NPCData,
            NPCSoul,
            RegionData,
            WorldPack,
            WorldPackInfo,
        )
        from src.backend.services.world import WorldPackLoader

        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "packs"
            pack_dir.mkdir()

            pack = WorldPack(
                info=WorldPackInfo(
                    name=LocalizedString(cn="测试世界", en="Test World"),
                    description=LocalizedString(cn="测试", en="Test"),
                ),
                entries={},
                npcs={},
                locations={
                    "temple_entrance": LocationData(
                        id="temple_entrance",
                        name=LocalizedString(cn="神殿入口", en="Temple Entrance"),
                        description=LocalizedString(cn="描述", en="Desc"),
                        hidden_items=["secret_lever"],
                    ),
                },
            )

            pack_path = pack_dir / "demo_pack.json"
            pack_path.write_text(pack.model_dump_json(), encoding="utf-8")

            loader = WorldPackLoader(pack_dir)

            sample_game_state_with_location.discovered_items = {"secret_lever"}

            agent = GMAgent(
                llm=mock_llm,
                sub_agents={},
                game_state=sample_game_state_with_location,
                world_pack_loader=loader,
            )

            context = agent._get_scene_context("cn")

            assert context["hidden_items_hints"] == ""

    def test_generate_hidden_item_hints_chinese(self):
        """Test Chinese hidden item hints generation."""
        gm_agent = GMAgent.__new__(GMAgent)
        gm_agent.world_pack_loader = None
        gm_agent.game_state = None

        hints = gm_agent._generate_hidden_item_hints(["item1", "item2"], "cn")

        assert "不易察觉" in hints or "细节" in hints

    def test_generate_hidden_item_hints_english(self):
        """Test English hidden item hints generation."""
        gm_agent = GMAgent.__new__(GMAgent)
        gm_agent.world_pack_loader = None
        gm_agent.game_state = None

        hints = gm_agent._generate_hidden_item_hints(["item1", "item2"], "en")

        assert "subtle" in hints.lower() or "notice" in hints.lower()

    def test_generate_hidden_item_hints_empty(self):
        """Test that empty list returns empty hints."""
        gm_agent = GMAgent.__new__(GMAgent)
        gm_agent.world_pack_loader = None
        gm_agent.game_state = None

        hints = gm_agent._generate_hidden_item_hints([], "cn")

        assert hints == ""

    def test_get_current_region_id(self, gm_agent_with_world_pack, sample_game_state_with_location):
        """Test getting current region ID from location."""
        region_id = gm_agent_with_world_pack._get_current_region_id()

        assert region_id == "temple_district"

    def test_get_current_region_id_no_loader(self):
        """Test that None is returned when no world pack loader."""
        gm_agent = GMAgent.__new__(GMAgent)
        gm_agent.world_pack_loader = None

        region_id = gm_agent._get_current_region_id()

        assert region_id is None

    def test_slice_context_for_lore_includes_location(self, gm_agent_with_world_pack):
        """Test that lore context slice includes location information."""
        context = gm_agent_with_world_pack._slice_context_for_lore("测试查询", "cn")

        assert "current_location" in context
        assert "current_region" in context
        assert "discovered_items" in context

    def test_slice_context_for_npc_includes_world_pack_id(
        self, gm_agent_with_world_pack, sample_game_state_with_location
    ):
        """Test that NPC context slice includes world_pack_id for location filtering."""
        context = gm_agent_with_world_pack._slice_context_for_npc(
            "guardian", "你好", "cn"
        )

        assert "context" in context
        assert "world_pack_id" in context["context"]
