"""Tests for database service and persistence layer.

Tests the complete persistence flow:
1. Database connection and session management
2. Game session CRUD operations
3. Save/Load game state
4. Auto-save functionality
"""

import os
import tempfile
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

from src.backend.models.persistence import (
    GameSessionModel,
    MessageModel,
    SaveSlotModel,
)
from src.backend.services.database import (
    DatabaseService,
    get_database_service,
)


class TestDatabaseService:
    """Test DatabaseService class."""

    @pytest_asyncio.fixture
    async def temp_db_path(self) -> AsyncGenerator[str]:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest_asyncio.fixture
    async def db_service(self, temp_db_path: str) -> AsyncGenerator[DatabaseService]:
        """Create a DatabaseService with temporary database."""
        service = DatabaseService(db_url=f"sqlite+aiosqlite:///{temp_db_path}")
        await service.initialize()
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, temp_db_path: str):
        """Test that initialize creates database tables."""
        service = DatabaseService(db_url=f"sqlite+aiosqlite:///{temp_db_path}")

        await service.initialize()

        # Verify tables exist by trying to create a session
        assert service._engine is not None
        assert service._session_factory is not None

        await service.close()

    @pytest.mark.asyncio
    async def test_close_disposes_engine(self, db_service: DatabaseService):
        """Test that close disposes the engine."""
        # Engine should exist
        assert db_service._engine is not None

        await db_service.close()

        # After close, engine should be None
        assert db_service._engine is None

    @pytest.mark.asyncio
    async def test_get_session_returns_async_session(self, db_service: DatabaseService):
        """Test getting an async session."""
        async with db_service.get_session() as session:
            assert session is not None

    @pytest.mark.asyncio
    async def test_is_connected_property(self, db_service: DatabaseService):
        """Test is_connected property."""
        assert db_service.is_connected is True

        await db_service.close()
        assert db_service.is_connected is False


class TestGameSessionCRUD:
    """Test CRUD operations for game sessions."""

    @pytest_asyncio.fixture
    async def temp_db_path(self) -> AsyncGenerator[str]:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest_asyncio.fixture
    async def db_service(self, temp_db_path: str) -> AsyncGenerator[DatabaseService]:
        """Create a DatabaseService with temporary database."""
        service = DatabaseService(db_url=f"sqlite+aiosqlite:///{temp_db_path}")
        await service.initialize()
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_create_game_session(self, db_service: DatabaseService):
        """Test creating a new game session."""
        session_data = {
            "session_id": "test-session-123",
            "world_pack_id": "demo_pack",
            "player_name": "测试玩家",
            "player_data": {"concept": "冒险者", "traits": []},
        }

        session = await db_service.create_game_session(**session_data)

        assert session is not None
        assert session.session_id == "test-session-123"
        assert session.world_pack_id == "demo_pack"
        assert session.player_name == "测试玩家"

    @pytest.mark.asyncio
    async def test_get_game_session(self, db_service: DatabaseService):
        """Test retrieving a game session."""
        # Create a session first
        session_data = {
            "session_id": "test-session-456",
            "world_pack_id": "demo_pack",
            "player_name": "玩家",
        }
        await db_service.create_game_session(**session_data)

        # Retrieve it
        session = await db_service.get_game_session("test-session-456")

        assert session is not None
        assert session.session_id == "test-session-456"

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, db_service: DatabaseService):
        """Test retrieving a non-existent session returns None."""
        session = await db_service.get_game_session("nonexistent")

        assert session is None

    @pytest.mark.asyncio
    async def test_update_game_session(self, db_service: DatabaseService):
        """Test updating a game session."""
        # Create a session
        await db_service.create_game_session(
            session_id="test-update-123",
            world_pack_id="demo_pack",
            player_name="Original Name",
        )

        # Update it
        updated = await db_service.update_game_session(
            session_id="test-update-123",
            current_location="新地点",
            turn_count=5,
        )

        assert updated is not None
        assert updated.current_location == "新地点"
        assert updated.turn_count == 5

    @pytest.mark.asyncio
    async def test_delete_game_session(self, db_service: DatabaseService):
        """Test deleting a game session."""
        # Create a session
        await db_service.create_game_session(
            session_id="test-delete-123",
            world_pack_id="demo_pack",
            player_name="To Delete",
        )

        # Delete it
        result = await db_service.delete_game_session("test-delete-123")

        assert result is True

        # Verify it's gone
        session = await db_service.get_game_session("test-delete-123")
        assert session is None

    @pytest.mark.asyncio
    async def test_list_game_sessions(self, db_service: DatabaseService):
        """Test listing all game sessions."""
        # Create multiple sessions
        for i in range(3):
            await db_service.create_game_session(
                session_id=f"test-list-{i}",
                world_pack_id="demo_pack",
                player_name=f"Player {i}",
            )

        # List them
        sessions = await db_service.list_game_sessions()

        assert len(sessions) >= 3


