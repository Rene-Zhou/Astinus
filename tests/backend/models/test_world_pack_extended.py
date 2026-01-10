"""Tests for extended WorldPack models (RegionData, extended LoreEntry, etc.)."""

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


class TestRegionData:
    """Test suite for RegionData model."""

    def test_create_basic_region(self):
        """Test creating a basic region."""
        region = RegionData(
            id="forest_region",
            name=LocalizedString(cn="森林区域", en="Forest Region"),
            description=LocalizedString(cn="一片茂密的森林", en="A dense forest"),
        )

        assert region.id == "forest_region"
        assert region.name.get("cn") == "森林区域"
        assert region.name.get("en") == "Forest Region"
        assert region.narrative_tone is None
        assert region.atmosphere_keywords == []
        assert region.location_ids == []
        assert region.tags == []

    def test_create_region_with_atmosphere(self):
        """Test creating a region with atmosphere."""
        region = RegionData(
            id="dungeon",
            name=LocalizedString(cn="地下城", en="Dungeon"),
            description=LocalizedString(cn="阴暗的地下洞穴", en="Dark underground cave"),
            narrative_tone=LocalizedString(cn="恐怖压抑", en="Terrifying and oppressive"),
            atmosphere_keywords=["dark", "damp", "scary"],
            location_ids=["entrance", "hall", "treasure_room"],
            tags=["dungeon", "dangerous"],
        )

        assert region.narrative_tone.get("cn") == "恐怖压抑"
        assert region.atmosphere_keywords == ["dark", "damp", "scary"]
        assert len(region.location_ids) == 3
        assert "dangerous" in region.tags

    def test_region_serialization(self):
        """Test region model serialization."""
        region = RegionData(
            id="test_region",
            name=LocalizedString(cn="测试区域", en="Test Region"),
            description=LocalizedString(cn="测试描述", en="Test description"),
            narrative_tone=LocalizedString(cn="测试基调", en="Test tone"),
            atmosphere_keywords=["test", "demo"],
        )

        data = region.model_dump()
        assert data["id"] == "test_region"
        assert data["name"]["cn"] == "测试区域"
        assert data["narrative_tone"]["cn"] == "测试基调"
        assert data["atmosphere_keywords"] == ["test", "demo"]


class TestLoreEntryExtended:
    """Test suite for extended LoreEntry fields."""

    def test_create_entry_with_visibility(self):
        """Test creating an entry with visibility tier."""
        entry = LoreEntry(
            uid=1,
            key=["秘密"],
            content=LocalizedString(cn="隐藏的秘密", en="Hidden secret"),
            visibility="detailed",
        )

        assert entry.visibility == "detailed"
        assert entry.applicable_regions == []
        assert entry.applicable_locations == []

    def test_create_entry_with_location_filter(self):
        """Test creating an entry with location filtering."""
        entry = LoreEntry(
            uid=2,
            key=["宝藏"],
            content=LocalizedString(cn="宝箱的位置", en="Chest location"),
            applicable_locations=["treasure_room"],
        )

        assert entry.applicable_locations == ["treasure_room"]
        assert entry.applicable_regions == []

    def test_create_entry_with_region_filter(self):
        """Test creating an entry with region filtering."""
        entry = LoreEntry(
            uid=3,
            key=["守卫"],
            content=LocalizedString(cn="区域守卫", en="Regional guardian"),
            applicable_regions=["temple_district"],
        )

        assert entry.applicable_regions == ["temple_district"]
        assert entry.applicable_locations == []

    def test_create_global_entry(self):
        """Test creating a global entry (no restrictions)."""
        entry = LoreEntry(
            uid=4,
            key=["世界观"],
            content=LocalizedString(cn="世界观背景", en="World background"),
        )

        assert entry.visibility == "basic"
        assert entry.applicable_regions == []
        assert entry.applicable_locations == []

    def test_create_entry_with_all_filters(self):
        """Test creating an entry with all filters."""
        entry = LoreEntry(
            uid=5,
            key=["特殊"],
            content=LocalizedString(cn="特殊内容", en="Special content"),
            visibility="detailed",
            applicable_regions=["region1"],
            applicable_locations=["location1"],
        )

        assert entry.visibility == "detailed"
        assert entry.applicable_regions == ["region1"]
        assert entry.applicable_locations == ["location1"]

    def test_lore_entry_defaults(self):
        """Test that LoreEntry has correct defaults."""
        entry = LoreEntry(
            uid=6,
            key=["测试"],
            content=LocalizedString(cn="测试内容", en="Test content"),
        )

        assert entry.constant is False
        assert entry.selective is True
        assert entry.order == 100
        assert entry.visibility == "basic"
        assert entry.applicable_regions == []
        assert entry.applicable_locations == []


