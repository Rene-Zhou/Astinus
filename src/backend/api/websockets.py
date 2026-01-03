"""
WebSocket endpoints for real-time game interaction.

Provides streaming responses from the GM Agent.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/game/{session_id}")
async def websocket_game_endpoint(
    websocket: WebSocket,
    session_id: str,
):
    """
    WebSocket endpoint for real-time game interaction.

    Allows streaming responses from the GM Agent.

    Args:
        websocket: WebSocket connection
        session_id: Game session identifier
    """
    from src.backend.main import gm_agent

    if gm_agent is None:
        await websocket.close(code=1011, reason="Game engine not initialized")
        return

    await websocket.accept()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            # Extract player input
            player_input = data.get("player_input", "")
            lang = data.get("lang", "cn")

            if not player_input:
                await websocket.send_json({
                    "error": "player_input is required",
                })
                continue

            # Send acknowledgment
            await websocket.send_json({
                "status": "processing",
                "message": "Processing your action...",
            })

            # Process through GM Agent
            result = await gm_agent.process({
                "player_input": player_input,
                "lang": lang,
            })

            # Send response back to client
            await websocket.send_json({
                "success": result.success,
                "content": result.content,
                "metadata": result.metadata,
                "error": result.error,
                "session_id": session_id,
            })

    except WebSocketDisconnect:
        print(f"Client disconnected from session {session_id}")
    except Exception as exc:
        print(f"WebSocket error: {exc}")
        await websocket.close(code=1011, reason=str(exc))