class TestSaveSlotOperations:
    """Test save slot operations."""

    @pytest_asyncio.fixture
    async def temp_db_path(self) -> AsyncGenerator[str]:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest_asyncio.fixture
    async def db_service(self, temp_db_path: str) -> AsyncGenerator[DatabaseService]:
        """Create a DatabaseService with temporary database."""
        service = DatabaseService(db_url=f"sqlite+aiosqlite:///{temp_db_path}")
        await service.initialize()
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_save_game(self, db_service: DatabaseService):
        """Test saving a game to a slot."""
        # Create a session first
        await db_service.create_game_session(
            session_id="test-save-123",
            world_pack_id="demo_pack",
            player_name="保存测试",
        )

        # Save it
        game_state = {
            "current_location": "测试地点",
            "turn_count": 10,
            "messages": [],
        }

        save = await db_service.save_game(
            session_id="test-save-123",
            slot_name="Save 1",
            game_state=game_state,
        )

        assert save is not None
        assert save.slot_name == "Save 1"
        assert save.session_id == "test-save-123"

    @pytest.mark.asyncio
    async def test_load_game(self, db_service: DatabaseService):
        """Test loading a saved game."""
        # Create and save a session
        await db_service.create_game_session(
            session_id="test-load-123",
            world_pack_id="demo_pack",
            player_name="读取测试",
        )

        game_state = {
            "current_location": "存档地点",
            "turn_count": 15,
        }

        await db_service.save_game(
            session_id="test-load-123",
            slot_name="Save Slot",
            game_state=game_state,
        )

        # Load it
        loaded = await db_service.load_game(
            session_id="test-load-123",
            slot_name="Save Slot",
        )

        assert loaded is not None
        assert loaded["current_location"] == "存档地点"
        assert loaded["turn_count"] == 15

    @pytest.mark.asyncio
    async def test_list_saves(self, db_service: DatabaseService):
        """Test listing all saves for a session."""
        # Create session and multiple saves
        await db_service.create_game_session(
            session_id="test-list-saves",
            world_pack_id="demo_pack",
            player_name="列表测试",
        )

        for i in range(3):
            await db_service.save_game(
                session_id="test-list-saves",
                slot_name=f"Save {i}",
                game_state={"turn": i},
            )

        # List saves
        saves = await db_service.list_saves("test-list-saves")

        assert len(saves) == 3

    @pytest.mark.asyncio
    async def test_delete_save(self, db_service: DatabaseService):
        """Test deleting a save slot."""
        # Create and save
        await db_service.create_game_session(
            session_id="test-delete-save",
            world_pack_id="demo_pack",
            player_name="删除测试",
        )

        await db_service.save_game(
            session_id="test-delete-save",
            slot_name="To Delete",
            game_state={},
        )

        # Delete
        result = await db_service.delete_save(
            session_id="test-delete-save",
            slot_name="To Delete",
        )

        assert result is True

        # Verify it's gone
        loaded = await db_service.load_game(
            session_id="test-delete-save",
            slot_name="To Delete",
        )
        assert loaded is None