class TestNPCBodyExtended:
    """Test suite for extended NPCBody fields."""

    def test_create_body_with_empty_location_knowledge(self):
        """Test creating a body with empty location_knowledge (backward compatible)."""
        body = NPCBody(
            location="village",
            inventory=["sword"],
            relations={},
            tags=[],
            memory={},
            location_knowledge={},
        )

        assert body.location_knowledge == {}

    def test_create_body_with_location_knowledge(self):
        """Test creating a body with location-specific knowledge."""
        body = NPCBody(
            location="library",
            inventory=["book"],
            relations={},
            tags=[],
            memory={},
            location_knowledge={
                "library": [1, 2, 3],
                "secret_room": [5, 6],
            },
        )

        assert body.location_knowledge["library"] == [1, 2, 3]
        assert body.location_knowledge["secret_room"] == [5, 6]

    def test_body_without_location_knowledge(self):
        """Test that body without location_knowledge uses default empty dict."""
        body = NPCBody(
            location="square",
            inventory=[],
            relations={},
            tags=[],
            memory={},
        )

        assert body.location_knowledge == {}


class TestNPCDataExtended:
    """Test suite for extended NPCData with location knowledge."""

    def test_npc_with_location_knowledge(self):
        """Test creating an NPC with location-specific knowledge."""
        npc = NPCData(
            id="wise_sage",
            soul=NPCSoul(
                name="智慧老者",
                description=LocalizedString(cn="年迈的智者", en="Elderly sage"),
                personality=["睿智", "耐心"],
                speech_style=LocalizedString(cn="缓慢而有条理", en="Slow and methodical"),
            ),
            body=NPCBody(
                location="tower",
                inventory=["scroll", "potion"],
                relations={},
                tags=["wizard"],
                memory={},
                location_knowledge={
                    "tower": [1, 2],
                    "village": [3],
                },
            ),
        )

        assert npc.id == "wise_sage"
        assert npc.body.location_knowledge["tower"] == [1, 2]
        assert npc.body.location_knowledge["village"] == [3]

    def test_npc_without_location_knowledge_backward_compatible(self):
        """Test NPC without location_knowledge works (backward compatible)."""
        npc = NPCData(
            id="simple_npc",
            soul=NPCSoul(
                name="普通NPC",
                description=LocalizedString(cn="普通人", en="Ordinary person"),
                personality=["友好"],
                speech_style=LocalizedString(cn="正常说话", en="Normal speech"),
            ),
            body=NPCBody(
                location="market",
                inventory=[],
                relations={},
                tags=[],
                memory={},
            ),
        )

        assert npc.body.location_knowledge == {}


class TestLocationDataExtended:
    """Test suite for extended LocationData fields."""

    def test_create_location_with_region(self):
        """Test creating a location with region association."""
        location = LocationData(
            id="village_square",
            name=LocalizedString(cn="村庄广场", en="Village Square"),
            description=LocalizedString(cn="村庄中心", en="Village center"),
            region_id="village_district",
        )

        assert location.region_id == "village_district"

    def test_create_location_without_region(self):
        """Test that location without region_id uses None."""
        location = LocationData(
            id="remote_hut",
            name=LocalizedString(cn="偏远小屋", en="Remote Hut"),
            description=LocalizedString(cn="偏僻的地方", en="A remote place"),
        )

        assert location.region_id is None

    def test_create_location_with_visibility_tiers(self):
        """Test creating a location with visible/hidden items."""
        location = LocationData(
            id="treasure_room",
            name=LocalizedString(cn="藏宝室", en="Treasure Room"),
            description=LocalizedString(cn="装满宝藏的房间", en="Room full of treasure"),
            visible_items=["gold_coins", "silver_goblet"],
            hidden_items=["crown_jewel", "ancient_scepter"],
        )

        assert location.visible_items == ["gold_coins", "silver_goblet"]
        assert location.hidden_items == ["crown_jewel", "ancient_scepter"]

    def test_create_location_with_lore_tags(self):
        """Test creating a location with lore filtering tags."""
        location = LocationData(
            id="ancient_ruins",
            name=LocalizedString(cn="古代遗迹", en="Ancient Ruins"),
            description=LocalizedString(cn="荒废的遗迹", en="Abandoned ruins"),
            lore_tags=["ancient", "mysterious", "dangerous"],
        )

        assert "ancient" in location.lore_tags
        assert "mysterious" in location.lore_tags
        assert "dangerous" in location.lore_tags

    def test_create_location_with_all_extensions(self):
        """Test creating a location with all new fields."""
        location = LocationData(
            id="complex_location",
            name=LocalizedString(cn="复杂地点", en="Complex Location"),
            description=LocalizedString(cn="复杂描述", en="Complex description"),
            atmosphere=LocalizedString(cn="神秘氛围", en="Mysterious atmosphere"),
            region_id="mystic_region",
            visible_items=["visible_item_1"],
            hidden_items=["hidden_item_1"],
            lore_tags=["tag1", "tag2"],
        )

        assert location.atmosphere.get("cn") == "神秘氛围"
        assert location.region_id == "mystic_region"
        assert location.visible_items == ["visible_item_1"]
        assert location.hidden_items == ["hidden_item_1"]
        assert location.lore_tags == ["tag1", "tag2"]


