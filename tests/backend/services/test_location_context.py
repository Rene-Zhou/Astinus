"""Tests for LocationContextService with hierarchical location-based context."""

import tempfile
from pathlib import Path

import pytest

from src.backend.models.i18n import LocalizedString
from src.backend.models.world_pack import (
    LoreEntry,
    LocationData,
    NPCBody,
    NPCData,
    NPCSoul,
    RegionData,
    WorldPack,
    WorldPackInfo,
)
from src.backend.services.location_context import LocationContextService
from src.backend.services.world import WorldPackLoader


class TestLocationContextServiceGetContextForLocation:
    """Test suite for LocationContextService.get_context_for_location()."""

    @pytest.fixture
    def sample_pack_with_region(self):
        """Create a sample world pack with regions and locations."""
        return WorldPack(
            info=WorldPackInfo(
                name=LocalizedString(cn="测试包", en="Test Pack"),
                description=LocalizedString(cn="测试用世界包", en="Test world pack"),
            ),
            entries={
                "1": LoreEntry(
                    uid=1,
                    key=["历史"],
                    content=LocalizedString(
                        cn="这片土地有着悠久的历史。",
                        en="This land has a long history.",
                    ),
                    order=1,
                    constant=False,
                    visibility="basic",
                ),
                "2": LoreEntry(
                    uid=2,
                    key=["秘密"],
                    content=LocalizedString(
                        cn="这里隐藏着可怕的秘密。",
                        en="Terrible secrets lie hidden here.",
                    ),
                    order=2,
                    constant=False,
                    visibility="detailed",
                    applicable_locations=["secret_room"],
                ),
                "100": LoreEntry(
                    uid=100,
                    key=["规则"],
                    content=LocalizedString(
                        cn="这是常量条目。", en="This is a constant entry.",
                    ),
                    order=0,
                    constant=True,
                ),
            },
            npcs={},
            locations={
                "village": LocationData(
                    id="village",
                    name=LocalizedString(cn="村庄", en="Village"),
                    description=LocalizedString(
                        cn="一个宁静的小村庄。", en="A peaceful small village.",
                    ),
                    atmosphere=LocalizedString(cn="宁静祥和", en="Peaceful and serene"),
                    connected_locations=["forest_path"],
                    present_npc_ids=[],
                    items=["well", "bench"],
                    tags=["safe"],
                    region_id="northern_region",
                    visible_items=["well", "bench"],
                    hidden_items=[],
                    lore_tags=["history"],
                ),
                "secret_room": LocationData(
                    id="secret_room",
                    name=LocalizedString(cn="密室", en="Secret Room"),
                    description=LocalizedString(
                        cn="一个黑暗潮湿的房间。", en="A dark and damp room.",
                    ),
                    atmosphere=LocalizedString(cn="阴森恐怖", en="Dark and terrifying"),
                    connected_locations=[],
                    present_npc_ids=[],
                    items=[],
                    tags=["dangerous"],
                    region_id="dungeon_region",
                    visible_items=["flickering_candle"],
                    hidden_items=["hidden_door", "locked_chest"],
                    lore_tags=["secrets"],
                ),
            },
            regions={
                "northern_region": RegionData(
                    id="northern_region",
                    name=LocalizedString(cn="北部地区", en="Northern Region"),
                    description=LocalizedString(cn="北部的寒冷地区", en="The cold northern lands"),
                    narrative_tone=LocalizedString(cn="寒冷而神秘", en="Cold and mysterious"),
                    atmosphere_keywords=["snow", "mysterious", "quiet"],
                    location_ids=["village"],
                    tags=["wilderness"],
                ),
                "dungeon_region": RegionData(
                    id="dungeon_region",
                    name=LocalizedString(cn="地下区域", en="Dungeon Region"),
                    description=LocalizedString(cn="阴暗的地下区域", en="The dark underground"),
                    narrative_tone=LocalizedString(cn="恐怖压抑", en="Terrifying and oppressive"),
                    atmosphere_keywords=["dark", "damp", "scary"],
                    location_ids=["secret_room"],
                    tags=["dungeon"],
                ),
            },
        )

    @pytest.fixture
    def world_pack_loader(self, sample_pack_with_region):
        """Create WorldPackLoader with sample pack."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "packs"
            pack_dir.mkdir()

            pack_path = pack_dir / "test_pack.json"
            pack_path.write_text(sample_pack_with_region.model_dump_json(), encoding="utf-8")

            loader = WorldPackLoader(pack_dir)
            loader.load("test_pack")

            yield loader, Path(tmpdir)

    def test_get_context_with_valid_location(self, world_pack_loader):
        """Test getting context for a valid location."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        context = service.get_context_for_location(
            world_pack_id="test_pack",
            location_id="village",
            discovered_items=set(),
            lang="cn",
        )

        assert context is not None
        assert context["location"]["id"] == "village"
        assert context["location"]["name"] == "村庄"
        assert context["location"]["description"] == "一个宁静的小村庄。"
        assert "well" in context["location"]["visible_items"]
        assert len(context["location"]["hidden_items_remaining"]) == 0

    def test_get_context_with_region(self, world_pack_loader):
        """Test that region context is included."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        context = service.get_context_for_location(
            world_pack_id="test_pack",
            location_id="village",
            discovered_items=set(),
            lang="cn",
        )

        assert context["region"]["id"] == "northern_region"
        assert context["region"]["name"] == "北部地区"
        assert "寒冷而神秘" in context["region"]["narrative_tone"]
        assert "snow" in context["region"]["atmosphere_keywords"]

    def test_get_context_with_nonexistent_location(self, world_pack_loader):
        """Test getting context for a non-existent location returns empty context."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        context = service.get_context_for_location(
            world_pack_id="test_pack",
            location_id="nonexistent",
            discovered_items=set(),
            lang="cn",
        )

        assert context["region"]["id"] == "_global"
        assert context["region"]["name"] == "Unknown"
        assert context["location"]["id"] == ""
        assert context["location"]["name"] == "Unknown"

    def test_get_context_without_region_uses_global(self, world_pack_loader):
        """Test that locations without region use global default."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        context = service.get_context_for_location(
            world_pack_id="test_pack",
            location_id="secret_room",
            discovered_items=set(),
            lang="cn",
        )

        assert context["region"]["id"] == "dungeon_region"
        assert context["region"]["name"] == "地下区域"

    def test_hidden_items_separation(self, world_pack_loader):
        """Test that hidden items are correctly separated into revealed/remaining."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        discovered = {"hidden_door"}
        context = service.get_context_for_location(
            world_pack_id="test_pack",
            location_id="secret_room",
            discovered_items=discovered,
            lang="cn",
        )

        assert "hidden_door" in context["location"]["hidden_items_revealed"]
        assert "locked_chest" in context["location"]["hidden_items_remaining"]

    def test_language_switching(self, world_pack_loader):
        """Test that language switching works correctly."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        context_cn = service.get_context_for_location(
            world_pack_id="test_pack",
            location_id="village",
            discovered_items=set(),
            lang="cn",
        )

        context_en = service.get_context_for_location(
            world_pack_id="test_pack",
            location_id="village",
            discovered_items=set(),
            lang="en",
        )

        assert context_cn["location"]["name"] == "村庄"
        assert context_en["location"]["name"] == "Village"
        assert context_cn["region"]["name"] == "北部地区"
        assert context_en["region"]["name"] == "Northern Region"

    def test_atmosphere_guidance(self, world_pack_loader):
        """Test that atmosphere guidance is built correctly."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        context = service.get_context_for_location(
            world_pack_id="test_pack",
            location_id="village",
            discovered_items=set(),
            lang="cn",
        )

        assert context["atmosphere_guidance"] != ""
        assert "寒冷而神秘" in context["atmosphere_guidance"] or "宁静祥和" in context["atmosphere_guidance"]

    def test_basic_lore_included(self, world_pack_loader):
        """Test that basic lore entries are included."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        context = service.get_context_for_location(
            world_pack_id="test_pack",
            location_id="village",
            discovered_items=set(),
            lang="cn",
        )

        assert len(context["basic_lore"]) >= 1
        assert any("悠久的历史" in lore for lore in context["basic_lore"])

    def test_visible_items_fallback_to_items(self, world_pack_loader):
        """Test that visible_items falls back to items if not set."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        context = service.get_context_for_location(
            world_pack_id="test_pack",
            location_id="secret_room",
            discovered_items=set(),
            lang="cn",
        )

        assert "flickering_candle" in context["location"]["visible_items"]


