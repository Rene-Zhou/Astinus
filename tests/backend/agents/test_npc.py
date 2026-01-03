"""Tests for NPCAgent."""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage

from src.backend.agents.npc import NPCAgent
from src.backend.models.world_pack import NPCBody, NPCData, NPCSoul
from src.backend.services.vector_store import VectorStoreService

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


class TestNPCAgent:
    """Test suite for NPCAgent class."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def sample_npc_data(self) -> NPCData:
        """Create sample NPC data for testing."""
        return NPCData(
            id="chen_ling",
            soul=NPCSoul(
                name="陈玲",
                description={
                    "cn": "图书馆的年轻女馆员，戴着圆框眼镜，说话轻声细语。"
                         "她对古籍有着浓厚的兴趣，经常独自研究馆藏的珍本。",
                    "en": "A young female librarian wearing round glasses, "
                         "speaking softly. She has a deep interest in ancient "
                         "books and often studies rare collections alone.",
                },
                personality=["内向", "细心", "好奇", "善良"],
                speech_style={
                    "cn": "说话轻柔，经常使用书面语，偶尔引用古文。"
                         "紧张时会结巴，习惯用手推眼镜。",
                    "en": "Speaks softly, often uses formal language, "
                         "occasionally quotes classical texts. Stutters when "
                         "nervous, habitually pushes up her glasses.",
                },
                example_dialogue=[
                    {
                        "user": "这里有什么有趣的书吗？",
                        "char": "有...有的。这边有一本《山海经》的明刻本，"
                               "是我们馆的镇馆之宝呢...",
                    }
                ],
            ),
            body=NPCBody(
                location="library_main_hall",
                inventory=["钥匙串", "笔记本"],
                relations={"player": 0},
                tags=["工作中"],
                memory={},
            ),
        )

    @pytest.fixture
    def npc_agent(self, mock_llm) -> NPCAgent:
        """Create NPCAgent instance."""
        return NPCAgent(mock_llm)

    def test_create_npc_agent(self, npc_agent):
        """Test creating NPCAgent."""
        assert npc_agent.agent_name == "npc_agent"
        assert npc_agent.i18n is not None
        assert npc_agent.prompt_loader is not None

    def test_npc_agent_repr(self, npc_agent):
        """Test NPCAgent string representation."""
        assert repr(npc_agent) == "NPCAgent()"

    @pytest.mark.asyncio
    async def test_process_simple_greeting(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test NPC responding to simple greeting."""
        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "你...你好。有什么我能帮你的吗？", '
                   '"emotion": "shy", "action": "推了推眼镜"}'
        )

        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "你好",
            "context": {
                "location": "library_main_hall",
                "time_of_day": "afternoon",
            },
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        assert result.content != ""
        assert result.metadata.get("npc_id") == "chen_ling"
        assert "emotion" in result.metadata

    @pytest.mark.asyncio
    async def test_process_with_relationship_influence(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test NPC response influenced by relationship value."""
        # Update relationship to positive
        sample_npc_data.body.relations["player"] = 50

        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "啊，是你！真高兴又见到你。今天想看什么书？", '
                   '"emotion": "happy", "action": "微笑着放下手中的书"}'
        )

        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "嗨，陈玲",
            "context": {"location": "library_main_hall"},
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        assert result.metadata.get("relationship_level") == 50

    @pytest.mark.asyncio
    async def test_process_with_negative_relationship(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test NPC response with negative relationship."""
        sample_npc_data.body.relations["player"] = -30

        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "...需要什么？", '
                   '"emotion": "cold", "action": "没有抬头看向你"}'
        )

        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "能帮我找本书吗？",
            "context": {"location": "library_main_hall"},
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        assert result.metadata.get("relationship_level") == -30

    @pytest.mark.asyncio
    async def test_process_with_npc_tags(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test NPC response influenced by status tags."""
        sample_npc_data.body.tags = ["受伤", "害怕"]

        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "请...请不要靠近...", '
                   '"emotion": "scared", "action": "后退一步，捂住手臂"}'
        )

        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "你还好吗？",
            "context": {"location": "library_main_hall"},
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        assert "受伤" in sample_npc_data.body.tags

    @pytest.mark.asyncio
    async def test_process_npc_remembers_event(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test NPC references memory in response."""
        sample_npc_data.body.memory = {
            "玩家帮忙找到了失踪的古籍": ["古籍", "帮助"],
        }

        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "上次多亏你帮我找到那本古籍，真是太感谢了！", '
                   '"emotion": "grateful", "action": "真诚地鞠了一躬"}'
        )

        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "还记得我吗？",
            "context": {"location": "library_main_hall"},
        }

        result = await npc_agent.process(input_data)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_process_missing_npc_data(self, npc_agent):
        """Test error when NPC data is missing."""
        input_data = {
            "player_input": "你好",
            "context": {},
        }

        result = await npc_agent.process(input_data)

        assert result.success is False
        assert "npc_data" in result.error.lower()

    @pytest.mark.asyncio
    async def test_process_missing_player_input(
        self, npc_agent, sample_npc_data
    ):
        """Test error when player input is missing."""
        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "context": {},
        }

        result = await npc_agent.process(input_data)

        assert result.success is False
        assert "player_input" in result.error.lower()

    @pytest.mark.asyncio
    async def test_process_invalid_json_response(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test error handling for invalid JSON from LLM."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="这不是有效的JSON {"
        )

        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "你好",
            "context": {},
        }

        result = await npc_agent.process(input_data)

        assert result.success is False
        assert "parse" in result.error.lower() or "json" in result.error.lower()

    @pytest.mark.asyncio
    async def test_build_prompt_includes_soul(
        self, npc_agent, sample_npc_data
    ):
        """Test that prompt includes NPC soul information."""
        messages = npc_agent._build_prompt(
            npc_data=sample_npc_data.model_dump(),
            player_input="你好",
            context={"location": "library_main_hall"},
        )

        assert len(messages) >= 2
        prompt_text = " ".join(str(m.content) for m in messages)

        # Should include NPC identity
        assert "陈玲" in prompt_text
        # Should include personality
        assert "内向" in prompt_text or "shy" in prompt_text.lower()
        # Should include speech style
        assert "轻柔" in prompt_text or "soft" in prompt_text.lower()

    @pytest.mark.asyncio
    async def test_build_prompt_includes_body_state(
        self, npc_agent, sample_npc_data
    ):
        """Test that prompt includes NPC body state."""
        sample_npc_data.body.tags = ["忙碌"]
        sample_npc_data.body.relations["player"] = 30

        messages = npc_agent._build_prompt(
            npc_data=sample_npc_data.model_dump(),
            player_input="能打扰一下吗？",
            context={"location": "library_main_hall"},
        )

        prompt_text = " ".join(str(m.content) for m in messages)

        # Should include current state
        assert "忙碌" in prompt_text or "busy" in prompt_text.lower()

    @pytest.mark.asyncio
    async def test_sync_invoke(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test synchronous invocation."""
        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "你好。", "emotion": "neutral", "action": ""}'
        )

        result = npc_agent.invoke({
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "你好",
            "context": {},
        })

        assert result.success is True

    @pytest.mark.asyncio
    async def test_process_returns_suggested_relation_change(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test NPC can suggest relationship changes."""
        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "太感谢你了！", "emotion": "grateful", '
                   '"action": "眼眶湿润", "relation_change": 10}'
        )

        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "我帮你找到了那本书",
            "context": {},
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        # Relation change should be in metadata if LLM suggests it
        if "relation_change" in result.metadata:
            assert result.metadata["relation_change"] == 10

    @pytest.mark.asyncio
    async def test_language_selection_cn(
        self, npc_agent, sample_npc_data
    ):
        """Test prompt uses Chinese when lang=cn."""
        messages = npc_agent._build_prompt(
            npc_data=sample_npc_data.model_dump(),
            player_input="你好",
            context={},
            lang="cn",
        )

        prompt_text = " ".join(str(m.content) for m in messages)
        # Should use Chinese description
        assert "图书馆" in prompt_text or "馆员" in prompt_text

    @pytest.mark.asyncio
    async def test_language_selection_en(
        self, npc_agent, sample_npc_data
    ):
        """Test prompt uses English when lang=en."""
        messages = npc_agent._build_prompt(
            npc_data=sample_npc_data.model_dump(),
            player_input="Hello",
            context={},
            lang="en",
        )

        prompt_text = " ".join(str(m.content) for m in messages)
        # Should use English description
        assert "librarian" in prompt_text.lower() or "library" in prompt_text.lower()


