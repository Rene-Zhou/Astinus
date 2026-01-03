"""
Narrative scene management service.

Handles scene transitions, narrative state updates, and story flow control.
Integrates with WorldPackLoader and NarrativeGraph to manage the game's story.
"""

from typing import Any

from src.backend.models.narrative import (
    NarrativeGraph,
    Scene,
    SceneTransition,
    SceneType,
)
from src.backend.models.world_pack import WorldPack, LocationData


class NarrativeManager:
    """
    Manages narrative flow and scene transitions.

    Provides high-level API for:
    - Loading narrative graphs from world packs
    - Transitioning between scenes
    - Tracking narrative state
    - Managing NPC presence in scenes

    Examples:
        >>> manager = NarrativeManager(world_loader)
        >>> manager.load_world_pack("demo_pack")
        >>> scene = manager.get_current_scene()
        >>> manager.transition_to("secret_room")
    """

    def __init__(self, world_pack_loader):
        """
        Initialize narrative manager.

        Args:
            world_pack_loader: WorldPackLoader instance
        """
        self.world_pack_loader = world_pack_loader
        self.narrative_graphs: dict[str, NarrativeGraph] = {}
        self.active_graph: NarrativeGraph | None = None

    def load_world_pack(self, world_pack_id: str) -> NarrativeGraph:
        """
        Load a world pack and create its narrative graph.

        Args:
            world_pack_id: ID of the world pack to load

        Returns:
            Created NarrativeGraph

        Raises:
            FileNotFoundError: If world pack doesn't exist
        """
        # Load the world pack
        world_pack = self.world_pack_loader.load(world_pack_id)

        # Create narrative graph from world pack
        narrative_graph = self._create_narrative_graph_from_pack(world_pack)

        # Store in cache
        self.narrative_graphs[world_pack_id] = narrative_graph

        # Set as active if none exists
        if self.active_graph is None:
            self.active_graph = narrative_graph

        return narrative_graph

    def _create_narrative_graph_from_pack(self, world_pack: WorldPack) -> NarrativeGraph:
        """
        Create a NarrativeGraph from a WorldPack.

        Args:
            world_pack: Loaded WorldPack

        Returns:
            NarrativeGraph with scenes from the pack
        """
        graph = NarrativeGraph(world_pack_id=world_pack.info.name.get("cn"))

        # Convert locations to scenes
        for location_id, location_data in world_pack.locations.items():
            scene = self._location_to_scene(location_id, location_data)
            graph.add_scene(scene)

        # Convert NPCs to scenes (NPC interaction scenes)
        for npc_id, npc_data in world_pack.npcs.items():
            scene = self._npc_to_scene(npc_id, npc_data)
            graph.add_scene(scene)

        # Set initial scene (usually first location or a specific start location)
        start_location = world_pack.locations.get("village") or next(
            iter(world_pack.locations.values()), None
        )
        if start_location:
            graph.set_current_scene(start_location.id)

        return graph

    def _location_to_scene(self, location_id: str, location: LocationData) -> Scene:
        """
        Convert a LocationData to a Scene.

        Args:
            location_id: Location identifier
            location: Location data

        Returns:
            Scene instance
        """
        return Scene(
            id=location_id,
            name=location.name.get("cn"),
            type=SceneType.LOCATION,
            description=location.description.get("cn"),
            active_npcs=location.present_npc_ids.copy(),
            available_actions=["观察", "移动", "互动"],
            transitions=[
                # Create transitions to connected locations
                *[
                    SceneTransition(target_scene_id=connected_id)
                    for connected_id in location.connected_locations
                ]
            ],
        )

    def _npc_to_scene(self, npc_id: str, npc_data) -> Scene:
        """
        Convert NPCData to an interaction scene.

        Args:
            npc_id: NPC identifier
            npc_data: NPC data

        Returns:
            Scene instance for NPC interaction
        """
        return Scene(
            id=f"npc_{npc_id}",
            name=f"与{npc_data.soul.name}对话",
            type=SceneType.DIALOGUE,
            description=f"与{npc_data.soul.name}进行对话",
            active_npcs=[npc_id],
            available_actions=["对话", "询问", "告别"],
            transitions=[
                # Transition back to location where NPC is
                SceneTransition(target_scene_id=npc_data.body.location)
            ],
        )

    def get_current_scene(self) -> Scene | None:
        """
        Get the currently active scene.

        Returns:
            Current Scene or None if no active graph
        """
        if self.active_graph:
            return self.active_graph.get_current_scene()
        return None

    def transition_to_scene(self, target_scene_id: str) -> bool:
        """
        Transition to a new scene.

        Args:
            target_scene_id: ID of scene to transition to

        Returns:
            True if transition was successful
        """
        if not self.active_graph:
            return False

        success = self.active_graph.transition_to(target_scene_id)
        return success

    def get_scene_by_id(self, scene_id: str) -> Scene | None:
        """
        Get a scene by ID from the active graph.

        Args:
            scene_id: Scene identifier

        Returns:
            Scene or None if not found
        """
        if self.active_graph:
            return self.active_graph.get_scene(scene_id)
        return None

    def set_narrative_flag(self, key: str, value: Any) -> None:
        """
        Set a global narrative flag.

        Args:
            key: Flag name
            value: Flag value
        """
        if self.active_graph:
            self.active_graph.set_global_flag(key, value)

    def get_narrative_flag(self, key: str, default: Any = None) -> Any:
        """
        Get a global narrative flag.

        Args:
            key: Flag name
            default: Default value if flag not set

        Returns:
            Flag value or default
        """
        if self.active_graph:
            return self.active_graph.get_global_flag(key, default)
        return default

    def has_narrative_flag(self, key: str, expected_value: Any = None) -> bool:
        """
        Check if a narrative flag exists.

        Args:
            key: Flag name
            expected_value: Optional expected value

        Returns:
            True if flag exists (and matches expected value if provided)
        """
        if self.active_graph:
            return self.active_graph.has_global_flag(key, expected_value)
        return False

    def add_npc_to_scene(self, scene_id: str, npc_id: str) -> None:
        """
        Add an NPC to a scene.

        Args:
            scene_id: Scene identifier
            npc_id: NPC identifier to add
        """
        scene = self.get_scene_by_id(scene_id)
        if scene:
            scene.add_npc(npc_id)

    def remove_npc_from_scene(self, scene_id: str, npc_id: str) -> None:
        """
        Remove an NPC from a scene.

        Args:
            scene_id: Scene identifier
            npc_id: NPC identifier to remove
        """
        scene = self.get_scene_by_id(scene_id)
        if scene:
            scene.remove_npc(npc_id)

    def get_scene_count(self) -> int:
        """
        Get total number of scenes in active graph.

        Returns:
            Scene count
        """
        if self.active_graph:
            return self.active_graph.get_scene_count()
        return 0

    def list_available_scenes(self) -> list[str]:
        """
        List all scene IDs in the active graph.

        Returns:
            List of scene IDs
        """
        if self.active_graph:
            return list(self.active_graph.scenes.keys())
        return []

    def get_active_world_pack_id(self) -> str | None:
        """
        Get the ID of the currently active world pack.

        Returns:
            World pack ID or None
        """
        if self.active_graph:
            return self.active_graph.world_pack_id
        return None

    def switch_to_graph(self, world_pack_id: str) -> bool:
        """
        Switch to a different narrative graph.

        Args:
            world_pack_id: ID of world pack to switch to

        Returns:
            True if switch was successful
        """
        if world_pack_id in self.narrative_graphs:
            self.active_graph = self.narrative_graphs[world_pack_id]
            return True
        return False