class TestLocationContextServiceFilterNpcLore:
    """Test suite for LocationContextService.filter_npc_lore()."""

    @pytest.fixture
    def pack_with_npc_knowledge(self):
        """Create a pack with NPCs that have location_knowledge."""
        return WorldPack(
            info=WorldPackInfo(
                name=LocalizedString(cn="测试包", en="Test Pack"),
                description=LocalizedString(cn="测试", en="Test"),
            ),
            entries={
                "1": LoreEntry(uid=1, key=["秘密"], content=LocalizedString(cn="秘密1", en="Secret 1")),
                "2": LoreEntry(uid=2, key=["历史"], content=LocalizedString(cn="历史1", en="History 1")),
                "3": LoreEntry(uid=3, key=["宝藏"], content=LocalizedString(cn="宝藏1", en="Treasure 1")),
            },
            npcs={
                "npc_no_restrictions": NPCData(
                    id="npc_no_restrictions",
                    soul=NPCSoul(
                        name="NPC无限制",
                        description=LocalizedString(cn="无限制NPC", en="No restrictions NPC"),
                        personality=["友好"],
                        speech_style=LocalizedString(cn="正常说话", en="Speaks normally"),
                    ),
                    body=NPCBody(
                        location="village",
                        inventory=[],
                        relations={},
                        tags=[],
                        memory={},
                        location_knowledge={},
                    ),
                ),
                "npc_with_knowledge": NPCData(
                    id="npc_with_knowledge",
                    soul=NPCSoul(
                        name="NPC有知识",
                        description=LocalizedString(cn="有知识NPC", en="Knowledgeable NPC"),
                        personality=["睿智"],
                        speech_style=LocalizedString(cn="睿智说话", en="Speaks wisely"),
                    ),
                    body=NPCBody(
                        location="village",
                        inventory=[],
                        relations={},
                        tags=[],
                        memory={},
                        location_knowledge={
                            "village": [1, 2],
                            "forest": [3],
                        },
                    ),
                ),
                "npc_no_knowledge_for_location": NPCData(
                    id="npc_no_knowledge_for_location",
                    soul=NPCSoul(
                        name="NPC无此处知识",
                        description=LocalizedString(cn="无此处知识", en="No knowledge here"),
                        personality=["冷漠"],
                        speech_style=LocalizedString(cn="冷漠说话", en="Speaks coldly"),
                    ),
                    body=NPCBody(
                        location="village",
                        inventory=[],
                        relations={},
                        tags=[],
                        memory={},
                        location_knowledge={
                            "other_location": [1],
                        },
                    ),
                ),
            },
            locations={
                "village": LocationData(
                    id="village",
                    name=LocalizedString(cn="村庄", en="Village"),
                    description=LocalizedString(cn="村庄描述", en="Village desc"),
                    region_id="region1",
                ),
                "forest": LocationData(
                    id="forest",
                    name=LocalizedString(cn="森林", en="Forest"),
                    description=LocalizedString(cn="森林描述", en="Forest desc"),
                    region_id="region1",
                ),
            },
            regions={
                "region1": RegionData(
                    id="region1",
                    name=LocalizedString(cn="区域", en="Region"),
                    description=LocalizedString(cn="描述", en="Desc"),
                    location_ids=["village", "forest"],
                ),
            },
        )

    @pytest.fixture
    def world_pack_loader(self, pack_with_npc_knowledge):
        """Create WorldPackLoader with sample pack."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "packs"
            pack_dir.mkdir()

            pack_path = pack_dir / "test_pack.json"
            pack_path.write_text(pack_with_npc_knowledge.model_dump_json(), encoding="utf-8")

            loader = WorldPackLoader(pack_dir)
            loader.load("test_pack")

            yield loader, Path(tmpdir)

    def test_filter_npc_lore_no_restrictions(self, world_pack_loader):
        """Test NPC with empty location_knowledge returns all lore."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        lore = service.filter_npc_lore(
            npc_id="npc_no_restrictions",
            location_id="village",
            world_pack_id="test_pack",
            lang="cn",
        )

        assert len(lore) == 3
        assert all(isinstance(e, LoreEntry) for e in lore)

    def test_filter_npc_lore_with_knowledge(self, world_pack_loader):
        """Test NPC with location_knowledge returns filtered lore."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        lore = service.filter_npc_lore(
            npc_id="npc_with_knowledge",
            location_id="village",
            world_pack_id="test_pack",
            lang="cn",
        )

        assert len(lore) == 2
        uids = [e.uid for e in lore]
        assert 1 in uids
        assert 2 in uids
        assert 3 not in uids

    def test_filter_npc_lore_for_different_location(self, world_pack_loader):
        """Test filtering for a different location returns different lore."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        lore = service.filter_npc_lore(
            npc_id="npc_with_knowledge",
            location_id="forest",
            world_pack_id="test_pack",
            lang="cn",
        )

        assert len(lore) == 1
        assert lore[0].uid == 3

    def test_filter_npc_lore_no_knowledge_for_location(self, world_pack_loader):
        """Test NPC with no knowledge for location returns empty list."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        lore = service.filter_npc_lore(
            npc_id="npc_no_knowledge_for_location",
            location_id="village",
            world_pack_id="test_pack",
            lang="cn",
        )

        assert len(lore) == 0

    def test_filter_npc_lore_nonexistent_npc(self, world_pack_loader):
        """Test filtering with non-existent NPC returns empty list."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        lore = service.filter_npc_lore(
            npc_id="nonexistent_npc",
            location_id="village",
            world_pack_id="test_pack",
            lang="cn",
        )

        assert len(lore) == 0


