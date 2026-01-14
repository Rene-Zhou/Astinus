"""
Location Context Service for building hierarchical location-based context.

This service aggregates region + location context, filters lore by location/region/visibility,
and manages discovery state transitions.
"""

from typing import Any

from src.backend.models.world_pack import LoreEntry
from src.backend.services.world import WorldPackLoader


class LocationContextService:
    """
    Service for building hierarchical location-based context.

    Responsibilities:
    - Aggregate region + location context
    - Filter lore by location/region/visibility
    - Build atmosphere prompts
    - Handle discovery state transitions
    """

    def __init__(self, world_pack_loader: WorldPackLoader):
        """
        Initialize the service.

        Args:
            world_pack_loader: WorldPackLoader instance for accessing world packs
        """
        self.world_pack_loader = world_pack_loader

    def get_context_for_location(
        self,
        world_pack_id: str,
        location_id: str,
        discovered_items: set[str],
        lang: str = "cn",
    ) -> dict[str, Any]:
        """
        Build complete hierarchical context for a location.

        Args:
            world_pack_id: ID of the world pack
            location_id: ID of the location
            discovered_items: Set of items the player has discovered
            lang: Language code for localized content

        Returns:
            Dictionary containing:
            {
                "region": {
                    "id": str,
                    "name": str,
                    "narrative_tone": str,
                    "atmosphere_keywords": list[str]
                },
                "location": {
                    "id": str,
                    "name": str,
                    "description": str,
                    "atmosphere": str,
                    "visible_items": list[str],
                    "hidden_items_revealed": list[str],
                    "hidden_items_remaining": list[str]
                },
                "basic_lore": list[str],
                "atmosphere_guidance": str
            }
        """
        # Load world pack
        pack = self.world_pack_loader.load(world_pack_id)

        # Get location
        location = pack.get_location(location_id)
        if not location:
            return self._empty_context()

        # Get region (or use default global region)
        region = pack.get_location_region(location_id)
        if not region and pack.regions:
            # Try to get global region
            region = pack.get_region("_global")

        # Build region context
        region_context = {
            "id": region.id if region else "_global",
            "name": region.name.get(lang)
            if region
            else "全局区域"
            if lang == "cn"
            else "Global Region",
            "narrative_tone": region.narrative_tone.get(lang)
            if region and region.narrative_tone
            else "",
            "atmosphere_keywords": region.atmosphere_keywords if region else [],
        }

        # Determine which hidden items have been discovered
        hidden_items_revealed = [item for item in location.hidden_items if item in discovered_items]
        hidden_items_remaining = [
            item for item in location.hidden_items if item not in discovered_items
        ]

        # Build location context
        location_context = {
            "id": location.id,
            "name": location.name.get(lang),
            "description": location.description.get(lang),
            "atmosphere": location.atmosphere.get(lang) if location.atmosphere else "",
            "visible_items": location.visible_items if location.visible_items else location.items,
            "hidden_items_revealed": hidden_items_revealed,
            "hidden_items_remaining": hidden_items_remaining,
        }

        # Get basic lore for this location
        basic_lore_entries = pack.get_lore_for_location(location_id, visibility="basic")
        basic_lore = [entry.content.get(lang) for entry in basic_lore_entries]

        # Build atmosphere guidance string
        atmosphere_guidance = self._build_atmosphere_guidance(
            region_context, location_context, lang
        )

        return {
            "region": region_context,
            "location": location_context,
            "basic_lore": basic_lore,
            "atmosphere_guidance": atmosphere_guidance,
        }

    def filter_npc_lore(
        self,
        npc_id: str,
        location_id: str,
        world_pack_id: str,
        lang: str = "cn",
    ) -> list[LoreEntry]:
        """
        Get lore entries that this NPC knows at this location.

        Logic:
        1. Load NPC's location_knowledge for current location
        2. If empty dict, allow all lore (no restriction - backward compatible)
        3. Otherwise, filter lore by allowed UIDs

        Args:
            npc_id: ID of the NPC
            location_id: Current location ID
            world_pack_id: ID of the world pack
            lang: Language code

        Returns:
            List of lore entries the NPC knows at this location
        """
        # Load world pack
        pack = self.world_pack_loader.load(world_pack_id)

        # Get NPC
        npc = pack.get_npc(npc_id)
        if not npc:
            return []

        # Check location-specific knowledge
        location_knowledge = npc.body.location_knowledge

        # If empty dict, no restrictions (backward compatible)
        if not location_knowledge:
            return list(pack.entries.values())

        # Get allowed lore UIDs for this location
        allowed_uids = location_knowledge.get(location_id, [])

        # If no UIDs for this location, NPC knows nothing here
        if not allowed_uids:
            return []

        # Filter lore entries by allowed UIDs
        filtered_entries = []
        for uid in allowed_uids:
            entry = pack.get_entry(uid)
            if entry:
                filtered_entries.append(entry)

        return filtered_entries

    def check_item_discovery(
        self,
        location_id: str,
        world_pack_id: str,
        item_id: str,
        discovered_items: set[str],
    ) -> dict[str, Any]:
        """
        Check if an item can be discovered (for hidden items).

        Args:
            location_id: Current location ID
            world_pack_id: ID of the world pack
            item_id: Item to check
            discovered_items: Set of already discovered items

        Returns:
            Dictionary containing:
            {
                "is_hidden": bool,
                "is_discovered": bool,
                "requires_check": bool,
                "check_difficulty": int | None
            }
        """
        # Load world pack
        pack = self.world_pack_loader.load(world_pack_id)

        # Get location
        location = pack.get_location(location_id)
        if not location:
            return {
                "is_hidden": False,
                "is_discovered": False,
                "requires_check": False,
                "check_difficulty": None,
            }

        # Check if item is hidden
        is_hidden = item_id in location.hidden_items
        is_discovered = item_id in discovered_items

        return {
            "is_hidden": is_hidden,
            "is_discovered": is_discovered,
            "requires_check": is_hidden and not is_discovered,
            "check_difficulty": None,  # Could be extended in future
        }

    def _empty_context(self) -> dict[str, Any]:
        """Return an empty context structure."""
        return {
            "region": {
                "id": "_global",
                "name": "Unknown",
                "narrative_tone": "",
                "atmosphere_keywords": [],
            },
            "location": {
                "id": "",
                "name": "Unknown",
                "description": "",
                "atmosphere": "",
                "visible_items": [],
                "hidden_items_revealed": [],
                "hidden_items_remaining": [],
            },
            "basic_lore": [],
            "atmosphere_guidance": "",
        }

    def _build_atmosphere_guidance(
        self,
        region_context: dict[str, Any],
        location_context: dict[str, Any],
        lang: str,
    ) -> str:
        """
        Build atmosphere guidance string for GM Agent.

        Combines region tone and location atmosphere into concise guidance.

        Args:
            region_context: Region context dictionary
            location_context: Location context dictionary
            lang: Language code

        Returns:
            Atmosphere guidance string
        """
        parts = []

        # Add region tone if available
        if region_context.get("narrative_tone"):
            parts.append(region_context["narrative_tone"])

        # Add location atmosphere if available
        if location_context.get("atmosphere"):
            parts.append(location_context["atmosphere"])

        # Add atmosphere keywords
        if region_context.get("atmosphere_keywords"):
            keywords = region_context["atmosphere_keywords"]
            if lang == "cn":
                parts.append(f"氛围关键词: {', '.join(keywords)}")
            else:
                parts.append(f"Atmosphere keywords: {', '.join(keywords)}")

        return " | ".join(parts) if parts else ""
