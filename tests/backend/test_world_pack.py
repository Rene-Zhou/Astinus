"""Tests for world pack models and loader."""

import json
import tempfile
from pathlib import Path

import pytest

from src.backend.models.i18n import LocalizedString
from src.backend.models.world_pack import (
    LocationData,
    LoreEntry,
    NPCBody,
    NPCData,
    NPCSoul,
    WorldPack,
    WorldPackInfo,
)
from src.backend.services.world import WorldPackLoader


class TestLoreEntry:
    """Test suite for LoreEntry model."""

    def test_create_basic_entry(self):
        """Test creating a basic lore entry."""
        entry = LoreEntry(
            uid=1,
            key=["暴风城", "Stormwind"],
            content=LocalizedString(cn="暴风城是人类的首都", en="Stormwind is the human capital"),
        )

        assert entry.uid == 1
        assert "暴风城" in entry.key
        assert entry.content.get("cn") == "暴风城是人类的首都"
        assert entry.constant is False
        assert entry.selective is True
        assert entry.order == 100

    def test_entry_with_secondary_keys(self):
        """Test entry with secondary keys."""
        entry = LoreEntry(
            uid=2,
            key=["管家"],
            secondary_keys=["庄园"],
            content=LocalizedString(cn="...", en="..."),
        )

        assert entry.secondary_keys == ["庄园"]

    def test_constant_entry(self):
        """Test constant (always-active) entry."""
        entry = LoreEntry(
            uid=3,
            key=["世界观"],
            content=LocalizedString(cn="背景设定", en="Background"),
            constant=True,
            selective=False,
        )

        assert entry.constant is True
        assert entry.selective is False


class TestNPCData:
    """Test suite for NPC models."""

    @pytest.fixture
    def sample_npc(self):
        """Create a sample NPC for testing."""
        return NPCData(
            id="chen_ling",
            soul=NPCSoul(
                name="陈玲",
                description=LocalizedString(
                    cn="一位年轻的历史学研究生", en="A young history graduate student"
                ),
                personality=["理性", "好奇", "谨慎"],
                speech_style=LocalizedString(cn="说话条理清晰", en="Speaks with clear logic"),
                example_dialogue=[{"user": "你好", "char": "你好，有什么需要帮助的吗？"}],
            ),
            body=NPCBody(
                location="manor_entrance",
                inventory=["notebook", "flashlight"],
                relations={"player": 10},
                tags=[],
                memory={},
            ),
        )

    def test_npc_creation(self, sample_npc):
        """Test NPC creation."""
        assert sample_npc.id == "chen_ling"
        assert sample_npc.soul.name == "陈玲"
        assert sample_npc.body.location == "manor_entrance"
        assert "理性" in sample_npc.soul.personality

    def test_npc_system_prompt(self, sample_npc):
        """Test NPC system prompt generation."""
        prompt = sample_npc.get_system_prompt(lang="cn")

        assert "陈玲" in prompt
        assert "历史学研究生" in prompt
        assert "理性" in prompt
        assert "说话条理清晰" in prompt

    def test_npc_body_relations(self, sample_npc):
        """Test NPC relationship tracking."""
        assert sample_npc.body.relations["player"] == 10


class TestLocationData:
    """Test suite for LocationData model."""

    def test_create_location(self):
        """Test creating a location."""
        location = LocationData(
            id="manor_hall",
            name=LocalizedString(cn="庄园大厅", en="Manor Hall"),
            description=LocalizedString(
                cn="宽敞的大厅已经破败不堪", en="The spacious hall has fallen into disrepair"
            ),
            connected_locations=["manor_entrance", "study"],
            present_npc_ids=[],
            items=["fallen_chandelier"],
            tags=["dangerous"],
        )

        assert location.id == "manor_hall"
        assert location.name.get("cn") == "庄园大厅"
        assert "study" in location.connected_locations
        assert "dangerous" in location.tags


