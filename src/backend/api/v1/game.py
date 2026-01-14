"""
Game API v1 routes.

Provides endpoints for game actions, state management, and dice operations.
"""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.backend.agents.npc import NPCAgent

router = APIRouter(prefix="/api/v1", tags=["game"])


class NewGameRequest(BaseModel):
    """Request model for starting a new game."""

    world_pack_id: str = Field(default="demo_pack", description="World pack to load")
    player_name: str = Field(
        default="玩家", description="Player (user) name - distinct from character name"
    )
    preset_character_id: str | None = Field(
        default=None, description="ID of preset character to use (from world pack)"
    )


class NewGameResponse(BaseModel):
    """Response model for new game creation."""

    session_id: str
    player: dict[str, Any]
    game_state: dict[str, Any]
    world_info: dict[str, Any]
    starting_scene: dict[str, Any]
    message: str


@router.post("/game/new", response_model=NewGameResponse)
async def start_new_game(request: NewGameRequest):
    """
    Start a new game session.

    Creates a new game session with the specified world pack and player info.
    Loads the world pack and sets up the starting location with full scene info.

    Args:
        request: NewGameRequest containing world_pack_id and player info

    Returns:
        NewGameResponse with session_id, player data, initial game state,
        world info, and starting scene description
    """
    from src.backend.main import get_world_pack_loader, gm_agent

    if gm_agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Game engine not initialized",
        )

    world_pack_loader = get_world_pack_loader()
    if world_pack_loader is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="World pack loader not initialized",
        )

    try:
        # Generate a new session ID
        session_id = str(uuid.uuid4())

        # Load the world pack
        try:
            world_pack = world_pack_loader.load(request.world_pack_id)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"World pack not found: {request.world_pack_id}. "
                f"Available packs: {world_pack_loader.list_available()}",
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid world pack: {exc}",
            ) from exc

        # Find starting location (look for "starting_area" tag)
        starting_location_id = None
        starting_location = None
        for loc_id, loc in world_pack.locations.items():
            if "starting_area" in loc.tags:
                starting_location_id = loc_id
                starting_location = loc
                break

        # Fallback to first location if no starting_area tag found
        if starting_location_id is None and world_pack.locations:
            starting_location_id = next(iter(world_pack.locations.keys()))
            starting_location = world_pack.locations[starting_location_id]

        if starting_location is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="World pack has no locations defined",
            )

        # Get NPCs at starting location
        active_npc_ids = starting_location.present_npc_ids or []

        # Register NPC Agents for NPCs in the starting location
        # First, remove any existing NPC agents from sub_agents
        npc_keys_to_remove = [k for k in gm_agent.sub_agents if k.startswith("npc_")]
        for key in npc_keys_to_remove:
            del gm_agent.sub_agents[key]

        # Then register new NPC agents for active NPCs
        for npc_id in active_npc_ids:
            npc_data = world_pack.get_npc(npc_id)
            if npc_data:
                # Import LLM from gm_agent
                npc_agent = NPCAgent(llm=gm_agent.llm, vector_store=gm_agent.vector_store)
                agent_key = f"npc_{npc_id}"
                gm_agent.sub_agents[agent_key] = npc_agent

        # Update game state with new session
        gm_agent.game_state.session_id = session_id
        gm_agent.game_state.world_pack_id = request.world_pack_id
        gm_agent.game_state.current_location = starting_location_id
        gm_agent.game_state.active_npc_ids = active_npc_ids

        # Set player (user) name - distinct from character name
        gm_agent.game_state.player_name = request.player_name

        # Handle preset character selection
        if request.preset_character_id:
            preset = world_pack.get_preset_character(request.preset_character_id)
            if preset is None:
                available_presets = [p.id for p in world_pack.preset_characters]
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Preset character not found: {request.preset_character_id}. "
                    f"Available: {available_presets}",
                )
            # Use preset character data
            gm_agent.game_state.player.name = preset.name
            gm_agent.game_state.player.concept = preset.concept
            gm_agent.game_state.player.traits = preset.traits.copy()

        # Reset game state for new session
        gm_agent.game_state.messages = []
        gm_agent.game_state.turn_count = 0
        gm_agent.game_state.last_check_result = None
        gm_agent.game_state.temp_context = {}
        gm_agent.game_state.flags = set()
        gm_agent.game_state.discovered_items = set()

        # Build player data response
        player_data = {
            "name": gm_agent.game_state.player.name,
            "concept": gm_agent.game_state.player.concept.model_dump(),
            "traits": [t.model_dump() for t in gm_agent.game_state.player.traits],
            "tags": gm_agent.game_state.player.tags,
            "fate_points": gm_agent.game_state.player.fate_points,
        }

        # Build game state response
        game_state_data = {
            "current_location": starting_location_id,
            "current_phase": gm_agent.game_state.current_phase.value,
            "turn_count": gm_agent.game_state.turn_count,
            "active_npc_ids": active_npc_ids,
        }

        # Build world info response
        world_info = {
            "id": request.world_pack_id,
            "name": world_pack.info.name.model_dump(),
            "description": world_pack.info.description.model_dump(),
            "version": world_pack.info.version,
            "author": world_pack.info.author,
        }

        # Add optional setting and player_hook if available
        info_dict = world_pack.info.model_dump() if hasattr(world_pack.info, "model_dump") else {}
        if "setting" in info_dict:
            world_info["setting"] = info_dict["setting"]
        if "player_hook" in info_dict:
            world_info["player_hook"] = info_dict["player_hook"]

        # Build starting scene response
        starting_scene = {
            "location_id": starting_location_id,
            "location_name": starting_location.name.model_dump(),
            "description": starting_location.description.model_dump(),
            "items": starting_location.items or [],
            "connected_locations": [],
            "npcs": [],
        }

        # Add atmosphere if available
        loc_dict = (
            starting_location.model_dump() if hasattr(starting_location, "model_dump") else {}
        )
        if "atmosphere" in loc_dict and loc_dict["atmosphere"]:
            starting_scene["atmosphere"] = loc_dict["atmosphere"]

        # Add connected location names
        for loc_id in starting_location.connected_locations or []:
            connected_loc = world_pack.get_location(loc_id)
            if connected_loc:
                starting_scene["connected_locations"].append(
                    {
                        "id": loc_id,
                        "name": connected_loc.name.model_dump(),
                    }
                )

        # Add NPC info - only appearance, NOT name (to prevent metagaming)
        for npc_id in active_npc_ids:
            npc = world_pack.get_npc(npc_id)
            if npc:
                npc_info = {
                    "id": npc_id,
                    # Don't include name - player hasn't learned it yet
                }
                # Use appearance if available, otherwise use first sentence of description
                soul_dict = npc.soul.model_dump() if hasattr(npc.soul, "model_dump") else {}
                if "appearance" in soul_dict and soul_dict["appearance"]:
                    npc_info["appearance"] = soul_dict["appearance"]
                else:
                    # Fallback: use first sentence of description (external appearance only)
                    npc_info["appearance"] = npc.soul.description.model_dump()
                starting_scene["npcs"].append(npc_info)

        return NewGameResponse(
            session_id=session_id,
            player=player_data,
            game_state=game_state_data,
            world_info=world_info,
            starting_scene=starting_scene,
            message="Game session created successfully",
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create game session: {str(exc)}",
        ) from exc


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
        result = await gm_agent.process(
            {
                "player_input": player_input,
                "lang": lang,
            }
        )

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
        Current game state including player info, location, scene details, etc.
    """
    from src.backend.main import get_world_pack_loader, gm_agent

    if gm_agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Game engine not initialized",
        )

    try:
        state = gm_agent.game_state
        world_pack_loader = get_world_pack_loader()

        # Basic state response
        response = {
            "session_id": state.session_id,
            "world_pack_id": state.world_pack_id,
            "player_name": state.player_name,  # PL name (user)
            "player": {
                "name": state.player.name,  # PC name (character)
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

        # Try to add scene details from world pack
        if world_pack_loader:
            try:
                world_pack = world_pack_loader.load(state.world_pack_id)
                location = world_pack.get_location(state.current_location)
                if location:
                    response["current_scene"] = {
                        "location_name": location.name.model_dump(),
                        "description": location.description.model_dump(),
                        "items": location.items or [],
                        "connected_locations": location.connected_locations or [],
                    }

                    # Add NPC names
                    npcs = []
                    for npc_id in state.active_npc_ids:
                        npc = world_pack.get_npc(npc_id)
                        if npc:
                            npcs.append({"id": npc_id, "name": npc.soul.name})
                    response["current_scene"]["npcs"] = npcs
            except Exception:
                # If world pack loading fails, continue without scene details
                pass

        return response

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
        gm_agent.game_state.flags = set()
        gm_agent.game_state.discovered_items = set()
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


@router.get("/game/world-packs")
async def list_world_packs():
    """
    List available world packs.

    Returns:
        List of available world pack IDs
    """
    from src.backend.main import get_world_pack_loader

    world_pack_loader = get_world_pack_loader()
    if world_pack_loader is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="World pack loader not initialized",
        )

    try:
        available = world_pack_loader.list_available()
        return {
            "world_packs": available,
            "count": len(available),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list world packs: {str(exc)}",
        ) from exc


@router.get("/game/world-pack/{pack_id}")
async def get_world_pack_info(pack_id: str):
    """
    Get information about a specific world pack.

    Args:
        pack_id: World pack identifier

    Returns:
        World pack metadata and summary
    """
    from src.backend.main import get_world_pack_loader

    world_pack_loader = get_world_pack_loader()
    if world_pack_loader is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="World pack loader not initialized",
        )

    try:
        world_pack = world_pack_loader.load(pack_id)

        # Build info dict with optional setting and player_hook
        info_dict = {
            "name": world_pack.info.name.model_dump(),
            "description": world_pack.info.description.model_dump(),
            "version": world_pack.info.version,
            "author": world_pack.info.author,
        }

        # Add setting if available
        if world_pack.info.setting:
            info_dict["setting"] = {
                "era": world_pack.info.setting.era.model_dump(),
                "genre": world_pack.info.setting.genre.model_dump(),
                "tone": world_pack.info.setting.tone.model_dump(),
            }

        # Add player_hook if available
        if world_pack.info.player_hook:
            info_dict["player_hook"] = world_pack.info.player_hook.model_dump()

        return {
            "id": pack_id,
            "info": info_dict,
            "summary": {
                "locations": len(world_pack.locations),
                "npcs": len(world_pack.npcs),
                "lore_entries": len(world_pack.entries),
                "preset_characters": len(world_pack.preset_characters),
            },
            "locations": [
                {
                    "id": loc_id,
                    "name": loc.name.model_dump(),
                    "tags": loc.tags,
                }
                for loc_id, loc in world_pack.locations.items()
            ],
            "npcs": [
                {
                    "id": npc_id,
                    "name": npc.soul.name,
                    "location": npc.body.location,
                }
                for npc_id, npc in world_pack.npcs.items()
            ],
            "preset_characters": [
                {
                    "id": preset.id,
                    "name": preset.name,
                    "concept": preset.concept.model_dump(),
                    "traits": [t.model_dump() for t in preset.traits],
                }
                for preset in world_pack.preset_characters
            ],
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"World pack not found: {pack_id}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get world pack info: {str(exc)}",
        ) from exc
