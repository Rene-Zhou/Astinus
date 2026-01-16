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
    DICE_CHECK = "dice_check"  # Dice check request from Rule Agent
    DICE_RESULT = "dice_result"  # Dice result from player


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
        self,
        session_id: str,
        phase: str,
        message: str | None = None,
        agent: str | None = None,
    ):
        """Send a status update."""
        data: dict[str, Any] = {"phase": phase, "message": message or ""}
        if agent:
            data["agent"] = agent
        await self.send_message(
            session_id,
            StreamMessage(
                type=MessageType.STATUS,
                data=data,
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

    async def send_dice_check(
        self,
        session_id: str,
        check_request: dict[str, Any],
    ):
        """
        Send a dice check request to the client.

        Args:
            session_id: Session to send to
            check_request: DiceCheckRequest data including:
                - intention: What player is trying to do
                - influencing_factors: Traits/tags affecting roll
                - dice_formula: Dice notation (e.g., "2d6", "3d6kl2")
                - instructions: Explanation of modifiers
        """
        await self.send_message(
            session_id,
            StreamMessage(
                type=MessageType.DICE_CHECK,
                data={"check_request": check_request},
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
    - Client sends player input: {"type": "player_input", "content": "...", "lang": "cn"}
    - Client sends dice result: {"type": "dice_result", "result": 8, "all_rolls": [...], ...}
    - Server sends status updates: {"type": "status", "data": {"phase": "processing"}}
    - Server streams content: {"type": "content", "data": {"chunk": "...", "is_partial": true}}
    - Server sends dice check: {"type": "dice_check", "data": {"check_request": {...}}}
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

            # Route based on message type
            message_type = data.get("type", "player_input")

            if message_type == "player_input":
                await _handle_player_input(session_id, data, gm_agent)
            elif message_type == "dice_result":
                await _handle_dice_result(session_id, data, gm_agent)
            else:
                await manager.send_error(session_id, f"Unknown message type: {message_type}")

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as exc:
        await manager.send_error(session_id, str(exc))
        manager.disconnect(session_id)
        await websocket.close(code=1011, reason=str(exc))


async def _handle_player_input(
    session_id: str,
    data: dict[str, Any],
    gm_agent,
) -> None:
    """
    Handle player input message.

    Args:
        session_id: Game session ID
        data: Message data containing content and lang
        gm_agent: GM Agent instance
    """
    # Extract parameters (support both old and new format)
    player_input = data.get("content") or data.get("player_input", "")
    lang = data.get("lang", "cn")
    stream = data.get("stream", True)

    if not player_input:
        await manager.send_error(session_id, "player_input_required")
        return

    async def status_callback(agent: str, message: str | None) -> None:
        await manager.send_status(
            session_id,
            phase="processing",
            message=message,
            agent=agent,
        )

    await manager.send_status(
        session_id,
        phase="processing",
        message="analyzing_action",
        agent="gm",
    )

    gm_agent.status_callback = status_callback

    try:
        result = await gm_agent.process(
            {
                "player_input": player_input,
                "lang": lang,
            }
        )
    except Exception as exc:
        await manager.send_error(session_id, f"Processing failed: {exc}")
        return
    finally:
        gm_agent.status_callback = None

    # Send phase update
    phase = gm_agent.game_state.current_phase.value
    await manager.send_phase_change(session_id, phase)

    if result.metadata.get("dice_check"):
        # Store the dice check context for later use when processing result
        dice_check = result.metadata["dice_check"]
        gm_agent.game_state.temp_context["pending_dice_check"] = dice_check

        # Update phase to DICE_CHECK
        from src.backend.models.game_state import GamePhase

        gm_agent.game_state.set_phase(GamePhase.DICE_CHECK)
        await manager.send_phase_change(session_id, "dice_check")

        # Send dice check request to client
        await manager.send_dice_check(
            session_id,
            check_request=dice_check,
        )
        return

    if result.success:
        # Stream content if requested and content is substantial
        if stream and len(result.content) > 50:
            await manager.send_status(
                session_id,
                phase="narrating",
                message="generating_narrative",
            )
            await stream_content(session_id, result.content)

        # Send complete response
        await manager.send_complete(
            session_id,
            content=result.content,
            metadata=result.metadata,
            success=True,
        )

        # Return to waiting_input phase after completing response
        from src.backend.models.game_state import GamePhase

        gm_agent.game_state.set_phase(GamePhase.WAITING_INPUT)
        await manager.send_phase_change(session_id, "waiting_input")
    else:
        await manager.send_complete(
            session_id,
            content=result.content or "",
            metadata=result.metadata,
            success=False,
        )
        if result.error:
            await manager.send_error(session_id, result.error)

        # Return to waiting_input phase even on failure
        from src.backend.models.game_state import GamePhase

        gm_agent.game_state.set_phase(GamePhase.WAITING_INPUT)
        await manager.send_phase_change(session_id, "waiting_input")


async def _handle_dice_result(
    session_id: str,
    data: dict[str, Any],
    gm_agent,
) -> None:
    result = data.get("result") or data.get("total")
    all_rolls = data.get("all_rolls", [])
    kept_rolls = data.get("kept_rolls", [])
    outcome = data.get("outcome", "unknown")
    fate_point_spent = data.get("fate_point_spent", False)

    if result is None:
        await manager.send_error(session_id, "dice result is required")
        return

    # Deduct fate point if player spent one to reroll
    if fate_point_spent:
        player = gm_agent.game_state.player
        if player.spend_fate_point():
            await manager.send_status(
                session_id,
                phase="processing",
                message="fate_point_spent",
            )

    pending_check = gm_agent.game_state.temp_context.get("pending_dice_check", {})
    intention = pending_check.get("intention", "action")

    dice_result = {
        "total": result,
        "all_rolls": all_rolls,
        "kept_rolls": kept_rolls,
        "outcome": outcome,
        "intention": intention,
        "success": outcome in ("success", "partial", "critical"),
        "is_partial": outcome == "partial",
        "critical": outcome == "critical",
        "fate_point_spent": fate_point_spent,
    }
    gm_agent.game_state.last_check_result = dice_result
    gm_agent.game_state.temp_context.pop("pending_dice_check", None)

    await manager.send_status(
        session_id,
        phase="processing",
        message="processing_dice_result",
    )

    from src.backend.models.game_state import GamePhase

    gm_agent.game_state.set_phase(GamePhase.PROCESSING)
    await manager.send_phase_change(session_id, "processing")

    lang = gm_agent.game_state.language

    try:
        gm_response = await gm_agent.resume_after_dice(
            dice_result=dice_result,
            lang=lang,
        )
    except Exception as exc:
        await manager.send_error(session_id, f"Processing failed: {exc}")
        gm_agent.game_state.set_phase(GamePhase.WAITING_INPUT)
        await manager.send_phase_change(session_id, "waiting_input")
        return

    phase = gm_agent.game_state.current_phase.value
    await manager.send_phase_change(session_id, phase)

    if gm_response.metadata.get("needs_check") and gm_response.metadata.get("dice_check"):
        dice_check = gm_response.metadata["dice_check"]
        gm_agent.game_state.temp_context["pending_dice_check"] = dice_check
        gm_agent.game_state.set_phase(GamePhase.DICE_CHECK)
        await manager.send_phase_change(session_id, "dice_check")
        await manager.send_dice_check(session_id, check_request=dice_check)
        return

    narrative = gm_response.content
    response_metadata = {
        "dice_result": dice_result,
        "phase": "narrating",
        "player": gm_agent.game_state.player.model_dump(),
    }
    response_metadata.update(gm_response.metadata)

    if len(narrative) > 50:
        await manager.send_status(
            session_id,
            phase="narrating",
            message="generating_narrative",
        )
        await stream_content(session_id, narrative)

    await manager.send_complete(
        session_id,
        content=narrative,
        metadata=response_metadata,
        success=True,
    )

    gm_agent.game_state.set_phase(GamePhase.WAITING_INPUT)
    await manager.send_phase_change(session_id, "waiting_input")


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
