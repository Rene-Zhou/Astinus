"""
NPC Agent - Generate character dialogue and actions.

Responsible for:
- Generating in-character responses based on NPCSoul personality
- Considering NPCBody state (tags, relations, memory)
- Returning structured dialogue with emotion and action
- Supporting bilingual (cn/en) prompts
"""

from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from src.backend.agents.base import AgentResponse, BaseAgent
from src.backend.core.i18n import get_i18n
from src.backend.core.prompt_loader import get_prompt_loader
from src.backend.models.world_pack import NPCData


class NPCAgent(BaseAgent):
    """
    NPC Agent - generates character dialogue and actions.

    Responsibilities:
    - Generate in-character responses based on NPC soul (personality)
    - Consider NPC body state (tags, relations, memory)
    - Return structured response with emotion and action
    - Suggest relationship changes based on interaction

    Examples:
        >>> agent = NPCAgent(llm)
        >>> result = await agent.process({
        ...     "npc_data": npc.model_dump(),
        ...     "player_input": "你好",
        ...     "context": {"location": "library"}
        ... })
    """

    def __init__(self, llm):
        """Initialize NPC Agent."""
        super().__init__(llm, "npc_agent")
        self.i18n = get_i18n()
        self.prompt_loader = get_prompt_loader()

    async def process(self, input_data: dict[str, Any]) -> AgentResponse:
        """
        Process player input and generate NPC response.

        Args:
            input_data: Context slice from GM containing:
                - npc_data: NPCData dict (soul + body)
                - player_input: What the player said/did
                - context: Scene context (location, time, etc.)
                - lang: Language code (default: "cn")

        Returns:
            AgentResponse with:
                - content: NPC's dialogue response
                - metadata: npc_id, emotion, action, relation_change
        """
        # Extract data from context slice
        npc_data_dict = input_data.get("npc_data")
        player_input = input_data.get("player_input", "")
        context = input_data.get("context", {})
        lang = input_data.get("lang", "cn")

        # Validate required fields
        if not npc_data_dict:
            return AgentResponse(
                content="",
                success=False,
                error="NPCAgent: npc_data is required",
                metadata={"agent": self.agent_name},
            )

        if not player_input:
            return AgentResponse(
                content="",
                success=False,
                error="NPCAgent: player_input is required",
                metadata={"agent": self.agent_name},
            )

        # Parse NPC data
        try:
            npc = NPCData(**npc_data_dict)
        except Exception as exc:
            return AgentResponse(
                content="",
                success=False,
                error=f"NPCAgent: Invalid npc_data - {exc}",
                metadata={"agent": self.agent_name},
            )

        # Get relationship level with player
        relationship_level = npc.body.relations.get("player", 0)

        # Build prompt
        messages = self._build_prompt(
            npc_data=npc_data_dict,
            player_input=player_input,
            context=context,
            lang=lang,
        )

        # Call LLM
        try:
            llm_response = await self._call_llm(messages)
        except Exception as exc:
            return AgentResponse(
                content="",
                success=False,
                error=f"NPCAgent: LLM call failed - {exc}",
                metadata={"agent": self.agent_name, "npc_id": npc.id},
            )

        # Parse JSON response
        try:
            result = self._extract_json_from_response(llm_response)
        except ValueError as exc:
            return AgentResponse(
                content="",
                success=False,
                error=f"NPCAgent: Failed to parse response - {exc}",
                metadata={
                    "agent": self.agent_name,
                    "npc_id": npc.id,
                    "raw_response": llm_response,
                },
            )

        # Extract response fields
        response_text = result.get("response", "")
        emotion = result.get("emotion", "neutral")
        action = result.get("action", "")
        relation_change = result.get("relation_change", 0)

        # Build metadata
        response_metadata = {
            "agent": self.agent_name,
            "npc_id": npc.id,
            "npc_name": npc.soul.name,
            "emotion": emotion,
            "action": action,
            "relationship_level": relationship_level,
        }

        if relation_change != 0:
            response_metadata["relation_change"] = relation_change

        return AgentResponse(
            content=response_text,
            metadata=response_metadata,
            success=True,
        )

    def _build_prompt(
        self,
        npc_data: dict,
        player_input: str,
        context: dict,
        lang: str = "cn",
    ) -> list[BaseMessage]:
        """
        Build prompt for LLM using NPC data.

        Args:
            npc_data: NPCData as dict
            player_input: What the player said/did
            context: Scene context
            lang: Language code

        Returns:
            List of messages for LLM
        """
        # Parse NPC data
        npc = NPCData(**npc_data)

        # Build system prompt from NPC soul
        system_parts = self._build_system_prompt(npc, lang)

        # Build user prompt with context and input
        user_parts = self._build_user_prompt(npc, player_input, context, lang)

        return [
            SystemMessage(content=system_parts),
            HumanMessage(content=user_parts),
        ]

    def _build_system_prompt(self, npc: NPCData, lang: str) -> str:
        """Build system prompt from NPC soul."""
        soul = npc.soul
        body = npc.body

        if lang == "cn":
            lines = [
                f"你是{soul.name}。以第一人称扮演这个角色。",
                "",
                "## 角色背景",
                soul.description.get(lang),
                "",
                f"## 性格特征: {', '.join(soul.personality)}",
                "",
                "## 说话风格",
                soul.speech_style.get(lang),
            ]

            # Add example dialogue
            if soul.example_dialogue:
                lines.append("")
                lines.append("## 对话示例")
                for example in soul.example_dialogue:
                    lines.append(f"玩家：{example.get('user', '')}")
                    lines.append(f"{soul.name}：{example.get('char', '')}")

            # Add current state from body
            lines.append("")
            lines.append("## 当前状态")
            if body.tags:
                lines.append(f"状态标签：{', '.join(body.tags)}")
            if body.relations.get("player", 0) != 0:
                rel = body.relations["player"]
                rel_desc = "友好" if rel > 0 else "敌对" if rel < 0 else "中立"
                lines.append(f"对玩家态度：{rel_desc} ({rel})")

            # Add memory
            if body.memory:
                lines.append("")
                lines.append("## 记忆")
                for event, _keywords in body.memory.items():
                    lines.append(f"- {event}")

            # Add response format
            lines.append("")
            lines.append("## 响应格式")
            lines.append("以 JSON 格式回复：")
            lines.append('{')
            lines.append('  "response": "你的对话内容",')
            lines.append('  "emotion": "情绪状态（如 happy, sad, angry, scared, neutral）",')
            lines.append('  "action": "伴随动作描述（可为空）",')
            lines.append('  "relation_change": 0  // 关系变化 -10 到 +10，通常为 0')
            lines.append('}')

        else:  # English
            lines = [
                f"You are {soul.name}. Roleplay this character in first person.",
                "",
                "## Character Background",
                soul.description.get(lang),
                "",
                f"## Personality: {', '.join(soul.personality)}",
                "",
                "## Speech Style",
                soul.speech_style.get(lang),
            ]

            if soul.example_dialogue:
                lines.append("")
                lines.append("## Example Dialogue")
                for example in soul.example_dialogue:
                    lines.append(f"Player: {example.get('user', '')}")
                    lines.append(f"{soul.name}: {example.get('char', '')}")

            lines.append("")
            lines.append("## Current State")
            if body.tags:
                lines.append(f"Status tags: {', '.join(body.tags)}")
            if body.relations.get("player", 0) != 0:
                rel = body.relations["player"]
                rel_desc = "friendly" if rel > 0 else "hostile" if rel < 0 else "neutral"
                lines.append(f"Attitude toward player: {rel_desc} ({rel})")

            if body.memory:
                lines.append("")
                lines.append("## Memory")
                for event, _keywords in body.memory.items():
                    lines.append(f"- {event}")

            lines.append("")
            lines.append("## Response Format")
            lines.append("Reply in JSON format:")
            lines.append('{')
            lines.append('  "response": "your dialogue",')
            lines.append('  "emotion": "emotional state (happy, sad, angry, scared, neutral)",')
            lines.append('  "action": "accompanying action description (can be empty)",')
            lines.append('  "relation_change": 0  // relation change -10 to +10, usually 0')
            lines.append('}')

        return "\n".join(lines)

    def _build_user_prompt(
        self, npc: NPCData, player_input: str, context: dict, lang: str
    ) -> str:
        """Build user prompt with context and player input."""
        if lang == "cn":
            lines = []
            if context.get("location"):
                lines.append(f"场景：{context['location']}")
            if context.get("time_of_day"):
                lines.append(f"时间：{context['time_of_day']}")
            if context.get("situation"):
                lines.append(f"情境：{context['situation']}")
            lines.append("")
            lines.append(f"玩家对你说/做：{player_input}")
            lines.append("")
            lines.append(f"请以{npc.soul.name}的身份回应。")
        else:
            lines = []
            if context.get("location"):
                lines.append(f"Scene: {context['location']}")
            if context.get("time_of_day"):
                lines.append(f"Time: {context['time_of_day']}")
            if context.get("situation"):
                lines.append(f"Situation: {context['situation']}")
            lines.append("")
            lines.append(f"Player says/does: {player_input}")
            lines.append("")
            lines.append(f"Respond as {npc.soul.name}.")

        return "\n".join(lines)

    def __repr__(self) -> str:
        """Return agent representation."""
        return "NPCAgent()"
