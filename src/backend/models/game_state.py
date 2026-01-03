"""
Game state models.

Defines GameState - the global truth owned by GM Agent.
"""

import contextlib
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .character import PlayerCharacter


class GamePhase(str, Enum):
    """
    Current phase of the game loop.

    The GM Agent uses this to track what's happening and what should happen next.
    """

    WAITING_INPUT = "waiting_input"  # Waiting for player input
    PROCESSING = "processing"  # GM is processing player action
    DICE_CHECK = "dice_check"  # Waiting for player to roll dice
    NPC_RESPONSE = "npc_response"  # NPC is responding
    NARRATING = "narrating"  # GM is narrating outcome


class GameState(BaseModel):
    """
    Global game state - GM Agent's world view.

    This is the single source of truth for the game. The GM Agent owns this
    and updates it. Sub-agents (Rule, NPC, Lore) receive sliced context from
    this state but never see or modify it directly.

    Key design decisions per plan:
    - `messages`: Full conversation history (append-only audit log)
    - `temp_context`: Temporary data for passing between agents (star topology)
    - `player`: The player character
    - `world_pack_id`: Which story pack is loaded
    - `flags`: Story flags for narrative branching

    Examples:
        >>> state = GameState(
        ...     session_id="test-123",
        ...     player=character,
        ...     world_pack_id="demo_pack",
        ...     current_location="living_room"
        ... )
        >>> state.add_flag("knows_there_is_traitor")
        >>> "knows_there_is_traitor" in state.flags
        True
    """

    # Session metadata
    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(default_factory=datetime.now, description="Session creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")

    # Core state
    player: PlayerCharacter = Field(..., description="Player character")
    current_phase: GamePhase = Field(
        default=GamePhase.WAITING_INPUT, description="Current game phase"
    )
    next_agent: str | None = Field(
        default=None, description="Which agent should act next (routing target)"
    )

    # World state
    world_pack_id: str = Field(..., description="ID of loaded world/story pack")
    current_location: str = Field(..., description="Current location ID in world pack")
    active_npc_ids: list[str] = Field(
        default_factory=list, description="NPCs present in current scene"
    )
    discovered_items: set[str] = Field(
        default_factory=set, description="Items player has discovered/interacted with"
    )
    flags: set[str] = Field(
        default_factory=set, description="Story flags (e.g., 'found_key', 'knows_secret')"
    )

    # Temporal tracking
    game_time: str = Field(
        default="00:00", description="In-game time (e.g., '23:47')"
    )
    turn_count: int = Field(default=0, ge=0, description="Number of turns elapsed")

    # Communication
    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Full conversation history - GM's complete context"
    )
    temp_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Temporary context for passing data to/from sub-agents"
    )
    last_check_result: dict[str, Any] | None = Field(
        default=None, description="Most recent dice check outcome"
    )

    # Settings
    language: str = Field(default="cn", description="Current language (cn/en)")

    def add_message(
        self,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        vector_store=None,
        collection_name: str | None = None,
    ) -> None:
        """
        Add a message to conversation history.

        Args:
            role: "user" or "assistant"
            content: Message content
            metadata: Optional metadata (agent name, phase, etc.)
            vector_store: Optional VectorStoreService for indexing
            collection_name: Optional collection name for vector storage
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "turn": self.turn_count,
        }
        if metadata:
            message["metadata"] = metadata

        self.messages.append(message)

        # Index in vector store if provided
        if vector_store and collection_name:
            message_id = f"{self.session_id}_msg_{len(self.messages)}"
            with contextlib.suppress(Exception):
                vector_store.add_documents(
                    collection_name=collection_name,
                    documents=[content],
                    metadatas=[
                        {
                            "role": role,
                            "turn": self.turn_count,
                            "timestamp": message["timestamp"],
                        }
                    ],
                    ids=[message_id],
                )

        self.updated_at = datetime.now()

    def get_recent_messages(self, count: int = 5) -> list[dict[str, Any]]:
        """
        Get the N most recent messages.

        Args:
            count: Number of recent messages to retrieve

        Returns:
            List of recent messages (most recent last)
        """
        return self.messages[-count:] if self.messages else []

    def update_location(self, location_id: str, npc_ids: list[str] | None = None) -> None:
        """
        Update current location and NPCs.

        Args:
            location_id: New location ID
            npc_ids: Optional list of NPC IDs at new location
        """
        self.current_location = location_id
        if npc_ids is not None:
            self.active_npc_ids = npc_ids
        self.updated_at = datetime.now()

    def add_flag(self, flag: str) -> None:
        """
        Add a story flag.

        Args:
            flag: Flag identifier (e.g., "found_key", "knows_traitor_identity")
        """
        self.flags.add(flag)
        self.updated_at = datetime.now()

    def has_flag(self, flag: str) -> bool:
        """
        Check if a story flag is set.

        Args:
            flag: Flag identifier

        Returns:
            True if flag is set
        """
        return flag in self.flags

    def add_discovered_item(self, item_id: str) -> None:
        """
        Mark an item as discovered.

        Args:
            item_id: Item identifier
        """
        self.discovered_items.add(item_id)
        self.updated_at = datetime.now()

    def has_discovered_item(self, item_id: str) -> bool:
        """
        Check if player has discovered an item.

        Args:
            item_id: Item identifier

        Returns:
            True if item has been discovered
        """
        return item_id in self.discovered_items

    def increment_turn(self) -> None:
        """Increment turn counter."""
        self.turn_count += 1
        self.updated_at = datetime.now()

    def set_phase(self, phase: GamePhase, next_agent: str | None = None) -> None:
        """
        Update current phase and optionally set next agent.

        Args:
            phase: New game phase
            next_agent: Optional agent to route to next
        """
        self.current_phase = phase
        if next_agent is not None:
            self.next_agent = next_agent
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"GameState(session={self.session_id}, "
            f"player={self.player.name}, "
            f"location={self.current_location}, "
            f"phase={self.current_phase.value}, "
            f"turn={self.turn_count})"
        )
