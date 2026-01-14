"""
Rule Agent - Judge whether player actions need dice checks and process results.

Ported from weave's Judge agent, adapted for:
- LangChain Runnable interface
- 2d6 dice system (vs weave's d20)
- Context slicing from GM
- Multi-language prompt support
- Dice result narrative generation
"""

from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

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
        lang = input_data.get("lang", "cn")

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
            lang,
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
        lang: str = "cn",
    ) -> list[BaseMessage]:
        """
        Build prompt for LLM using rule_agent template.

        Args:
            input_data: Raw context data
            character: Character data
            tags: Current tags
            action: Player action
            argument: Player argument (optional)
            lang: Language code

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

        # Get traits - extract full trait information (name, description, positive_aspect, negative_aspect)
        def _get_localized(trait_data: dict, field: str, preferred_lang: str = "cn") -> str:
            """Extract LocalizedString field with fallback to preferred language."""
            value = trait_data.get(field, {})
            if isinstance(value, dict):
                return value.get(preferred_lang, "") or value.get("en", "")
            return str(value) if value else ""

        traits_full = []
        for trait in character.get("traits", []):
            if isinstance(trait, dict):
                traits_full.append({
                    "name": _get_localized(trait, "name", lang),
                    "description": _get_localized(trait, "description", lang),
                    "positive": _get_localized(trait, "positive_aspect", lang),
                    "negative": _get_localized(trait, "negative_aspect", lang),
                })
        traits = traits_full

        # Render system message
        system_message = template.get_system_message(
            lang=lang,
            character_name=character_name,
            concept=concept_display,
            traits=traits,
            tags=tags,
        )

        # Render user message with action
        user_message = template.get_user_message(
            lang=lang,
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

    async def process_result(
        self,
        result_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """
        Process dice check result and generate narrative.

        Args:
            result_data: Dice check result containing:
                - intention: What player tried to do
                - dice_formula: Dice notation used
                - dice_values: Individual roll values
                - total: Final total
                - threshold: Target number
                - success: Whether check succeeded
                - critical: Whether this was a critical
                - modifiers: Applied modifiers (optional)
            context: Optional scene context for narrative

        Returns:
            AgentResponse with narrative and state updates
        """
        success = result_data.get("success", False)
        critical = result_data.get("critical", False)

        # Build prompt for narrative generation
        messages = self._build_result_prompt(result_data, context=context, lang="cn")

        try:
            llm_response = await self._call_llm(messages)
            narrative_result = self._extract_json_from_response(llm_response)
        except Exception as exc:
            return AgentResponse(
                content="",
                metadata={},
                success=False,
                error=f"Failed to generate narrative: {exc}",
            )

        # Build response metadata
        outcome_type = narrative_result.get(
            "outcome_type", self._determine_outcome_type(success, critical)
        )

        response_metadata = {
            "agent": self.agent_name,
            "narrative": narrative_result.get("narrative", ""),
            "outcome_type": outcome_type,
            "consequences": narrative_result.get("consequences", []),
            "suggested_tags": narrative_result.get("suggested_tags", []),
            "dice_total": result_data.get("total"),
            "threshold": result_data.get("threshold"),
        }

        # Add optional fields if present
        if narrative_result.get("bonus_effect"):
            response_metadata["bonus_effect"] = narrative_result["bonus_effect"]
        if narrative_result.get("fate_point_applicable"):
            response_metadata["fate_point_applicable"] = narrative_result["fate_point_applicable"]
            response_metadata["fate_point_reason"] = narrative_result.get("fate_point_reason", "")
        if narrative_result.get("npc_reaction_hint"):
            response_metadata["npc_reaction_hint"] = narrative_result["npc_reaction_hint"]

        return AgentResponse(
            content=narrative_result.get("narrative", ""),
            metadata=response_metadata,
            success=True,
        )

    def _build_result_prompt(
        self,
        result_data: dict[str, Any],
        context: dict[str, Any] | None = None,
        lang: str = "cn",
    ) -> list[BaseMessage]:
        """
        Build prompt for narrative generation from dice result.

        Args:
            result_data: Dice check result
            context: Optional scene context
            lang: Language code

        Returns:
            List of messages for LLM
        """
        intention = result_data.get("intention", "行动")
        dice_values = result_data.get("dice_values", [])
        total = result_data.get("total", 0)
        threshold = result_data.get("threshold", 7)
        success = result_data.get("success", False)
        critical = result_data.get("critical", False)
        modifiers = result_data.get("modifiers", [])

        outcome_type = self._determine_outcome_type(success, critical)

        if lang == "cn":
            # Chinese prompt
            system_lines = [
                "你是一个TTRPG叙事生成器。根据骰子检定结果生成简短的叙事描述。",
                "",
                "## 要求",
                "- 叙事应该简洁有力，2-3句话",
                "- 根据成功/失败调整叙事基调",
                "- 大成功/大失败应该有戏剧性的描述",
                "- 失败可能带来后果",
                "",
                "## 响应格式",
                "以JSON格式返回：",
                "{",
                '  "narrative": "叙事描述",',
                '  "outcome_type": "success/failure/critical_success/critical_failure",',
                '  "consequences": ["后果1", "后果2"],',
                '  "suggested_tags": ["建议添加的状态标签"]',
                "}",
            ]

            user_lines = [
                "## 检定信息",
                f"- 意图：{intention}",
                f"- 骰子结果：{dice_values} = {total}",
                f"- 目标值：{threshold}",
                f"- 结果：{outcome_type}",
            ]

            if modifiers:
                mod_strs = [f"{m.get('source', '未知')}: {m.get('effect', '')}" for m in modifiers]
                user_lines.append(f"- 修正：{', '.join(mod_strs)}")

            if context:
                user_lines.append("")
                user_lines.append("## 场景背景")
                if context.get("location"):
                    user_lines.append(f"- 地点：{context['location']}")
                if context.get("situation"):
                    user_lines.append(f"- 情境：{context['situation']}")
                if context.get("nearby_npcs"):
                    user_lines.append(f"- 附近NPC：{', '.join(context['nearby_npcs'])}")

            user_lines.append("")
            user_lines.append("请生成叙事。")

        else:
            # English prompt
            system_lines = [
                "You are a TTRPG narrative generator. Generate brief narrative based on dice check results.",
                "",
                "## Requirements",
                "- Narrative should be concise, 2-3 sentences",
                "- Adjust tone based on success/failure",
                "- Critical success/failure should be dramatic",
                "- Failures may have consequences",
                "",
                "## Response Format",
                "Return JSON:",
                "{",
                '  "narrative": "narrative description",',
                '  "outcome_type": "success/failure/critical_success/critical_failure",',
                '  "consequences": ["consequence1", "consequence2"],',
                '  "suggested_tags": ["suggested status tags"]',
                "}",
            ]

            user_lines = [
                "## Check Information",
                f"- Intention: {intention}",
                f"- Dice Result: {dice_values} = {total}",
                f"- Target: {threshold}",
                f"- Outcome: {outcome_type}",
            ]

            if modifiers:
                mod_strs = [
                    f"{m.get('source', 'unknown')}: {m.get('effect', '')}" for m in modifiers
                ]
                user_lines.append(f"- Modifiers: {', '.join(mod_strs)}")

            if context:
                user_lines.append("")
                user_lines.append("## Scene Context")
                if context.get("location"):
                    user_lines.append(f"- Location: {context['location']}")
                if context.get("situation"):
                    user_lines.append(f"- Situation: {context['situation']}")
                if context.get("nearby_npcs"):
                    user_lines.append(f"- Nearby NPCs: {', '.join(context['nearby_npcs'])}")

            user_lines.append("")
            user_lines.append("Generate the narrative.")

        return [
            SystemMessage(content="\n".join(system_lines)),
            HumanMessage(content="\n".join(user_lines)),
        ]

    def _determine_outcome_type(self, success: bool, critical: bool) -> str:
        """
        Determine the outcome type string.

        Args:
            success: Whether the check succeeded
            critical: Whether this was a critical

        Returns:
            Outcome type string
        """
        if critical:
            return "critical_success" if success else "critical_failure"
        return "success" if success else "failure"

    def __repr__(self) -> str:
        """Return agent representation."""
        return "RuleAgent()"
