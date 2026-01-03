"""
Lore Agent - retrieves and provides world lore information.

This agent is responsible for:
- Querying world packs for lore entries
- Filtering relevant lore based on context
- Formatting lore for inclusion in agent prompts

Based on GUIDE.md Section 4.3 (Lore Agent's retrieval strategy).
"""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.backend.agents.base import AgentResponse, BaseAgent
from src.backend.services.world import WorldPackLoader


class LoreAgent(BaseAgent):
    """
    Lore Agent - world lore retrieval specialist.

    Responsibilities:
    - Query world packs for relevant lore entries
    - Search by keywords with context filtering
    - Format lore for use in other agents' prompts
    - Provide background information for scenes

    Examples:
        >>> agent = LoreAgent(llm, world_pack_loader)
        >>> result = await agent.process({
        ...     "query": "暴风城的历史",
        ...     "context": "玩家询问暴风城的背景"
        ... })
    """

    def __init__(self, llm, world_pack_loader: WorldPackLoader):
        """
        Initialize Lore Agent.

        Args:
            llm: Language model instance
            world_pack_loader: Service for loading world packs
        """
        super().__init__(llm, "lore_agent")
        self.world_pack_loader = world_pack_loader

    async def process(self, input_data: dict[str, Any]) -> AgentResponse:
        """
        Process a lore query.

        Args:
            input_data: Must contain:
                - query: What the player is asking about
                - context: Current game context
                - world_pack_id: Optional specific pack to query

        Returns:
            AgentResponse with lore information
        """
        # Extract parameters
        query = input_data.get("query", "")
        context = input_data.get("context", "")
        world_pack_id = input_data.get("world_pack_id", "demo_pack")

        if not query:
            return AgentResponse(
                content="",
                success=False,
                error="Lore Agent: No query provided",
                metadata={"agent": self.agent_name},
            )

        try:
            # Load the world pack
            world_pack = self.world_pack_loader.load(world_pack_id)

            # Search for relevant lore entries
            lore_entries = self._search_lore(world_pack, query, context)

            # Format the lore for use
            formatted_lore = self._format_lore(lore_entries, query, context)

            return AgentResponse(
                content=formatted_lore,
                metadata={
                    "agent": self.agent_name,
                    "query": query,
                    "entries_found": len(lore_entries),
                    "world_pack_id": world_pack_id,
                },
                success=True,
            )

        except Exception as exc:
            return AgentResponse(
                content="",
                success=False,
                error=f"Lore Agent error: {str(exc)}",
                metadata={
                    "agent": self.agent_name,
                    "query": query,
                },
            )

    def _search_lore(
        self,
        world_pack,
        query: str,
        context: str,
    ) -> list:
        """
        Search for relevant lore entries.

        Args:
            world_pack: WorldPack instance
            query: What the player is asking about
            context: Current game context

        Returns:
            List of relevant lore entries
        """
        # Get constant entries (always included)
        constant_entries = world_pack.get_constant_entries()

        # Search for keyword matches
        search_terms = self._extract_search_terms(query)
        matched_entries = []

        for term in search_terms:
            matches = world_pack.search_entries_by_keyword(term, include_secondary=True)
            matched_entries.extend(matches)

        # Remove duplicates and sort by order
        unique_entries = {}
        for entry in constant_entries + matched_entries:
            unique_entries[entry.uid] = entry

        # Sort by order
        return sorted(unique_entries.values(), key=lambda e: e.order)

    def _extract_search_terms(self, query: str) -> list[str]:
        """
        Extract search terms from a query.

        Args:
            query: Player's query text

        Returns:
            List of relevant search terms
        """
        # Simple keyword extraction - can be enhanced with NLP
        # Split by common delimiters and filter out stop words
        stop_words = {"的", "了", "是", "在", "我", "你", "他", "她", "它", "有", "没有", "什么", "怎么", "如何"}

        # Extract Chinese and English terms
        terms = []
        for word in query.split():
            # Remove punctuation
            clean_word = word.strip("，。！？：；""''()（）[]【】")
            if clean_word and clean_word not in stop_words and len(clean_word) > 1:
                terms.append(clean_word)

        return terms[:5]  # Limit to 5 terms to avoid noise

    def _format_lore(
        self,
        entries: list,
        query: str,
        context: str,
    ) -> str:
        """
        Format lore entries for use in prompts.

        Args:
            entries: List of lore entries
            query: Original query
            context: Game context

        Returns:
            Formatted lore string
        """
        if not entries:
            return f"没有找到与'{query}'相关的背景信息。"

        # Format each entry
        formatted_parts = []

        for entry in entries:
            # Get Chinese content (default)
            content = entry.content.get("cn") or entry.content.get("en", "")

            # Add to formatted parts
            if entry.key:
                key_str = " / ".join(entry.key)
                formatted_parts.append(f"[{key_str}]\n{content}")
            else:
                formatted_parts.append(content)

        # Join all entries
        lore_text = "\n\n".join(formatted_parts)

        # Add header
        header = f"与'{query}'相关的背景信息：\n"
        return header + lore_text

    def _build_prompt(self, input_data: dict[str, Any]) -> list[SystemMessage]:
        """
        Build prompt for LLM (not used in current implementation).

        Args:
            input_data: Input data (unused)

        Returns:
            Empty list (Lore Agent uses direct search, not LLM)
        """
        # Lore Agent uses direct search rather than LLM generation
        # This method is required by BaseAgent but not used
        return []
