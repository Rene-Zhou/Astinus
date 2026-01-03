"""Tests for narrative graph and scene management."""

import pytest

from src.backend.models.narrative import (
    NarrativeGraph,
    Scene,
    SceneType,
    SceneTransition,
    TransitionCondition,
)


class TestScene:
    """Test suite for Scene model."""

    def test_create_basic_scene(self):
        """Test creating a basic scene."""
        scene = Scene(
            id="study",
            name="书房",
            type=SceneType.LOCATION,
            description="一间古老的书房",
        )

        assert scene.id == "study"
        assert scene.name == "书房"
        assert scene.type == SceneType.LOCATION
        assert scene.description == "一间古老的书房"
        assert len(scene.narrative_state) == 0
        assert len(scene.active_npcs) == 0

    def test_scene_narrative_flags(self):
        """Test narrative flag management."""
        scene = Scene(
            id="test",
            name="测试场景",
            type=SceneType.LOCATION,
        )

        # Set flags
        scene.add_narrative_flag("door_unlocked", True)
        scene.add_narrative_flag("treasure_found", False)

        # Check flags
        assert scene.has_narrative_flag("door_unlocked", True) is True
        assert scene.has_narrative_flag("door_unlocked", False) is False
        assert scene.has_narrative_flag("treasure_found", False) is True
        assert scene.has_narrative_flag("nonexistent") is False

    def test_scene_npc_management(self):
        """Test NPC presence in scenes."""
        scene = Scene(
            id="hall",
            name="大厅",
            type=SceneType.LOCATION,
        )

        # Add NPCs
        scene.add_npc("chen_ling")
        scene.add_npc("old_guard")

        assert "chen_ling" in scene.active_npcs
        assert "old_guard" in scene.active_npcs
        assert len(scene.active_npcs) == 2

        # Remove NPC
        scene.remove_npc("chen_ling")
        assert "chen_ling" not in scene.active_npcs
        assert len(scene.active_npcs) == 1

    def test_scene_transitions(self):
        """Test scene transitions."""
        scene = Scene(
            id="entrance",
            name="入口",
            type=SceneType.LOCATION,
        )

        # Add transitions
        scene.add_transition(
            SceneTransition(
                target_scene_id="hall",
                description="走进大厅",
            )
        )
        scene.add_transition(
            SceneTransition(
                target_scene_id="study",
                condition=TransitionCondition(
                    type="flag",
                    key="has_key",
                    value=True,
                ),
                description="用钥匙开门进入书房",
            )
        )

        assert len(scene.transitions) == 2
        assert scene.can_transition_to("hall") is True
        assert scene.can_transition_to("study") is True
        assert scene.can_transition_to("nonexistent") is False


