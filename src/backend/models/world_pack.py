"""
World Pack models for storing world settings and lore.

Based on GUIDE.md Section 4 (世界包结构), world packs contain:
- Info: Metadata about the world pack
- Entries: Lore entries triggered by keywords
- NPCs: NPC definitions with soul (narrative) and body (data) layers
- Locations: Scene/location definitions
"""

from pydantic import BaseModel, Field

from .i18n import LocalizedString
from .trait import Trait


class WorldPackSetting(BaseModel):
    """
    World setting information for establishing the game's context.

    Helps players understand the era, genre, and tone of the world.
    """

    era: LocalizedString = Field(..., description="Time period of the setting")
    genre: LocalizedString = Field(..., description="Genre and magic/realism level")
    tone: LocalizedString = Field(..., description="Overall tone and atmosphere")


class WorldPackInfo(BaseModel):
    """
    Metadata for a world pack.

    Contains the pack's name, description, version, author,
    and optional setting/player_hook for introduction.
    """

    name: LocalizedString = Field(..., description="World pack name")
    description: LocalizedString = Field(..., description="World pack description")
    version: str = Field(default="1.0.0", description="Semantic version")
    author: str = Field(default="Unknown", description="Pack author")
    setting: WorldPackSetting | None = Field(
        default=None, description="World setting (era, genre, tone)"
    )
    player_hook: LocalizedString | None = Field(
        default=None, description="Player motivation/hook for entering the story"
    )


class RegionData(BaseModel):
    """
    A hierarchical region containing multiple locations.

    Regions provide overarching context (atmosphere, tone) that affects
    all locations within them, enabling dynamic narrative adaptation.
    """

    id: str = Field(..., description="Unique region identifier (snake_case)")
    name: LocalizedString = Field(..., description="Display name")
    description: LocalizedString = Field(..., description="Region overview for context")

    # Atmosphere/tone guidance for GM Agent
    narrative_tone: LocalizedString | None = Field(
        default=None,
        description="GM narrative tone for this region (e.g., 'tense and foreboding', 'peaceful pastoral')",
    )
    atmosphere_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords for atmosphere (dark, foggy, bustling, peaceful) - used for prompt injection",
    )

    # Location hierarchy
    location_ids: list[str] = Field(
        default_factory=list, description="IDs of locations within this region"
    )

    # Context filtering metadata
    tags: list[str] = Field(
        default_factory=list, description="Region tags (wilderness, urban, supernatural, etc.)"
    )


class LoreEntry(BaseModel):
    """
    A lore entry for world background information.

    Based on GUIDE.md Section 4.2, entries are triggered by keywords
    and inject context into the narrative.

    Attributes:
        uid: Unique identifier for the entry
        key: Primary trigger keywords (OR logic)
        secondary_keys: Must also match if present (AND logic with key)
        content: The actual lore content
        comment: Editor notes (not sent to AI)
        constant: If True, always include in context
        selective: If True, only load when triggered
        order: Insertion order (lower = earlier in prompt)
        visibility: Discovery tier ('basic' auto-revealed, 'detailed' requires investigation)
        applicable_regions: If non-empty, only load in these regions
        applicable_locations: If non-empty, only load at these locations
    """

    uid: int = Field(..., description="Unique identifier")
    key: list[str] = Field(..., description="Primary trigger keywords")
    secondary_keys: list[str] = Field(
        default_factory=list, description="Secondary trigger keywords (AND logic)"
    )
    content: LocalizedString = Field(..., description="Lore content")
    comment: LocalizedString | None = Field(
        default=None, description="Editor notes (not sent to AI)"
    )
    constant: bool = Field(default=False, description="Always include in context (use sparingly)")
    selective: bool = Field(default=True, description="Only load when triggered")
    order: int = Field(default=100, description="Insertion order (lower = earlier)")

    # NEW: Discovery tier and location filtering
    visibility: str = Field(
        default="basic",
        description="Discovery tier: 'basic' (auto-revealed), 'detailed' (requires investigation)",
    )
    applicable_regions: list[str] = Field(
        default_factory=list,
        description="If non-empty, only load in these regions (empty = global)",
    )
    applicable_locations: list[str] = Field(
        default_factory=list,
        description="If non-empty, only load at these locations (empty = global)",
    )