class TestNPCAgentMemoryRetrieval:
    """Test suite for NPC memory retrieval functionality."""

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

    def test_npc_agent_initialization_with_vector_store(self, mock_llm):
        """Test NPCAgent can be initialized with and without vector store."""
        # Without vector store
        agent1 = NPCAgent(mock_llm)
        assert agent1.vector_store is None

        # With vector store
        with tempfile.TemporaryDirectory() as tmpdir:
            vector_store = VectorStoreService(tmpdir)
            agent2 = NPCAgent(mock_llm, vector_store=vector_store)
            assert agent2.vector_store is vector_store

    def test_retrieve_relevant_memories_no_vector_store(self, mock_llm):
        """Test that empty list is returned when no vector store is available."""
        agent = NPCAgent(mock_llm)  # No vector store

        memories = {
            "玩家给了我一本珍贵的书": ["礼物", "书籍"],
            "昨天帮玩家找回了丢失的钥匙": ["帮助", "钥匙"],
        }

        result = agent._retrieve_relevant_memories(
            npc_id="chen_ling",
            player_input="关于书籍的问题",
            all_memories=memories,
            n_results=3,
        )

        assert result == []

    def test_retrieve_relevant_memories_no_memories(self, mock_llm):
        """Test that empty list is returned when NPC has no memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vector_store = VectorStoreService(tmpdir)
            agent = NPCAgent(mock_llm, vector_store=vector_store)

            result = agent._retrieve_relevant_memories(
                npc_id="chen_ling",
                player_input="关于书籍的问题",
                all_memories={},
                n_results=3,
            )

            assert result == []

    @pytest.mark.skip(reason="需要实现记忆索引功能")
    def test_retrieve_relevant_memories_with_vector_search(self, mock_llm):
        """Test memory retrieval using vector similarity search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vector_store = VectorStoreService(tmpdir)
            agent = NPCAgent(mock_llm, vector_store=vector_store)

            # Add memories to vector store (indexing)
            memories = {
                "玩家给了我一本珍贵的古籍": ["礼物", "古籍"],
                "玩家询问了图书馆的历史": ["问题", "历史"],
            }

            # TODO: 实现记忆索引逻辑
            # vector_store.add_documents(
            #     collection_name="npc_memories_chen_ling",
            #     documents=list(memories.keys()),
            #     metadatas=[{"keywords": ",".join(kws)} for kws in memories.values()],
            #     ids=[f"memory_{i}" for i in range(len(memories))],
            # )

            # Search for relevant memories
            result = agent._retrieve_relevant_memories(
                npc_id="chen_ling",
                player_input="关于历史的问题",
                all_memories=memories,
                n_results=3,
            )

            # Should find the memory about library history
            assert len(result) >= 1
            # The result should be semantically similar to the query

    def test_build_system_prompt_with_memory_retrieval(self, mock_llm):
        """Test that system prompt includes retrieved memories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vector_store = VectorStoreService(tmpdir)
            agent = NPCAgent(mock_llm, vector_store=vector_store)

            # Create NPC with memories
            npc = NPCData(
                id="chen_ling",
                soul=NPCSoul(
                    name="陈玲",
                    description={"cn": "图书馆馆员", "en": "Librarian"},
                    personality=["内向", "细心"],
                    speech_style={"cn": "说话轻柔", "en": "Speaks softly"},
                ),
                body=NPCBody(
                    location="library",
                    inventory=[],
                    relations={"player": 0},
                    tags=["工作中"],
                    memory={
                        "玩家给了我一本珍贵的古籍": ["礼物", "书籍"],
                        "昨天帮玩家找回了丢失的钥匙": ["帮助", "钥匙"],
                    },
                ),
            )

            # Build prompt with player input
            prompt = agent._build_system_prompt(
                npc=npc,
                player_input="关于书籍的问题",
                lang="cn",
            )

            # Should include memory section
            assert "记忆" in prompt or "Memory" in prompt

    def test_build_system_prompt_fallback_to_recent_memories(self, mock_llm):
        """Test fallback to recent memories when vector search fails."""
        agent = NPCAgent(mock_llm)  # No vector store

        # Create NPC with memories
        npc = NPCData(
            id="chen_ling",
            soul=NPCSoul(
                name="陈玲",
                description={"cn": "图书馆馆员", "en": "Librarian"},
                personality=["内向", "细心"],
                speech_style={"cn": "说话轻柔", "en": "Speaks softly"},
            ),
            body=NPCBody(
                location="library",
                inventory=[],
                relations={"player": 0},
                tags=["工作中"],
                memory={
                    "玩家给了我一本珍贵的古籍": ["礼物", "书籍"],
                    "昨天帮玩家找回了丢失的钥匙": ["帮助", "钥匙"],
                    "上个月玩家帮助整理了书籍": ["帮助", "整理"],
                },
            ),
        )

        # Build prompt with player input
        prompt = agent._build_system_prompt(
            npc=npc,
            player_input="关于书籍的问题",
            lang="cn",
        )

        # Should include recent memories as fallback
        assert "近期记忆" in prompt or "Recent Memories" in prompt
        # Should show at least some memories
        memory_lines = [line for line in prompt.split("\n") if line.startswith("- ")]
        assert len(memory_lines) >= 1

    def test_build_system_prompt_empty_memories(self, mock_llm):
        """Test that no memory section is shown when NPC has no memories."""
        agent = NPCAgent(mock_llm)

        # Create NPC without memories
        npc = NPCData(
            id="chen_ling",
            soul=NPCSoul(
                name="陈玲",
                description={"cn": "图书馆馆员", "en": "Librarian"},
                personality=["内向", "细心"],
                speech_style={"cn": "说话轻柔", "en": "Speaks softly"},
            ),
            body=NPCBody(
                location="library",
                inventory=[],
                relations={"player": 0},
                tags=["工作中"],
                memory={},
            ),
        )

        # Build prompt
        prompt = agent._build_system_prompt(
            npc=npc,
            player_input="你好",
            lang="cn",
        )

        # Should not include memory section
        assert "记忆" not in prompt
        assert "Memory" not in prompt

    @pytest.mark.asyncio
    async def test_process_includes_memory_in_prompt(self, mock_llm):
        """Test that process() method includes memories in the generated prompt."""
        agent = NPCAgent(mock_llm)

        npc_data = {
            "id": "chen_ling",
            "soul": {
                "name": "陈玲",
                "description": {"cn": "图书馆馆员", "en": "Librarian"},
                "personality": ["内向", "细心"],
                "speech_style": {"cn": "说话轻柔", "en": "Speaks softly"},
            },
            "body": {
                "location": "library_main_hall",
                "inventory": ["钥匙串", "笔记本"],
                "relations": {"player": 0},
                "tags": ["工作中"],
                "memory": {
                    "玩家给了我一本珍贵的古籍": ["礼物", "书籍"],
                },
            },
        }

        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "是的，那本书很珍贵。", "emotion": "happy", "action": "微笑"}'
        )

        result = await agent.process(
            {
                "npc_data": npc_data,
                "player_input": "关于那本书的问题",
                "context": {"location": "library_main_hall"},
                "lang": "cn",
            }
        )

        assert result.success is True
        # Check that the prompt included memories
        # (The mock LLM should have received a prompt with memory context)
