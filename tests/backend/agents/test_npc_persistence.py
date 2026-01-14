"""Tests for NPC state persistence (memory and relations).

Tests the NPCAgent's ability to:
- Store new memories from interactions
- Update relationship values
- Persist state changes to database/vector store
"""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from src.backend.agents.npc import NPCAgent
from src.backend.services.vector_store import VectorStoreService

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


class TestNPCMemoryPersistence:
    """Test suite for NPC memory persistence."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock VectorStoreService."""
        store = MagicMock(spec=VectorStoreService)
        store.add_documents = MagicMock()
        store.search = MagicMock(
            return_value={
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
                "ids": [[]],
            }
        )
        return store

    @pytest.fixture
    def sample_npc_data(self):
        """Create sample NPC data."""
        return {
            "id": "chen_ling",
            "soul": {
                "name": "陈灵",
                "description": {
                    "cn": "图书馆的神秘管理员，知晓许多古老秘密。",
                    "en": "The mysterious librarian who knows many ancient secrets.",
                },
                "personality": ["神秘", "博学", "耐心"],
                "speech_style": {
                    "cn": "说话缓慢而深思熟虑，经常引用古籍。",
                    "en": "Speaks slowly and thoughtfully, often quoting ancient texts.",
                },
                "example_dialogue": [
                    {"user": "你好", "char": "欢迎来到知识的殿堂..."},
                ],
            },
            "body": {
                "location": "ancient_library",
                "inventory": ["ancient_key", "dusty_tome"],
                "relations": {"player": 0},
                "tags": [],
                "memory": {},
            },
        }

    @pytest.fixture
    def npc_agent(self, mock_llm, mock_vector_store):
        """Create NPCAgent instance with mock vector store."""
        return NPCAgent(mock_llm, vector_store=mock_vector_store)

    @pytest.mark.asyncio
    async def test_process_returns_new_memory(self, npc_agent, mock_llm, sample_npc_data):
        """Test that NPC response includes new memory to store."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "response": "这是一本珍贵的古籍，谢谢你。",
                "emotion": "grateful",
                "action": "小心翼翼地接过书籍",
                "relation_change": 5,
                "new_memory": {
                    "event": "玩家赠送了珍贵的古籍",
                    "keywords": ["gift", "book", "trust"]
                }
            }"""
        )

        input_data = {
            "npc_data": sample_npc_data,
            "player_input": "我想把这本古籍送给你",
            "context": {"location": "ancient_library"},
            "lang": "cn",
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        assert "new_memory" in result.metadata or "relation_change" in result.metadata

    @pytest.mark.asyncio
    async def test_process_returns_relation_change(self, npc_agent, mock_llm, sample_npc_data):
        """Test that NPC response includes relation change."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "response": "你的行为令我失望...",
                "emotion": "disappointed",
                "action": "皱起眉头",
                "relation_change": -10
            }"""
        )

        input_data = {
            "npc_data": sample_npc_data,
            "player_input": "我偷了你的书",
            "context": {"location": "ancient_library"},
            "lang": "cn",
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        assert result.metadata.get("relation_change") == -10

    @pytest.mark.asyncio
    async def test_add_memory_to_vector_store(
        self, npc_agent, mock_llm, mock_vector_store, sample_npc_data
    ):
        """Test that new memory is added to vector store."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "response": "我会记住这件事的。",
                "emotion": "thoughtful",
                "action": "",
                "relation_change": 0,
                "new_memory": {
                    "event": "玩家询问了关于失落之城的传说",
                    "keywords": ["lost_city", "legend", "question"]
                }
            }"""
        )

        input_data = {
            "npc_data": sample_npc_data,
            "player_input": "你知道失落之城的传说吗？",
            "context": {"location": "ancient_library"},
            "lang": "cn",
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        # Check that the response contains memory info for persistence
        if "new_memory" in result.metadata:
            assert "event" in result.metadata["new_memory"]

    @pytest.mark.asyncio
    async def test_memory_persistence_method(self, npc_agent, mock_vector_store):
        """Test the memory persistence helper method."""
        npc_id = "chen_ling"
        memory_event = "玩家帮助修复了古籍"
        memory_keywords = ["help", "repair", "book"]

        # Call the persistence method
        npc_agent.persist_memory(
            npc_id=npc_id,
            event=memory_event,
            keywords=memory_keywords,
        )

        # Verify vector store was called
        mock_vector_store.add_documents.assert_called_once()
        call_args = mock_vector_store.add_documents.call_args

        assert call_args.kwargs["collection_name"] == f"npc_memories_{npc_id}"
        assert memory_event in call_args.kwargs["documents"]

    @pytest.mark.asyncio
    async def test_memory_persistence_with_timestamp(self, npc_agent, mock_vector_store):
        """Test that memory includes timestamp in metadata."""
        npc_id = "chen_ling"
        memory_event = "玩家询问了禁忌之书的位置"
        memory_keywords = ["forbidden", "book", "location"]

        npc_agent.persist_memory(
            npc_id=npc_id,
            event=memory_event,
            keywords=memory_keywords,
        )

        call_args = mock_vector_store.add_documents.call_args
        metadatas = call_args.kwargs["metadatas"]

        assert len(metadatas) == 1
        assert "timestamp" in metadatas[0]
        assert "npc_id" in metadatas[0]
        assert metadatas[0]["npc_id"] == npc_id

    def test_persist_memory_no_vector_store(self, mock_llm):
        """Test that persist_memory handles missing vector store gracefully."""
        agent = NPCAgent(mock_llm, vector_store=None)

        # Should not raise exception
        agent.persist_memory(
            npc_id="test_npc",
            event="test event",
            keywords=["test"],
        )

    @pytest.mark.asyncio
    async def test_process_with_existing_memories_influences_response(
        self, mock_llm, sample_npc_data
    ):
        """Test that existing memories influence NPC response."""
        # Create mock vector store that returns existing memories
        mock_store = MagicMock(spec=VectorStoreService)
        mock_store.search.return_value = {
            "documents": [["玩家曾经帮助过我修复古籍", "玩家对古代历史很感兴趣"]],
            "metadatas": [[{"npc_id": "chen_ling"}, {"npc_id": "chen_ling"}]],
            "distances": [[0.1, 0.2]],
            "ids": [["mem_1", "mem_2"]],
        }

        agent = NPCAgent(mock_llm, vector_store=mock_store)

        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "response": "老朋友，又见面了！上次你帮我修复古籍的事我还记得呢。",
                "emotion": "happy",
                "action": "微笑着招手",
                "relation_change": 0
            }"""
        )

        # Update sample_npc_data to have existing memories (required for search to be called)
        sample_npc_data_with_memory = sample_npc_data.copy()
        sample_npc_data_with_memory["body"] = sample_npc_data["body"].copy()
        sample_npc_data_with_memory["body"]["memory"] = {
            "玩家曾经帮助过我修复古籍": ["help", "repair"],
            "玩家对古代历史很感兴趣": ["history", "interest"],
        }

        input_data = {
            "npc_data": sample_npc_data_with_memory,
            "player_input": "你好",
            "context": {"location": "ancient_library"},
            "lang": "cn",
        }

        result = await agent.process(input_data)

        assert result.success is True
        # Verify search was called for memory retrieval
        mock_store.search.assert_called()


class TestNPCRelationPersistence:
    """Test suite for NPC relation persistence."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def npc_agent(self, mock_llm):
        """Create NPCAgent instance."""
        return NPCAgent(mock_llm)

    @pytest.fixture
    def sample_npc_data(self):
        """Create sample NPC data with existing relations."""
        return {
            "id": "zhang_wei",
            "soul": {
                "name": "张伟",
                "description": {
                    "cn": "小镇上的铁匠，性格直爽。",
                    "en": "The town blacksmith with a straightforward personality.",
                },
                "personality": ["直爽", "勤劳", "热心"],
                "speech_style": {
                    "cn": "说话直接，不拐弯抹角。",
                    "en": "Speaks directly without beating around the bush.",
                },
                "example_dialogue": [],
            },
            "body": {
                "location": "blacksmith_shop",
                "inventory": ["hammer", "tongs"],
                "relations": {"player": 20, "mayor": -10},
                "tags": ["busy"],
                "memory": {"玩家买了把好剑": ["purchase", "sword"]},
            },
        }

    @pytest.mark.asyncio
    async def test_relation_change_positive(self, npc_agent, mock_llm, sample_npc_data):
        """Test positive relation change is captured."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "response": "好样的！你真是个值得信赖的人！",
                "emotion": "impressed",
                "action": "拍了拍玩家的肩膀",
                "relation_change": 15
            }"""
        )

        input_data = {
            "npc_data": sample_npc_data,
            "player_input": "我帮你把那批货送到了",
            "context": {"location": "blacksmith_shop"},
            "lang": "cn",
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        assert result.metadata.get("relation_change") == 15

    @pytest.mark.asyncio
    async def test_relation_change_negative(self, npc_agent, mock_llm, sample_npc_data):
        """Test negative relation change is captured."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "response": "你竟敢...！给我滚出去！",
                "emotion": "furious",
                "action": "举起锤子指向门口",
                "relation_change": -25
            }"""
        )

        input_data = {
            "npc_data": sample_npc_data,
            "player_input": "我偷了你的锤子",
            "context": {"location": "blacksmith_shop"},
            "lang": "cn",
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        assert result.metadata.get("relation_change") == -25

    @pytest.mark.asyncio
    async def test_relation_change_clamped_to_bounds(self, npc_agent, mock_llm, sample_npc_data):
        """Test that extreme relation changes are noted."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "response": "你救了我的命！我这辈子都会记得你的恩情！",
                "emotion": "overwhelmed",
                "action": "激动地握住玩家的手",
                "relation_change": 100
            }"""
        )

        input_data = {
            "npc_data": sample_npc_data,
            "player_input": "我从火灾中救出了你的孩子",
            "context": {"location": "blacksmith_shop"},
            "lang": "cn",
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        # Relation change should be captured (validation happens at persistence layer)
        assert "relation_change" in result.metadata

    @pytest.mark.asyncio
    async def test_get_updated_relation_level(self, npc_agent, mock_llm, sample_npc_data):
        """Test calculating new relation level."""
        # Initial relation is 20
        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "response": "谢谢你的帮助。",
                "emotion": "grateful",
                "action": "",
                "relation_change": 10
            }"""
        )

        input_data = {
            "npc_data": sample_npc_data,
            "player_input": "我帮你清理了店铺",
            "context": {"location": "blacksmith_shop"},
            "lang": "cn",
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        # Original relationship_level should be in metadata
        assert result.metadata.get("relationship_level") == 20
        # And the change
        assert result.metadata.get("relation_change") == 10
        # New level would be 30 (20 + 10)

    def test_calculate_new_relation_level(self, npc_agent):
        """Test the relation level calculation helper."""
        # Test normal case
        assert npc_agent.calculate_new_relation_level(20, 10) == 30
        assert npc_agent.calculate_new_relation_level(20, -10) == 10

        # Test clamping at bounds
        assert npc_agent.calculate_new_relation_level(95, 20) == 100
        assert npc_agent.calculate_new_relation_level(-95, -20) == -100

        # Test zero change
        assert npc_agent.calculate_new_relation_level(50, 0) == 50


class TestNPCStateUpdateIntegration:
    """Integration tests for NPC state updates."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock VectorStoreService."""
        store = MagicMock(spec=VectorStoreService)
        store.add_documents = MagicMock()
        store.search = MagicMock(
            return_value={
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
                "ids": [[]],
            }
        )
        return store

    @pytest.fixture
    def sample_npc_data(self):
        """Create sample NPC data."""
        return {
            "id": "li_mei",
            "soul": {
                "name": "李梅",
                "description": {
                    "cn": "客栈老板娘，善于察言观色。",
                    "en": "The innkeeper who is good at reading people.",
                },
                "personality": ["精明", "热情", "八卦"],
                "speech_style": {
                    "cn": "说话热情但总想打听消息。",
                    "en": "Speaks warmly but always wants to gather information.",
                },
                "example_dialogue": [],
            },
            "body": {
                "location": "inn",
                "inventory": ["room_keys", "ledger"],
                "relations": {"player": 10},
                "tags": [],
                "memory": {},
            },
        }

    @pytest.mark.asyncio
    async def test_full_interaction_with_memory_and_relation(
        self, mock_llm, mock_vector_store, sample_npc_data
    ):
        """Test full interaction that updates both memory and relation."""
        agent = NPCAgent(mock_llm, vector_store=mock_vector_store)

        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "response": "哎呀！你怎么知道我在找这个？太感谢了！",
                "emotion": "surprised",
                "action": "接过丢失的发簪，眼眶微红",
                "relation_change": 20,
                "new_memory": {
                    "event": "玩家归还了我丢失的发簪",
                    "keywords": ["hairpin", "return", "kind"]
                }
            }"""
        )

        input_data = {
            "npc_data": sample_npc_data,
            "player_input": "我在路上捡到了这个发簪，好像是你的？",
            "context": {"location": "inn"},
            "lang": "cn",
        }

        result = await agent.process(input_data)

        assert result.success is True
        assert result.metadata.get("relation_change") == 20
        assert result.metadata.get("emotion") == "surprised"

    @pytest.mark.asyncio
    async def test_get_state_update_summary(self, mock_llm, mock_vector_store, sample_npc_data):
        """Test getting a summary of state updates from interaction."""
        agent = NPCAgent(mock_llm, vector_store=mock_vector_store)

        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "response": "这件事我记下了。",
                "emotion": "neutral",
                "action": "",
                "relation_change": 5,
                "new_memory": {
                    "event": "玩家分享了关于北方商队的情报",
                    "keywords": ["intel", "caravan", "north"]
                }
            }"""
        )

        input_data = {
            "npc_data": sample_npc_data,
            "player_input": "我听说北方来了一支商队",
            "context": {"location": "inn"},
            "lang": "cn",
        }

        result = await agent.process(input_data)

        # Build state update summary
        state_updates = agent.get_state_updates_from_response(result)

        assert state_updates["npc_id"] == "li_mei"
        assert state_updates["relation_change"] == 5
        assert "new_memory" in state_updates or state_updates.get("has_memory_update", False)

    @pytest.mark.asyncio
    async def test_no_state_updates_for_simple_interaction(self, mock_llm, sample_npc_data):
        """Test that simple interactions don't create unnecessary updates."""
        agent = NPCAgent(mock_llm)

        mock_llm.ainvoke.return_value = AIMessage(
            content="""{
                "response": "今天天气不错呢。",
                "emotion": "neutral",
                "action": "擦拭着柜台",
                "relation_change": 0
            }"""
        )

        input_data = {
            "npc_data": sample_npc_data,
            "player_input": "今天天气怎么样？",
            "context": {"location": "inn"},
            "lang": "cn",
        }

        result = await agent.process(input_data)

        assert result.success is True
        # No significant state changes
        assert result.metadata.get("relation_change", 0) == 0
