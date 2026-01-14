"""
Narrative graph and scene management for Astinus.

Provides scene transitions, narrative state tracking, and story flow control.
Based on GUIDE.md specifications for modular narrative design.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SceneType(Enum):
    """Types of scenes in the narrative."""

    LOCATION = "location"
    ENCOUNTER = "encounter"
    DIALOGUE = "dialogue"
    CUTSCENE = "cutscene"
    PUZZLE = "puzzle"
    COMBAT = "combat"


class TransitionCondition(BaseModel):
    """Condition for scene transition."""

    type: str = Field(..., description="Condition type: tag, flag, item, etc.")
    key: str = Field(..., description="Condition key (e.g., 'has_key', 'player_has_tag')")
    value: Any = Field(..., description="Required value for the condition")


class SceneTransition(BaseModel):
    """Transition from one scene to another."""

    target_scene_id: str = Field(..., description="ID of target scene")
    condition: TransitionCondition | None = Field(
        default=None, description="Optional condition to allow this transition"
    )
    description: str = Field(
        default="", description="Description of what happens during transition"
    )


class Scene(BaseModel):
    """
    A scene in the narrative graph.

    Scenes represent locations, encounters, or story beats where
    player actions can occur and affect the story flow.

    Attributes:
        id: Unique scene identifier
        name: Display name for the scene
        type: Type of scene (location, encounter, etc.)
        description: Current scene description (may change based on state)
        narrative_state: Key-value pairs tracking story progress
        active_npcs: NPCs currently present in this scene
        available_actions: List of possible actions player can take
        transitions: Possible transitions to other scenes
    """

    id: str = Field(..., description="Unique scene identifier")
    name: str = Field(..., description="Display name")
    type: SceneType = Field(default=SceneType.LOCATION, description="Scene type")
    description: str = Field(default="", description="Current scene description (can be dynamic)")
    narrative_state: dict[str, Any] = Field(
        default_factory=dict, description="Story progress state (flags, discovered info, etc.)"
    )
    active_npcs: list[str] = Field(
        default_factory=list, description="NPC IDs present in this scene"
    )
    available_actions: list[str] = Field(
        default_factory=list, description="Possible actions in this scene"
    )
    transitions: list[SceneTransition] = Field(
        default_factory=list, description="Possible transitions to other scenes"
    )

    def add_narrative_flag(self, key: str, value: Any) -> None:
        """Set a narrative flag."""
        self.narrative_state[key] = value

    def has_narrative_flag(self, key: str, expected_value: Any = None) -> bool:
        """Check if a narrative flag exists with optional expected value."""
        if key not in self.narrative_state:
            return False
        if expected_value is None:
            return True
        return self.narrative_state[key] == expected_value

    def add_npc(self, npc_id: str) -> None:
        """Add an NPC to this scene."""
        if npc_id not in self.active_npcs:
            self.active_npcs.append(npc_id)

    def remove_npc(self, npc_id: str) -> None:
        """Remove an NPC from this scene."""
        if npc_id in self.active_npcs:
            self.active_npcs.remove(npc_id)

    def add_transition(self, transition: SceneTransition) -> None:
        """Add a transition to another scene."""
        self.transitions.append(transition)

    def can_transition_to(self, target_scene_id: str) -> bool:
        """Check if transition to target scene is allowed."""
        return any(transition.target_scene_id == target_scene_id for transition in self.transitions)

    def get_available_transitions(self) -> list[SceneTransition]:
        """Get list of available transitions (conditions met)."""
        # For now, return all transitions
        # In full implementation, filter based on conditions
        return self.transitions


class NarrativeGraph(BaseModel):
    """
    Complete narrative graph for a world pack.

    Manages all scenes, transitions, and story state for a narrative.

    Attributes:
        world_pack_id: ID of the world pack this graph belongs to
        scenes: Dictionary of all scenes by ID
        current_scene_id: ID of the currently active scene
        global_narrative_state: Global story state shared across scenes
    """

    world_pack_id: str = Field(..., description="World pack identifier")
    scenes: dict[str, Scene] = Field(
        default_factory=dict, description="All scenes in the narrative graph"
    )
    current_scene_id: str | None = Field(default=None, description="Currently active scene")
    global_narrative_state: dict[str, Any] = Field(
        default_factory=dict, description="Global story state (applies across all scenes)"
    )

    def add_scene(self, scene: Scene) -> None:
        """Add a scene to the graph."""
        self.scenes[scene.id] = scene

    def get_scene(self, scene_id: str) -> Scene | None:
        """Get a scene by ID."""
        return self.scenes.get(scene_id)

    def set_current_scene(self, scene_id: str) -> bool:
        """Set the current scene if it exists."""
        if scene_id in self.scenes:
            self.current_scene_id = scene_id
            return True
        return False

    def get_current_scene(self) -> Scene | None:
        """Get the currently active scene."""
        if self.current_scene_id:
            return self.scenes.get(self.current_scene_id)
        return None

    def transition_to(self, target_scene_id: str) -> bool:
        """
        Transition to a new scene.

        Args:
            target_scene_id: ID of scene to transition to

        Returns:
            True if transition was successful
        """
        current_scene = self.get_current_scene()
        if current_scene and current_scene.can_transition_to(target_scene_id):
            self.current_scene_id = target_scene_id
            return True
        return False

    def set_global_flag(self, key: str, value: Any) -> None:
        """Set a global narrative flag."""
        self.global_narrative_state[key] = value

    def get_global_flag(self, key: str, default: Any = None) -> Any:
        """Get a global narrative flag."""
        return self.global_narrative_state.get(key, default)

    def has_global_flag(self, key: str, expected_value: Any = None) -> bool:
        """Check if a global narrative flag exists."""
        if key not in self.global_narrative_state:
            return False
        if expected_value is None:
            return True
        return self.global_narrative_state[key] == expected_value

    def list_scenes_by_type(self, scene_type: SceneType) -> list[Scene]:
        """Get all scenes of a specific type."""
        return [s for s in self.scenes.values() if s.type == scene_type]

    def get_scene_count(self) -> int:
        """Get total number of scenes."""
        return len(self.scenes)
