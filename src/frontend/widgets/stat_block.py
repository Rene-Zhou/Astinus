"""
StatBlock widget for displaying character statistics.

Enhanced features:
- Character name and concept
- Attributes with PbtA-style modifiers
- HP/MP status bars
- Active effects list
- Current location and NPC info
- Game phase and turn tracking
"""

from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Label, ProgressBar, Static


class StatBlock(Static):
    """
    A widget for displaying character statistics.

    Shows:
    - Character name and concept
    - Attributes (Strength, Dexterity, etc.)
    - HP/MP bars
    - Active effects
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

    .attribute-row {
        height: 2;
        width: 100%;
    }

    .attribute-name {
        width: 40%;
        text-style: bold;
        color: $text;
    }

    .attribute-value {
        width: 20%;
        text-align: center;
        color: $accent;
        text-style: bold;
    }

    .attribute-value.positive {
        color: $success;
    }

    .attribute-value.negative {
        color: $error;
    }

    .hp-bar {
        width: 100%;
        height: 1;
        margin: 0;
    }

    .hp-bar > .bar--bar {
        color: $error;
    }

    .mp-bar {
        width: 100%;
        height: 1;
        margin: 0;
    }

    .mp-bar > .bar--bar {
        color: $primary;
    }

    .bar-label {
        width: 100%;
        height: 1;
        text-align: left;
        color: $text-muted;
    }

    .effects-list {
        width: 100%;
        min-height: 2;
        max-height: 4;
        padding: 0 1;
    }

    .effect-item {
        height: 1;
        color: $warning;
    }

    .effect-item.buff {
        color: $success;
    }

    .effect-item.debuff {
        color: $error;
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
    """

    # Reactive character data
    character_data: Optional[Dict[str, Any]] = reactive(None)
    game_state_data: Optional[Dict[str, Any]] = reactive(None)

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the StatBlock."""
        super().__init__(*args, **kwargs)
        self._hp_current = 10
        self._hp_max = 10
        self._mp_current = 5
        self._mp_max = 5
        self._effects: List[Dict[str, Any]] = []
        self._nearby_npcs: List[Dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        """Compose the stat block layout."""
        with Vertical():
            # Character Info Section
            yield Label("⚔️ Character", classes="section-title")

            with Horizontal(classes="stat-row"):
                yield Label("Name:", classes="stat-label")
                yield Label("Unknown", id="char-name", classes="stat-value")

            with Horizontal(classes="stat-row"):
                yield Label("Concept:", classes="stat-label")
                yield Label("Unknown", id="char-concept", classes="stat-value")

            # Attributes Section
            yield Label("📊 Attributes", classes="section-title")

            with Horizontal(classes="attribute-row"):
                yield Label("Strength", classes="attribute-name")
                yield Label("+0", id="attr-strength", classes="attribute-value")
                yield Label("Dexterity", classes="attribute-name")
                yield Label("+0", id="attr-dexterity", classes="attribute-value")

            with Horizontal(classes="attribute-row"):
                yield Label("Intelligence", classes="attribute-name")
                yield Label("+0", id="attr-intelligence", classes="attribute-value")
                yield Label("Charisma", classes="attribute-name")
                yield Label("+0", id="attr-charisma", classes="attribute-value")

            with Horizontal(classes="attribute-row"):
                yield Label("Perception", classes="attribute-name")
                yield Label("+0", id="attr-perception", classes="attribute-value")
                yield Label("", classes="attribute-name")
                yield Label("", classes="attribute-value")

            # Status Bars Section
            yield Label("❤️ Status", classes="section-title")

            yield Label("HP: 10/10", id="hp-label", classes="bar-label")
            yield ProgressBar(total=100, show_eta=False, id="hp-bar", classes="hp-bar")

            yield Label("MP: 5/5", id="mp-label", classes="bar-label")
            yield ProgressBar(total=100, show_eta=False, id="mp-bar", classes="mp-bar")

            # Effects Section
            yield Label("✨ Active Effects", classes="section-title")
            with Vertical(id="effects-container", classes="effects-list"):
                yield Label("None", id="no-effects", classes="effect-item")

            # Location & NPCs Section
            yield Label("📍 Location", classes="section-title")

            with Horizontal(classes="stat-row"):
                yield Label("Location:", classes="stat-label")
                yield Label("Unknown", id="char-location", classes="stat-value")

            yield Label("👥 Nearby", classes="section-title")
            with Vertical(id="npcs-container", classes="npc-list"):
                yield Label("No one nearby", id="no-npcs", classes="npc-item")

            # Game State Section
            yield Label("🎮 Game", classes="section-title")

            with Horizontal(classes="stat-row"):
                yield Label("Phase:", classes="stat-label")
                yield Label("Waiting", id="game-phase", classes="stat-value")

            with Horizontal(classes="stat-row"):
                yield Label("Turn:", classes="stat-label")
                yield Label("0", id="turn-count", classes="stat-value")

    def on_mount(self) -> None:
        """Called when widget mounts."""
        # Initialize progress bars
        self._update_hp_bar()
        self._update_mp_bar()

    def update_character(self, character_data: Dict[str, Any]) -> None:
        """
        Update character information.

        Args:
            character_data: Character data dictionary with structure:
                {
                    "name": str,
                    "concept": str or dict,
                    "attributes": {
                        "strength": int,
                        "dexterity": int,
                        ...
                    },
                    "hp": {"current": int, "max": int},
                    "mp": {"current": int, "max": int},
                    "effects": [{"name": str, "type": str}, ...]
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

    def update_hp(self, current: int, max_hp: int) -> None:
        """
        Update HP values.

        Args:
            current: Current HP
            max_hp: Maximum HP
        """
        self._hp_current = max(0, min(current, max_hp))
        self._hp_max = max_hp
        self._update_hp_bar()

    def update_mp(self, current: int, max_mp: int) -> None:
        """
        Update MP values.

        Args:
            current: Current MP
            max_mp: Maximum MP
        """
        self._mp_current = max(0, min(current, max_mp))
        self._mp_max = max_mp
        self._update_mp_bar()

    def update_effects(self, effects: List[Dict[str, Any]]) -> None:
        """
        Update active effects list.

        Args:
            effects: List of effect dictionaries with structure:
                {"name": str, "type": "buff"|"debuff"|"neutral", "duration": int}
        """
        self._effects = effects
        self._render_effects()

    def update_nearby_npcs(self, npcs: List[Dict[str, Any]]) -> None:
        """
        Update nearby NPCs list.

        Args:
            npcs: List of NPC dictionaries with structure:
                {"name": str, "disposition": "friendly"|"hostile"|"neutral"}
        """
        self._nearby_npcs = npcs
        self._render_npcs()

    def _format_attribute_value(self, value: int) -> str:
        """Format attribute value with sign."""
        if value > 0:
            return f"+{value}"
        return str(value)

    def _render_character_data(self) -> None:
        """Render character data to the display."""
        if not self.character_data:
            return

        try:
            # Update name
            name = self.character_data.get("name", "Unknown")
            self.query_one("#char-name", Label).update(name)

            # Update concept
            concept = self.character_data.get("concept", {})
            if isinstance(concept, dict):
                # Multi-language concept
                concept_text = concept.get("en", concept.get("cn", "Unknown"))
            else:
                concept_text = str(concept) if concept else "Unknown"
            self.query_one("#char-concept", Label).update(concept_text)

            # Update attributes
            attributes = self.character_data.get("attributes", {})
            for attr_name in ["strength", "dexterity", "intelligence", "charisma", "perception"]:
                value = attributes.get(attr_name, 0)
                formatted = self._format_attribute_value(value)
                try:
                    attr_label = self.query_one(f"#attr-{attr_name}", Label)
                    attr_label.update(formatted)
                    # Update class for coloring
                    attr_label.remove_class("positive")
                    attr_label.remove_class("negative")
                    if value > 0:
                        attr_label.add_class("positive")
                    elif value < 0:
                        attr_label.add_class("negative")
                except NoMatches:
                    pass

            # Update HP/MP if provided
            hp_data = self.character_data.get("hp", {})
            if hp_data:
                self.update_hp(hp_data.get("current", 10), hp_data.get("max", 10))

            mp_data = self.character_data.get("mp", {})
            if mp_data:
                self.update_mp(mp_data.get("current", 5), mp_data.get("max", 5))

            # Update effects if provided
            effects = self.character_data.get("effects", [])
            if effects:
                self.update_effects(effects)

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

    def _update_hp_bar(self) -> None:
        """Update HP progress bar."""
        try:
            hp_label = self.query_one("#hp-label", Label)
            hp_bar = self.query_one("#hp-bar", ProgressBar)

            hp_label.update(f"HP: {self._hp_current}/{self._hp_max}")

            # Calculate percentage
            if self._hp_max > 0:
                percentage = (self._hp_current / self._hp_max) * 100
            else:
                percentage = 0

            hp_bar.update(progress=percentage)
        except NoMatches:
            pass

    def _update_mp_bar(self) -> None:
        """Update MP progress bar."""
        try:
            mp_label = self.query_one("#mp-label", Label)
            mp_bar = self.query_one("#mp-bar", ProgressBar)

            mp_label.update(f"MP: {self._mp_current}/{self._mp_max}")

            # Calculate percentage
            if self._mp_max > 0:
                percentage = (self._mp_current / self._mp_max) * 100
            else:
                percentage = 0

            mp_bar.update(progress=percentage)
        except NoMatches:
            pass

    def _render_effects(self) -> None:
        """Render active effects list."""
        try:
            container = self.query_one("#effects-container", Vertical)
            no_effects_label = self.query_one("#no-effects", Label)

            # Clear existing effect items (except the no-effects label)
            for child in list(container.children):
                if child.id != "no-effects":
                    child.remove()

            if not self._effects:
                no_effects_label.styles.display = "block"
            else:
                no_effects_label.styles.display = "none"
                for effect in self._effects[:4]:  # Show max 4 effects
                    effect_name = effect.get("name", "Unknown")
                    effect_type = effect.get("type", "neutral")
                    duration = effect.get("duration", 0)

                    # Format effect text
                    if duration > 0:
                        text = f"• {effect_name} ({duration} turns)"
                    else:
                        text = f"• {effect_name}"

                    # Create label with appropriate class
                    label = Label(text, classes=f"effect-item {effect_type}")
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