class TestNarrativeGraph:
    """Test suite for NarrativeGraph model."""

    @pytest.fixture
    def sample_graph(self):
        """Create a sample narrative graph."""
        graph = NarrativeGraph(world_pack_id="test_pack")

        # Add scenes
        graph.add_scene(
            Scene(
                id="village",
                name="村庄",
                type=SceneType.LOCATION,
                description="一个平静的小村庄",
            )
        )
        graph.add_scene(
            Scene(
                id="forest",
                name="森林",
                type=SceneType.LOCATION,
                description="茂密的森林",
            )
        )
        graph.add_scene(
            Scene(
                id="cave",
                name="洞穴",
                type=SceneType.LOCATION,
                description="黑暗的洞穴",
            )
        )

        # Set current scene
        graph.set_current_scene("village")

        return graph

    def test_graph_creation(self, sample_graph):
        """Test creating a narrative graph."""
        assert sample_graph.world_pack_id == "test_pack"
        assert sample_graph.get_scene_count() == 3

    def test_get_scene(self, sample_graph):
        """Test getting scenes by ID."""
        village = sample_graph.get_scene("village")
        assert village is not None
        assert village.name == "村庄"

        nonexistent = sample_graph.get_scene("nonexistent")
        assert nonexistent is None

    def test_set_current_scene(self, sample_graph):
        """Test setting the current scene."""
        assert sample_graph.current_scene_id == "village"

        # Valid transition
        assert sample_graph.set_current_scene("forest") is True
        assert sample_graph.current_scene_id == "forest"

        # Invalid transition (scene doesn't exist)
        assert sample_graph.set_current_scene("nonexistent") is False
        assert sample_graph.current_scene_id == "forest"  # Unchanged

    def test_get_current_scene(self, sample_graph):
        """Test getting the current scene."""
        scene = sample_graph.get_current_scene()
        assert scene is not None
        assert scene.id == "village"
        assert scene.name == "村庄"

    def test_transition_to(self, sample_graph):
        """Test transitioning between scenes."""
        # Add transitions first
        village = sample_graph.get_scene("village")
        village.add_transition(SceneTransition(target_scene_id="forest"))

        forest = sample_graph.get_scene("forest")
        forest.add_transition(SceneTransition(target_scene_id="cave"))

        # Valid transition
        assert sample_graph.transition_to("forest") is True
        assert sample_graph.current_scene_id == "forest"

        # Another valid transition
        assert sample_graph.transition_to("cave") is True
        assert sample_graph.current_scene_id == "cave"

        # Invalid transition (no transition defined from cave)
        assert sample_graph.transition_to("village") is False
        assert sample_graph.current_scene_id == "cave"  # Unchanged

    def test_global_narrative_flags(self, sample_graph):
        """Test global narrative flag management."""
        # Set flags
        sample_graph.set_global_flag("quest_started", True)
        sample_graph.set_global_flag("player_level", 3)

        # Check flags
        assert sample_graph.has_global_flag("quest_started", True) is True
        assert sample_graph.has_global_flag("player_level", 3) is True
        assert sample_graph.has_global_flag("player_level", 2) is False
        assert sample_graph.has_global_flag("nonexistent") is False

        # Get flag value
        assert sample_graph.get_global_flag("quest_started") is True
        assert sample_graph.get_global_flag("nonexistent", "default") == "default"

    def test_list_scenes_by_type(self, sample_graph):
        """Test filtering scenes by type."""
        # Add different types
        sample_graph.add_scene(
            Scene(
                id="dialogue_chen",
                name="与陈玲对话",
                type=SceneType.DIALOGUE,
            )
        )
        sample_graph.add_scene(
            Scene(
                id="encounter_wolf",
                name="遭遇狼群",
                type=SceneType.ENCOUNTER,
            )
        )

        locations = sample_graph.list_scenes_by_type(SceneType.LOCATION)
        assert len(locations) == 3
        assert all(s.type == SceneType.LOCATION for s in locations)

        dialogues = sample_graph.list_scenes_by_type(SceneType.DIALOGUE)
        assert len(dialogues) == 1
        assert dialogues[0].id == "dialogue_chen"

    def test_scene_count(self, sample_graph):
        """Test getting scene count."""
        assert sample_graph.get_scene_count() == 3

        # Add another scene
        sample_graph.add_scene(
            Scene(
                id="tower",
                name="高塔",
                type=SceneType.LOCATION,
            )
        )
        assert sample_graph.get_scene_count() == 4


class TestSceneTransition:
    """Test suite for SceneTransition model."""

    def test_create_basic_transition(self):
        """Test creating a basic transition."""
        transition = SceneTransition(
            target_scene_id="study",
            description="进入书房",
        )

        assert transition.target_scene_id == "study"
        assert transition.condition is None
        assert transition.description == "进入书房"

    def test_create_conditional_transition(self):
        """Test creating a conditional transition."""
        transition = SceneTransition(
            target_scene_id="treasure_room",
            condition=TransitionCondition(
                type="item",
                key="golden_key",
                value=True,
            ),
            description="使用金钥匙打开宝藏室",
        )

        assert transition.target_scene_id == "treasure_room"
        assert transition.condition is not None
        assert transition.condition.type == "item"
        assert transition.condition.key == "golden_key"
        assert transition.condition.value is True
        assert "金钥匙" in transition.description


class TestTransitionCondition:
    """Test suite for TransitionCondition model."""

    def test_create_flag_condition(self):
        """Test creating a flag condition."""
        condition = TransitionCondition(
            type="flag",
            key="door_unlocked",
            value=True,
        )

        assert condition.type == "flag"
        assert condition.key == "door_unlocked"
        assert condition.value is True

    def test_create_item_condition(self):
        """Test creating an item condition."""
        condition = TransitionCondition(
            type="item",
            key="magic_sword",
            value=True,
        )

        assert condition.type == "item"
        assert condition.key == "magic_sword"
        assert condition.value is True
