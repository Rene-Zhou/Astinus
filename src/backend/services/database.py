"""
Database service for async SQLite operations.

Provides:
- Async database connection management
- Game session CRUD operations
- Message persistence
- Save/Load game state
- Auto-save functionality
"""

import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.models.persistence import (
    Base,
    GameSessionModel,
    MessageModel,
    SaveSlotModel,
)

# Module-level singleton
_database_service: Optional["DatabaseService"] = None


def get_database_service(db_url: str | None = None) -> "DatabaseService":
    """
    Get or create the singleton DatabaseService instance.

    Args:
        db_url: Database URL. Only used on first call.

    Returns:
        DatabaseService singleton instance
    """
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService(db_url=db_url)
    return _database_service


class DatabaseService:
    """
    Async database service for game persistence.

    Handles all database operations including:
    - Connection management
    - Game session CRUD
    - Message storage
    - Save slots
    """

    def __init__(self, db_url: str | None = None):
        """
        Initialize the database service.

        Args:
            db_url: SQLAlchemy database URL.
                    Defaults to SQLite file in data directory.
        """
        self._db_url = db_url or "sqlite+aiosqlite:///data/astinus.db"
        self._engine = None
        self._session_factory = None

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._engine is not None

    async def initialize(self) -> None:
        """
        Initialize database connection and create tables.

        Must be called before using the service.
        """
        if self._engine is not None:
            return

        # Create async engine
        self._engine = create_async_engine(
            self._db_url,
            echo=False,  # Set to True for SQL debugging
        )

        # Create session factory
        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
        )

        # Create tables
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logging.info(f"Database initialized: {self._db_url}")

    async def close(self) -> None:
        """Close database connection."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logging.info("Database connection closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession]:
        """
        Get an async database session.

        Usage:
            async with db.get_session() as session:
                # use session
        """
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # ==================== Game Session CRUD ====================

    async def create_game_session(
        self,
        session_id: str,
        world_pack_id: str,
        player_name: str,
        player_data: dict[str, Any] | None = None,
        current_location: str = "",
        **kwargs,
    ) -> GameSessionModel:
        """
        Create a new game session.

        Args:
            session_id: Unique session identifier
            world_pack_id: World pack being used
            player_name: Player's character name
            player_data: Optional player data dict
            current_location: Starting location

        Returns:
            Created GameSessionModel
        """
        async with self.get_session() as session:
            game_session = GameSessionModel(
                session_id=session_id,
                world_pack_id=world_pack_id,
                player_name=player_name,
                player_data=player_data,
                current_location=current_location,
                **kwargs,
            )
            session.add(game_session)
            await session.flush()
            await session.refresh(game_session)
            return game_session

    async def get_game_session(self, session_id: str) -> GameSessionModel | None:
        """
        Get a game session by ID.

        Args:
            session_id: Session identifier

        Returns:
            GameSessionModel or None if not found
        """
        async with self.get_session() as session:
            result = await session.execute(
                select(GameSessionModel).where(GameSessionModel.session_id == session_id)
            )
            return result.scalar_one_or_none()

    async def update_game_session(
        self,
        session_id: str,
        **kwargs,
    ) -> GameSessionModel | None:
        """
        Update a game session.

        Args:
            session_id: Session identifier
            **kwargs: Fields to update

        Returns:
            Updated GameSessionModel or None if not found
        """
        async with self.get_session() as session:
            # First check if session exists
            result = await session.execute(
                select(GameSessionModel).where(GameSessionModel.session_id == session_id)
            )
            game_session = result.scalar_one_or_none()

            if not game_session:
                return None

            # Update fields
            for key, value in kwargs.items():
                if hasattr(game_session, key):
                    setattr(game_session, key, value)

            game_session.updated_at = datetime.utcnow()
            await session.flush()
            await session.refresh(game_session)
            return game_session

    async def delete_game_session(self, session_id: str) -> bool:
        """
        Delete a game session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        async with self.get_session() as session:
            result = await session.execute(
                delete(GameSessionModel).where(GameSessionModel.session_id == session_id)
            )
            return result.rowcount > 0

    async def list_game_sessions(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GameSessionModel]:
        """
        List all game sessions.

        Args:
            limit: Maximum number to return
            offset: Number to skip

        Returns:
            List of GameSessionModel
        """
        async with self.get_session() as session:
            result = await session.execute(
                select(GameSessionModel)
                .order_by(GameSessionModel.updated_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())

    # ==================== Message Operations ====================

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        turn: int = 0,
        extra_data: dict[str, Any] | None = None,
    ) -> MessageModel:
        """
        Add a message to a session.

        Args:
            session_id: Session identifier
            role: Message role (user/assistant/system)
            content: Message content
            turn: Turn number
            extra_data: Optional extra data

        Returns:
            Created MessageModel
        """
        async with self.get_session() as session:
            message = MessageModel(
                session_id=session_id,
                role=role,
                content=content,
                turn=turn,
                metadata=extra_data,
            )
            session.add(message)
            await session.flush()
            await session.refresh(message)
            return message

    async def get_messages(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[MessageModel]:
        """
        Get messages for a session.

        Args:
            session_id: Session identifier
            limit: Optional limit on number of messages

        Returns:
            List of MessageModel, ordered by turn
        """
        async with self.get_session() as session:
            query = (
                select(MessageModel)
                .where(MessageModel.session_id == session_id)
                .order_by(MessageModel.turn.asc(), MessageModel.id.asc())
            )

            if limit:
                # Get most recent messages
                query = (
                    select(MessageModel)
                    .where(MessageModel.session_id == session_id)
                    .order_by(MessageModel.turn.desc(), MessageModel.id.desc())
                    .limit(limit)
                )
                result = await session.execute(query)
                messages = list(result.scalars().all())
                # Reverse to get chronological order
                return list(reversed(messages))

            result = await session.execute(query)
            return list(result.scalars().all())

    # ==================== Save Slot Operations ====================

    async def save_game(
        self,
        session_id: str,
        slot_name: str,
        game_state: dict[str, Any],
        description: str | None = None,
        is_auto_save: bool = False,
    ) -> SaveSlotModel:
        """
        Save game state to a slot.

        Args:
            session_id: Session identifier
            slot_name: Name of save slot
            game_state: Game state dict to save
            description: Optional description
            is_auto_save: Whether this is an auto-save

        Returns:
            Created or updated SaveSlotModel
        """
        async with self.get_session() as session:
            # Check if slot exists
            result = await session.execute(
                select(SaveSlotModel).where(
                    SaveSlotModel.session_id == session_id,
                    SaveSlotModel.slot_name == slot_name,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing save
                existing.game_state_json = json.dumps(game_state)
                existing.description = description
                existing.updated_at = datetime.utcnow()
                await session.flush()
                await session.refresh(existing)
                return existing
            else:
                # Create new save
                save = SaveSlotModel(
                    session_id=session_id,
                    slot_name=slot_name,
                    game_state_json=json.dumps(game_state),
                    description=description,
                    is_auto_save=is_auto_save,
                )
                session.add(save)
                await session.flush()
                await session.refresh(save)
                return save

    async def load_game(
        self,
        session_id: str,
        slot_name: str,
    ) -> dict[str, Any] | None:
        """
        Load game state from a slot.

        Args:
            session_id: Session identifier
            slot_name: Name of save slot

        Returns:
            Game state dict or None if not found
        """
        async with self.get_session() as session:
            result = await session.execute(
                select(SaveSlotModel).where(
                    SaveSlotModel.session_id == session_id,
                    SaveSlotModel.slot_name == slot_name,
                )
            )
            save = result.scalar_one_or_none()

            if save:
                return save.game_state
            return None

    async def list_saves(self, session_id: str) -> list[SaveSlotModel]:
        """
        List all saves for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of SaveSlotModel
        """
        async with self.get_session() as session:
            result = await session.execute(
                select(SaveSlotModel)
                .where(SaveSlotModel.session_id == session_id)
                .order_by(SaveSlotModel.updated_at.desc())
            )
            return list(result.scalars().all())

    async def delete_save(self, session_id: str, slot_name: str) -> bool:
        """
        Delete a save slot.

        Args:
            session_id: Session identifier
            slot_name: Name of save slot

        Returns:
            True if deleted, False if not found
        """
        async with self.get_session() as session:
            result = await session.execute(
                delete(SaveSlotModel).where(
                    SaveSlotModel.session_id == session_id,
                    SaveSlotModel.slot_name == slot_name,
                )
            )
            return result.rowcount > 0

    async def auto_save(
        self,
        session_id: str,
        game_state: dict[str, Any],
        max_auto_saves: int = 3,
    ) -> SaveSlotModel:
        """
        Create an auto-save with rotation.

        Args:
            session_id: Session identifier
            game_state: Game state to save
            max_auto_saves: Maximum auto-saves to keep

        Returns:
            Created SaveSlotModel
        """
        # Get existing auto-saves
        async with self.get_session() as session:
            result = await session.execute(
                select(SaveSlotModel)
                .where(
                    SaveSlotModel.session_id == session_id,
                    SaveSlotModel.is_auto_save == True,  # noqa: E712
                )
                .order_by(SaveSlotModel.created_at.asc())
            )
            auto_saves = list(result.scalars().all())

            # Delete old auto-saves if over limit
            while len(auto_saves) >= max_auto_saves:
                oldest = auto_saves.pop(0)
                await session.delete(oldest)

        # Create new auto-save with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        slot_name = f"AutoSave_{timestamp}"

        return await self.save_game(
            session_id=session_id,
            slot_name=slot_name,
            game_state=game_state,
            description="Auto-save",
            is_auto_save=True,
        )
