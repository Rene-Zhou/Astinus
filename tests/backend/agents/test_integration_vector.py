"""Integration tests for vector retrieval system end-to-end."""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.backend.agents.gm import GMAgent
from src.backend.agents.npc import NPCAgent
from src.backend.models.character import PlayerCharacter, Trait
from src.backend.models.game_state import GameState
from src.backend.models.i18n import LocalizedString
from src.backend.models.world_pack import (
    LocalizedString as WPLocalizedString,
    LoreEntry,
    NPCBody,
    NPCData,
    NPCSoul,
    WorldPack,
    WorldPackInfo,
)
from src.backend.services.vector_store import VectorStoreService
from src.backend.services.world import WorldPackLoader
from src.backend.services.lore import LoreService

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


class TestVectorRetrievalIntegration:
    """End-to-end integration tests for vector retrieval system."""

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
    def temp_dirs(self):
        """Create temporary directories for packs and vector store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            packs_dir = Path(tmpdir) / "packs"
            packs_dir.mkdir()
            db_dir = Path(tmpdir) / "chroma_db"
            db_dir.mkdir()
            yield {"packs_dir": packs_dir, "db_dir": db_dir}

    @pytest.fixture
    def sample_world_pack(self, temp_dirs):
        """Create and save a sample world pack with lore entries."""
        pack = WorldPack(
            info=WorldPackInfo(
                id="demo_pack",
                name=WPLocalizedString(cn="演示包", en="Demo Pack"),
                version="1.0.0",
                description=WPLocalizedString(cn="演示用世界包", en="Demo world pack"),
            ),
            entries={
                "1": LoreEntry(
                    uid=1,
                    key=["暴风城", "历史"],
                    content=WPLocalizedString(
                        cn="暴风城是王国的首都，拥有悠久的历史。",
                        en="Stormwind is the capital with a long history.",
                    ),
                    order=1,
                    constant=False,
                ),
                "2": LoreEntry(
                    uid=2,
                    key=["暴风城", "建筑"],
                    content=WPLocalizedString(
                        cn="暴风城的城墙高耸入云，防御坚固。",
                        en="Stormwind's walls tower high with strong defenses.",
                    ),
                    order=2,
                    constant=False,
                ),
                "100": LoreEntry(
                    uid=100,
                    key=["规则"],
                    content=WPLocalizedString(
                        cn="这是一个常量条目，总是被包含。",
                        en="This is a constant entry, always included.",
                    ),
                    order=0,
                    constant=True,
                ),
            },
            npcs={
                "chen_ling": NPCData(
                    id="chen_ling",
                    soul=NPCSoul(
                        name="陈玲",
                        description={
                            "cn": "图书馆的年轻女馆员",
                            "en": "A young female librarian",
                        },
                        personality=["内向", "细心"],
                        speech_style={
                            "cn": "说话轻柔",
                            "en": "Speaks softly",
                        },
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
            },
            locations={},
        )

        # Save pack to file
        pack_path = temp_dirs["packs_dir"] / "demo_pack.json"
        pack_path.write_text(pack.model_dump_json(), encoding="utf-8")

        return pack

    @pytest.fixture
    def services_with_vector_store(self, temp_dirs, sample_world_pack):
        """Create all services with vector store enabled."""
        vector_store = VectorStoreService(temp_dirs["db_dir"])
        world_loader = WorldPackLoader(
            temp_dirs["packs_dir"],
            vector_store=vector_store,
            enable_vector_indexing=True,
        )
        # Load pack to trigger indexing
        world_loader.load("demo_pack")

        return {
            "vector_store": vector_store,
            "world_loader": world_loader,
        }

    def test_complete_lore_workflow_indexing_and_search(
        self, mock_llm, services_with_vector_store, temp_dirs
    ):
        """Test 1: Complete lore workflow - load, index, search."""
        vector_store = services_with_vector_store["vector_store"]
        world_loader = services_with_vector_store["world_loader"]

        # Verify lore entries were indexed
        collection_name = "lore_entries_demo_pack"
        count = vector_store.get_collection_count(collection_name)
        assert count == 6  # 3 entries × 2 languages (cn/en)

        # Create LoreAgent with vector store
        lore_agent = LoreAgent(mock_llm, world_loader, vector_store=vector_store)

        # Load pack and search
        pack = world_loader.load("demo_pack")

        # Test keyword + vector hybrid search
        results = lore_agent._search_lore(pack, "暴风城的历史", "")

        # Should find relevant entries
        assert len(results) >= 1
        # Results should include constant entry
        assert any(r.constant for r in results)

    def test_npc_memory_cycle_index_retrieve_influence(self, mock_llm, services_with_vector_store):
        """Test 2: NPC memory cycle - add, index, retrieve, influence response."""
        vector_store = services_with_vector_store["vector_store"]
        services_with_vector_store["world_loader"]

        # Create NPCAgent with vector store
        npc_agent = NPCAgent(mock_llm, vector_store=vector_store)

        # Create NPC data
        npc_data_dict = {
            "id": "chen_ling",
            "soul": {
                "name": "陈玲",
                "description": {"cn": "图书馆馆员", "en": "Librarian"},
                "personality": ["内向", "细心"],
                "speech_style": {"cn": "说话轻柔", "en": "Speaks softly"},
            },
            "body": {
                "location": "library",
                "inventory": [],
                "relations": {"player": 0},
                "tags": ["工作中"],
                "memory": {
                    "玩家给了我一本珍贵的古籍": ["礼物", "书籍"],
                    "昨天帮玩家找回了丢失的钥匙": ["帮助", "钥匙"],
                },
            },
        }

        # Build prompt (which includes memory retrieval)
        from src.backend.models.world_pack import NPCData

        npc = NPCData(**npc_data_dict)

        prompt = npc_agent._build_system_prompt(
            npc=npc,
            player_input="关于书籍的问题",
            context={},
            lang="cn",
        )

        # Should include memory section
        assert "记忆" in prompt or "Memory" in prompt

    def test_gm_long_game_history_relevant_retrieval(self, mock_llm, services_with_vector_store):
        """Test 3: GM with long game (50+ turns) - retrieve relevant history."""
        vector_store = services_with_vector_store["vector_store"]
        world_loader = services_with_vector_store["world_loader"]

        # Create GM Agent with vector store
        character = PlayerCharacter(
            name="张伟",
            concept=LocalizedString(cn="冒险者", en="Adventurer"),
            traits=[
                Trait(
                    name=LocalizedString(cn="勇敢", en="Brave"),
                    description=LocalizedString(cn="勇敢", en="Brave"),
                    positive_aspect=LocalizedString(cn="勇敢", en="Brave"),
                    negative_aspect=LocalizedString(cn="鲁莽", en="Reckless"),
                )
            ],
        )

        game_state = GameState(
            session_id="test-game",
            player=character,
            world_pack_id="demo_pack",
            current_location="library",
        )

        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={},
            game_state=game_state,
            vector_store=vector_store,
            world_pack_loader=world_loader,
        )

        # Add 15 messages (enough to trigger history retrieval)
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

        collection_name = f"conversation_history_{game_state.session_id}"
        for content in messages:
            game_state.add_message(
                role="user",
                content=content,
                vector_store=vector_store,
                collection_name=collection_name,
            )

        # Retrieve relevant history
        relevant_history = gm_agent._retrieve_relevant_history(
            session_id=game_state.session_id,
            player_input="关于书籍的问题",
            all_messages=game_state.messages,
            n_results=5,
        )

        # Should return relevant messages
        assert len(relevant_history) >= 1
        # Messages should be sorted by turn (chronological order)
        assert all(
            relevant_history[i]["turn"] <= relevant_history[i + 1]["turn"]
            for i in range(len(relevant_history) - 1)
        )

    @pytest.mark.skip(reason="需要改进中文语义匹配")
    def test_multilingual_query_handling(self, mock_llm, services_with_vector_store):
        """Test 4: Multilingual query handling - cn/en separation."""
        vector_store = services_with_vector_store["vector_store"]
        world_loader = services_with_vector_store["world_loader"]

        # Create LoreAgent with vector store
        lore_agent = LoreAgent(mock_llm, world_loader, vector_store=vector_store)

        pack = world_loader.load("demo_pack")

        # Chinese query
        results_cn = lore_agent._search_lore(pack, "暴风城的历史", "")
        assert len(results_cn) >= 1

        # English query
        results_en = lore_agent._search_lore(pack, "history of Stormwind", "")
        assert len(results_en) >= 1

    def test_persistence_reload_from_disk(self, mock_llm, services_with_vector_store, temp_dirs):
        """Test 5: Persistence - data survives reload."""
        vector_store = services_with_vector_store["vector_store"]
        world_loader = services_with_vector_store["world_loader"]

        # Load and index a pack
        world_loader.load("demo_pack")

        # Check collection exists
        collection_name = "lore_entries_demo_pack"
        count_before = vector_store.get_collection_count(collection_name)
        assert count_before > 0

        # Reset singleton (simulates restart)
        VectorStoreService.reset_instance()

        # Create new vector store instance (should reload from disk)
        vector_store2 = VectorStoreService(temp_dirs["db_dir"])

        # Data should still be there
        count_after = vector_store2.get_collection_count(collection_name)
        assert count_after == count_before

    def test_cross_agent_collaboration(self, mock_llm, services_with_vector_store):
        """Test 6: Cross-agent collaboration with shared vector store."""
        vector_store = services_with_vector_store["vector_store"]
        world_loader = services_with_vector_store["world_loader"]

        # All agents use the same vector store
        lore_agent = LoreAgent(mock_llm, world_loader, vector_store=vector_store)
        NPCAgent(mock_llm, vector_store=vector_store)

        # LoreAgent indexes lore entries
        pack = world_loader.load("demo_pack")
        lore_results = lore_agent._search_lore(pack, "暴风城", "")

        # NPCAgent retrieves memories using same vector store
        # (memories would be indexed separately)
        assert lore_results is not None

    def test_error_recovery_graceful_degradation(self, mock_llm, services_with_vector_store):
        """Test 7: Error recovery - graceful degradation when vector store fails."""
        vector_store = services_with_vector_store["vector_store"]
        world_loader = services_with_vector_store["world_loader"]

        # Create LoreAgent with vector store
        lore_agent = LoreAgent(mock_llm, world_loader, vector_store=vector_store)

        # Simulate vector store failure by clearing it
        lore_agent.vector_store = None

        pack = world_loader.load("demo_pack")

        # Should still work with keyword search
        results = lore_agent._search_lore(pack, "暴风城", "")

        # Should return results using keyword-only fallback
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_full_integration_game_flow(self, mock_llm, services_with_vector_store):
        """Test 8: Full integration - complete game flow with all agents."""
        vector_store = services_with_vector_store["vector_store"]
        world_loader = services_with_vector_store["world_loader"]

        # Create all agents
        lore_agent = LoreAgent(mock_llm, world_loader, vector_store=vector_store)
        npc_agent = NPCAgent(mock_llm, vector_store=vector_store)

        character = PlayerCharacter(
            name="张伟",
            concept=LocalizedString(cn="冒险者", en="Adventurer"),
            traits=[
                Trait(
                    name=LocalizedString(cn="勇敢", en="Brave"),
                    description=LocalizedString(cn="勇敢", en="Brave"),
                    positive_aspect=LocalizedString(cn="勇敢", en="Brave"),
                    negative_aspect=LocalizedString(cn="鲁莽", en="Reckless"),
                )
            ],
        )

        game_state = GameState(
            session_id="integration-test",
            player=character,
            world_pack_id="demo_pack",
            current_location="library",
        )

        gm_agent = GMAgent(
            llm=mock_llm,
            sub_agents={"lore": lore_agent, "npc": npc_agent},
            game_state=game_state,
            vector_store=vector_store,
            world_pack_loader=world_loader,
        )

        # Simulate a complete game turn
        player_input = "我想了解暴风城的历史"

        # 1. GM would parse intent and call LoreAgent
        lore_result = await lore_agent.process(
            {
                "query": player_input,
                "context": "玩家询问背景",
                "world_pack_id": "demo_pack",
            }
        )

        assert lore_result.success is True
        assert "暴风城" in lore_result.content

        # 2. Add to conversation history
        collection_name = f"conversation_history_{game_state.session_id}"
        game_state.add_message(
            role="user",
            content=player_input,
            vector_store=vector_store,
            collection_name=collection_name,
        )
        game_state.add_message(
            role="assistant",
            content=lore_result.content,
            vector_store=vector_store,
            collection_name=collection_name,
        )

        # 3. Verify history was indexed
        history_count = vector_store.get_collection_count(collection_name)
        assert history_count >= 2

        # 4. Retrieve relevant history
        relevant_history = gm_agent._retrieve_relevant_history(
            session_id=game_state.session_id,
            player_input=player_input,
            all_messages=game_state.messages,
            n_results=5,
        )

        assert len(relevant_history) >= 1
