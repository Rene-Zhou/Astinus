"""Tests for Narrative Manager."""

from pathlib import Path
import pytest

from src.backend.services.narrative import NarrativeManager
from src.backend.services.world import WorldPackLoader


class TestNarrativeManager:
    """Test suite for Narrative Manager."""

    @pytest.fixture
    def world_loader(self):
        """Create a world pack loader."""
        packs_dir = Path(__file__).parent.parent.parent / "data" / "packs"
        if not (packs_dir / "demo_pack.json").exists():
            pytest.skip("Demo pack not available")
        return WorldPackLoader(packs_dir)

    @pytest.fixture
    def narrative_manager(self, world_loader):
        """Create a narrative manager."""
        return NarrativeManager(world_loader)

    def test_manager_creation(self, narrative_manager):
        """Test NarrativeManager initialization."""
        assert narrative_manager.world_pack_loader is not None
        assert len(narrative_manager.narrative_graphs) == 0
        assert narrative_manager.active_graph is None

    def test_load_world_pack(self, narrative_manager, world_loader):
        """Test loading a world pack."""
        # Load the demo pack
        graph = narrative_manager.load_world_pack("demo_pack")

        assert graph is not None
        assert graph.world_pack_id is not None
        assert narrative_manager.get_scene_count() > 0
        assert narrative_manager.active_graph is not None

    def test_get_current_scene(self, narrative_manager):
        """Test getting the current scene."""
        # Load pack first
        narrative_manager.load_world_pack("demo_pack")

        # Get current scene
        scene = narrative_manager.get_current_scene()

        assert scene is not None
        assert scene.id is not None
        assert scene.name is not None

    def test_transition_to_scene(self, narrative_manager):
        """Test transitioning between scenes."""
        # Load pack
        narrative_manager.load_world_pack("demo_pack")

        # Get list of available scenes
        scene_ids = narrative_manager.list_available_scenes()
        assert len(scene_ids) > 0

        # Try to transition to a different scene
        if len(scene_ids) > 1:
            current = narrative_manager.get_current_scene()
            target_id = [s for s in scene_ids if s != current.id][0]

            success = narrative_manager.transition_to_scene(target_id)
            assert success is True

            new_current = narrative_manager.get_current_scene()
            assert new_current.id == target_id

    def test_get_scene_by_id(self, narrative_manager):
        """Test getting a specific scene by ID."""
        # Load pack
        narrative_manager.load_world_pack("demo_pack")

        # Get available scene IDs
        scene_ids = narrative_manager.list_available_scenes()
        assert len(scene_ids) > 0

        # Get a specific scene
        scene = narrative_manager.get_scene_by_id(scene_ids[0])
        assert scene is not None
        assert scene.id == scene_ids[0]

        # Get non-existent scene
        nonexistent = narrative_manager.get_scene_by_id("nonexistent_scene")
        assert nonexistent is None

    def test_narrative_flags(self, narrative_manager):
        """Test narrative flag management."""
        # Load pack
        narrative_manager.load_world_pack("demo_pack")

        # Set flags
        narrative_manager.set_narrative_flag("quest_started", True)
        narrative_manager.set_narrative_flag("player_level", 3)

        # Check flags
        assert narrative_manager.has_narrative_flag("quest_started", True) is True
        assert narrative_manager.has_narrative_flag("player_level", 3) is True
        assert narrative_manager.has_narrative_flag("nonexistent") is False

        # Get flag values
        assert narrative_manager.get_narrative_flag("quest_started") is True
        assert (
            narrative_manager.get_narrative_flag("nonexistent", "default")
            == "default"
        )

    def test_npc_management(self, narrative_manager):
        """Test NPC management in scenes."""
        # Load pack
        narrative_manager.load_world_pack("demo_pack")

        # Get current scene
        scene = narrative_manager.get_current_scene()
        initial_npc_count = len(scene.active_npcs)

        # Add NPC to scene
        narrative_manager.add_npc_to_scene(scene.id, "chen_ling")
        updated_scene = narrative_manager.get_scene_by_id(scene.id)
        assert "chen_ling" in updated_scene.active_npcs

        # Remove NPC from scene
        narrative_manager.remove_npc_from_scene(scene.id, "chen_ling")
        final_scene = narrative_manager.get_scene_by_id(scene.id)
        assert "chen_ling" not in final_scene.active_npcs

    def test_get_scene_count(self, narrative_manager):
        """Test getting scene count."""
        # Initially zero
        assert narrative_manager.get_scene_count() == 0

        # After loading pack
        narrative_manager.load_world_pack("demo_pack")
        count = narrative_manager.get_scene_count()
        assert count > 0

    def test_list_available_scenes(self, narrative_manager):
        """Test listing all scene IDs."""
        # Initially empty
        assert narrative_manager.list_available_scenes() == []

        # After loading pack
        narrative_manager.load_world_pack("demo_pack")
        scene_ids = narrative_manager.list_available_scenes()
        assert len(scene_ids) > 0
        assert all(isinstance(sid, str) for sid in scene_ids)

    def test_get_active_world_pack_id(self, narrative_manager):
        """Test getting the active world pack ID."""
        # Initially None
        assert narrative_manager.get_active_world_pack_id() is None

        # After loading
        narrative_manager.load_world_pack("demo_pack")
        pack_id = narrative_manager.get_active_world_pack_id()
        assert pack_id is not None

    def test_switch_to_graph(self, narrative_manager, world_loader):
        """Test switching between narrative graphs."""
        # Load first pack
        narrative_manager.load_world_pack("demo_pack")
        first_graph = narrative_manager.active_graph
        first_scene_count = narrative_manager.get_scene_count()

        # Create and cache another graph (simulate loading different pack)
        # For this test, we'll just verify switching doesn't break
        if first_scene_count > 0:
            # Switch to same graph (only one loaded)
            success = narrative_manager.switch_to_graph("demo_pack")
            assert success is True
            assert narrative_manager.active_graph == first_graph

        # Try to switch to non-existent graph
        success = narrative_manager.switch_to_graph("nonexistent_pack")
        assert success is False

    def test_scene_types_in_graph(self, narrative_manager):
        """Test that different scene types are created."""
        # Load pack
        narrative_manager.load_world_pack("demo_pack")

        # Check that we have location scenes
        from src.backend.models.narrative import SceneType

        graph = narrative_manager.active_graph
        location_scenes = graph.list_scenes_by_type(SceneType.LOCATION)
        assert len(location_scenes) > 0

        # Check that we have NPC dialogue scenes
        dialogue_scenes = graph.list_scenes_by_type(SceneType.DIALOGUE)
        assert len(dialogue_scenes) > 0
