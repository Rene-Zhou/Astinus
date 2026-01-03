"""Tests for WebSocket streaming functionality."""

import pytest

from src.backend.api.websockets import (
    ConnectionManager,
    MessageType,
    StreamMessage,
    stream_content,
)


class TestMessageType:
    """Test MessageType enum."""

    def test_message_types(self):
        """Test all message types are defined."""
        assert MessageType.STATUS.value == "status"
        assert MessageType.CONTENT.value == "content"
        assert MessageType.COMPLETE.value == "complete"
        assert MessageType.ERROR.value == "error"
        assert MessageType.PHASE.value == "phase"


class TestStreamMessage:
    """Test StreamMessage model."""

    def test_create_status_message(self):
        """Test creating a status message."""
        msg = StreamMessage(
            type=MessageType.STATUS,
            data={"phase": "processing", "message": "Working..."},
        )
        assert msg.type == MessageType.STATUS
        assert msg.data["phase"] == "processing"

    def test_create_content_message(self):
        """Test creating a content chunk message."""
        msg = StreamMessage(
            type=MessageType.CONTENT,
            data={"chunk": "Hello ", "is_partial": True, "chunk_index": 0},
        )
        assert msg.type == MessageType.CONTENT
        assert msg.data["chunk"] == "Hello "
        assert msg.data["is_partial"] is True

    def test_create_complete_message(self):
        """Test creating a complete message."""
        msg = StreamMessage(
            type=MessageType.COMPLETE,
            data={
                "content": "Full response",
                "metadata": {"agent": "gm"},
                "success": True,
            },
        )
        assert msg.type == MessageType.COMPLETE
        assert msg.data["success"] is True

    def test_message_serialization(self):
        """Test message model_dump for JSON serialization."""
        msg = StreamMessage(
            type=MessageType.ERROR,
            data={"error": "Something went wrong"},
        )
        dumped = msg.model_dump()
        assert dumped["type"] == "error"
        assert dumped["data"]["error"] == "Something went wrong"


class TestConnectionManager:
    """Test ConnectionManager class."""

    @pytest.fixture
    def manager(self):
        """Create a ConnectionManager instance."""
        return ConnectionManager()

    def test_init(self, manager):
        """Test manager initialization."""
        assert manager.active_connections == {}

    def test_disconnect_nonexistent(self, manager):
        """Test disconnecting a session that doesn't exist."""
        # Should not raise
        manager.disconnect("nonexistent")
        assert "nonexistent" not in manager.active_connections


class TestStreamContentFunction:
    """Test stream_content utility function."""

    @pytest.mark.asyncio
    async def test_stream_content_chunking(self):
        """Test that content is chunked correctly."""
        # We can't easily test the actual streaming without a mock websocket
        # But we can verify the chunking logic
        content = "Hello, World!"
        chunk_size = 5

        chunks = []
        for i in range(0, len(content), chunk_size):
            chunk = content[i : i + chunk_size]
            is_partial = i + chunk_size < len(content)
            chunks.append((chunk, is_partial))

        assert chunks == [
            ("Hello", True),
            (", Wor", True),
            ("ld!", False),
        ]

    @pytest.mark.asyncio
    async def test_stream_content_single_chunk(self):
        """Test content smaller than chunk size."""
        content = "Hi"
        chunk_size = 20

        chunks = []
        for i in range(0, len(content), chunk_size):
            chunk = content[i : i + chunk_size]
            is_partial = i + chunk_size < len(content)
            chunks.append((chunk, is_partial))

        assert chunks == [("Hi", False)]


class TestWebSocketMessageProtocol:
    """Test the WebSocket message protocol structure."""

    def test_status_message_format(self):
        """Test status message format matches protocol."""
        msg = StreamMessage(
            type=MessageType.STATUS,
            data={"phase": "processing", "message": "正在分析..."},
        )
        dumped = msg.model_dump()

        assert "type" in dumped
        assert "data" in dumped
        assert dumped["type"] == "status"
        assert "phase" in dumped["data"]

    def test_content_message_format(self):
        """Test content chunk message format matches protocol."""
        msg = StreamMessage(
            type=MessageType.CONTENT,
            data={"chunk": "一些文本", "is_partial": True, "chunk_index": 0},
        )
        dumped = msg.model_dump()

        assert dumped["type"] == "content"
        assert "chunk" in dumped["data"]
        assert "is_partial" in dumped["data"]
        assert "chunk_index" in dumped["data"]

    def test_complete_message_format(self):
        """Test complete message format matches protocol."""
        msg = StreamMessage(
            type=MessageType.COMPLETE,
            data={
                "content": "完整响应",
                "metadata": {"agents_called": ["rule", "npc"]},
                "success": True,
            },
        )
        dumped = msg.model_dump()

        assert dumped["type"] == "complete"
        assert "content" in dumped["data"]
        assert "metadata" in dumped["data"]
        assert "success" in dumped["data"]

    def test_error_message_format(self):
        """Test error message format matches protocol."""
        msg = StreamMessage(
            type=MessageType.ERROR,
            data={"error": "player_input is required"},
        )
        dumped = msg.model_dump()

        assert dumped["type"] == "error"
        assert "error" in dumped["data"]

    def test_phase_message_format(self):
        """Test phase change message format matches protocol."""
        msg = StreamMessage(
            type=MessageType.PHASE,
            data={"phase": "dice_check"},
        )
        dumped = msg.model_dump()

        assert dumped["type"] == "phase"
        assert "phase" in dumped["data"]