class TestWorldPackNewMethods:
    """Test suite for new WorldPack methods."""

    @pytest.fixture
    def sample_pack(self):
        """Create a sample world pack for testing."""
        return WorldPack(
            info=WorldPackInfo(
                name=LocalizedString(cn="测试包", en="Test Pack"),
                description=LocalizedString(cn="测试", en="Test"),
            ),
            entries={
                "1": LoreEntry(
                    uid=1,
                    key=["全局"],
                    content=LocalizedString(cn="全局内容", en="Global content"),
                    order=1,
                    visibility="basic",
                ),
                "2": LoreEntry(
                    uid=2,
                    key=["区域"],
                    content=LocalizedString(cn="区域内容", en="Region content"),
                    order=2,
                    visibility="basic",
                    applicable_regions=["region1"],
                ),
                "3": LoreEntry(
                    uid=3,
                    key=["地点"],
                    content=LocalizedString(cn="地点内容", en="Location content"),
                    order=3,
                    visibility="basic",
                    applicable_locations=["loc1"],
                ),
                "4": LoreEntry(
                    uid=4,
                    key=["详细"],
                    content=LocalizedString(cn="详细内容", en="Detailed content"),
                    order=4,
                    visibility="detailed",
                    applicable_locations=["loc1"],
                ),
                "100": LoreEntry(
                    uid=100,
                    key=["常量"],
                    content=LocalizedString(cn="常量内容", en="Constant content"),
                    order=0,
                    constant=True,
                    visibility="basic",
                ),
            },
            npcs={},
            locations={
                "loc1": LocationData(
                    id="loc1",
                    name=LocalizedString(cn="地点1", en="Location 1"),
                    description=LocalizedString(cn="描述1", en="Desc 1"),
                    region_id="region1",
                ),
                "loc2": LocationData(
                    id="loc2",
                    name=LocalizedString(cn="地点2", en="Location 2"),
                    description=LocalizedString(cn="描述2", en="Desc 2"),
                    region_id="region2",
                ),
            },
            regions={
                "region1": RegionData(
                    id="region1",
                    name=LocalizedString(cn="区域1", en="Region 1"),
                    description=LocalizedString(cn="区域描述", en="Region desc"),
                    location_ids=["loc1"],
                ),
                "region2": RegionData(
                    id="region2",
                    name=LocalizedString(cn="区域2", en="Region 2"),
                    description=LocalizedString(cn="区域描述2", en="Region desc 2"),
                    location_ids=["loc2"],
                ),
            },
        )

    def test_get_region(self, sample_pack):
        """Test getting a region by ID."""
        region = sample_pack.get_region("region1")

        assert region is not None
        assert region.id == "region1"
        assert region.name.get("cn") == "区域1"

        nonexistent = sample_pack.get_region("nonexistent")
        assert nonexistent is None

    def test_get_location_region(self, sample_pack):
        """Test getting the region containing a location."""
        region = sample_pack.get_location_region("loc1")

        assert region is not None
        assert region.id == "region1"

    def test_get_lore_for_location_basic(self, sample_pack):
        """Test getting basic lore for a location."""
        lore = sample_pack.get_lore_for_location("loc1", visibility="basic")

        assert len(lore) >= 1
        uids = [e.uid for e in lore]
        assert 1 in uids
        assert 100 in uids

    def test_get_lore_for_location_detailed(self, sample_pack):
        """Test getting detailed lore for a location."""
        lore = sample_pack.get_lore_for_location("loc1", visibility="detailed")

        uids = [e.uid for e in lore]
        assert 4 in uids
        assert 3 not in uids

    def test_get_lore_priority_location_first(self, sample_pack):
        """Test that location-specific lore is prioritized."""
        lore = sample_pack.get_lore_for_location("loc1", visibility="basic")

        uids = [e.uid for e in lore]
        assert 3 in uids
        assert 2 in uids
        assert 1 in uids

    def test_get_lore_for_different_location(self, sample_pack):
        """Test getting lore for a different location."""
        lore = sample_pack.get_lore_for_location("loc2", visibility="basic")

        uids = [e.uid for e in lore]
        assert 1 in uids
        assert 2 not in uids
        assert 3 not in uids

    def test_get_lore_sorted_by_order(self, sample_pack):
        """Test that lore is sorted by order."""
        lore = sample_pack.get_lore_for_location("loc1", visibility="basic")

        orders = [e.order for e in lore]
        assert orders == sorted(orders)

    def test_get_lore_constant_always_included(self, sample_pack):
        """Test that constant entries are always included regardless of visibility."""
        lore_basic = sample_pack.get_lore_for_location("loc1", visibility="basic")
        lore_detailed = sample_pack.get_lore_for_location("loc1", visibility="detailed")

        uids_basic = [e.uid for e in lore_basic]
        uids_detailed = [e.uid for e in lore_detailed]

        assert 100 in uids_basic
        assert 100 in uids_detailed


