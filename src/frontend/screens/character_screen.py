"""
Character sheet screen.

Based on GUIDE.md Section 3 - Pure trait-based system:
- Character name and concept
- Traits with positive/negative aspects
- Tags (status effects)
- Fate points
- Current game state

No numerical attributes, no HP/MP.
"""

from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static


class CharacterScreen(Screen):
    """
    Character sheet display screen.

    Shows detailed character information using trait-based system.
    """

    DEFAULT_CSS = """
    CharacterScreen {
        background: $background;
    }

    #character-layout {
        height: 100%;
        width: 100%;
        padding: 1;
    }

    .nav-button {
        width: 100%;
        height: 3;
        margin: 0 1;
        background: $panel;
        color: $text;
        border: solid $accent;
        text-align: center;
    }

    .nav-button:hover {
        background: $accent;
        color: $text;
    }

    .section {
        border: solid $primary;
        padding: 1;
        margin: 1 0;
        background: $panel;
    }

    .section-title {
        height: 3;
        text-align: center;
        text-style: bold;
        color: $primary;
        border: solid $primary;
        margin-bottom: 1;
    }

    .field-label {
        width: 25%;
        text-style: bold;
        color: $accent;
    }

    .field-value {
        width: 75%;
    }

    .field-row {
        height: 2;
        width: 100%;
    }

    .fate-points-display {
        width: 100%;
        height: 2;
        text-align: center;
        text-style: bold;
        color: $warning;
        margin: 1 0;
    }

    .trait-item {
        width: 100%;
        height: auto;
        min-height: 4;
        border: solid $accent;
        padding: 1;
        margin: 0 0 1 0;
    }

    .trait-name {
        text-style: bold;
        color: $accent;
        height: 1;
    }

    .trait-desc {
        color: $text-muted;
        height: 1;
    }

    .trait-positive {
        color: $success;
        height: 1;
    }

    .trait-negative {
        color: $error;
        height: 1;
    }

    .tags-container {
        width: 100%;
        height: auto;
        min-height: 2;
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

    .no-items {
        color: $text-muted;
        height: 1;
    }
    """

    def __init__(self) -> None:
        """Initialize the character screen."""
        super().__init__()
        self.character_data: Optional[Dict[str, Any]] = None

    def compose(self) -> ComposeResult:
        """Compose the character screen layout."""
        with Container(id="character-layout"):
            # Navigation
            with Horizontal(classes="nav-bar"):
                yield Button("← 返回游戏 / Back to Game (G)", id="btn-back", classes="nav-button")

            with ScrollableContainer():
                # Character Identity Section
                yield Label("📋 角色信息 / Character Info", classes="section-title")

                with Vertical(classes="section"):
                    with Horizontal(classes="field-row"):
                        yield Label("名称 / Name:", classes="field-label")
                        yield Label("Loading...", id="char-name", classes="field-value")

                    with Horizontal(classes="field-row"):
                        yield Label("概念 / Concept:", classes="field-label")
                        yield Label("Loading...", id="char-concept", classes="field-value")

                # Fate Points Section
                yield Label("⭐ 命运点 / Fate Points", classes="section-title")
                yield Label(
                    "★★★☆☆ (3/5)",
                    id="fate-points-display",
                    classes="fate-points-display",
                )

                # Traits Section
                yield Label("📜 角色特质 / Character Traits", classes="section-title")
                with Vertical(classes="section", id="traits-section"):
                    yield Static("无特质 / No traits", id="traits-list")

                # Tags Section (Status Effects)
                yield Label("🏷️ 状态标签 / Status Tags", classes="section-title")
                with Vertical(classes="section", id="tags-section"):
                    yield Static("无状态 / No status effects", id="tags-list")

                # Game State Section
                yield Label("🎮 游戏状态 / Game State", classes="section-title")

                with Vertical(classes="section"):
                    with Horizontal(classes="field-row"):
                        yield Label("位置 / Location:", classes="field-label")
                        yield Label("Unknown", id="char-location", classes="field-value")

                    with Horizontal(classes="field-row"):
                        yield Label("阶段 / Phase:", classes="field-label")
                        yield Label("Waiting", id="game-phase", classes="field-value")

                    with Horizontal(classes="field-row"):
                        yield Label("回合 / Turn:", classes="field-label")
                        yield Label("0", id="turn-count", classes="field-value")

    def on_mount(self) -> None:
        """Called when screen mounts."""
        self.load_character_data()

    def load_character_data(self) -> None:
        """Load character data from app."""
        if self.app:
            # Try to get character data from app
            if hasattr(self.app, "player_character") and self.app.player_character:
                self.character_data = self.app.player_character
            elif hasattr(self.app, "client") and self.app.client:
                self.character_data = {
                    "name": getattr(self.app.client, "player_name", None) or "Player",
                    "concept": {"cn": "冒险者", "en": "Adventurer"},
                    "traits": [],
                    "fate_points": 3,
                    "tags": [],
                }
            else:
                self.character_data = {
                    "name": "Player",
                    "concept": {"cn": "冒险者", "en": "Adventurer"},
                    "traits": [],
                    "fate_points": 3,
                    "tags": [],
                }
            self._render_character_data()

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

    def _render_fate_points(self, current: int, maximum: int = 5) -> str:
        """Render fate points as stars."""
        filled = "★" * current
        empty = "☆" * (maximum - current)
        return f"{filled}{empty} ({current}/{maximum})"

    def _render_character_data(self) -> None:
        """Render character data to the UI."""
        if not self.character_data:
            return

        try:
            # Update name
            name = self.character_data.get("name", "Unknown")
            self.query_one("#char-name", Label).update(name)

            # Update concept
            concept = self.character_data.get("concept", {})
            concept_text = self._get_localized_text(concept)
            if not concept_text:
                concept_text = "Unknown"
            self.query_one("#char-concept", Label).update(concept_text)

            # Update fate points
            fate_points = self.character_data.get("fate_points", 3)
            fate_display = self._render_fate_points(fate_points)
            self.query_one("#fate-points-display", Label).update(fate_display)

            # Update traits
            traits = self.character_data.get("traits", [])
            self._render_traits(traits)

            # Update tags
            tags = self.character_data.get("tags", [])
            self._render_tags(tags)

        except Exception as e:
            self.log(f"Error rendering character data: {e}")

    def _render_traits(self, traits: List[Dict[str, Any]]) -> None:
        """Render traits list."""
        try:
            traits_list = self.query_one("#traits-list", Static)

            if not traits:
                traits_list.update("无特质 / No traits")
                return

            # Build traits display text
            lines = []
            for trait in traits:
                name = self._get_localized_text(trait.get("name", ""))
                description = self._get_localized_text(trait.get("description", ""))
                positive = self._get_localized_text(trait.get("positive_aspect", ""))
                negative = self._get_localized_text(trait.get("negative_aspect", ""))

                if not name:
                    continue

                lines.append(f"[bold]{name}[/bold]")
                if description:
                    lines.append(f"  {description}")
                if positive:
                    lines.append(f"  [green]✓ {positive}[/green]")
                if negative:
                    lines.append(f"  [red]✗ {negative}[/red]")
                lines.append("")  # Empty line between traits

            traits_list.update("\n".join(lines) if lines else "无特质 / No traits")

        except Exception as e:
            self.log(f"Error rendering traits: {e}")

    def _render_tags(self, tags: List[str]) -> None:
        """Render status tags list."""
        try:
            tags_list = self.query_one("#tags-list", Static)

            if not tags:
                tags_list.update("无状态 / No status effects")
                return

            # Build tags display with coloring based on content
            lines = []
            for tag in tags:
                # Determine tag type based on content
                if any(
                    word in tag for word in ["受伤", "中毒", "疲惫", "眩晕", "injured", "poisoned"]
                ):
                    lines.append(f"[red]• {tag}[/red]")
                elif any(word in tag for word in ["增强", "祝福", "激励", "blessed", "inspired"]):
                    lines.append(f"[green]• {tag}[/green]")
                else:
                    lines.append(f"[yellow]• {tag}[/yellow]")

            tags_list.update("\n".join(lines))

        except Exception as e:
            self.log(f"Error rendering tags: {e}")

    def update_character(self, character_data: Dict[str, Any]) -> None:
        """
        Update character data.

        Args:
            character_data: Character data dictionary
        """
        self.character_data = character_data
        self._render_character_data()

    def update_game_state(self, game_state: Dict[str, Any]) -> None:
        """
        Update game state display.

        Args:
            game_state: Game state data
        """
        try:
            # Update location
            location = game_state.get("current_location", "Unknown")
            self.query_one("#char-location", Label).update(location)

            # Update phase
            phase = game_state.get("current_phase", "Unknown")
            self.query_one("#game-phase", Label).update(phase)

            # Update turn count
            turn_count = game_state.get("turn_count", 0)
            self.query_one("#turn-count", Label).update(str(turn_count))

        except Exception as e:
            self.log(f"Error updating game state: {e}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button presses.

        Args:
            event: Button press event
        """
        button_id = event.button.id

        if button_id == "btn-back":
            if self.app:
                self.app.action_switch_to_game()
