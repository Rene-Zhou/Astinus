"""
Rule Agent - Judge whether player actions need dice checks.

Ported from weave's Judge agent, adapted for:
- LangChain Runnable interface
- 2d6 dice system (vs weave's d20)
- Context slicing from GM
- Multi-language prompt support
"""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.backend.agents.base import AgentResponse, BaseAgent
from src.backend.core.i18n import get_i18n
from src.backend.core.prompt_loader import get_prompt_loader
from src.backend.models.dice_check import DiceCheckRequest


class RuleAgent(BaseAgent):
    """
    Rule Agent - analyzes player actions and generates dice checks.

    Responsibilities:
    - Judge whether player action needs a dice check
    - Identify negative tags causing disadvantage
    - Evaluate player arguments for advantage
    - Generate DiceCheckRequest for the frontend

    Examples:
        >>> agent = RuleAgent(llm)
        >>> result = await agent.process({
        ...     "action": "逃离房间",
        ...     "character": {...},
        ...     "tags": ["右腿受伤"]
        ... })
    """

    def __init__(self, llm):
        """Initialize Rule Agent."""
        super().__init__(llm, "rule_agent")
        self.i18n = get_i18n()
        self.prompt_loader = get_prompt_loader()

    async def process(self, input_data: dict[str, Any]) -> AgentResponse:
        """
        Process player action and determine if dice check is needed.

        Args:
            input_data: Context slice from GM containing:
                - action: Player's action description
                - character: PlayerCharacter dict
                - tags: List of current tags (conditions)
                - argument: Optional player argument for advantage

        Returns:
            AgentResponse with:
                - content: JSON string of judgment result
                - metadata: Includes "needs_check" and DiceCheckRequest if needed
        """
        # Extract data from context slice
        action = input_data.get("action", "")
        character = input_data.get("character", {})
        tags = input_data.get("tags", [])
        argument = input_data.get("argument", "")

        if not action:
            return AgentResponse(
                content="",
                success=False,
                error="RuleAgent: No action provided",
                metadata={"agent": self.agent_name},
            )

        # Build prompt using template
        messages = self._build_prompt(
            input_data,
            character,
            tags,
            action,
            argument,
        )

        # Call LLM
        llm_response = await self._call_llm(messages)

        # Parse JSON response
        try:
            result = self._extract_json_from_response(llm_response)
        except ValueError as exc:
            return AgentResponse(
                content="",
                success=False,
                error=f"Failed to parse Rule Agent response: {exc}",
                metadata={
                    "agent": self.agent_name,
                    "raw_response": llm_response,
                },
            )

        # Validate response structure
        if not isinstance(result, dict):
            return AgentResponse(
                content="",
                success=False,
                error="Rule Agent response must be JSON object",
                metadata={"agent": self.agent_name},
            )

        # Extract fields
        needs_check = result.get("needs_check", False)
        reasoning = result.get("reasoning", "")
        check_request_data = result.get("check_request", {})

        # Build response
        response_metadata = {
            "agent": self.agent_name,
            "needs_check": needs_check,
            "reasoning": reasoning,
        }

        if needs_check and check_request_data:
            try:
                # Create DiceCheckRequest from LLM response
                dice_check = DiceCheckRequest(**check_request_data)
                response_metadata["dice_check"] = dice_check.model_dump()

                return AgentResponse(
                    content=llm_response,  # Return raw LLM response
                    metadata=response_metadata,
                    success=True,
                )
            except Exception as exc:
                return AgentResponse(
                    content="",
                    success=False,
                    error=f"Invalid DiceCheckRequest: {exc}",
                    metadata={
                        "agent": self.agent_name,
                        "reasoning": reasoning,
                    },
                )
        else:
            # No check needed
            return AgentResponse(
                content=reasoning or "No dice check needed",
                metadata=response_metadata,
                success=True,
            )

    def _build_prompt(
        self,
        input_data: dict,
        character: dict,
        tags: list[str],
        action: str,
        argument: str,
    ) -> list[SystemMessage]:
        """
        Build prompt for LLM using rule_agent template.

        Args:
            input_data: Raw context data
            character: Character data
            tags: Current tags
            action: Player action
            argument: Player argument (optional)

        Returns:
            List of messages for LLM
        """
        # Get template
        template = self.prompt_loader.get_template("rule_agent")

        # Get character info
        character_name = character.get("name", "Unknown")
        character_concept = character.get("concept", {})

        # Handle concept (LocalizedString)
        if isinstance(character_concept, dict):
            concept_cn = character_concept.get("cn", "")
            concept_en = character_concept.get("en", "")
            concept_display = concept_cn or concept_en
        else:
            concept_display = str(character_concept)

        # Get traits
        traits = character.get("traits", [])
        if traits and isinstance(traits[0], dict):
            # Trait objects
            trait_names = []
            for trait in traits:
                if isinstance(trait, dict):
                    name = trait.get("name", {})
                    if isinstance(name, dict):
                        trait_names.append(name.get("cn", "") or name.get("en", ""))
                    else:
                        trait_names.append(str(name))
            traits = trait_names

        # Render system message
        system_message = template.get_system_message(
            lang="cn",
            character_name=character_name,
            concept=concept_display,
            traits=traits,
            tags=tags,
        )

        # Render user message with action
        user_message = template.get_user_message(
            lang="cn",
            character_name=character_name,
            concept=concept_display,
            traits=traits,
            tags=tags,
            action=action,
            argument=argument,
        )

        return [
            SystemMessage(content=system_message),
            HumanMessage(content=user_message),
        ]

    def __repr__(self) -> str:
        """Return agent representation."""
        return "RuleAgent()"
