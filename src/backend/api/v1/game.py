"""
Game API v1 routes.

Provides endpoints for game actions, state management, and dice operations.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/v1", tags=["game"])


@router.post("/game/action")
async def process_player_action(
    action_data: dict[str, Any],
):
    """
    Process a player action through the GM Agent.

    Args:
        action_data: Dictionary containing:
            - player_input: Player's action/description
            - lang: Language code (cn/en, default: cn)

    Returns:
        Response from GM Agent including any agent calls and narrative
    """
    from src.backend.main import gm_agent

    if gm_agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Game engine not initialized",
        )

    try:
        # Extract player input and language
        player_input = action_data.get("player_input", "")
        lang = action_data.get("lang", "cn")

        if not player_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="player_input is required",
            )

        # Process through GM Agent
        result = await gm_agent.process({
            "player_input": player_input,
            "lang": lang,
        })

        # Return response
        return {
            "success": result.success,
            "content": result.content,
            "metadata": result.metadata,
            "error": result.error,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process action: {str(exc)}",
        ) from exc


@router.get("/game/state")
async def get_game_state():
    """
    Get the current game state.

    Returns:
        Current game state including player info, location, etc.
    """
    from src.backend.main import gm_agent

    if gm_agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Game engine not initialized",
        )

    try:
        state = gm_agent.game_state

        return {
            "session_id": state.session_id,
            "world_pack_id": state.world_pack_id,
            "player": {
                "name": state.player.name,
                "concept": state.player.concept.model_dump(),
                "traits": [t.model_dump() for t in state.player.traits],
                "tags": state.player.tags,
                "fate_points": state.player.fate_points,
            },
            "current_location": state.current_location,
            "active_npc_ids": state.active_npc_ids,
            "current_phase": state.current_phase.value,
            "turn_count": state.turn_count,
            "language": state.language,
            "messages": state.messages[-10:],  # Last 10 messages
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get game state: {str(exc)}",
        ) from exc


@router.post("/game/dice-result")
async def submit_dice_result(
    dice_data: dict[str, Any],
):
    """
    Submit a dice roll result.

    Args:
        dice_data: Dictionary containing:
            - total: Dice roll total
            - all_rolls: List of all dice rolled
            - kept_rolls: List of kept dice
            - outcome: Roll outcome (critical/success/partial/failure)

    Returns:
        Confirmation and next steps
    """
    from src.backend.main import gm_agent

    if gm_agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Game engine not initialized",
        )

    try:
        # Validate required fields
        required_fields = ["total", "all_rolls", "kept_rolls", "outcome"]
        for field in required_fields:
            if field not in dice_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}",
                )

        # Store dice result in game state
        gm_agent.game_state.last_check_result = dice_data

        # TODO: Process the result through appropriate agents
        # For now, just acknowledge receipt

        return {
            "success": True,
            "message": "Dice result recorded",
            "next_phase": "narrating",
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process dice result: {str(exc)}",
        ) from exc


@router.get("/game/messages")
async def get_recent_messages(count: int = 10):
    """
    Get recent game messages.

    Args:
        count: Number of recent messages to retrieve (default: 10)

    Returns:
        List of recent messages
    """
    from src.backend.main import gm_agent

    if gm_agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Game engine not initialized",
        )

    try:
        messages = gm_agent.game_state.get_recent_messages(count=count)
        return {
            "messages": messages,
            "count": len(messages),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(exc)}",
        ) from exc


@router.post("/game/reset")
async def reset_game_state():
    """
    Reset the game to initial state.

    Returns:
        Confirmation of reset
    """
    from src.backend.main import gm_agent

    if gm_agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Game engine not initialized",
        )

    try:
        # Reset game state
        gm_agent.game_state.messages = []
        gm_agent.game_state.turn_count = 0
        gm_agent.game_state.last_check_result = None
        gm_agent.game_state.temp_context = {}
        gm_agent.game_state.set_phase("waiting_input")

        return {
            "success": True,
            "message": "Game state reset",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset game: {str(exc)}",
        ) from exc
