"""
Character sheet screen.

Displays:
- Character name and concept
- Traits and abilities
- Current stats
"""

from typing import Dict, Any, Optional
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Label, Button, Static


class CharacterScreen(Screen):
    """
    Character sheet display screen.

    Shows detailed character information.
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
        width: 20%;
        text-style: bold;
        color: $accent;
    }

    .field-value {
        width: 80%;
    }

    .field-row {
        height: 2;
        width: 100%;
    }

    .trait-item {
        height: 2;
        width: 100%;
        border: solid $accent;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    .trait-name {
        text-style: bold;
        color: $accent;
    }

    .trait-desc {
        color: $text-muted;
        font-size: 0.9;
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
                yield Button("← Back to Game (G)", id="btn-back", classes="nav-button")

            # Character Name
            yield Label("Character Sheet", classes="section-title")

            with Vertical(classes="section"):
                with Horizontal(classes="field-row"):
                    yield Label("Name:", classes="field-label")
                    yield Label("Loading...", id="char-name", classes="field-value")

                with Horizontal(classes="field-row"):
                    yield Label("Concept:", classes="field-label")
                    yield Label("Loading...", id="char-concept", classes="field-value")

            # Traits Section
            with Vertical(classes="section"):
                yield Label("Traits & Abilities", classes="section-title")
                yield Static("No traits", id="traits-list")

            # Status Section
            with Vertical(classes="section"):
                yield Label("Status", classes="section-title")

                with Horizontal(classes="field-row"):
                    yield Label("Location:", classes="field-label")
                    yield Label("Unknown", id="char-location", classes="field-value")

                with Horizontal(classes="field-row"):
                    yield Label("Current Phase:", classes="field-label")
                    yield Label("Waiting", id="game-phase", classes="field-value")

                with Horizontal(classes="field-row"):
                    yield Label("Turn Count:", classes="field-label")
                    yield Label("0", id="turn-count", classes="field-value")

    def on_mount(self) -> None:
        """Called when screen mounts."""
        self.load_character_data()

    def load_character_data(self) -> None:
        """Load character data from backend."""
        if self.app and self.app.client:
            # This will be async in a real implementation
            # For now, use placeholder data
            self.character_data = {
                "name": self.app.client.player_name or "Player",
                "concept": {"en": "Adventurer", "cn": "冒险者"},
                "traits": [],
            }
            self._render_character_data()

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
            if isinstance(concept, dict):
                concept_text = concept.get("en", concept.get("cn", "Unknown"))
            else:
                concept_text = str(concept)
            self.query_one("#char-concept", Label).update(concept_text)

            # Update traits
            traits = self.character_data.get("traits", [])
            if traits:
                # Render traits list
                traits_text = "\n".join(
                    f"[bold]{trait.get('name', {}).get('en', 'Unknown')}[/bold]\n"
                    f"{trait.get('description', {}).get('en', '')}"
                    for trait in traits
                )
                self.query_one("#traits-list", Static).update(traits_text)
            else:
                self.query_one("#traits-list", Static).update("No traits")

        except Exception as e:
            self.log(f"Error rendering character data: {e}")

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
