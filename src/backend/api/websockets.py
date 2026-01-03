"""
WebSocket endpoints for real-time game interaction.

Provides streaming responses from the GM Agent with:
- Status updates during processing
- Chunked content streaming (typewriter effect)
- Real-time phase updates
"""

import asyncio
import json
from enum import Enum
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter(tags=["websocket"])


class MessageType(str, Enum):
    """WebSocket message types."""

    STATUS = "status"  # Processing status update
    CONTENT = "content"  # Streamed content chunk
    COMPLETE = "complete"  # Final complete response
    ERROR = "error"  # Error message
    PHASE = "phase"  # Game phase change


class StreamMessage(BaseModel):
    """Structured WebSocket message."""

    type: MessageType
    data: dict[str, Any]


class ConnectionManager:
    """Manages WebSocket connections for game sessions."""

    def __init__(self):
        """Initialize the connection manager."""
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept and track a new connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        """Remove a connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_message(self, session_id: str, message: StreamMessage):
        """Send a structured message to a session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message.model_dump())

    async def send_status(
        self, session_id: str, phase: str, message: str | None = None
    ):
        """Send a status update."""
        await self.send_message(
            session_id,
            StreamMessage(
                type=MessageType.STATUS,
                data={"phase": phase, "message": message or ""},
            ),
        )

    async def send_content_chunk(
        self,
        session_id: str,
        chunk: str,
        is_partial: bool = True,
        chunk_index: int = 0,
    ):
        """Send a content chunk for streaming effect."""
        await self.send_message(
            session_id,
            StreamMessage(
                type=MessageType.CONTENT,
                data={
                    "chunk": chunk,
                    "is_partial": is_partial,
                    "chunk_index": chunk_index,
                },
            ),
        )

    async def send_complete(
        self,
        session_id: str,
        content: str,
        metadata: dict[str, Any],
        success: bool = True,
    ):
        """Send the complete response."""
        await self.send_message(
            session_id,
            StreamMessage(
                type=MessageType.COMPLETE,
                data={
                    "content": content,
                    "metadata": metadata,
                    "success": success,
                },
            ),
        )

    async def send_error(self, session_id: str, error: str):
        """Send an error message."""
        await self.send_message(
            session_id,
            StreamMessage(
                type=MessageType.ERROR,
                data={"error": error},
            ),
        )

    async def send_phase_change(self, session_id: str, phase: str):
        """Send a game phase change notification."""
        await self.send_message(
            session_id,
            StreamMessage(
                type=MessageType.PHASE,
                data={"phase": phase},
            ),
        )


# Global connection manager
manager = ConnectionManager()


async def stream_content(
    session_id: str,
    content: str,
    chunk_size: int = 20,
    delay: float = 0.03,
):
    """
    Stream content in chunks for typewriter effect.

    Args:
        session_id: Session to stream to
        content: Full content to stream
        chunk_size: Characters per chunk
        delay: Delay between chunks in seconds
    """
    for i in range(0, len(content), chunk_size):
        chunk = content[i : i + chunk_size]
        is_partial = i + chunk_size < len(content)
        await manager.send_content_chunk(
            session_id,
            chunk=chunk,
            is_partial=is_partial,
            chunk_index=i // chunk_size,
        )
        if is_partial:
            await asyncio.sleep(delay)


@router.websocket("/ws/game/{session_id}")
async def websocket_game_endpoint(
    websocket: WebSocket,
    session_id: str,
):
    """
    WebSocket endpoint for real-time game interaction.

    Provides streaming responses from the GM Agent.

    Message Protocol:
    - Client sends: {"player_input": "...", "lang": "cn", "stream": true}
    - Server sends status updates: {"type": "status", "data": {"phase": "processing"}}
    - Server streams content: {"type": "content", "data": {"chunk": "...", "is_partial": true}}
    - Server sends complete: {"type": "complete", "data": {"content": "...", "metadata": {}}}

    Args:
        websocket: WebSocket connection
        session_id: Game session identifier
    """
    from src.backend.main import gm_agent

    if gm_agent is None:
        await websocket.close(code=1011, reason="Game engine not initialized")
        return

    await manager.connect(session_id, websocket)

    try:
        while True:
            # Receive message from client
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
            except json.JSONDecodeError:
                await manager.send_error(session_id, "Invalid JSON")
                continue

            # Extract parameters
            player_input = data.get("player_input", "")
            lang = data.get("lang", "cn")
            stream = data.get("stream", True)  # Default to streaming

            if not player_input:
                await manager.send_error(session_id, "player_input is required")
                continue

            # Send processing status
            await manager.send_status(
                session_id,
                phase="processing",
                message="Analyzing your action..." if lang == "en" else "正在分析你的行动...",
            )

            # Process through GM Agent
            try:
                result = await gm_agent.process({
                    "player_input": player_input,
                    "lang": lang,
                })
            except Exception as exc:
                await manager.send_error(session_id, f"Processing failed: {exc}")
                continue

            # Send phase update
            phase = gm_agent.game_state.current_phase.value
            await manager.send_phase_change(session_id, phase)

            if result.success:
                # Stream content if requested and content is substantial
                if stream and len(result.content) > 50:
                    await manager.send_status(
                        session_id,
                        phase="narrating",
                        message="Generating narrative..." if lang == "en" else "正在生成叙事...",
                    )
                    await stream_content(session_id, result.content)

                # Send complete response
                await manager.send_complete(
                    session_id,
                    content=result.content,
                    metadata=result.metadata,
                    success=True,
                )
            else:
                await manager.send_complete(
                    session_id,
                    content=result.content or "",
                    metadata=result.metadata,
                    success=False,
                )
                if result.error:
                    await manager.send_error(session_id, result.error)

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as exc:
        await manager.send_error(session_id, str(exc))
        manager.disconnect(session_id)
        await websocket.close(code=1011, reason=str(exc))


@router.websocket("/ws/game/{session_id}/stream")
async def websocket_stream_only_endpoint(
    websocket: WebSocket,
    session_id: str,
):
    """
    Simplified streaming endpoint for receiving game updates only.

    This endpoint doesn't accept player input, only broadcasts
    game state changes to connected clients.

    Useful for spectator mode or multi-device synchronization.
    """
    from src.backend.main import gm_agent

    if gm_agent is None:
        await websocket.close(code=1011, reason="Game engine not initialized")
        return

    await manager.connect(f"{session_id}_observer", websocket)

    try:
        # Send initial state
        await manager.send_phase_change(
            f"{session_id}_observer",
            gm_agent.game_state.current_phase.value,
        )

        # Keep connection alive, waiting for broadcasts
        while True:
            # Just keep the connection open
            # Actual updates will come through the main endpoint
            await asyncio.sleep(30)  # Heartbeat interval
            await websocket.send_json({"type": "heartbeat"})

    except WebSocketDisconnect:
        manager.disconnect(f"{session_id}_observer")