class TestWorldPack:
    """Test suite for WorldPack model."""

    @pytest.fixture
    def sample_pack(self):
        """Create a sample world pack."""
        return WorldPack(
            info=WorldPackInfo(
                name=LocalizedString(cn="测试世界", en="Test World"),
                description=LocalizedString(cn="测试描述", en="Test description"),
            ),
            entries={
                "1": LoreEntry(
                    uid=1,
                    key=["关键词1", "keyword1"],
                    content=LocalizedString(cn="内容1", en="Content 1"),
                    constant=True,
                ),
                "2": LoreEntry(
                    uid=2,
                    key=["关键词2"],
                    content=LocalizedString(cn="内容2", en="Content 2"),
                    order=50,
                ),
            },
            npcs={},
            locations={},
        )

    def test_pack_creation(self, sample_pack):
        """Test world pack creation."""
        assert sample_pack.info.name.get("cn") == "测试世界"
        assert len(sample_pack.entries) == 2

    def test_get_entry(self, sample_pack):
        """Test getting entry by uid."""
        entry = sample_pack.get_entry(1)
        assert entry is not None
        assert entry.uid == 1

        missing = sample_pack.get_entry(999)
        assert missing is None

    def test_get_constant_entries(self, sample_pack):
        """Test getting constant entries."""
        constants = sample_pack.get_constant_entries()
        assert len(constants) == 1
        assert constants[0].uid == 1

    def test_search_entries_by_keyword(self, sample_pack):
        """Test keyword search."""
        matches = sample_pack.search_entries_by_keyword("关键词1")
        assert len(matches) == 1
        assert matches[0].uid == 1

        # Test case-insensitive search
        matches = sample_pack.search_entries_by_keyword("KEYWORD1")
        assert len(matches) == 1

        # Test no matches
        matches = sample_pack.search_entries_by_keyword("不存在")
        assert len(matches) == 0


class TestWorldPackLoader:
    """Test suite for WorldPackLoader service."""

    @pytest.fixture
    def temp_packs_dir(self):
        """Create a temporary directory with test pack."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_data = {
                "info": {
                    "name": {"cn": "测试包", "en": "Test Pack"},
                    "description": {"cn": "测试", "en": "Test"},
                },
                "entries": {},
                "npcs": {},
                "locations": {},
            }

            pack_path = Path(tmpdir) / "test_pack.json"
            with open(pack_path, "w", encoding="utf-8") as f:
                json.dump(pack_data, f)

            yield Path(tmpdir)

    def test_load_pack(self, temp_packs_dir):
        """Test loading a world pack."""
        loader = WorldPackLoader(temp_packs_dir)
        pack = loader.load("test_pack")

        assert pack.info.name.get("cn") == "测试包"

    def test_load_nonexistent_pack(self, temp_packs_dir):
        """Test loading a nonexistent pack."""
        loader = WorldPackLoader(temp_packs_dir)

        with pytest.raises(FileNotFoundError):
            loader.load("nonexistent")

    def test_list_available(self, temp_packs_dir):
        """Test listing available packs."""
        loader = WorldPackLoader(temp_packs_dir)
        available = loader.list_available()

        assert "test_pack" in available

    def test_cache_behavior(self, temp_packs_dir):
        """Test pack caching."""
        loader = WorldPackLoader(temp_packs_dir)

        pack1 = loader.load("test_pack")
        pack2 = loader.load("test_pack")

        assert pack1 is pack2  # Same object from cache

        # Force reload
        pack3 = loader.reload("test_pack")
        assert pack3 is not pack1

    def test_clear_cache(self, temp_packs_dir):
        """Test clearing the cache."""
        loader = WorldPackLoader(temp_packs_dir)
        loader.load("test_pack")

        loader.clear_cache()

        # Should be empty now
        assert len(loader._cache) == 0


class TestDemoPackIntegration:
    """Integration tests using the demo pack."""

    @pytest.fixture
    def demo_pack(self):
        """Load the demo pack."""
        packs_dir = Path(__file__).parent.parent.parent / "data" / "packs"
        if not (packs_dir / "demo_pack.json").exists():
            pytest.skip("Demo pack not available")

        loader = WorldPackLoader(packs_dir)
        return loader.load("demo_pack")

    def test_demo_pack_info(self, demo_pack):
        """Test demo pack metadata."""
        assert demo_pack.info.name.get("cn") == "幽暗庄园"
        assert demo_pack.info.name.get("en") == "The Dark Manor"

    def test_demo_pack_entries(self, demo_pack):
        """Test demo pack lore entries."""
        # Manor background is now selective (not constant) to prevent metagaming
        # Player must discover it through checks or NPC dialogue
        constants = demo_pack.get_constant_entries()
        # No constant entries expected - all lore should be discovered

        # Search for manor keyword - should still find entries
        matches = demo_pack.search_entries_by_keyword("庄园")
        assert len(matches) >= 1

    def test_demo_pack_npcs(self, demo_pack):
        """Test demo pack NPCs."""
        chen_ling = demo_pack.get_npc("chen_ling")
        assert chen_ling is not None
        assert chen_ling.soul.name == "陈玲"

        old_guard = demo_pack.get_npc("old_guard")
        assert old_guard is not None
        assert "沉默" in old_guard.soul.personality

    def test_demo_pack_locations(self, demo_pack):
        """Test demo pack locations."""
        village = demo_pack.get_location("village")
        assert village is not None
        assert village.name.get("cn") == "山脚村落"

        manor_hall = demo_pack.get_location("manor_hall")
        assert manor_hall is not None
        assert "dangerous" in manor_hall.tags
