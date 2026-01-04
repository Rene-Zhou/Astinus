"""
StatBlock widget for displaying character statistics.

Features:
- Character name and concept
- Attributes/skills
- Status (HP, MP, etc.)
"""

from typing import Dict, Any, Optional
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from textual.widgets import Static, Label
from textual.css.query import NoMatches


class StatBlock(Static):
    """
    A widget for displaying character statistics.

    Shows:
    - Character name and concept
    - Attributes
    - Status values
    - Current location
    """

    DEFAULT_CSS = """
    StatBlock {
        width: 100%;
        border: solid $accent;
        padding: 1;
        background: $panel;
    }

    .stat-label {
        width: 20%;
        text-style: bold;
        color: $accent;
    }

    .stat-value {
        width: 80%;
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
        border: solid $primary;
        margin-bottom: 1;
    }
    """

    # Reactive character data
    character_data: Optional[Dict[str, Any]] = reactive(None)

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the StatBlock."""
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """Compose the stat block layout."""
        with Vertical():
            # Character Info Section
            yield Label("Character", classes="section-title")

            with Horizontal(classes="stat-row"):
                yield Label("Name:", classes="stat-label")
                yield Label("Unknown", id="char-name", classes="stat-value")

            with Horizontal(classes="stat-row"):
                yield Label("Concept:", classes="stat-label")
                yield Label("Unknown", id="char-concept", classes="stat-value")

            # Status Section
            yield Label("Status", classes="section-title")

            with Horizontal(classes="stat-row"):
                yield Label("Location:", classes="stat-label")
                yield Label("Unknown", id="char-location", classes="stat-value")

            with Horizontal(classes="stat-row"):
                yield Label("Phase:", classes="stat-label")
                yield Label("Waiting", id="game-phase", classes="stat-value")

            with Horizontal(classes="stat-row"):
                yield Label("Turn:", classes="stat-label")
                yield Label("0", id="turn-count", classes="stat-value")

    def update_character(self, character_data: Dict[str, Any]) -> None:
        """
        Update character information.

        Args:
            character_data: Character data dictionary
        """
        self.character_data = character_data
        self._render_character_data()

    def update_game_state(self, game_state: Dict[str, Any]) -> None:
        """
        Update game state information.

        Args:
            game_state: Game state dictionary
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

        except NoMatches as e:
            # Widgets not ready yet
            pass

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
                concept_text = str(concept)
            self.query_one("#char-concept", Label).update(concept_text)

        except NoMatches as e:
            # Widgets not ready yet
            pass
