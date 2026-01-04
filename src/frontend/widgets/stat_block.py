"""
StatBlock widget for displaying character statistics.

Based on GUIDE.md Section 3 - Pure trait-based system:
- Character name and concept
- Traits (with positive/negative aspects)
- Tags (status effects like "右腿受伤", "疲惫")
- Fate points (narrative currency)
- Current location and NPC info
- Game phase and turn tracking

NO numerical attributes, NO HP/MP - status tracked via Tags.
"""

from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Label, Static


class StatBlock(Static):
    """
    A widget for displaying character statistics.

    Based on GUIDE.md trait-based design:
    - Character name and concept
    - Traits with dual aspects
    - Tags (status effects)
    - Fate points
    - Current location
    - Nearby NPCs
    - Game phase and turn
    """

    DEFAULT_CSS = """
    StatBlock {
        width: 100%;
        border: solid $accent;
        padding: 1;
        background: $panel;
    }

    .stat-label {
        width: 30%;
        text-style: bold;
        color: $accent;
    }

    .stat-value {
        width: 70%;
    }

    .stat-row {
        height: 2;
        width: 100%;
    }

    .section-title {
        height: 2;
        text-style: bold;
        color: $primary;
        text-align: center;
        border-bottom: solid $primary;
        margin-bottom: 1;
    }

    .fate-points {
        width: 100%;
        height: 2;
        text-align: center;
        text-style: bold;
        color: $warning;
    }

    .fate-point-star {
        color: $warning;
    }

    .fate-point-star.empty {
        color: $text-muted;
    }

    .traits-list {
        width: 100%;
        min-height: 2;
        max-height: 8;
        padding: 0 1;
    }

    .trait-item {
        height: auto;
        min-height: 2;
        width: 100%;
        margin-bottom: 1;
        padding: 0 1;
        border: solid $accent;
    }

    .trait-name {
        text-style: bold;
        color: $accent;
    }

    .trait-positive {
        color: $success;
    }

    .trait-negative {
        color: $error;
    }

    .tags-list {
        width: 100%;
        min-height: 2;
        max-height: 4;
        padding: 0 1;
    }

    .tag-item {
        height: 1;
        color: $warning;
        padding: 0 1;
    }

    .tag-item.negative {
        color: $error;
    }

    .tag-item.positive {
        color: $success;
    }

    .npc-list {
        width: 100%;
        min-height: 2;
        max-height: 4;
        padding: 0 1;
    }

    .npc-item {
        height: 1;
        color: $text;
    }

    .npc-item.friendly {
        color: $success;
    }

    .npc-item.hostile {
        color: $error;
    }

    .npc-item.neutral {
        color: $warning;
    }

    .no-items {
        color: $text-muted;
        height: 1;
    }
    """

    # Reactive character data
    character_data: Optional[Dict[str, Any]] = reactive(None)
    game_state_data: Optional[Dict[str, Any]] = reactive(None)

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the StatBlock."""
        super().__init__(*args, **kwargs)
        self._fate_points = 3
        self._max_fate_points = 5
        self._traits: List[Dict[str, Any]] = []
        self._tags: List[str] = []
        self._nearby_npcs: List[Dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        """Compose the stat block layout."""
        with Vertical():
            # Character Info Section
            yield Label("⚔️ 角色 / Character", classes="section-title")

            with Horizontal(classes="stat-row"):
                yield Label("名称:", classes="stat-label")
                yield Label("Unknown", id="char-name", classes="stat-value")

            with Horizontal(classes="stat-row"):
                yield Label("概念:", classes="stat-label")
                yield Label("Unknown", id="char-concept", classes="stat-value")

            # Fate Points Section
            yield Label("⭐ 命运点 / Fate Points", classes="section-title")
            yield Label(
                self._render_fate_points_stars(), id="fate-points-display", classes="fate-points"
            )

            # Traits Section
            yield Label("📜 特质 / Traits", classes="section-title")
            with Vertical(id="traits-container", classes="traits-list"):
                yield Label("无特质 / No traits", id="no-traits", classes="no-items")

            # Tags Section (Status Effects)
            yield Label("🏷️ 状态标签 / Status Tags", classes="section-title")
            with Vertical(id="tags-container", classes="tags-list"):
                yield Label("无状态 / No status effects", id="no-tags", classes="no-items")

            # Location & NPCs Section
            yield Label("📍 位置 / Location", classes="section-title")

            with Horizontal(classes="stat-row"):
                yield Label("当前:", classes="stat-label")
                yield Label("Unknown", id="char-location", classes="stat-value")

            yield Label("👥 附近 / Nearby", classes="section-title")
            with Vertical(id="npcs-container", classes="npc-list"):
                yield Label("无人附近 / No one nearby", id="no-npcs", classes="no-items")

            # Game State Section
            yield Label("🎮 游戏 / Game", classes="section-title")

            with Horizontal(classes="stat-row"):
                yield Label("阶段:", classes="stat-label")
                yield Label("Waiting", id="game-phase", classes="stat-value")

            with Horizontal(classes="stat-row"):
                yield Label("回合:", classes="stat-label")
                yield Label("0", id="turn-count", classes="stat-value")

    def on_mount(self) -> None:
        """Called when widget mounts."""
        pass

    def _render_fate_points_stars(self) -> str:
        """Render fate points as stars."""
        filled = "★" * self._fate_points
        empty = "☆" * (self._max_fate_points - self._fate_points)
        return f"{filled}{empty} ({self._fate_points}/{self._max_fate_points})"

    def update_character(self, character_data: Dict[str, Any]) -> None:
        """
        Update character information.

        Args:
            character_data: Character data dictionary with structure:
                {
                    "name": str,
                    "concept": str or dict (LocalizedString),
                    "traits": [
                        {
                            "name": str or dict,
                            "description": str or dict,
                            "positive_aspect": str or dict,
                            "negative_aspect": str or dict
                        },
                        ...
                    ],
                    "fate_points": int,
                    "tags": [str, ...]
                }
        """
        self.character_data = character_data
        self._render_character_data()

    def update_game_state(self, game_state: Dict[str, Any]) -> None:
        """
        Update game state information.

        Args:
            game_state: Game state dictionary with structure:
                {
                    "current_location": str,
                    "current_phase": str,
                    "turn_count": int,
                    "nearby_npcs": [{"name": str, "disposition": str}, ...]
                }
        """
        self.game_state_data = game_state
        self._render_game_state()

    def update_fate_points(self, current: int, maximum: int = 5) -> None:
        """
        Update fate points display.

        Args:
            current: Current fate points (0-5)
            maximum: Maximum fate points (default 5)
        """
        self._fate_points = max(0, min(current, maximum))
        self._max_fate_points = maximum
        self._update_fate_points_display()

    def update_traits(self, traits: List[Dict[str, Any]]) -> None:
        """
        Update traits list.

        Args:
            traits: List of trait dictionaries with structure:
                {
                    "name": str or dict,
                    "description": str or dict,
                    "positive_aspect": str or dict,
                    "negative_aspect": str or dict
                }
        """
        self._traits = traits
        self._render_traits()

    def update_tags(self, tags: List[str]) -> None:
        """
        Update status tags list.

        Args:
            tags: List of tag strings (e.g., ["右腿受伤", "疲惫"])
        """
        self._tags = tags
        self._render_tags()

    def update_nearby_npcs(self, npcs: List[Dict[str, Any]]) -> None:
        """
        Update nearby NPCs list.

        Args:
            npcs: List of NPC dictionaries with structure:
                {"name": str, "disposition": "friendly"|"hostile"|"neutral"}
        """
        self._nearby_npcs = npcs
        self._render_npcs()

    def _get_localized_text(self, value: Any, lang: str = "cn") -> str:
        """
        Get localized text from value.

        Args:
            value: String or dict with language keys
            lang: Preferred language code

        Returns:
            Localized text string
        """
        if isinstance(value, dict):
            return value.get(lang, value.get("en", value.get("cn", str(value))))
        return str(value) if value else ""

    def _render_character_data(self) -> None:
        """Render character data to the display."""
        if not self.character_data:
            return

        try:
            # Update name
            name = self.character_data.get("name", "Unknown")
            self.query_one("#char-name", Label).update(name)

            # Update concept (supports LocalizedString)
            concept = self.character_data.get("concept", {})
            concept_text = self._get_localized_text(concept)
            if not concept_text:
                concept_text = "Unknown"
            self.query_one("#char-concept", Label).update(concept_text)

            # Update fate points
            fate_points = self.character_data.get("fate_points", 3)
            self.update_fate_points(fate_points)

            # Update traits
            traits = self.character_data.get("traits", [])
            self.update_traits(traits)

            # Update tags
            tags = self.character_data.get("tags", [])
            self.update_tags(tags)

        except NoMatches:
            # Widgets not ready yet
            pass

    def _render_game_state(self) -> None:
        """Render game state to the display."""
        if not self.game_state_data:
            return

        try:
            # Update location
            location = self.game_state_data.get("current_location", "Unknown")
            self.query_one("#char-location", Label).update(location)

            # Update phase
            phase = self.game_state_data.get("current_phase", "Unknown")
            self.query_one("#game-phase", Label).update(phase)

            # Update turn count
            turn_count = self.game_state_data.get("turn_count", 0)
            self.query_one("#turn-count", Label).update(str(turn_count))

            # Update nearby NPCs
            npcs = self.game_state_data.get("nearby_npcs", [])
            if npcs:
                self.update_nearby_npcs(npcs)

        except NoMatches:
            # Widgets not ready yet
            pass

    def _update_fate_points_display(self) -> None:
        """Update fate points display."""
        try:
            display = self.query_one("#fate-points-display", Label)
            display.update(self._render_fate_points_stars())
        except NoMatches:
            pass

    def _render_traits(self) -> None:
        """Render traits list."""
        try:
            container = self.query_one("#traits-container", Vertical)
            no_traits_label = self.query_one("#no-traits", Label)

            # Clear existing trait items (except the no-traits label)
            for child in list(container.children):
                if child.id != "no-traits":
                    child.remove()

            if not self._traits:
                no_traits_label.styles.display = "block"
            else:
                no_traits_label.styles.display = "none"
                for i, trait in enumerate(self._traits[:4]):  # Show max 4 traits
                    trait_name = self._get_localized_text(trait.get("name", ""))
                    positive = self._get_localized_text(trait.get("positive_aspect", ""))
                    negative = self._get_localized_text(trait.get("negative_aspect", ""))

                    if not trait_name:
                        continue

                    # Create trait display with all aspects
                    with Vertical(classes="trait-item"):
                        name_label = Label(f"[bold]{trait_name}[/bold]", classes="trait-name")
                        container.mount(name_label)

                        if positive:
                            pos_label = Label(f"  ✓ {positive}", classes="trait-positive")
                            container.mount(pos_label)

                        if negative:
                            neg_label = Label(f"  ✗ {negative}", classes="trait-negative")
                            container.mount(neg_label)

        except NoMatches:
            pass

    def _render_tags(self) -> None:
        """Render status tags list."""
        try:
            container = self.query_one("#tags-container", Vertical)
            no_tags_label = self.query_one("#no-tags", Label)

            # Clear existing tag items (except the no-tags label)
            for child in list(container.children):
                if child.id != "no-tags":
                    child.remove()

            if not self._tags:
                no_tags_label.styles.display = "block"
            else:
                no_tags_label.styles.display = "none"
                for tag in self._tags[:6]:  # Show max 6 tags
                    # Determine tag type based on content (simple heuristic)
                    tag_class = "tag-item"
                    if any(
                        word in tag
                        for word in ["受伤", "中毒", "疲惫", "眩晕", "injured", "poisoned"]
                    ):
                        tag_class += " negative"
                    elif any(
                        word in tag for word in ["增强", "祝福", "激励", "blessed", "inspired"]
                    ):
                        tag_class += " positive"

                    label = Label(f"• {tag}", classes=tag_class)
                    container.mount(label)

        except NoMatches:
            pass

    def _render_npcs(self) -> None:
        """Render nearby NPCs list."""
        try:
            container = self.query_one("#npcs-container", Vertical)
            no_npcs_label = self.query_one("#no-npcs", Label)

            # Clear existing NPC items (except the no-npcs label)
            for child in list(container.children):
                if child.id != "no-npcs":
                    child.remove()

            if not self._nearby_npcs:
                no_npcs_label.styles.display = "block"
            else:
                no_npcs_label.styles.display = "none"
                for npc in self._nearby_npcs[:4]:  # Show max 4 NPCs
                    npc_name = npc.get("name", "Unknown")
                    disposition = npc.get("disposition", "neutral")

                    # Format NPC text with icon
                    if disposition == "friendly":
                        icon = "😊"
                    elif disposition == "hostile":
                        icon = "😠"
                    else:
                        icon = "😐"

                    text = f"{icon} {npc_name}"

                    # Create label with appropriate class
                    label = Label(text, classes=f"npc-item {disposition}")
                    container.mount(label)

        except NoMatches:
            pass

    # Legacy compatibility methods (deprecated - for migration only)
    def update_hp(self, current: int, max_hp: int) -> None:
        """
        DEPRECATED: HP is not used in trait-based system.
        Status is tracked via tags instead.

        This method is kept for backward compatibility during migration.
        """
        # Convert HP loss to a tag
        if current < max_hp:
            percent = current / max_hp if max_hp > 0 else 0
            if percent < 0.25:
                if "重伤" not in self._tags:
                    self._tags.append("重伤")
            elif percent < 0.5:
                if "受伤" not in self._tags:
                    self._tags.append("受伤")
            self._render_tags()

    def update_mp(self, current: int, max_mp: int) -> None:
        """
        DEPRECATED: MP is not used in trait-based system.
        This method is kept for backward compatibility during migration.
        """
        pass

    def update_effects(self, effects: List[Dict[str, Any]]) -> None:
        """
        DEPRECATED: Use update_tags instead.
        Convert effects to tags for backward compatibility.
        """
        # Convert effects to tags
        for effect in effects:
            effect_name = effect.get("name", "")
            if effect_name and effect_name not in self._tags:
                self._tags.append(effect_name)
        self._render_tags()