class NPCSoul(BaseModel):
    """
    NPC narrative layer (The Soul) - determines how they speak.

    Injected into LLM System Prompt to define speaking style and personality.
    Based on GUIDE.md Section 5.1.A.
    """

    name: str = Field(..., description="NPC identifier name")
    description: LocalizedString = Field(
        ..., description="Appearance, background, personality (100-300 words)"
    )
    appearance: LocalizedString | None = Field(
        default=None,
        description="Brief external appearance description for initial encounter (no name, no background)",
    )
    personality: list[str] = Field(
        ..., description="3-5 personality adjectives", min_length=1, max_length=5
    )
    speech_style: LocalizedString = Field(
        ..., description="Speaking habits, accent, common phrases"
    )
    example_dialogue: list[dict[str, str]] = Field(
        default_factory=list,
        description="Few-shot examples: [{'user': '...', 'char': '...'}]",
    )


class NPCBody(BaseModel):
    """
    NPC data layer (The Body) - structured state.

    Managed by backend, not editable by LLM. Based on GUIDE.md Section 5.1.B.
    """

    location: str = Field(..., description="Current scene/location ID")
    inventory: list[str] = Field(default_factory=list, description="Items held by NPC")
    relations: dict[str, int] = Field(
        default_factory=dict,
        description="Relationship scores with entities (-100 to +100)",
    )
    tags: list[str] = Field(
        default_factory=list, description="Current status tags (injured, angry, etc.)"
    )
    memory: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Key event memories: {'event description': ['keywords']}",
    )

    # NEW: Location-specific knowledge
    location_knowledge: dict[str, list[int]] = Field(
        default_factory=dict,
        description="Location-based knowledge: {location_id: [lore_entry_uids]}. Empty dict = no restrictions (backward compatible)",
    )


class NPCData(BaseModel):
    """
    Complete NPC definition combining soul and body layers.

    An NPC in Astinus has two layers:
    - Soul: Narrative layer for LLM personality (how they speak)
    - Body: Data layer for game state (what they can do)
    """

    id: str = Field(..., description="Unique NPC identifier (snake_case)")
    soul: NPCSoul = Field(..., description="Narrative layer")
    body: NPCBody = Field(..., description="Data layer")

    def get_system_prompt(self, lang: str = "cn") -> str:
        """
        Generate the NPC's system prompt for LLM.

        Args:
            lang: Language code for localized content

        Returns:
            System prompt string for the NPC agent
        """
        soul = self.soul
        lines = [
            f"你是{soul.name}。",
            "",
            soul.description.get(lang),
            "",
            f"性格特征：{', '.join(soul.personality)}",
            "",
            f"说话风格：{soul.speech_style.get(lang)}",
        ]

        if soul.example_dialogue:
            lines.append("")
            lines.append("对话示例：")
            for example in soul.example_dialogue:
                lines.append(f"玩家：{example.get('user', '')}")
                lines.append(f"{soul.name}：{example.get('char', '')}")

        return "\n".join(lines)


class PresetCharacter(BaseModel):
    """
    A preset character for players to choose from.

    Preset characters provide ready-to-play options that fit the world setting,
    with pre-defined traits that make sense for the story context.
    """

    id: str = Field(..., description="Unique identifier for the preset (snake_case)")
    name: str = Field(..., description="Fixed character name (PC name)")
    concept: LocalizedString = Field(..., description="One-sentence character concept")
    traits: list[Trait] = Field(
        default_factory=list,
        description="Character traits (typically 3 for demo)",
        min_length=1,
        max_length=4,
    )


class LocationData(BaseModel):
    """
    A location/scene in the world.

    Locations are where gameplay happens. They can contain NPCs,
    items, and connections to other locations.
    """

    id: str = Field(..., description="Unique location identifier (snake_case)")
    name: LocalizedString = Field(..., description="Display name")
    description: LocalizedString = Field(..., description="Scene description for narration")
    atmosphere: LocalizedString | None = Field(
        default=None,
        description="Time, weather, and environmental atmosphere for scene-setting",
    )
    connected_locations: list[str] = Field(
        default_factory=list, description="IDs of adjacent locations"
    )
    present_npc_ids: list[str] = Field(
        default_factory=list, description="NPCs currently at this location"
    )
    items: list[str] = Field(default_factory=list, description="Interactable items in the scene")
    tags: list[str] = Field(
        default_factory=list, description="Location tags (dark, dangerous, etc.)"
    )

    # NEW: Region association
    region_id: str | None = Field(
        default=None,
        description="Parent region ID - if None, belongs to default global region",
    )

    # NEW: Discovery tiers for hybrid revelation
    visible_items: list[str] = Field(
        default_factory=list,
        description="Items immediately visible (auto-revealed on entry)",
    )
    hidden_items: list[str] = Field(
        default_factory=list,
        description="Items requiring investigation/checks to discover",
    )

    # NEW: Lore filtering metadata
    lore_tags: list[str] = Field(
        default_factory=list,
        description="Tags for filtering lore entries relevant to this location",
    )


