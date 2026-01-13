"""
NPC Agent - Generate character dialogue and actions.

Responsible for:
- Generating in-character responses based on NPCSoul personality
- Considering NPCBody state (tags, relations, memory)
- Returning structured dialogue with emotion and action
- Supporting bilingual (cn/en) prompts
- Persisting memory and relationship changes
"""

from datetime import datetime
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from src.backend.agents.base import AgentResponse, BaseAgent
from src.backend.core.i18n import get_i18n
from src.backend.core.prompt_loader import get_prompt_loader
from src.backend.models.world_pack import NPCData
from src.backend.services.location_context import LocationContextService
from src.backend.services.vector_store import VectorStoreService
from src.backend.services.world import WorldPackLoader


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

    def __init__(
        self,
        llm,
        vector_store: VectorStoreService | None = None,
        world_pack_loader: WorldPackLoader | None = None,
    ):
        """
        Initialize NPC Agent.

        Args:
            llm: Language model instance
            vector_store: Optional VectorStoreService for semantic memory retrieval
            world_pack_loader: Optional WorldPackLoader for location-based knowledge filtering
        """
        super().__init__(llm, "npc_agent")
        self.i18n = get_i18n()
        self.prompt_loader = get_prompt_loader()
        self.vector_store = vector_store
        self.world_pack_loader = world_pack_loader

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
        npc_data_dict = input_data.get("npc_data")
        player_input = input_data.get("player_input", "")
        context = input_data.get("context", {})
        lang = input_data.get("lang", "cn")
        narrative_style = input_data.get("narrative_style", "detailed")

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

        messages = self._build_prompt(
            npc_data=npc_data_dict,
            player_input=player_input,
            context=context,
            lang=lang,
            narrative_style=narrative_style,
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

        # Extract new memory if present
        new_memory = result.get("new_memory")
        if new_memory:
            response_metadata["new_memory"] = new_memory

        return AgentResponse(
            content=response_text,
            metadata=response_metadata,
            success=True,
        )

    def _retrieve_relevant_memories(
        self,
        npc_id: str,
        player_input: str,
        all_memories: dict[str, list[str]],
        n_results: int = 3,
    ) -> list[str]:
        """
        Retrieve relevant memories using vector similarity search.

        Args:
            npc_id: NPC identifier
            player_input: Current player input/query
            all_memories: All NPC memories {event: [keywords]}
            n_results: Number of memories to retrieve (default: 3)

        Returns:
            List of relevant memory event descriptions (top n_results)
        """
        # If no vector store or no memories, return empty list
        if not self.vector_store or not all_memories:
            return []

        try:
            collection_name = f"npc_memories_{npc_id}"

            # Search for similar memories
            results = self.vector_store.search(
                collection_name=collection_name,
                query_text=player_input,
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )

            # Extract memory events from results
            if results["documents"] and results["documents"][0]:
                return results["documents"][0]
            return []

        except Exception:
            # If search fails, return empty list (graceful degradation)
            return []

    def _build_prompt(
        self,
        npc_data: dict,
        player_input: str,
        context: dict,
        lang: str = "cn",
        narrative_style: str = "detailed",
    ) -> list[BaseMessage]:
        npc = NPCData(**npc_data)

        system_parts = self._build_system_prompt(npc, player_input, context, lang, narrative_style)
        user_parts = self._build_user_prompt(npc, player_input, context, lang)

        return [
            SystemMessage(content=system_parts),
            HumanMessage(content=user_parts),
        ]

    def _build_system_prompt(
        self,
        npc: NPCData,
        player_input: str,
        context: dict,
        lang: str,
        narrative_style: str = "detailed",
    ) -> str:
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

            # Retrieve and add relevant memories
            relevant_memories = self._retrieve_relevant_memories(
                npc_id=npc.id,
                player_input=player_input,
                all_memories=body.memory,
                n_results=3,
            )

            if relevant_memories:
                lines.append("")
                lines.append("## 相关记忆")
                for memory in relevant_memories:
                    lines.append(f"- {memory}")
            elif body.memory:
                # Fallback: show a few recent memories if retrieval fails
                lines.append("")
                lines.append("## 近期记忆")
                recent_memories = list(body.memory.keys())[:3]
                for event in recent_memories:
                    lines.append(f"- {event}")

            # NEW: Add location-specific knowledge if applicable
            location_lore = self._get_location_specific_lore(npc, context, lang)
            if location_lore:
                lines.append("")
                lines.append("## 你知道的信息")
                lines.append(location_lore)

            lines.append("")
            lines.append("## 叙事风格指示")
            if narrative_style == "brief":
                lines.append("当前处于连续对话中，请精简动作描写：")
                lines.append("- action 字段留空或只写极简动作（如「点头」「摇头」）")
                lines.append("- 重点放在对白本身，避免重复之前已描述过的神态动作")
            else:
                lines.append("这是对话开始或间隔较久后的交互，请丰富动作描写：")
                lines.append("- action 字段写出有画面感的动作、神态、小动作")
                lines.append("- 体现角色性格特征和当前情绪状态")

            lines.append("")
            lines.append("## 响应格式")
            lines.append("以 JSON 格式回复：")
            lines.append("{")
            lines.append('  "response": "你的对话内容",')
            lines.append('  "emotion": "情绪状态（如 happy, sad, angry, scared, neutral）",')
            lines.append('  "action": "伴随动作描述（根据叙事风格指示填写）",')
            lines.append('  "relation_change": 0  // 关系变化 -10 到 +10，通常为 0')
            lines.append("}")

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

            # Retrieve and add relevant memories
            relevant_memories = self._retrieve_relevant_memories(
                npc_id=npc.id,
                player_input=player_input,
                all_memories=body.memory,
                n_results=3,
            )

            if relevant_memories:
                lines.append("")
                lines.append("## Relevant Memories")
                for memory in relevant_memories:
                    lines.append(f"- {memory}")
            elif body.memory:
                # Fallback: show a few recent memories if retrieval fails
                lines.append("")
                lines.append("## Recent Memories")
                recent_memories = list(body.memory.keys())[:3]
                for event in recent_memories:
                    lines.append(f"- {event}")

            # NEW: Add location-specific knowledge if applicable
            location_lore = self._get_location_specific_lore(npc, context, lang)
            if location_lore:
                lines.append("")
                lines.append("## What You Know")
                lines.append(location_lore)

            lines.append("")
            lines.append("## Narrative Style")
            if narrative_style == "brief":
                lines.append("Currently in continuous dialogue, keep action description minimal:")
                lines.append("- Leave action field empty or use minimal actions (e.g., 'nods', 'shakes head')")
                lines.append("- Focus on the dialogue itself, avoid repeating previously described gestures")
            else:
                lines.append("This is a new interaction or after a gap, enrich the action description:")
                lines.append("- Write vivid actions, expressions, and subtle movements in action field")
                lines.append("- Reflect character personality and current emotional state")

            lines.append("")
            lines.append("## Response Format")
            lines.append("Reply in JSON format:")
            lines.append("{")
            lines.append('  "response": "your dialogue",')
            lines.append('  "emotion": "emotional state (happy, sad, angry, scared, neutral)",')
            lines.append('  "action": "accompanying action description (follow narrative style above)",')
            lines.append('  "relation_change": 0  // relation change -10 to +10, usually 0')
            lines.append("}")

        return "\n".join(lines)

    def _get_location_specific_lore(
        self, npc: NPCData, context: dict, lang: str
    ) -> str:
        """
        Get location-specific lore that this NPC knows.

        Checks NPCBody.location_knowledge for restrictions. If empty, NPC knows
        everything (backward compatible). Otherwise, filters by allowed lore UIDs.

        Args:
            npc: NPC data
            context: Scene context with location and world_pack_id
            lang: Language code

        Returns:
            Formatted lore string or empty string if no lore/restrictions
        """
        # Check if we have required dependencies
        if not self.world_pack_loader:
            return ""

        # Extract context info
        location_id = context.get("location")
        world_pack_id = context.get("world_pack_id")

        if not location_id or not world_pack_id:
            return ""

        body = npc.body

        # Check if NPC has location_knowledge restrictions
        if not body.location_knowledge:
            # No restrictions - NPC knows everything (backward compatible)
            # Don't inject anything here to avoid bloating the prompt
            return ""

        # Get allowed lore UIDs for this location
        allowed_uids = body.location_knowledge.get(location_id, [])

        # If no UIDs for this location, NPC knows little here
        if not allowed_uids:
            if lang == "cn":
                return "（你对当前位置的情况所知甚少）"
            else:
                return "(You know very little about the current location)"

        # Use LocationContextService to get filtered lore
        try:
            context_service = LocationContextService(self.world_pack_loader)
            lore_entries = context_service.filter_npc_lore(
                npc_id=npc.id,
                location_id=location_id,
                world_pack_id=world_pack_id,
                lang=lang,
            )

            if not lore_entries:
                return ""

            # Format lore entries
            lore_parts = []
            for entry in lore_entries:
                content = entry.content.get(lang)
                if content:
                    lore_parts.append(content)

            return "\n\n".join(lore_parts) if lore_parts else ""

        except Exception:
            # If filtering fails, return empty (graceful degradation)
            return ""

    def _build_user_prompt(self, npc: NPCData, player_input: str, context: dict, lang: str) -> str:
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

    def persist_memory(
        self,
        npc_id: str,
        event: str,
        keywords: list[str],
    ) -> None:
        """
        Persist a new memory to the vector store.

        Args:
            npc_id: NPC identifier
            event: Description of the event to remember
            keywords: Keywords for the memory
        """
        if not self.vector_store:
            return

        collection_name = f"npc_memories_{npc_id}"
        timestamp = datetime.utcnow().isoformat()
        memory_id = f"mem_{npc_id}_{timestamp.replace(':', '_').replace('.', '_')}"

        try:
            self.vector_store.add_documents(
                collection_name=collection_name,
                documents=[event],
                metadatas=[
                    {
                        "npc_id": npc_id,
                        "keywords": ",".join(keywords),
                        "timestamp": timestamp,
                    }
                ],
                ids=[memory_id],
            )
        except Exception:
            # Fail silently - memory persistence is not critical
            pass

    def calculate_new_relation_level(
        self,
        current_level: int,
        change: int,
    ) -> int:
        """
        Calculate new relation level with bounds checking.

        Args:
            current_level: Current relationship level (-100 to 100)
            change: Amount to change (-10 to +10 typically)

        Returns:
            New relation level clamped to -100 to 100
        """
        new_level = current_level + change
        return max(-100, min(100, new_level))

    def get_state_updates_from_response(
        self,
        response: AgentResponse,
    ) -> dict[str, Any]:
        """
        Extract state updates from an NPC response.

        Args:
            response: AgentResponse from process()

        Returns:
            Dict containing state updates:
                - npc_id: NPC identifier
                - relation_change: Change in relationship
                - new_memory: Memory to persist (if any)
                - has_memory_update: Whether memory was updated
        """
        metadata = response.metadata or {}

        updates = {
            "npc_id": metadata.get("npc_id", ""),
            "relation_change": metadata.get("relation_change", 0),
            "has_memory_update": False,
        }

        new_memory = metadata.get("new_memory")
        if new_memory:
            updates["new_memory"] = new_memory
            updates["has_memory_update"] = True

        return updates

    def __repr__(self) -> str:
        """Return agent representation."""
        return "NPCAgent()"