class TestLocationContextServiceCheckItemDiscovery:
    """Test suite for LocationContextService.check_item_discovery()."""

    @pytest.fixture
    def pack_with_items(self):
        """Create a pack with items in locations."""
        return WorldPack(
            info=WorldPackInfo(
                name=LocalizedString(cn="测试包", en="Test Pack"),
                description=LocalizedString(cn="测试", en="Test"),
            ),
            entries={},
            npcs={},
            locations={
                "room": LocationData(
                    id="room",
                    name=LocalizedString(cn="房间", en="Room"),
                    description=LocalizedString(cn="房间描述", en="Room desc"),
                    visible_items=["table", "chair"],
                    hidden_items=["secret_box", "hidden_door"],
                ),
            },
        )

    @pytest.fixture
    def world_pack_loader(self, pack_with_items):
        """Create WorldPackLoader with sample pack."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "packs"
            pack_dir.mkdir()

            pack_path = pack_dir / "test_pack.json"
            pack_path.write_text(pack_with_items.model_dump_json(), encoding="utf-8")

            loader = WorldPackLoader(pack_dir)
            loader.load("test_pack")

            yield loader, Path(tmpdir)

    def test_visible_item_not_hidden(self, world_pack_loader):
        """Test that visible items are not marked as hidden."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        result = service.check_item_discovery(
            location_id="room",
            world_pack_id="test_pack",
            item_id="table",
            discovered_items=set(),
        )

        assert result["is_hidden"] is False
        assert result["is_discovered"] is False
        assert result["requires_check"] is False

    def test_hidden_item_undiscovered(self, world_pack_loader):
        """Test that undiscovered hidden items require check."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        result = service.check_item_discovery(
            location_id="room",
            world_pack_id="test_pack",
            item_id="secret_box",
            discovered_items=set(),
        )

        assert result["is_hidden"] is True
        assert result["is_discovered"] is False
        assert result["requires_check"] is True

    def test_hidden_item_discovered(self, world_pack_loader):
        """Test that discovered hidden items are marked as discovered."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        result = service.check_item_discovery(
            location_id="room",
            world_pack_id="test_pack",
            item_id="secret_box",
            discovered_items={"secret_box"},
        )

        assert result["is_hidden"] is True
        assert result["is_discovered"] is True
        assert result["requires_check"] is False

    def test_nonexistent_location(self, world_pack_loader):
        """Test that non-existent location returns default values."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        result = service.check_item_discovery(
            location_id="nonexistent",
            world_pack_id="test_pack",
            item_id="item",
            discovered_items=set(),
        )

        assert result["is_hidden"] is False
        assert result["is_discovered"] is False
        assert result["requires_check"] is False


class TestLocationContextServiceEmptyContext:
    """Test suite for empty context helper."""

    @pytest.fixture
    def world_pack_loader(self):
        """Create empty loader."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "packs"
            pack_dir.mkdir()

            loader = WorldPackLoader(pack_dir)

            yield loader, Path(tmpdir)

    def test_empty_context_structure(self, world_pack_loader):
        """Test that _empty_context returns correct structure."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        context = service._empty_context()

        assert context["region"]["id"] == "_global"
        assert context["region"]["name"] == "Unknown"
        assert context["region"]["narrative_tone"] == ""
        assert context["region"]["atmosphere_keywords"] == []

        assert context["location"]["id"] == ""
        assert context["location"]["name"] == "Unknown"
        assert context["location"]["description"] == ""
        assert context["location"]["visible_items"] == []
        assert context["location"]["hidden_items_revealed"] == []
        assert context["location"]["hidden_items_remaining"] == []

        assert context["basic_lore"] == []
        assert context["atmosphere_guidance"] == ""


class TestLocationContextServiceAtmosphereGuidance:
    """Test suite for atmosphere guidance building."""

    @pytest.fixture
    def world_pack_loader(self):
        """Create empty loader."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "packs"
            pack_dir.mkdir()

            loader = WorldPackLoader(pack_dir)

            yield loader, Path(tmpdir)

    def test_atmosphere_guidance_with_region_and_location(self, world_pack_loader):
        """Test atmosphere guidance with both region and location data."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        region_context = {
            "id": "region1",
            "name": "北部地区",
            "narrative_tone": "寒冷而神秘",
            "atmosphere_keywords": ["snow", "mysterious"],
        }
        location_context = {
            "id": "village",
            "name": "村庄",
            "description": "描述",
            "atmosphere": "宁静",
            "visible_items": [],
        }

        guidance_cn = service._build_atmosphere_guidance(
            region_context, location_context, "cn"
        )

        assert "寒冷而神秘" in guidance_cn
        assert "宁静" in guidance_cn
        assert "snow" in guidance_cn or "mysterious" in guidance_cn

    def test_atmosphere_guidance_empty(self, world_pack_loader):
        """Test that empty guidance returns empty string."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        guidance = service._build_atmosphere_guidance({}, {}, "cn")

        assert guidance == ""

    def test_atmosphere_guidance_english(self, world_pack_loader):
        """Test that English keywords label is used."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        region_context = {
            "id": "region1",
            "name": "Northern Region",
            "narrative_tone": "cold and mysterious",
            "atmosphere_keywords": ["snow", "mysterious"],
        }
        location_context = {
            "id": "village",
            "name": "Village",
            "description": "desc",
            "atmosphere": "peaceful",
            "visible_items": [],
        }

        guidance_en = service._build_atmosphere_guidance(
            region_context, location_context, "en"
        )

        assert "cold and mysterious" in guidance_en
        assert "peaceful" in guidance_en
        assert "Atmosphere keywords" in guidance_en


class TestLocationContextServiceIntegration:
    """Integration tests for LocationContextService."""

    @pytest.fixture
    def full_pack(self):
        """Create a complete world pack for integration testing."""
        return WorldPack(
            info=WorldPackInfo(
                name=LocalizedString(cn="集成测试包", en="Integration Test Pack"),
                description=LocalizedString(cn="用于集成测试", en="For integration testing"),
            ),
            entries={
                "1": LoreEntry(
                    uid=1,
                    key=["古代"],
                    content=LocalizedString(cn="古代文明遗址", en="Ancient civilization ruins"),
                    order=1,
                    constant=False,
                    visibility="basic",
                ),
                "2": LoreEntry(
                    uid=2,
                    key=["宝藏"],
                    content=LocalizedString(cn="传说中的宝藏", en="Legendary treasure"),
                    order=2,
                    constant=False,
                    visibility="detailed",
                    applicable_locations=["treasure_room"],
                ),
                "3": LoreEntry(
                    uid=3,
                    key=["守卫"],
                    content=LocalizedString(cn="无形的守卫保护着这里", en="Invisible guardians protect this place"),
                    order=3,
                    constant=False,
                    visibility="basic",
                    applicable_regions=["temple_district"],
                ),
            },
            npcs={
                "guardian": NPCData(
                    id="guardian",
                    soul=NPCSoul(
                        name="神殿守卫",
                        description=LocalizedString(cn="无形的存在", en="An invisible presence"),
                        personality=["警觉", "神秘"],
                        speech_style=LocalizedString(cn="空灵的声音", en="Ethereal voice"),
                    ),
                    body=NPCBody(
                        location="temple_entrance",
                        inventory=[],
                        relations={},
                        tags=[],
                        memory={},
                        location_knowledge={
                            "temple_entrance": [1, 3],
                            "treasure_room": [1, 2, 3],
                        },
                    ),
                ),
            },
            locations={
                "village_square": LocationData(
                    id="village_square",
                    name=LocalizedString(cn="村庄广场", en="Village Square"),
                    description=LocalizedString(cn="村庄的中心广场", en="The central square of the village"),
                    atmosphere=LocalizedString(cn="喧闹繁忙", en="Busy and bustling"),
                    connected_locations=["temple_entrance"],
                    present_npc_ids=[],
                    items=["fountain", "statue"],
                    region_id="village_district",
                    visible_items=["fountain", "statue"],
                    hidden_items=[],
                    lore_tags=["history"],
                ),
                "temple_entrance": LocationData(
                    id="temple_entrance",
                    name=LocalizedString(cn="神殿入口", en="Temple Entrance"),
                    description=LocalizedString(cn="古老神殿的入口", en="Entrance to the ancient temple"),
                    atmosphere=LocalizedString(cn="庄严神圣", en="Solemn and sacred"),
                    connected_locations=["village_square", "treasure_room"],
                    present_npc_ids=["guardian"],
                    items=["altar"],
                    region_id="temple_district",
                    visible_items=["altar"],
                    hidden_items=["hidden_lever"],
                    lore_tags=["religion", "ancient"],
                ),
                "treasure_room": LocationData(
                    id="treasure_room",
                    name=LocalizedString(cn="宝藏室", en="Treasure Room"),
                    description=LocalizedString(cn="藏宝室", en="The treasure chamber"),
                    atmosphere=LocalizedString(cn="金光闪闪", en="Glorious and golden"),
                    connected_locations=["temple_entrance"],
                    present_npc_ids=[],
                    items=[],
                    region_id="temple_district",
                    visible_items=["gold_coins"],
                    hidden_items=["sacred_gem"],
                    lore_tags=["treasure"],
                ),
            },
            regions={
                "village_district": RegionData(
                    id="village_district",
                    name=LocalizedString(cn="村庄区", en="Village District"),
                    description=LocalizedString(cn="村民居住的区域", en="The residential area of the village"),
                    narrative_tone=LocalizedString(cn="温馨舒适", en="Cozy and comfortable"),
                    atmosphere_keywords=["homey", "peaceful", "bustling"],
                    location_ids=["village_square"],
                    tags=["civilian"],
                ),
                "temple_district": RegionData(
                    id="temple_district",
                    name=LocalizedString(cn="神殿区", en="Temple District"),
                    description=LocalizedString(cn="神圣的神殿区域", en="The sacred temple area"),
                    narrative_tone=LocalizedString(cn="庄严神秘", en="Solemn and mysterious"),
                    atmosphere_keywords=["holy", "mysterious", "ancient"],
                    location_ids=["temple_entrance", "treasure_room"],
                    tags=["religious", "sacred"],
                ),
            },
        )

    @pytest.fixture
    def world_pack_loader(self, full_pack):
        """Create WorldPackLoader with full pack."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_dir = Path(tmpdir) / "packs"
            pack_dir.mkdir()

            pack_path = pack_dir / "integration_pack.json"
            pack_path.write_text(full_pack.model_dump_json(), encoding="utf-8")

            loader = WorldPackLoader(pack_dir)
            loader.load("integration_pack")

            yield loader, Path(tmpdir)

    def test_integration_full_context_flow(self, world_pack_loader):
        """Test complete context flow from location to lore."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        context = service.get_context_for_location(
            world_pack_id="integration_pack",
            location_id="temple_entrance",
            discovered_items=set(),
            lang="en",
        )

        assert context["region"]["name"] == "Temple District"
        assert context["location"]["name"] == "Temple Entrance"
        assert "altar" in context["location"]["visible_items"]
        assert "hidden_lever" in context["location"]["hidden_items_remaining"]
        assert len(context["basic_lore"]) >= 2

    def test_integration_npc_lore_filtering(self, world_pack_loader):
        """Test NPC lore filtering integration."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        lore = service.filter_npc_lore(
            npc_id="guardian",
            location_id="treasure_room",
            world_pack_id="integration_pack",
            lang="en",
        )

        assert len(lore) == 3
        uids = [e.uid for e in lore]
        assert 1 in uids
        assert 2 in uids
        assert 3 in uids

    def test_integration_item_discovery_flow(self, world_pack_loader):
        """Test item discovery state transitions."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        context_before = service.get_context_for_location(
            world_pack_id="integration_pack",
            location_id="temple_entrance",
            discovered_items=set(),
            lang="en",
        )

        assert "hidden_lever" in context_before["location"]["hidden_items_remaining"]

        discovered = {"hidden_lever"}
        context_after = service.get_context_for_location(
            world_pack_id="integration_pack",
            location_id="temple_entrance",
            discovered_items=discovered,
            lang="en",
        )

        assert "hidden_lever" in context_after["location"]["hidden_items_revealed"]
        assert "hidden_lever" not in context_after["location"]["hidden_items_remaining"]

    def test_integration_region_affects_all_locations(self, world_pack_loader):
        """Test that region atmosphere affects all locations in it."""
        loader, _ = world_pack_loader
        service = LocationContextService(loader)

        context_entrance = service.get_context_for_location(
            world_pack_id="integration_pack",
            location_id="temple_entrance",
            discovered_items=set(),
            lang="en",
        )

        context_treasure = service.get_context_for_location(
            world_pack_id="integration_pack",
            location_id="treasure_room",
            discovered_items=set(),
            lang="en",
        )

        assert context_entrance["region"]["id"] == context_treasure["region"]["id"]
        assert context_entrance["region"]["narrative_tone"] == context_treasure["region"]["narrative_tone"]
        assert "holy" in context_entrance["atmosphere_guidance"]
        assert "holy" in context_treasure["atmosphere_guidance"]
