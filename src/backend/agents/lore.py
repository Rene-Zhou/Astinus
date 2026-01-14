"""
Lore Agent - retrieves and provides world lore information.

This agent is responsible for:
- Querying world packs for lore entries
- Filtering relevant lore based on context
- Formatting lore for inclusion in agent prompts

Based on GUIDE.md Section 4.3 (Lore Agent's retrieval strategy).
"""

from typing import Any

from langchain_core.messages import SystemMessage

from src.backend.agents.base import AgentResponse, BaseAgent
from src.backend.services.vector_store import VectorStoreService
from src.backend.services.world import WorldPackLoader

# Hybrid search configuration
KEYWORD_MATCH_WEIGHT = 1.0  # Strong signal from explicit keyword match
VECTOR_MATCH_WEIGHT = 0.7  # Secondary signal from semantic similarity
DUAL_MATCH_BOOST = 1.5  # Boost for entries matching both keyword and vector


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

    def __init__(
        self,
        llm,
        world_pack_loader: WorldPackLoader,
        vector_store: VectorStoreService | None = None,
    ):
        """
        Initialize Lore Agent.

        Args:
            llm: Language model instance
            world_pack_loader: Service for loading world packs
            vector_store: Optional VectorStoreService for semantic search
        """
        super().__init__(llm, "lore_agent")
        self.world_pack_loader = world_pack_loader
        self.vector_store = vector_store

    async def process(self, input_data: dict[str, Any]) -> AgentResponse:
        """
        Process a lore query.

        Args:
            input_data: Must contain:
                - query: What the player is asking about
                - context: Current game context
                - world_pack_id: Optional specific pack to query
                - current_location: (Optional) Current location ID for filtering
                - current_region: (Optional) Current region ID for filtering

        Returns:
            AgentResponse with lore information
        """
        # Extract parameters
        query = input_data.get("query", "")
        context = input_data.get("context", "")
        world_pack_id = input_data.get("world_pack_id", "demo_pack")
        current_location = input_data.get("current_location")
        current_region = input_data.get("current_region")

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

            # Search for relevant lore entries with location filtering
            lore_entries = self._search_lore(
                world_pack, query, context, current_location, current_region
            )

            # Format the lore for use
            formatted_lore = self._format_lore(lore_entries, query, context)

            return AgentResponse(
                content=formatted_lore,
                metadata={
                    "agent": self.agent_name,
                    "query": query,
                    "entries_found": len(lore_entries),
                    "world_pack_id": world_pack_id,
                    "current_location": current_location,
                    "current_region": current_region,
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
        current_location: str | None = None,
        current_region: str | None = None,
    ) -> list:
        """
        Search for relevant lore entries using hybrid search with location filtering.

        Combines keyword matching and vector similarity:
        - Keyword matches get score = 1.0
        - Vector matches get score = 0.7 * similarity
        - Dual matches (both keyword + vector) get 1.5x boost
        - Filters by location/region applicability

        Args:
            world_pack: WorldPack instance
            query: What the player is asking about
            context: Current game context
            current_location: (Optional) Current location ID for filtering
            current_region: (Optional) Current region ID for filtering

        Returns:
            List of top 5 relevant lore entries, sorted by score then order
        """
        # Get constant entries (always included with highest score)
        constant_entries = world_pack.get_constant_entries()

        # If no vector store, fall back to keyword-only search
        if self.vector_store is None:
            return self._keyword_only_search(
                world_pack, query, constant_entries, current_location, current_region
            )

        # Hybrid search: combine keyword and vector scores
        entry_scores = {}

        # Step 1: Keyword matching
        search_terms = self._extract_search_terms(query)
        keyword_matched_uids = set()

        for term in search_terms:
            matches = world_pack.search_entries_by_keyword(term, include_secondary=True)
            for entry in matches:
                keyword_matched_uids.add(entry.uid)
                if entry.uid not in entry_scores:
                    entry_scores[entry.uid] = {
                        "entry": entry,
                        "score": KEYWORD_MATCH_WEIGHT,
                        "keyword_match": True,
                        "vector_match": False,
                    }

        # Step 2: Vector similarity search
        try:
            # Determine language for search
            lang = "cn" if any("\u4e00" <= c <= "\u9fff" for c in query) else "en"
            collection_name = f"lore_entries_{world_pack.pack_info.id}"

            # Search for similar documents (top 10)
            results = self.vector_store.search(
                collection_name=collection_name,
                query_text=query,
                n_results=10,
                where={"lang": lang},
                include=["metadatas", "distances"],
            )

            # Process vector search results
            if results["distances"] and results["distances"][0]:
                for metadata, distance in zip(
                    results["metadatas"][0], results["distances"][0], strict=True
                ):
                    uid = metadata["uid"]
                    # Convert distance to similarity (lower distance = higher similarity)
                    similarity = 1.0 - min(distance, 1.0)
                    vector_score = VECTOR_MATCH_WEIGHT * similarity

                    if uid in entry_scores:
                        # Dual match: boost the score
                        entry_scores[uid]["score"] *= DUAL_MATCH_BOOST
                        entry_scores[uid]["vector_match"] = True
                    else:
                        # Vector-only match
                        entry = world_pack.get_entry(uid)
                        if entry:
                            entry_scores[uid] = {
                                "entry": entry,
                                "score": vector_score,
                                "keyword_match": False,
                                "vector_match": True,
                            }

        except Exception:
            # If vector search fails, continue with keyword results
            pass

        # Step 3: Add constant entries with maximum score
        for entry in constant_entries:
            if entry.uid not in entry_scores:
                entry_scores[entry.uid] = {
                    "entry": entry,
                    "score": 2.0,  # Higher than any other score
                    "keyword_match": False,
                    "vector_match": False,
                }

        # Step 4: Filter by location/region applicability
        filtered_scores = self._filter_by_location(
            entry_scores.values(), current_location, current_region
        )

        # Step 5: Sort by score (desc), then by order (asc)
        sorted_entries = sorted(
            filtered_scores,
            key=lambda x: (-x["score"], x["entry"].order),
        )

        # Return top 5
        return [item["entry"] for item in sorted_entries[:5]]

    def _filter_by_location(
        self,
        entry_scores: list,
        current_location: str | None,
        current_region: str | None,
    ) -> list:
        """
        Filter lore entries by location/region applicability.

        Logic:
        1. Skip if location-restricted and doesn't match
        2. Skip if region-restricted and doesn't match
        3. Only include 'basic' visibility by default (detailed requires investigation)

        Args:
            entry_scores: List of entry score dictionaries
            current_location: Current location ID
            current_region: Current region ID

        Returns:
            Filtered list of entry scores
        """
        filtered = []
        for item in entry_scores:
            entry = item["entry"]

            # Filter by visibility (only 'basic' or constant entries)
            if entry.visibility != "basic" and not entry.constant:
                continue

            # Skip if location-restricted and doesn't match
            if entry.applicable_locations and (
                not current_location or current_location not in entry.applicable_locations
            ):
                continue

            # Skip if region-restricted and doesn't match
            if entry.applicable_regions and (
                not current_region or current_region not in entry.applicable_regions
            ):
                continue

            # Entry passed all filters
            filtered.append(item)

        return filtered

    def _keyword_only_search(
        self,
        world_pack,
        query: str,
        constant_entries: list,
        current_location: str | None = None,
        current_region: str | None = None,
    ) -> list:
        """
        Fallback to keyword-only search when vector store is unavailable.

        Args:
            world_pack: WorldPack instance
            query: Search query
            constant_entries: List of constant entries
            current_location: (Optional) Current location ID for filtering
            current_region: (Optional) Current region ID for filtering

        Returns:
            List of matched entries sorted by order
        """
        search_terms = self._extract_search_terms(query)
        matched_entries = []

        for term in search_terms:
            matches = world_pack.search_entries_by_keyword(term, include_secondary=True)
            matched_entries.extend(matches)

        # Remove duplicates
        unique_entries = {}
        for entry in constant_entries + matched_entries:
            unique_entries[entry.uid] = entry

        # Filter by location/region
        filtered_entries = []
        for entry in unique_entries.values():
            # Filter by visibility
            if entry.visibility != "basic" and not entry.constant:
                continue

            # Skip if location-restricted and doesn't match
            if entry.applicable_locations and (
                not current_location or current_location not in entry.applicable_locations
            ):
                continue

            # Skip if region-restricted and doesn't match
            if entry.applicable_regions and (
                not current_region or current_region not in entry.applicable_regions
            ):
                continue

            filtered_entries.append(entry)

        return sorted(filtered_entries, key=lambda e: e.order)

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
        stop_words = {
            "的",
            "了",
            "是",
            "在",
            "我",
            "你",
            "他",
            "她",
            "它",
            "有",
            "没有",
            "什么",
            "怎么",
            "如何",
        }

        # Extract Chinese and English terms
        terms = []
        for word in query.split():
            # Remove punctuation
            clean_word = word.strip("，。！？：；''()（）[]【】")
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