class WorldPack(BaseModel):
    """
    A complete world pack containing all world data.

    World packs are the modular content units in Astinus, containing:
    - info: Pack metadata
    - entries: Lore entries for background injection
    - npcs: NPC definitions
    - locations: Scene/location definitions
    - regions: Hierarchical regions containing locations

    Based on GUIDE.md Section 4.
    """

    info: WorldPackInfo = Field(..., description="Pack metadata")
    entries: dict[str, LoreEntry] = Field(
        default_factory=dict, description="Lore entries keyed by uid string"
    )
    npcs: dict[str, NPCData] = Field(default_factory=dict, description="NPCs keyed by id")
    locations: dict[str, LocationData] = Field(
        default_factory=dict, description="Locations keyed by id"
    )
    preset_characters: list[PresetCharacter] = Field(
        default_factory=list,
        description="Preset characters for players to choose from",
    )

    # NEW: Regions hierarchy
    regions: dict[str, RegionData] = Field(
        default_factory=dict,
        description="Regions keyed by id (optional - if empty, single global region)",
    )

    def get_entry(self, uid: int) -> LoreEntry | None:
        """Get a lore entry by uid."""
        return self.entries.get(str(uid))

    def get_npc(self, npc_id: str) -> NPCData | None:
        """Get an NPC by id."""
        return self.npcs.get(npc_id)

    def get_location(self, location_id: str) -> LocationData | None:
        """Get a location by id."""
        return self.locations.get(location_id)

    def get_constant_entries(self) -> list[LoreEntry]:
        """Get all constant (always-active) lore entries."""
        return [e for e in self.entries.values() if e.constant]

    def get_preset_character(self, preset_id: str) -> PresetCharacter | None:
        """Get a preset character by id."""
        for preset in self.preset_characters:
            if preset.id == preset_id:
                return preset
        return None

    def get_region(self, region_id: str) -> RegionData | None:
        """Get a region by id."""
        return self.regions.get(region_id)

    def get_location_region(self, location_id: str) -> RegionData | None:
        """
        Get the region containing a location.

        Args:
            location_id: The location to find the region for

        Returns:
            The region containing the location, or None if not found
        """
        location = self.get_location(location_id)
        if not location or not location.region_id:
            return None
        return self.get_region(location.region_id)

    def get_lore_for_location(self, location_id: str, visibility: str = "basic") -> list[LoreEntry]:
        """
        Get lore entries applicable to a location, filtered by visibility.

        Priority:
        1. Location-specific entries (applicable_locations contains location_id)
        2. Region-specific entries (applicable_regions contains region_id)
        3. Global entries (both lists empty)
        4. Constant entries (always included)

        Args:
            location_id: The location to get lore for
            visibility: Filter by visibility tier ('basic' or 'detailed')

        Returns:
            List of matching lore entries, sorted by order
        """
        location = self.get_location(location_id)
        region = self.get_location_region(location_id) if location else None

        matches = []
        for entry in self.entries.values():
            # Filter by visibility
            if entry.visibility != visibility and not entry.constant:
                continue

            # Constant entries always included
            if entry.constant:
                matches.append(entry)
                continue

            # Check location-specific
            if entry.applicable_locations:
                if location_id in entry.applicable_locations:
                    matches.append(entry)
                continue

            # Check region-specific
            if entry.applicable_regions and region:
                if region.id in entry.applicable_regions:
                    matches.append(entry)
                continue

            # Global entries (no restrictions)
            if not entry.applicable_locations and not entry.applicable_regions:
                matches.append(entry)

        return sorted(matches, key=lambda e: e.order)

    def search_entries_by_keyword(
        self, keyword: str, include_secondary: bool = True
    ) -> list[LoreEntry]:
        """
        Find lore entries matching a keyword.

        Args:
            keyword: The keyword to search for
            include_secondary: Whether to check secondary_keys too

        Returns:
            List of matching entries, sorted by order
        """
        matches = []
        keyword_lower = keyword.lower()

        for entry in self.entries.values():
            # Check primary keys (bidirectional: keyword in key OR key in keyword)
            if any(keyword_lower in k.lower() or k.lower() in keyword_lower for k in entry.key):
                matches.append(entry)
                continue

            # Check secondary keys if enabled (bidirectional match)
            if (
                include_secondary
                and entry.secondary_keys
                and any(
                    keyword_lower in k.lower() or k.lower() in keyword_lower
                    for k in entry.secondary_keys
                )
            ):
                matches.append(entry)

        # Sort by order
        return sorted(matches, key=lambda e: e.order)