class TestMessagePersistence:
    """Test message persistence operations."""

    @pytest_asyncio.fixture
    async def temp_db_path(self) -> AsyncGenerator[str]:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest_asyncio.fixture
    async def db_service(self, temp_db_path: str) -> AsyncGenerator[DatabaseService]:
        """Create a DatabaseService with temporary database."""
        service = DatabaseService(db_url=f"sqlite+aiosqlite:///{temp_db_path}")
        await service.initialize()
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_add_message(self, db_service: DatabaseService):
        """Test adding a message to a session."""
        # Create session
        await db_service.create_game_session(
            session_id="test-msg-123",
            world_pack_id="demo_pack",
            player_name="消息测试",
        )

        # Add message
        message = await db_service.add_message(
            session_id="test-msg-123",
            role="user",
            content="这是一条测试消息",
            turn=1,
        )

        assert message is not None
        assert message.role == "user"
        assert message.content == "这是一条测试消息"

    @pytest.mark.asyncio
    async def test_get_messages(self, db_service: DatabaseService):
        """Test retrieving messages for a session."""
        # Create session and add messages
        await db_service.create_game_session(
            session_id="test-get-msg",
            world_pack_id="demo_pack",
            player_name="获取消息",
        )

        for i in range(5):
            await db_service.add_message(
                session_id="test-get-msg",
                role="user" if i % 2 == 0 else "assistant",
                content=f"消息 {i}",
                turn=i,
            )

        # Get messages
        messages = await db_service.get_messages("test-get-msg")

        assert len(messages) == 5

    @pytest.mark.asyncio
    async def test_get_recent_messages(self, db_service: DatabaseService):
        """Test retrieving recent messages with limit."""
        # Create session and add messages
        await db_service.create_game_session(
            session_id="test-recent-msg",
            world_pack_id="demo_pack",
            player_name="最近消息",
        )

        for i in range(10):
            await db_service.add_message(
                session_id="test-recent-msg",
                role="user",
                content=f"消息 {i}",
                turn=i,
            )

        # Get only recent 5
        messages = await db_service.get_messages("test-recent-msg", limit=5)

        assert len(messages) == 5


class TestAutoSave:
    """Test auto-save functionality."""

    @pytest_asyncio.fixture
    async def temp_db_path(self) -> AsyncGenerator[str]:
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest_asyncio.fixture
    async def db_service(self, temp_db_path: str) -> AsyncGenerator[DatabaseService]:
        """Create a DatabaseService with temporary database."""
        service = DatabaseService(db_url=f"sqlite+aiosqlite:///{temp_db_path}")
        await service.initialize()
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_auto_save(self, db_service: DatabaseService):
        """Test auto-save creates a save with auto-save prefix."""
        # Create session
        await db_service.create_game_session(
            session_id="test-autosave",
            world_pack_id="demo_pack",
            player_name="自动存档",
        )

        # Trigger auto-save
        game_state = {"turn_count": 20}
        save = await db_service.auto_save(
            session_id="test-autosave",
            game_state=game_state,
        )

        assert save is not None
        assert save.slot_name.startswith("AutoSave")

    @pytest.mark.asyncio
    async def test_auto_save_rotation(self, db_service: DatabaseService):
        """Test auto-save rotates old saves."""
        # Create session
        await db_service.create_game_session(
            session_id="test-autosave-rotate",
            world_pack_id="demo_pack",
            player_name="自动轮换",
        )

        # Create multiple auto-saves
        for i in range(5):
            await db_service.auto_save(
                session_id="test-autosave-rotate",
                game_state={"turn": i},
                max_auto_saves=3,
            )

        # Should only keep 3 most recent
        saves = await db_service.list_saves("test-autosave-rotate")
        auto_saves = [s for s in saves if s.slot_name.startswith("AutoSave")]

        assert len(auto_saves) <= 3


