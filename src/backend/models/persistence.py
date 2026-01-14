"""
Persistence models for SQLAlchemy ORM.

Defines database models for:
- Game sessions
- Messages (conversation history)
- Save slots
"""

import json
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class GameSessionModel(Base):
    """
    Model for game sessions.

    Stores the current state of a game session including player info,
    location, and game progress.
    """

    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    world_pack_id: Mapped[str] = mapped_column(String(64))
    player_name: Mapped[str] = mapped_column(String(128))
    player_data_json: Mapped[str | None] = mapped_column(Text, default=None)
    current_location: Mapped[str] = mapped_column(String(256), default="")
    current_phase: Mapped[str] = mapped_column(String(32), default="waiting_input")
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    active_npc_ids_json: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    messages: Mapped[list["MessageModel"]] = relationship(
        "MessageModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    saves: Mapped[list["SaveSlotModel"]] = relationship(
        "SaveSlotModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __init__(
        self,
        session_id: str,
        world_pack_id: str,
        player_name: str,
        player_data: dict[str, Any] | None = None,
        current_location: str = "",
        current_phase: str = "waiting_input",
        turn_count: int = 0,
        active_npc_ids: list[str] | None = None,
        **kwargs,
    ):
        """
        Initialize a GameSessionModel.

        Args:
            session_id: Unique session identifier
            world_pack_id: World pack being used
            player_name: Player's character name
            player_data: Player data as dict (will be JSON serialized)
            current_location: Current location in game
            current_phase: Current game phase
            turn_count: Number of turns played
            active_npc_ids: List of active NPC IDs
        """
        super().__init__(**kwargs)
        self.session_id = session_id
        self.world_pack_id = world_pack_id
        self.player_name = player_name
        self.player_data_json = json.dumps(player_data) if player_data else None
        self.current_location = current_location
        self.current_phase = current_phase
        self.turn_count = turn_count
        self.active_npc_ids_json = json.dumps(active_npc_ids) if active_npc_ids else None

    @property
    def player_data(self) -> dict[str, Any] | None:
        """Get player data as dict."""
        if self.player_data_json:
            return json.loads(self.player_data_json)
        return None

    @player_data.setter
    def player_data(self, value: dict[str, Any] | None) -> None:
        """Set player data from dict."""
        self.player_data_json = json.dumps(value) if value else None

    @property
    def active_npc_ids(self) -> list[str]:
        """Get active NPC IDs as list."""
        if self.active_npc_ids_json:
            return json.loads(self.active_npc_ids_json)
        return []

    @active_npc_ids.setter
    def active_npc_ids(self, value: list[str] | None) -> None:
        """Set active NPC IDs from list."""
        self.active_npc_ids_json = json.dumps(value) if value else None

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "world_pack_id": self.world_pack_id,
            "player_name": self.player_name,
            "player_data": self.player_data,
            "current_location": self.current_location,
            "current_phase": self.current_phase,
            "turn_count": self.turn_count,
            "active_npc_ids": self.active_npc_ids,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        """Return string representation."""
        return f"GameSessionModel(session_id={self.session_id!r}, player={self.player_name!r})"


class MessageModel(Base):
    """
    Model for conversation messages.

    Stores the conversation history for a game session.
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("game_sessions.session_id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(32))  # user, assistant, system
    content: Mapped[str] = mapped_column(Text)
    turn: Mapped[int] = mapped_column(Integer, default=0)
    extra_data_json: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    session: Mapped["GameSessionModel"] = relationship(
        "GameSessionModel", back_populates="messages"
    )

    def __init__(
        self,
        session_id: str,
        role: str,
        content: str,
        turn: int = 0,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ):
        """
        Initialize a MessageModel.

        Args:
            session_id: Session this message belongs to
            role: Message role (user/assistant/system)
            content: Message content
            turn: Turn number when message was sent
            metadata: Optional metadata dict
        """
        super().__init__(**kwargs)
        self.session_id = session_id
        self.role = role
        self.content = content
        self.turn = turn
        self.extra_data_json = json.dumps(metadata) if metadata else None

    @property
    def extra_data(self) -> dict[str, Any] | None:
        """Get extra data as dict."""
        if self.extra_data_json:
            return json.loads(self.extra_data_json)
        return None

    @extra_data.setter
    def extra_data(self, value: dict[str, Any] | None) -> None:
        """Set extra data from dict."""
        self.extra_data_json = json.dumps(value) if value else None

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "turn": self.turn,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        """Return string representation."""
        return f"MessageModel(role={self.role!r}, turn={self.turn})"


class SaveSlotModel(Base):
    """
    Model for save slots.

    Stores saved game states that can be loaded later.
    """

    __tablename__ = "save_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("game_sessions.session_id", ondelete="CASCADE"), index=True
    )
    slot_name: Mapped[str] = mapped_column(String(128), index=True)
    game_state_json: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(String(512), default=None)
    is_auto_save: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship
    session: Mapped["GameSessionModel"] = relationship("GameSessionModel", back_populates="saves")

    def __init__(
        self,
        session_id: str,
        slot_name: str,
        game_state_json: str,
        description: str | None = None,
        is_auto_save: bool = False,
        **kwargs,
    ):
        """
        Initialize a SaveSlotModel.

        Args:
            session_id: Session this save belongs to
            slot_name: Name of the save slot
            game_state_json: JSON string of game state
            description: Optional description
            is_auto_save: Whether this is an auto-save
        """
        super().__init__(**kwargs)
        self.session_id = session_id
        self.slot_name = slot_name
        self.game_state_json = game_state_json
        self.description = description
        self.is_auto_save = is_auto_save

    @property
    def game_state(self) -> dict[str, Any]:
        """Get game state as dict."""
        return json.loads(self.game_state_json)

    @game_state.setter
    def game_state(self, value: dict[str, Any]) -> None:
        """Set game state from dict."""
        self.game_state_json = json.dumps(value)

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "slot_name": self.slot_name,
            "game_state": self.game_state,
            "description": self.description,
            "is_auto_save": self.is_auto_save,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        """Return string representation."""
        return f"SaveSlotModel(slot={self.slot_name!r}, auto={self.is_auto_save})"
