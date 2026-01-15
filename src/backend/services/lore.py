"""
Lore Service - world lore retrieval service.

This service provides hybrid search (keyword + vector) for world lore entries.
It's a pure logic service without LLM reasoning, designed to be used as a tool by GM Agent.

Refactored from LoreAgent to separate deterministic retrieval from AI agent orchestration.
"""

import jieba
from typing import Any

from src.backend.services.vector_store import VectorStoreService
from src.backend.services.world import WorldPackLoader

# Hybrid search configuration
# Updated for Qwen3-Embedding which provides better multilingual semantic understanding
KEYWORD_MATCH_WEIGHT = 2.0  # Strong signal from explicit primary keyword match
KEYWORD_SECONDARY_WEIGHT = 1.0  # Lower weight for secondary keyword matches
VECTOR_MATCH_WEIGHT = 0.8  # Secondary signal from semantic similarity (improved model)
DUAL_MATCH_BOOST = 1.5  # Boost for entries matching both keyword and vector


class LoreService:
    """
    Lore Service - world lore retrieval specialist.

    Responsibilities:
    - Query world packs for relevant lore entries
    - Hybrid search combining keyword matching and vector similarity
    - Filter results by location/region context
    - Format lore for use in GM Agent prompts

    This is a pure service class (no LLM), designed to be called directly
    by GM Agent as a tool function.

    Examples:
        >>> lore_service = LoreService(world_pack_loader, vector_store)
        >>> result = lore_service.search(
        ...     query="暴风城的历史",
        ...     context="玩家询问暴风城的背景",
        ...     world_pack_id="demo_pack",
        ...     current_location="stormwind_square",
        ...     current_region="stormwind",
        ...     lang="cn"
        ... )
        >>> print(result)
    """

    def __init__(
        self,
        world_pack_loader: WorldPackLoader,
        vector_store: VectorStoreService | None = None,
    ):
        """
        Initialize Lore Service.

        Args:
            world_pack_loader: Service for loading world packs
            vector_store: Optional VectorStoreService for semantic search
        """
        self.world_pack_loader = world_pack_loader
        self.vector_store = vector_store

    def search(
        self,
        query: str,
        context: str = "",
        world_pack_id: str = "demo_pack",
        current_location: str | None = None,
        current_region: str | None = None,
        lang: str = "cn",
    ) -> str:
        """
        Search for relevant lore entries and return formatted result.

        This is the main entry point for GM Agent to query lore.

        Args:
            query: What player is asking about
            context: Current game context
            world_pack_id: Specific pack to query
            current_location: (Optional) Current location ID for filtering
            current_region: (Optional) Current region ID for filtering
            lang: Language code ("cn" or "en")

        Returns:
            Formatted lore text string

        Raises:
            Exception: If world pack loading fails
        """
        if not query:
            return f"{'未提供查询内容。' if lang == 'cn' else 'No query provided.'}"

        try:
            # Load world pack
            world_pack = self.world_pack_loader.load(world_pack_id)

            # Search for relevant lore entries with location filtering
            lore_entries = self._search_lore(
                world_pack, query, context, current_location, current_region
            )

            # Format lore for use
            formatted_lore = self._format_lore(lore_entries, query, context, lang)

            return formatted_lore

        except Exception as exc:
            # Return error message instead of raising
            # This allows GM Agent to continue gracefully
            if lang == "cn":
                return f"检索背景信息时出错: {str(exc)}"
            else:
                return f"Error retrieving lore: {str(exc)}"

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
            query: What player is asking about
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

        # Step 1: Keyword matching (with different weights for primary vs secondary)
        search_terms = self._extract_search_terms(query)
        keyword_matched_uids = set()

        for term in search_terms:
            # First, check primary keywords (higher weight)
            primary_matches = world_pack.search_entries_by_keyword(
                term, include_secondary=False
            )
            for entry in primary_matches:
                keyword_matched_uids.add(entry.uid)
                if entry.uid not in entry_scores:
                    entry_scores[entry.uid] = {
                        "entry": entry,
                        "score": KEYWORD_MATCH_WEIGHT,
                        "keyword_match": True,
                        "vector_match": False,
                    }

            # Then, check secondary keywords (lower weight, only if not already matched)
            secondary_matches = world_pack.search_entries_by_keyword(
                term, include_secondary=True
            )
            for entry in secondary_matches:
                # Skip if this was already a primary match
                if entry.uid in keyword_matched_uids:
                    continue
                keyword_matched_uids.add(entry.uid)
                if entry.uid not in entry_scores:
                    entry_scores[entry.uid] = {
                        "entry": entry,
                        "score": KEYWORD_SECONDARY_WEIGHT,
                        "keyword_match": True,
                        "vector_match": False,
                    }

        # Step 2: Vector similarity search
        try:
            # Determine language for search
            search_lang = "cn" if any("\u4e00" <= c <= "\u9fff" for c in query) else "en"
            collection_name = f"lore_entries_{world_pack.pack_info.id}"

            # Search for similar documents (top 10)
            results = self.vector_store.search(
                collection_name=collection_name,
                query_text=query,
                n_results=10,
                where={"lang": search_lang},
                include=["metadatas", "distances"],
            )

            # Process vector search results
            if results["distances"] and results["distances"][0]:
                for metadata, distance in zip(
                    results["metadatas"][0], results["distances"][0], strict=True
                ):
                    uid = metadata["uid"]
                    # Convert cosine distance to similarity
                    # Cosine distance range: [0, 2], where 0 = identical, 2 = opposite
                    similarity = 1.0 - distance
                    vector_score = VECTOR_MATCH_WEIGHT * similarity

                    if uid in entry_scores:
                        # Dual match: boost score
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
            filtered_scores, key=lambda x: (-x["score"], x["entry"].order)
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
        Extract search terms from a query using jieba for Chinese segmentation.

        Args:
            query: Player's query text

        Returns:
            List of relevant search terms
        """
        # Chinese stop words
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
            "这",
            "那",
            "就",
            "也",
            "都",
            "很",
            "非常",
            "a",
            "an",
            "the",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
        }

        # Use jieba for Chinese word segmentation
        terms = []
        words = jieba.lcut(query)

        for word in words:
            # Remove punctuation
            clean_word = word.strip("，。！？：；''()（）[]【】\"\"")
            # Filter: must not be stop word, and length > 1
            if clean_word and clean_word not in stop_words and len(clean_word) > 1 and not clean_word.isspace():
                terms.append(clean_word)

        # Remove duplicates and limit to 5 terms
        seen = set()
        unique_terms = []
        for term in terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
                if len(unique_terms) >= 5:
                    break

        return unique_terms

    def _format_lore(
        self, entries: list, query: str, context: str, lang: str = "cn"
    ) -> str:
        """
        Format lore entries for use in prompts.

        Args:
            entries: List of lore entries
            query: Original query
            context: Game context
            lang: Language code

        Returns:
            Formatted lore string
        """
        if not entries:
            if lang == "cn":
                return f"没有找到与'{query}'相关的背景信息。"
            else:
                return f"No background information found related to '{query}'."

        # Format each entry
        formatted_parts = []

        for entry in entries:
            # Get content in the requested language
            content = entry.content.get(lang) or entry.content.get("en", "")

            # Add to formatted parts
            if entry.key:
                key_str = " / ".join(entry.key)
                formatted_parts.append(f"[{key_str}]\n{content}")
            else:
                formatted_parts.append(content)

        # Join all entries
        lore_text = "\n\n".join(formatted_parts)

        # Add header based on language
        if lang == "cn":
            header = f"与'{query}'相关的背景信息：\n"
        else:
            header = f"Background information related to '{query}':\n"

        return header + lore_text