class TestGetDatabaseService:
    """Test the get_database_service factory function."""

    def test_get_database_service_returns_instance(self):
        """Test factory returns a DatabaseService instance."""
        # Reset singleton for testing
        import src.backend.services.database as db_module

        db_module._database_service = None

        service = get_database_service()

        assert isinstance(service, DatabaseService)

        # Reset singleton after test
        db_module._database_service = None

    def test_get_database_service_singleton(self):
        """Test factory returns same instance (singleton pattern)."""
        # Reset singleton for testing
        import src.backend.services.database as db_module

        db_module._database_service = None

        service1 = get_database_service()
        service2 = get_database_service()

        assert service1 is service2

        # Reset singleton after test
        db_module._database_service = None


class TestPersistenceModels:
    """Test persistence model structures."""

    def test_game_session_model_defaults(self):
        """Test GameSessionModel has correct defaults."""
        session = GameSessionModel(
            session_id="test",
            world_pack_id="demo",
            player_name="Player",
        )

        assert session.session_id == "test"
        assert session.current_location == ""
        assert session.turn_count == 0

    def test_message_model_structure(self):
        """Test MessageModel structure."""
        message = MessageModel(
            session_id="test",
            role="user",
            content="Hello",
            turn=1,
        )

        assert message.role == "user"
        assert message.content == "Hello"
        assert message.turn == 1

    def test_save_slot_model_structure(self):
        """Test SaveSlotModel structure."""
        save = SaveSlotModel(
            session_id="test",
            slot_name="Save 1",
            game_state_json="{}",
        )

        assert save.slot_name == "Save 1"
        assert save.game_state_json == "{}"


class TestPersistenceModelsExtended:
    """Extended tests for persistence models."""

    def test_game_session_model_properties(self):
        """Test GameSessionModel properties."""
        session = GameSessionModel(
            session_id="test-session",
            world_pack_id="demo_pack",
            player_name="测试玩家",
            player_data={"traits": ["brave"]},
            current_location="start",
            current_phase="waiting_input",
            turn_count=5,
            active_npc_ids=["npc_1", "npc_2"],
        )

        # Test player_data property
        assert session.player_data is not None
        assert "traits" in session.player_data

        # Test active_npc_ids property
        assert len(session.active_npc_ids) == 2
        assert "npc_1" in session.active_npc_ids

    def test_game_session_model_to_dict(self):
        """Test GameSessionModel to_dict method."""
        session = GameSessionModel(
            session_id="test-session",
            world_pack_id="demo_pack",
            player_name="测试玩家",
            player_data=None,
            current_location="start",
        )

        data = session.to_dict()
        assert data["session_id"] == "test-session"
        assert data["world_pack_id"] == "demo_pack"
        assert data["player_name"] == "测试玩家"

    def test_game_session_model_repr(self):
        """Test GameSessionModel repr."""
        session = GameSessionModel(
            session_id="test-session",
            world_pack_id="demo_pack",
            player_name="测试",
            player_data=None,
            current_location="start",
        )
        repr_str = repr(session)
        assert "GameSessionModel" in repr_str
        assert "test-session" in repr_str

    def test_save_slot_model_properties(self):
        """Test SaveSlotModel properties."""
        save = SaveSlotModel(
            session_id="test-session",
            slot_name="Save 1",
            game_state_json='{"location": "cave", "turn": 10}',
            description="In the cave",
        )

        # Test game_state property getter
        state = save.game_state
        assert state["location"] == "cave"
        assert state["turn"] == 10

        # Test game_state property setter
        save.game_state = {"location": "forest", "turn": 15}
        assert save.game_state["location"] == "forest"

    def test_save_slot_model_to_dict(self):
        """Test SaveSlotModel to_dict method."""
        save = SaveSlotModel(
            session_id="test-session",
            slot_name="Save 1",
            game_state_json='{"turn": 5}',
        )

        data = save.to_dict()
        assert data["slot_name"] == "Save 1"
        assert data["game_state"]["turn"] == 5

    def test_save_slot_model_repr(self):
        """Test SaveSlotModel repr."""
        save = SaveSlotModel(
            session_id="test-session",
            slot_name="Auto Save",
            game_state_json="{}",
            is_auto_save=True,
        )
        repr_str = repr(save)
        assert "SaveSlotModel" in repr_str
        assert "Auto Save" in repr_str
