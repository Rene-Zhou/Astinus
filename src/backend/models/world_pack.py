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


class WorldPackInfo(BaseModel):
    """
    Metadata for a world pack.

    Contains the pack's name, description, version, and author.
    """

    name: LocalizedString = Field(..., description="World pack name")
    description: LocalizedString = Field(..., description="World pack description")
    version: str = Field(default="1.0.0", description="Semantic version")
    author: str = Field(default="Unknown", description="Pack author")


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
    constant: bool = Field(
        default=False, description="Always include in context (use sparingly)"
    )
    selective: bool = Field(default=True, description="Only load when triggered")
    order: int = Field(default=100, description="Insertion order (lower = earlier)")


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
    inventory: list[str] = Field(
        default_factory=list, description="Items held by NPC"
    )
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


class LocationData(BaseModel):
    """
    A location/scene in the world.

    Locations are where gameplay happens. They can contain NPCs,
    items, and connections to other locations.
    """

    id: str = Field(..., description="Unique location identifier (snake_case)")
    name: LocalizedString = Field(..., description="Display name")
    description: LocalizedString = Field(
        ..., description="Scene description for narration"
    )
    connected_locations: list[str] = Field(
        default_factory=list, description="IDs of adjacent locations"
    )
    present_npc_ids: list[str] = Field(
        default_factory=list, description="NPCs currently at this location"
    )
    items: list[str] = Field(
        default_factory=list, description="Interactable items in the scene"
    )
    tags: list[str] = Field(
        default_factory=list, description="Location tags (dark, dangerous, etc.)"
    )


class WorldPack(BaseModel):
    """
    A complete world pack containing all world data.

    World packs are the modular content units in Astinus, containing:
    - info: Pack metadata
    - entries: Lore entries for background injection
    - npcs: NPC definitions
    - locations: Scene/location definitions

    Based on GUIDE.md Section 4.
    """

    info: WorldPackInfo = Field(..., description="Pack metadata")
    entries: dict[str, LoreEntry] = Field(
        default_factory=dict, description="Lore entries keyed by uid string"
    )
    npcs: dict[str, NPCData] = Field(
        default_factory=dict, description="NPCs keyed by id"
    )
    locations: dict[str, LocationData] = Field(
        default_factory=dict, description="Locations keyed by id"
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
            # Check primary keys
            if any(keyword_lower in k.lower() for k in entry.key):
                matches.append(entry)
                continue

            # Check secondary keys if enabled
            if (
                include_secondary
                and entry.secondary_keys
                and any(keyword_lower in k.lower() for k in entry.secondary_keys)
            ):
                matches.append(entry)

        # Sort by order
        return sorted(matches, key=lambda e: e.order)
