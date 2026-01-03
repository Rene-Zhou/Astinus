"""
GM Agent - Central orchestrator for the game.

The GM Agent is the center of the star topology, responsible for:
- Parsing player intent
- Deciding which sub-agents to call
- Preparing context slices for sub-agents
- Synthesizing sub-agent responses

Ported from weave's Orchestrator, adapted for:
- LangChain Runnable interface
- Context slicing to prevent information leakage
- Multi-agent coordination
"""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.backend.agents.base import AgentResponse, BaseAgent
from src.backend.core.prompt_loader import get_prompt_loader
from src.backend.models.game_state import GameState


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
    ):
        """
        Initialize GM Agent.

        Args:
            llm: Language model instance
            sub_agents: Dictionary of sub-agents by name
            game_state: Global game state (owned by GM)
        """
        super().__init__(llm, "gm_agent")
        self.sub_agents = sub_agents
        self.game_state = game_state
        self.prompt_loader = get_prompt_loader()

    async def process(self, input_data: dict[str, Any]) -> AgentResponse:
        """
        Process player input and orchestrate sub-agents.

        Args:
            input_data: Must contain:
                - player_input: Player's action/description
                - lang: Language code (cn/en)

        Returns:
            AgentResponse with orchestration results and narrative
        """
        # Extract input
        player_input = input_data.get("player_input", "")
        lang = input_data.get("lang", "cn")

        if not player_input:
            return AgentResponse(
                content="",
                success=False,
                error="GM Agent: No player input provided",
                metadata={"agent": self.agent_name},
            )

        # Parse intent and plan agent dispatch
        agent_dispatch_plan = await self._parse_intent_and_plan(player_input, lang)

        if not agent_dispatch_plan["success"]:
            return AgentResponse(
                content="",
                success=False,
                error=agent_dispatch_plan["error"],
                metadata={"agent": self.agent_name},
            )

        # Execute agent dispatch plan
        agents_to_call = agent_dispatch_plan["agents_to_call"]
        context_slices = agent_dispatch_plan["context_slices"]

        agent_results = []
        for agent_name in agents_to_call:
            if agent_name in self.sub_agents:
                agent = self.sub_agents[agent_name]
                context = context_slices.get(agent_name, {})

                # Call sub-agent
                result = await agent.ainvoke(context)
                agent_results.append(
                    {
                        "agent": agent_name,
                        "result": result,
                    }
                )
            else:
                agent_results.append(
                    {
                        "agent": agent_name,
                        "error": f"Agent not found: {agent_name}",
                    }
                )

        # Synthesize responses into narrative
        narrative = await self._synthesize_response(
            player_input,
            agent_dispatch_plan["player_intent"],
            agent_results,
            lang,
        )

        # Update game state
        self.game_state.add_message(
            role="user",
            content=player_input,
            metadata={"phase": "player_input"},
        )
        self.game_state.increment_turn()
        self.game_state.add_message(
            role="assistant",
            content=narrative,
            metadata={"phase": "gm_response", "agents_called": agents_to_call},
        )

        return AgentResponse(
            content=narrative,
            metadata={
                "agent": self.agent_name,
                "player_intent": agent_dispatch_plan["player_intent"],
                "agents_called": agents_to_call,
                "agent_results": [
                    {
                        "agent": r["agent"],
                        "success": r["result"].success if "result" in r else False,
                    }
                    for r in agent_results
                ],
            },
            success=True,
        )

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
                - agents_to_call: list[str]
                - context_slices: dict[str, dict]
                - error: str (if success=False)
        """
        # Get template
        template = self.prompt_loader.get_template("gm_agent")

        # Prepare template variables
        template_vars = {
            "current_location": self.game_state.current_location,
            "active_npcs": self.game_state.active_npc_ids,
            "game_phase": self.game_state.current_phase.value,
            "turn_count": self.game_state.turn_count,
            "player_input": player_input,
        }

        # Build prompt
        system_message = template.get_system_message(lang=lang, **template_vars)
        user_message = template.get_user_message(lang=lang, **template_vars)

        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=user_message),
        ]

        # Call LLM
        llm_response = await self._call_llm(messages)

        # Parse JSON
        try:
            result = self._extract_json_from_response(llm_response)
        except ValueError as exc:
            return {
                "success": False,
                "error": f"Failed to parse GM dispatch plan: {exc}",
            }

        # Validate and prepare context slices
        player_intent = result.get("player_intent", "unknown")
        agents_to_call = result.get("agents_to_call", [])
        context_slices = result.get("context_slices", {})

        # Prepare context for Rule Agent if needed
        if "rule" in agents_to_call:
            context_slices["rule"] = self._slice_context_for_rule(
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
                "traits": [
                    t.model_dump() for t in self.game_state.player.traits
                ],
            },
            "tags": self.game_state.player.tags,
            "lang": lang,
        }

    def _slice_context_for_npc(
        self,
        npc_id: str,
        player_input: str,
        lang: str,
    ) -> dict[str, Any]:
        """
        Prepare context slice for NPC Agent.

        Only gives NPC Agent relevant context - prevents leakage.

        Args:
            npc_id: NPC identifier
            player_input: Player's action
            lang: Language code

        Returns:
            Context slice for NPC Agent
        """
        # Get recent messages with this NPC
        recent_messages = self.game_state.get_recent_messages(count=10)
        npc_messages = [
            msg
            for msg in recent_messages
            if msg.get("metadata", {}).get("npc_id") == npc_id
        ]

        return {
            "npc_id": npc_id,
            "player_input": player_input,
            "recent_messages": npc_messages,
            "lang": lang,
            # Note: No access to other NPCs, other locations, etc.
        }

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

        Args:
            player_input: Original player input
            player_intent: Parsed intent
            agent_results: Results from sub-agents
            lang: Language code

        Returns:
            Unified narrative response
        """
        # Simple synthesis for now - can be enhanced later
        parts = []

        # Add brief intro
        if lang == "cn":
            parts.append(f"你尝试{player_input}。")
        else:
            parts.append(f"You attempt: {player_input}.")

        # Add agent responses
        for agent_result in agent_results:
            if "result" in agent_result and agent_result["result"].success:
                result = agent_result["result"]
                # Add action result or narrative
                if result.content:
                    parts.append(result.content)
            elif "error" in agent_result:
                # Log error but don't expose to player
                continue

        # Join parts
        narrative = " ".join(parts)

        # Update game phase
        from src.backend.models.game_state import GamePhase

        if "rule" in [r["agent"] for r in agent_results]:
            self.game_state.set_phase(GamePhase.DICE_CHECK)
        else:
            self.game_state.set_phase(GamePhase.NARRATING)

        return narrative

    def __repr__(self) -> str:
        """Return agent representation."""
        return f"GMAgent(agents={list(self.sub_agents.keys())})"