class TestWorldPackBackwardCompatibility:
    """Test suite for backward compatibility with old world packs."""

    def test_pack_without_regions(self):
        """Test that pack without regions still works."""
        pack = WorldPack(
            info=WorldPackInfo(
                name=LocalizedString(cn="旧包", en="Old Pack"),
                description=LocalizedString(cn="没有区域的旧包", en="Old pack without regions"),
            ),
            entries={},
            npcs={},
            locations={
                "old_loc": LocationData(
                    id="old_loc",
                    name=LocalizedString(cn="旧地点", en="Old Location"),
                    description=LocalizedString(cn="描述", en="Desc"),
                    items=["old_item"],
                ),
            },
        )

        assert pack.regions == {}
        assert pack.get_location_region("old_loc") is None

    def test_lore_without_visibility_defaults_to_basic(self):
        """Test that lore without visibility uses default 'basic'."""
        entry = LoreEntry(
            uid=1,
            key=["test"],
            content=LocalizedString(cn="内容", en="Content"),
        )

        assert entry.visibility == "basic"
        assert entry.applicable_regions == []
        assert entry.applicable_locations == []

    def test_npc_without_location_knowledge(self):
        """Test that NPC without location_knowledge uses empty dict."""
        pack = WorldPack(
            info=WorldPackInfo(
                name=LocalizedString(cn="旧包", en="Old Pack"),
                description=LocalizedString(cn="旧NPC", en="Old NPC"),
            ),
            npcs={
                "old_npc": NPCData(
                    id="old_npc",
                    soul=NPCSoul(
                        name="旧NPC",
                        description=LocalizedString(cn="描述", en="Desc"),
                        personality=["普通"],
                        speech_style=LocalizedString(cn="正常", en="Normal"),
                    ),
                    body=NPCBody(
                        location="old_loc",
                        inventory=[],
                        relations={},
                        tags=[],
                        memory={},
                    ),
                ),
            },
        )

        npc = pack.get_npc("old_npc")
        assert npc is not None
        assert npc.body.location_knowledge == {}

    def test_location_without_extensions(self):
        """Test that location without extensions uses defaults."""
        pack = WorldPack(
            info=WorldPackInfo(
                name=LocalizedString(cn="旧包", en="Old Pack"),
                description=LocalizedString(cn="没有扩展的旧包", en="Old pack without extensions"),
            ),
            locations={
                "old_loc": LocationData(
                    id="old_loc",
                    name=LocalizedString(cn="旧地点", en="Old Location"),
                    description=LocalizedString(cn="描述", en="Desc"),
                    items=["item1", "item2"],
                ),
            },
        )

        loc = pack.get_location("old_loc")
        assert loc is not None
        assert loc.region_id is None
        assert loc.visible_items == []
        assert loc.hidden_items == []
        assert loc.lore_tags == []
