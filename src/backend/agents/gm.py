"""GM Agent - Central orchestrator using ReAct loop for multi-agent coordination."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.backend.agents.base import AgentResponse, BaseAgent


class GMActionType(str, Enum):
    RESPOND = "RESPOND"
    CALL_AGENT = "CALL_AGENT"


@dataclass
class GMAction:
    action_type: GMActionType
    content: str = ""
    agent_name: str | None = None
    agent_context: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""

StatusCallback = Callable[[str, str | None], Awaitable[None]]
from src.backend.core.config import get_settings
from src.backend.core.prompt_loader import get_prompt_loader
from src.backend.models.game_state import GameState
from src.backend.services.game_logger import get_game_logger
from src.backend.services.location_context import LocationContextService
from src.backend.services.vector_store import VectorStoreService
from src.backend.services.world import WorldPackLoader


class GMAgent(BaseAgent):
    """
    GM Agent - central orchestrator.

    Responsibilities:
    - Parse player intent (examine, move, talk, act, etc.)
    - Decide which sub-agents to call (Rule, NPC, Lore)
    - Prepare precise context slices for each sub-agent
    - Synthesize responses into unified narrative
    - Maintain global game state

    Examples:
        >>> gm = GMAgent(llm, sub_agents={"rule": rule_agent})
        >>> result = await gm.process({"player_input": "我要逃跑"})
    """

    def __init__(
        self,
        llm,
        sub_agents: dict[str, BaseAgent],
        game_state: GameState,
        world_pack_loader: WorldPackLoader | None = None,
        vector_store: VectorStoreService | None = None,
    ):
        """
        Initialize GM Agent.

        Args:
            llm: Language model instance
            sub_agents: Dictionary of sub-agents by name
            game_state: Global game state (owned by GM)
            world_pack_loader: Optional loader for world packs (for NPC data)
            vector_store: Optional VectorStoreService for conversation history retrieval
        """
        super().__init__(llm, "gm_agent")
        self.sub_agents = sub_agents
        self.game_state = game_state
        self.world_pack_loader = world_pack_loader
        self.vector_store = vector_store
        self.prompt_loader = get_prompt_loader()
        self.status_callback: StatusCallback | None = None

    async def process(self, input_data: dict[str, Any]) -> AgentResponse:
        player_input = input_data.get("player_input", "")
        lang = input_data.get("lang", "cn")

        if not player_input:
            return AgentResponse(
                content="",
                success=False,
                error="GM Agent: No player input provided",
                metadata={"agent": self.agent_name},
            )

        if self.status_callback:
            await self.status_callback("gm", None)

        self.game_state.add_message(role="player", content=player_input)

        return await self._run_react_loop(
            player_input=player_input,
            lang=lang,
            iteration=0,
            agent_results=[],
            dice_result=None,
        )

    async def resume_after_dice(
        self,
        dice_result: dict[str, Any],
        lang: str = "cn",
    ) -> AgentResponse:
        pending_state = self.game_state.react_pending_state
        if not pending_state:
            return AgentResponse(
                content="",
                success=False,
                error="No pending ReAct state to resume",
                metadata={"agent": self.agent_name},
            )

        player_input = pending_state["player_input"]
        iteration = pending_state["iteration"]
        agent_results = pending_state["agent_results"]

        self.game_state.clear_react_state()

        return await self._run_react_loop(
            player_input=player_input,
            lang=lang,
            iteration=iteration,
            agent_results=agent_results,
            dice_result=dice_result,
        )

    async def _run_react_loop(
        self,
        player_input: str,
        lang: str,
        iteration: int,
        agent_results: list[dict[str, Any]],
        dice_result: dict[str, Any] | None,
    ) -> AgentResponse:
        logger = get_game_logger()
        max_iterations = get_settings().game.gm_max_iterations
        agents_called: list[str] = []

        while iteration < max_iterations:
            force_output = iteration >= max_iterations - 1

            action = await self._get_react_action(
                player_input=player_input,
                lang=lang,
                iteration=iteration,
                max_iterations=max_iterations,
                agent_results=agent_results,
                dice_result=dice_result,
                force_output=force_output,
            )

            if action.action_type == GMActionType.RESPOND:
                return self._finalize_response(
                    narrative=action.content,
                    player_input=player_input,
                    agents_called=agents_called,
                    target_location=action.agent_context.get("target_location"),
                    logger=logger,
                )

            elif action.action_type == GMActionType.CALL_AGENT:
                agent_name = action.agent_name
                if not agent_name:
                    iteration += 1
                    continue

                agents_called.append(agent_name)

                if self.status_callback:
                    await self.status_callback(agent_name, None)

                agent_context = self._prepare_agent_context(
                    agent_name=agent_name,
                    player_input=player_input,
                    lang=lang,
                    provided_context=action.agent_context,
                    dice_result=dice_result,
                )

                result = await self._invoke_sub_agent(agent_name, agent_context)
                agent_results.append({
                    "agent": agent_name,
                    "content": result.content if result.success else "",
                    "metadata": result.metadata,
                    "success": result.success,
                })

                if agent_name == "rule" and result.metadata.get("needs_check"):
                    dice_check = result.metadata.get("dice_check", {})
                    narrative = await self._generate_pre_check_narrative(
                        player_input, agent_results, lang
                    )

                    self.game_state.save_react_state(
                        iteration=iteration + 1,
                        llm_messages=[],
                        player_input=player_input,
                        agent_results=agent_results,
                    )

                    from src.backend.models.game_state import GamePhase
                    self.game_state.set_phase(GamePhase.DICE_CHECK)

                    return AgentResponse(
                        content=narrative,
                        success=True,
                        metadata={
                            "agent": self.agent_name,
                            "needs_check": True,
                            "dice_check": dice_check,
                            "agents_called": agents_called,
                        },
                    )

                dice_result = None
                iteration += 1

            else:
                iteration += 1

        return AgentResponse(
            content="",
            metadata={"agents_called": agents_called},
            success=False,
            error="Unable to generate narrative: max iterations reached",
        )

    async def _get_react_action(
        self,
        player_input: str,
        lang: str,
        iteration: int,
        max_iterations: int,
        agent_results: list[dict[str, Any]],
        dice_result: dict[str, Any] | None,
        force_output: bool,
    ) -> GMAction:
        template = self.prompt_loader.get_template("gm_agent")
        scene_context = self._get_scene_context(lang)

        recent_messages = self.game_state.get_recent_messages(
            count=get_settings().game.conversation_history_length
        )
        conversation_history = [
            {
                "turn": msg.get("turn", 0),
                "role": "玩家" if msg.get("role") == "player" else "GM",
                "content": msg.get("content", "")[:200],
            }
            for msg in recent_messages
        ]

        def _format_agent_result(r: dict[str, Any]) -> dict[str, Any]:
            """Format agent result for GM prompt - parse NPC metadata for clarity."""
            agent_name = r.get("agent", "unknown")
            metadata = r.get("metadata", {})
            
            # For NPC agents, parse and format metadata for clarity
            if agent_name.startswith("npc_") or agent_name == "npc":
                response = r.get("content", "")
                emotion = metadata.get("emotion", "unknown")
                action = metadata.get("action", "")
                relation_change = metadata.get("relation_change", 0)
                relation_reason = metadata.get("relation_reason", "")

                # Build structured content
                parts = [f"回应: {response}" if response else "回应: (无)"]
                if emotion != "unknown":
                    parts.append(f"情绪: {emotion}")
                if action:
                    # Truncate action if too long
                    if len(action) > 300:
                        action = action[:300] + "..."
                    parts.append(f"动作: {action}")
                if relation_change != 0:
                    parts.append(f"关系变化: {relation_change:+d} ({relation_reason})")
                
                return {
                    "agent": agent_name,
                    "content": " | ".join(parts),
                }
            else:
                # For other agents, keep simple format
                return {
                    "agent": agent_name,
                    "content": r.get("content", ""),
                }

        formatted_agent_results = [_format_agent_result(r) for r in agent_results]

        template_vars = {
            "region_name": scene_context.get("region_name"),
            "region_tone": scene_context.get("region_tone"),
            "atmosphere_keywords": scene_context.get("atmosphere_keywords", []),
            "current_location": self.game_state.current_location,
            "location_description": scene_context.get("location_description"),
            "location_atmosphere": scene_context.get("location_atmosphere"),
            "visible_items": scene_context.get("visible_items", []),
            "hidden_items_hints": scene_context.get("hidden_items_hints"),
            "connected_locations": scene_context.get("connected_locations", []),
            "basic_lore": scene_context.get("basic_lore", []),
            "atmosphere_guidance": scene_context.get("atmosphere_guidance"),
            "active_npcs_details": scene_context.get("active_npcs_details", []),
            "world_background": scene_context.get("world_background"),
            "game_phase": self.game_state.current_phase.value,
            "turn_count": self.game_state.turn_count,
            "current_iteration": iteration + 1,
            "max_iterations": max_iterations,
            "conversation_history": conversation_history,
            "player_input": player_input,
            "agent_results": formatted_agent_results if agent_results else None,
            "dice_result": dice_result,
            "force_output": force_output,
        }

        system_message = template.get_system_message(lang=lang, **template_vars)
        user_message = template.get_user_message(lang=lang, **template_vars)

        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=user_message),
        ]

        llm_response = await self._call_llm(messages)

        logger = get_game_logger()
        logger.log_llm_raw_response(
            agent_name="gm_agent_react",
            prompt_summary=f"Iteration {iteration + 1}/{max_iterations} | Player: {player_input[:50]}",
            raw_response=llm_response,
        )

        try:
            result = self._extract_json_from_response(llm_response)
        except ValueError:
            return GMAction(
                action_type=GMActionType.RESPOND,
                content=llm_response,
                reasoning="Failed to parse JSON, using raw response as narrative",
            )

        action_str = result.get("action", "RESPOND").upper()

        if action_str == "RESPOND":
            return GMAction(
                action_type=GMActionType.RESPOND,
                content=result.get("narrative", ""),
                agent_context={"target_location": result.get("target_location")},
                reasoning=result.get("reasoning", ""),
            )
        elif action_str == "CALL_AGENT":
            return GMAction(
                action_type=GMActionType.CALL_AGENT,
                agent_name=result.get("agent_name"),
                agent_context=result.get("agent_context", {}),
                reasoning=result.get("reasoning", ""),
            )
        else:
            return GMAction(
                action_type=GMActionType.RESPOND,
                content=result.get("narrative", llm_response),
                reasoning="Unknown action type, defaulting to RESPOND",
            )

    def _prepare_agent_context(
        self,
        agent_name: str,
        player_input: str,
        lang: str,
        provided_context: dict[str, Any],
        dice_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if agent_name == "rule":
            return self._slice_context_for_rule(player_input, lang)
        elif agent_name == "lore":
            return self._slice_context_for_lore(player_input, lang)
        elif agent_name.startswith("npc_"):
            npc_id = agent_name[4:]
            return self._slice_context_for_npc(npc_id, player_input, lang, dice_result)
        else:
            context = {"player_input": player_input, "lang": lang}
            context.update(provided_context)
            return context

    async def _invoke_sub_agent(
        self,
        agent_name: str,
        context: dict[str, Any],
    ) -> AgentResponse:
        actual_agent_name = agent_name
        if agent_name.startswith("npc_"):
            actual_agent_name = "npc"

        if actual_agent_name in self.sub_agents:
            agent = self.sub_agents[actual_agent_name]
            if agent_name.startswith("npc_"):
                context["npc_id"] = agent_name[4:]
            return await agent.ainvoke(context)
        else:
            return AgentResponse(
                content="",
                success=False,
                error=f"Agent not found: {agent_name}",
                metadata={"agent": agent_name},
            )

    async def _generate_pre_check_narrative(
        self,
        player_input: str,
        agent_results: list[dict[str, Any]],
        lang: str,
    ) -> str:
        rule_result = next(
            (r for r in agent_results if r.get("agent") == "rule"),
            None
        )
        if rule_result:
            content = rule_result.get("content")
            if content and isinstance(content, str):
                return content

        if lang == "cn":
            return f"你准备{player_input}。这需要进行一次检定。"
        return f"You prepare to {player_input}. This requires a check."

    def _finalize_response(
        self,
        narrative: str,
        player_input: str,
        agents_called: list[str],
        target_location: str | None,
        logger,
    ) -> AgentResponse:
        if target_location:
            self._handle_scene_transition(target_location)

        logger.log_player_input(self.game_state.turn_count, player_input)

        self.game_state.increment_turn()
        self.game_state.add_message(
            role="assistant",
            content=narrative,
            metadata={"phase": "gm_response", "agents_called": agents_called},
        )

        logger.log_gm_output(
            self.game_state.turn_count,
            narrative,
            "react_response",
            agents_called,
        )

        from src.backend.models.game_state import GamePhase
        self.game_state.set_phase(GamePhase.WAITING_INPUT)

        return AgentResponse(
            content=narrative,
            success=True,
            metadata={
                "agent": self.agent_name,
                "agents_called": agents_called,
            },
        )

    def _get_scene_context(self, lang: str) -> dict[str, Any]:
        """
        Get complete hierarchical scene context from the world pack.

        Uses LocationContextService to build layered context with regions,
        locations, and discovery tiers.

        Args:
            lang: Language code (cn/en)

        Returns:
            Dict containing region, location, lore, NPCs, etc.
        """
        context: dict[str, Any] = {
            "region_name": "Unknown",
            "region_tone": "",
            "atmosphere_keywords": [],
            "location_description": None,
            "location_atmosphere": "",
            "visible_items": [],
            "hidden_items_hints": "",
            "connected_locations": [],
            "active_npcs_details": [],
            "basic_lore": [],
            "atmosphere_guidance": "",
            "world_background": None,
        }

        if not self.world_pack_loader:
            return context

        try:
            # Use LocationContextService to get hierarchical context
            context_service = LocationContextService(self.world_pack_loader)

            hierarchical_context = context_service.get_context_for_location(
                world_pack_id=self.game_state.world_pack_id,
                location_id=self.game_state.current_location,
                discovered_items=self.game_state.discovered_items,
                lang=lang,
            )

            # Transform for prompt template
            context.update(
                {
                    "region_name": hierarchical_context["region"]["name"],
                    "region_tone": hierarchical_context["region"]["narrative_tone"],
                    "atmosphere_keywords": hierarchical_context["region"]["atmosphere_keywords"],
                    "location_description": hierarchical_context["location"]["description"],
                    "location_atmosphere": hierarchical_context["location"]["atmosphere"],
                    "visible_items": hierarchical_context["location"]["visible_items"],
                    "hidden_items_hints": self._generate_hidden_item_hints(
                        hierarchical_context["location"]["hidden_items_remaining"], lang
                    ),
                    "basic_lore": hierarchical_context["basic_lore"],
                    "atmosphere_guidance": hierarchical_context["atmosphere_guidance"],
                }
            )

            # Load world pack for additional data
            world_pack = self.world_pack_loader.load(self.game_state.world_pack_id)

            location = world_pack.get_location(self.game_state.current_location)
            if location:
                connected = []
                for loc_id in location.connected_locations or []:
                    connected_loc = world_pack.get_location(loc_id)
                    if connected_loc:
                        connected.append(f"{connected_loc.name.get(lang)} (ID: {loc_id})")
                    else:
                        connected.append(f"(ID: {loc_id})")
                context["connected_locations"] = connected

            # Get NPC details for active NPCs
            npcs_details = []
            for npc_id in self.game_state.active_npc_ids:
                npc = world_pack.get_npc(npc_id)
                if npc:
                    # Get a brief description (first 100 chars of description)
                    description = npc.soul.description.get(lang)
                    brief = description[:100] + "..." if len(description) > 100 else description
                    npcs_details.append(
                        {
                            "id": npc_id,
                            "name": npc.soul.name,
                            "brief": brief,
                        }
                    )
            context["active_npcs_details"] = npcs_details

            # Get world background from constant entries
            constant_entries = world_pack.get_constant_entries()
            if constant_entries:
                backgrounds = []
                for entry in constant_entries:
                    content = entry.content.get(lang)
                    if content:
                        backgrounds.append(content)
                if backgrounds:
                    context["world_background"] = "\n".join(backgrounds)

        except Exception:
            # If loading fails, return default context
            pass

        return context

    def _generate_hidden_item_hints(self, hidden_items: list[str], lang: str) -> str:
        """
        Generate subtle hints for hidden items without revealing IDs.

        Args:
            hidden_items: List of hidden item IDs remaining to discover
            lang: Language code

        Returns:
            Hint string (empty if no hidden items)
        """
        if not hidden_items:
            return ""
        if lang == "cn":
            return "房间里似乎还有一些不易察觉的细节..."
        else:
            return "There seem to be some subtle details yet to notice..."

    def _get_current_region_id(self) -> str | None:
        """
        Get the current region ID based on the player's location.

        Returns:
            Region ID or None if not found
        """
        if not self.world_pack_loader:
            return None

        try:
            world_pack = self.world_pack_loader.load(self.game_state.world_pack_id)
            region = world_pack.get_location_region(self.game_state.current_location)
            return region.id if region else None
        except Exception:
            return None

    def _handle_scene_transition(self, target_location: str) -> bool:
        """
        Handle scene transition when player moves to a new location.

        Args:
            target_location: Target location ID from LLM response

        Returns:
            True if transition was successful
        """
        logger = get_game_logger()
        from_location = self.game_state.current_location

        if not self.world_pack_loader:
            logger.log_scene_transition(from_location, target_location, False)
            return False

        try:
            world_pack = self.world_pack_loader.load(self.game_state.world_pack_id)
            current_location = world_pack.get_location(from_location)

            if not current_location:
                logger.log_error("scene_transition", f"Current location not found: {from_location}")
                logger.log_scene_transition(from_location, target_location, False)
                return False

            if target_location not in (current_location.connected_locations or []):
                logger.log_error(
                    "scene_transition",
                    f"Target not connected: {target_location}",
                    {"connected": current_location.connected_locations},
                )
                logger.log_scene_transition(from_location, target_location, False)
                return False

            target_loc = world_pack.get_location(target_location)
            if not target_loc:
                logger.log_error("scene_transition", f"Target location not found: {target_location}")
                logger.log_scene_transition(from_location, target_location, False)
                return False

            npc_ids = target_loc.present_npc_ids or []
            self.game_state.update_location(target_location, npc_ids)
            logger.log_scene_transition(from_location, target_location, True, npc_ids)
            logger.log_state_change("current_location", from_location, target_location, "scene_transition")
            return True

        except Exception as e:
            logger.log_error("scene_transition", str(e))
            logger.log_scene_transition(from_location, target_location, False)
            return False

    async def _parse_intent_and_plan(
        self,
        player_input: str,
        lang: str,
    ) -> dict[str, Any]:
        """
        Parse player intent and create agent dispatch plan.

        Args:
            player_input: Player's action/description
            lang: Language code

        Returns:
            Dict with:
                - success: bool
                - player_intent: str
                - can_respond_directly: bool
                - direct_response: str (if can_respond_directly)
                - agents_to_call: list[str]
                - context_slices: dict[str, dict]
                - error: str (if success=False)
        """
        # Get template
        template = self.prompt_loader.get_template("gm_agent")

        # Get scene context from world pack
        scene_context = self._get_scene_context(lang)

        recent_messages = self.game_state.get_recent_messages(
            count=get_settings().game.conversation_history_length
        )
        conversation_history = [
            {
                "turn": msg.get("turn", 0),
                "role": "玩家" if msg.get("role") == "player" else "GM",
                "content": msg.get("content", "")[:200],
            }
            for msg in recent_messages
        ]

        # Prepare template variables with hierarchical context
        template_vars = {
            # Region context (NEW)
            "region_name": scene_context.get("region_name"),
            "region_tone": scene_context.get("region_tone"),
            "atmosphere_keywords": scene_context.get("atmosphere_keywords", []),
            # Location context
            "current_location": self.game_state.current_location,
            "location_description": scene_context.get("location_description"),
            "location_atmosphere": scene_context.get("location_atmosphere"),
            "visible_items": scene_context.get("visible_items", []),
            "hidden_items_hints": scene_context.get("hidden_items_hints"),
            "connected_locations": scene_context.get("connected_locations", []),
            # Basic lore (NEW)
            "basic_lore": scene_context.get("basic_lore", []),
            "atmosphere_guidance": scene_context.get("atmosphere_guidance"),
            # NPCs and world
            "active_npcs_details": scene_context.get("active_npcs_details", []),
            "world_background": scene_context.get("world_background"),
            # Game state
            "game_phase": self.game_state.current_phase.value,
            "turn_count": self.game_state.turn_count,
            "conversation_history": conversation_history,
            "player_input": player_input,
        }

        # Build prompt
        system_message = template.get_system_message(lang=lang, **template_vars)
        user_message = template.get_user_message(lang=lang, **template_vars)

        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=user_message),
        ]

        llm_response = await self._call_llm(messages)

        logger = get_game_logger()
        logger.log_llm_raw_response(
            agent_name="gm_agent",
            prompt_summary=f"Player: {player_input} | Location: {self.game_state.current_location}",
            raw_response=llm_response,
        )

        try:
            result = self._extract_json_from_response(llm_response)
            logger.log_llm_raw_response(
                agent_name="gm_agent",
                prompt_summary="PARSED JSON",
                raw_response=str(result),
                parsed_json=result,
            )
        except ValueError as exc:
            logger.log_error("gm_parse_json", str(exc), {"raw": llm_response[:500]})
            return {
                "success": False,
                "error": f"Failed to parse GM dispatch plan: {exc}",
            }

        # Validate and prepare context slices
        player_intent = result.get("player_intent", "unknown")
        can_respond_directly = result.get("can_respond_directly", False)
        direct_response = result.get("direct_response", "")
        target_location = result.get("target_location")
        agents_to_call = result.get("agents_to_call", [])
        context_slices = result.get("context_slices", {})

        # Prepare context for Rule Agent if needed
        if "rule" in agents_to_call:
            context_slices["rule"] = self._slice_context_for_rule(
                player_input,
                lang,
            )

        # Prepare context for Lore Agent if needed
        if "lore" in agents_to_call:
            context_slices["lore"] = self._slice_context_for_lore(
                player_input,
                lang,
            )

        # Prepare context for NPC Agents if needed
        for agent_name in agents_to_call:
            if agent_name.startswith("npc_"):
                npc_id = agent_name[4:]  # Remove "npc_" prefix
                context_slices[agent_name] = self._slice_context_for_npc(
                    npc_id,
                    player_input,
                    lang,
                )

        return {
            "success": True,
            "player_intent": player_intent,
            "can_respond_directly": can_respond_directly,
            "direct_response": direct_response,
            "target_location": target_location,
            "agents_to_call": agents_to_call,
            "context_slices": context_slices,
        }

    def _slice_context_for_rule(
        self,
        player_input: str,
        lang: str,
    ) -> dict[str, Any]:
        """
        Prepare context slice for Rule Agent.

        Only gives Rule Agent what it needs - prevents information leakage.

        Args:
            player_input: Player's action
            lang: Language code

        Returns:
            Context slice for Rule Agent
        """
        return {
            "action": player_input,
            "character": {
                "name": self.game_state.player.name,
                "concept": self.game_state.player.concept.model_dump(),
                "traits": [t.model_dump() for t in self.game_state.player.traits],
            },
            "tags": self.game_state.player.tags,
            "lang": lang,
        }

    def _slice_context_for_lore(
        self,
        player_input: str,
        lang: str,
    ) -> dict[str, Any]:
        """
        Prepare context slice for Lore Agent.

        Includes location filtering metadata for region/location-based lore.

        Args:
            player_input: Player's query or action
            lang: Language code

        Returns:
            Context slice for Lore Agent
        """
        return {
            "query": player_input,
            "context": f"Player is at {self.game_state.current_location}",
            "world_pack_id": self.game_state.world_pack_id,
            "lang": lang,
            # NEW: Location filtering
            "current_location": self.game_state.current_location,
            "current_region": self._get_current_region_id(),
            "discovered_items": list(self.game_state.discovered_items),
        }

    def _slice_context_for_npc(
        self,
        npc_id: str,
        player_input: str,
        lang: str,
        dice_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Prepare context slice for NPC Agent.

        Only gives NPC Agent relevant context - prevents leakage.

        Args:
            npc_id: NPC identifier
            player_input: Player's action
            lang: Language code
            dice_result: Optional dice check result from a previous roll

        Returns:
            Context slice for NPC Agent
        """
        recent_messages = self.game_state.get_recent_messages(count=10)
        npc_messages = [
            msg for msg in recent_messages if msg.get("metadata", {}).get("npc_id") == npc_id
        ]

        npc_data = None
        if self.world_pack_loader:
            try:
                world_pack = self.world_pack_loader.load(self.game_state.world_pack_id)
                npc = world_pack.get_npc(npc_id)
                if npc:
                    npc_data = npc.model_dump()
            except Exception:
                pass

        narrative_style = self._determine_npc_narrative_style(npc_messages, npc_data)

        context = {
            "npc_id": npc_id,
            "player_input": player_input,
            "recent_messages": npc_messages,
            "lang": lang,
            "narrative_style": narrative_style,
            "context": {
                "location": self.game_state.current_location,
                "world_pack_id": self.game_state.world_pack_id,
            },
        }

        if npc_data:
            context["npc_data"] = npc_data

        if dice_result:
            # Don't pass dice_result to NPC - only pass roleplay direction
            context["roleplay_direction"] = self._generate_roleplay_direction(dice_result, lang)

        return context

    def _generate_roleplay_direction(
        self,
        dice_result: dict[str, Any],
        lang: str,
    ) -> str:
        """
        Generate roleplay direction for NPC based on dice check outcome.

        NPC doesn't need to know the dice result or game rules,
        only the direction for how to roleplay the response.

        Args:
            dice_result: Dice check result with 'outcome' field
            lang: Language code

        Returns:
            Roleplay direction string for NPC prompt, or empty if no outcome
        """
        outcome = dice_result.get("outcome", "")

        if not outcome:
            return ""

        directions = {
            "cn": {
                "critical_success": "NPC 应该非常积极地回应，态度明显软化甚至热情，愿意主动提供帮助或重要信息。",
                "success": "NPC 应该积极回应，态度有所软化，愿意提供帮助或信息。",
                "partial": "NPC 的态度应有所松动，但仍保持一定警惕，可能只透露有限信息、给出警告、或提出额外条件。",
                "failure": "NPC 应该拒绝请求，态度可能更加冷淡或警惕。",
                "critical_failure": "NPC 应该强烈拒绝，态度恶化，可能产生敌意或采取对抗行动。",
            },
            "en": {
                "critical_success": "The NPC should respond very positively, with a notably softened or even warm attitude, willing to proactively offer help or important information.",
                "success": "The NPC should respond positively, with a softened attitude, willing to provide help or information.",
                "partial": "The NPC's attitude should soften somewhat, but remain guarded, perhaps only revealing limited information, giving a warning, or requesting additional conditions.",
                "failure": "The NPC should refuse the request, with a colder or more guarded attitude.",
                "critical_failure": "The NPC should strongly refuse, with worsened attitude, possibly showing hostility or taking confrontational action.",
            }
        }

        lang_directions = directions.get(lang, directions["en"])
        return lang_directions.get(outcome, "")

    def _determine_npc_narrative_style(
        self,
        npc_messages: list[dict[str, Any]],
        npc_data: dict[str, Any] | None,
    ) -> str:
        current_turn = self.game_state.turn_count

        if npc_messages:
            last_npc_turn = max(msg.get("turn", 0) for msg in npc_messages)
            turns_since_last = current_turn - last_npc_turn

            if turns_since_last <= 2:
                return "brief"

            if len(npc_messages) >= 3:
                recent_three = sorted(npc_messages, key=lambda m: m.get("turn", 0))[-3:]
                turns_span = recent_three[-1].get("turn", 0) - recent_three[0].get("turn", 0)
                if turns_span <= 5:
                    return "brief"

        return "detailed"

    def _retrieve_relevant_history(
        self,
        session_id: str,
        player_input: str,
        all_messages: list[dict[str, Any]],
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant conversation history.

        If messages < 10, return all messages.
        If messages >= 10, use vector search to find top 5 relevant messages,
        then sort by timestamp to maintain chronological order.

        Args:
            session_id: Session identifier
            player_input: Current player input (for semantic search)
            all_messages: All conversation messages
            n_results: Number of messages to retrieve (default: 5)

        Returns:
            List of relevant messages (sorted by timestamp if using vector search)
        """
        # If less than 10 messages, return all
        if len(all_messages) < 10:
            return all_messages

        # If no vector store, return recent messages
        if not self.vector_store:
            return all_messages[-n_results:]

        try:
            collection_name = f"conversation_history_{session_id}"

            # Search for relevant messages
            results = self.vector_store.search(
                collection_name=collection_name,
                query_text=player_input,
                n_results=n_results,
                include=["documents", "metadatas", "distances", "ids"],
            )

            if not results["documents"] or not results["documents"][0]:
                # Fallback to recent messages if search fails
                return all_messages[-n_results:]

            # Extract message IDs and sort by turn to maintain chronological order
            retrieved_ids = set(results["ids"][0])
            retrieved_messages = [
                msg for msg in all_messages if f"{session_id}_msg_{msg['turn']}" in retrieved_ids
            ]

            # Sort by turn (chronological order)
            retrieved_messages.sort(key=lambda m: m["turn"])

            return retrieved_messages

        except Exception:
            # Fail gracefully - return recent messages
            return all_messages[-n_results:]

    def _build_prompt(self, input_data: dict[str, Any]) -> list[SystemMessage]:
        """
        Build prompt for LLM.

        Note: GM Agent uses a different pattern (_parse_intent_and_plan)
        so this method is not used in practice, but required by BaseAgent.

        Args:
            input_data: Input data (unused)

        Returns:
            Empty list (not used)
        """
        # GM Agent uses _parse_intent_and_plan instead
        return []

    async def _synthesize_response(
        self,
        player_input: str,
        player_intent: str,
        agent_results: list[dict],
        lang: str,
    ) -> str:
        """
        Synthesize sub-agent responses into unified narrative.

        Uses LLM to transform agent results into coherent narrative.

        Args:
            player_input: Original player input
            player_intent: Parsed intent
            agent_results: Results from sub-agents
            lang: Language code

        Returns:
            Unified narrative response
        """
        # Collect agent outputs
        agent_outputs = []
        for agent_result in agent_results:
            if "result" in agent_result and agent_result["result"].success:
                result = agent_result["result"]
                agent_outputs.append(
                    {
                        "agent": agent_result["agent"],
                        "content": result.content,
                        "metadata": result.metadata,
                    }
                )
            elif "error" in agent_result:
                agent_outputs.append(
                    {
                        "agent": agent_result["agent"],
                        "error": agent_result["error"],
                    }
                )

        # If no successful agent outputs, return error
        if not agent_outputs or all("error" in o for o in agent_outputs):
            agents_in_loop = [o.get("agent") for o in agent_outputs if "error" not in o]
            return AgentResponse(
                content="",
                metadata={"agents_called": agents_in_loop},
                success=False,
                error="No successful agent outputs from ReAct loop",
            )

        # Build synthesis prompt
        if lang == "cn":
            synthesis_prompt = f"""请将以下 Agent 的响应综合成一段连贯的叙事文本。
使用第二人称（"你"），保持沉浸感。

【信息控制规则 - 必须遵守】：
1. 绝对禁止在叙事中显示任何 ID、标识符或技术名称（如 village_well、old_guard 等）
2. 除非 NPC 已自我介绍或玩家通过其他方式得知，否则不要使用 NPC 的真名
3. 不要透露玩家角色不应该知道的背景信息
4. 不要提及 Agent 的名称或任何技术细节
5. 所有信息的揭示必须有合理的来源（NPC告知、检定成功、阅读文件等）

【叙事整合规则 - 禁止加戏】：
1. 玩家行动：玩家输入中已描述的行动，不要重复或润色（玩家说"我走到老人面前"，你不需要再描述"走向"、"站定"等）
2. NPC 输出：
   - "对白" 字段：原样呈现为角色说的话
   - "动作" 字段：这是 NPC Agent 精心设计的描写，原样整合到叙事中，不要修改、替换或另外创作
   - "情绪" 字段：仅供参考语气，不需要额外描述
3. 你的职责是"连接"而非"创作"：只添加必要的过渡语句，不要创作额外的动作、神态、语气描写

玩家意图：{player_intent}
玩家输入：{player_input}

Agent 响应：
"""
        else:
            synthesis_prompt = f"""Please synthesize the following agent responses into a coherent narrative.
Use second person ("you"), maintain immersion.

【Information Control Rules - MUST FOLLOW】:
1. NEVER show any IDs, identifiers, or technical names in narrative (e.g., village_well, old_guard)
2. Do NOT use NPC's real name unless they have introduced themselves or player learned it otherwise
3. Do NOT reveal background information the player character shouldn't know
4. Do NOT mention agent names or any technical details
5. All information revelation must have a reasonable source (NPC told them, successful check, read document)

【Narrative Integration Rules - NO EMBELLISHMENT】:
1. Player actions: Do NOT repeat or embellish actions already described in player input (if player said "I walk to the old man", don't add "you stride toward", "you halt", etc.)
2. NPC output:
   - "Dialogue" field: Present as-is as the character's spoken words
   - "Action" field: This is carefully crafted by the NPC Agent - integrate it as-is, do NOT modify, replace, or create alternatives
   - "Emotion" field: Reference only for tone, no need to describe explicitly
3. Your role is to "connect" not to "create": Only add necessary transitions, do NOT create additional actions, expressions, or tone descriptions

Player intent: {player_intent}
Player input: {player_input}

Agent responses:
"""

        for output in agent_outputs:
            if "content" in output:
                agent_name = output["agent"]
                content = output["content"]

                if agent_name.startswith("npc_") and output.get("metadata"):
                    metadata = output["metadata"]
                    action = metadata.get("action", "")
                    emotion = metadata.get("emotion", "")

                    if lang == "cn":
                        npc_output = f"对白: {content}"
                        if action:
                            npc_output += f"\n动作: {action}"
                        if emotion and emotion != "neutral":
                            npc_output += f"\n情绪: {emotion}"
                    else:
                        npc_output = f"Dialogue: {content}"
                        if action:
                            npc_output += f"\nAction: {action}"
                        if emotion and emotion != "neutral":
                            npc_output += f"\nEmotion: {emotion}"

                    synthesis_prompt += f"\n{agent_name}:\n{npc_output}"
                else:
                    synthesis_prompt += f"\n{agent_name}: {content}"

        synthesis_prompt += "\n\n请生成叙事：" if lang == "cn" else "\n\nGenerate narrative:"

        # Call LLM for synthesis
        messages = [
            SystemMessage(
                content=(
                    "你是一个 TTRPG 叙事助手，负责将多个来源的信息整合成流畅的叙事文本。"
                    "【重要】你必须严格遵守两条核心规则：\n"
                    "1. 信息控制：禁止泄露任何内部ID或标识符，禁止使用玩家尚未得知的NPC名字，禁止透露玩家不应知道的背景信息。\n"
                    "2. 禁止加戏：不要重复或润色玩家已描述的行动，NPC的动作描写必须原样使用，不要自己创作额外的神态、动作、语气描写。"
                )
                if lang == "cn"
                else (
                    "You are a TTRPG narrative assistant, responsible for synthesizing information "
                    "from multiple sources into smooth narrative text. "
                    "【IMPORTANT】You MUST follow two core rules:\n"
                    "1. Information Control: NEVER expose internal IDs, NEVER use NPC names player hasn't learned, NEVER reveal hidden background info.\n"
                    "2. No Embellishment: Do NOT repeat/embellish player's described actions, use NPC action descriptions as-is, do NOT create additional expressions/actions/tone descriptions."
                )
            ),
            HumanMessage(content=synthesis_prompt),
        ]

        try:
            narrative = await self._call_llm(messages)
        except Exception as exc:
            raise RuntimeError(f"Failed to synthesize narrative: {exc}") from exc

        # Update game phase
        from src.backend.models.game_state import GamePhase

        if "rule" in [r["agent"] for r in agent_results]:
            # Check if dice check is needed
            for result in agent_results:
                if result.get("agent") == "rule" and "result" in result:
                    if result["result"].metadata.get("needs_check"):
                        self.game_state.set_phase(GamePhase.DICE_CHECK)
                        return narrative

        self.game_state.set_phase(GamePhase.NARRATING)
        return narrative

    def __repr__(self) -> str:
        """Return agent representation."""
        return f"GMAgent(agents={list(self.sub_agents.keys())})"
