"""
Character creation screen - create a new character.

Displays:
- Character name input
- Attribute allocation (PbtA style: -2 to +3)
- Character concept selection
- Validation and confirmation

Handles:
- Name input validation
- Point-based attribute allocation
- Concept selection
- Character data export
"""

from typing import Any, Dict, List, Optional, Tuple

from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Select, Static

# Default attributes for PbtA-style system
DEFAULT_ATTRIBUTES = {
    "strength": 0,
    "dexterity": 0,
    "intelligence": 0,
    "charisma": 0,
    "perception": 0,
}

# Available character concepts
AVAILABLE_CONCEPTS = [
    ("warrior", "Warrior - A skilled fighter"),
    ("scholar", "Scholar - A seeker of knowledge"),
    ("rogue", "Rogue - A cunning opportunist"),
    ("mystic", "Mystic - A wielder of arcane arts"),
    ("diplomat", "Diplomat - A master of words"),
]

# Point allocation settings
INITIAL_POINTS = 7
MIN_ATTRIBUTE = -2
MAX_ATTRIBUTE = 3
MAX_NAME_LENGTH = 50


class CharacterCreationScreen(Screen):
    """
    Character creation screen.

    Layout:
    - Top: Title and instructions
    - Middle: Name input, attribute allocation, concept selection
    - Bottom: Validation errors and confirm/back buttons
    """

    TITLE = "Create Character"

    BINDINGS = [
        ("escape", "back", "Back"),
        ("enter", "confirm", "Confirm"),
    ]

    DEFAULT_CSS = """
    CharacterCreationScreen {
        background: $background;
        align: center middle;
    }

    #creation-container {
        width: 80;
        height: auto;
        max-height: 90%;
        padding: 2;
        background: $panel;
        border: solid $accent;
    }

    #creation-title {
        width: 100%;
        height: 3;
        text-align: center;
        text-style: bold;
        color: $accent;
        padding: 1;
    }

    .section-title {
        width: 100%;
        height: 2;
        text-style: bold;
        color: $primary;
        margin-top: 1;
        border-bottom: solid $primary;
    }

    #name-input {
        width: 100%;
        margin: 1 0;
    }

    .attribute-row {
        width: 100%;
        height: 3;
        margin: 0 0 1 0;
    }

    .attribute-label {
        width: 30%;
        text-style: bold;
        padding: 0 1;
    }

    .attribute-value {
        width: 20%;
        text-align: center;
        color: $accent;
    }

    .attribute-button {
        width: 5;
        height: 3;
        min-width: 5;
        margin: 0 1;
    }

    .attribute-button:hover {
        background: $accent;
    }

    #points-remaining {
        width: 100%;
        height: 2;
        text-align: center;
        color: $warning;
        margin: 1 0;
    }

    #concept-select {
        width: 100%;
        margin: 1 0;
    }

    #validation-errors {
        width: 100%;
        min-height: 3;
        color: $error;
        padding: 1;
        margin: 1 0;
    }

    .action-button {
        width: 20;
        height: 3;
        margin: 1;
    }

    #action-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 2;
    }

    #btn-confirm {
        background: $success;
    }

    #btn-confirm:hover {
        background: $success-darken-1;
    }

    #btn-back {
        background: $error;
    }

    #btn-back:hover {
        background: $error-darken-1;
    }
    """

    # Reactive state
    character_name: str = reactive("")
    attributes: Dict[str, int] = reactive(dict)
    remaining_points: int = reactive(INITIAL_POINTS)
    character_concept: Optional[str] = reactive(None)
    validation_errors: List[str] = reactive(list)

    class CharacterCreated(Message):
        """Message sent when character is created successfully."""

        def __init__(self, character_data: Dict[str, Any]) -> None:
            self.character_data = character_data
            super().__init__()

    def __init__(self) -> None:
        """Initialize the character creation screen."""
        super().__init__()
        # Initialize attributes dict
        self._attributes = DEFAULT_ATTRIBUTES.copy()
        self._remaining_points = INITIAL_POINTS

    @property
    def attributes(self) -> Dict[str, int]:
        """Get current attributes."""
        return self._attributes

    @property
    def remaining_points(self) -> int:
        """Get remaining points."""
        return self._remaining_points

    @property
    def available_concepts(self) -> List[Tuple[str, str]]:
        """Get available character concepts."""
        return AVAILABLE_CONCEPTS

    def compose(self) -> ComposeResult:
        """Compose the character creation screen layout."""
        with Center():
            with Container(id="creation-container"):
                yield Label("⚔️ Create Your Character ⚔️", id="creation-title")

                # Name section
                yield Label("Character Name", classes="section-title")
                yield Input(
                    placeholder="Enter your character's name...",
                    id="name-input",
                    max_length=MAX_NAME_LENGTH,
                )

                # Attributes section
                yield Label(
                    f"Attributes (Points: {self._remaining_points})",
                    classes="section-title",
                    id="points-label",
                )

                for attr_name in DEFAULT_ATTRIBUTES.keys():
                    with Horizontal(classes="attribute-row"):
                        yield Label(attr_name.capitalize(), classes="attribute-label")
                        yield Button("-", id=f"btn-{attr_name}-dec", classes="attribute-button")
                        yield Label(
                            self._format_attribute_value(self._attributes[attr_name]),
                            id=f"attr-{attr_name}-value",
                            classes="attribute-value",
                        )
                        yield Button("+", id=f"btn-{attr_name}-inc", classes="attribute-button")

                yield Label(
                    f"Points Remaining: {self._remaining_points}",
                    id="points-remaining",
                )

                # Concept section
                yield Label("Character Concept", classes="section-title")
                yield Select(
                    [(desc, key) for key, desc in AVAILABLE_CONCEPTS],
                    prompt="Select a concept...",
                    id="concept-select",
                )

                # Validation errors
                yield Static("", id="validation-errors")

                # Action buttons
                with Horizontal(id="action-buttons"):
                    yield Button("← Back", id="btn-back", classes="action-button")
                    yield Button("Confirm ✓", id="btn-confirm", classes="action-button")

    def on_mount(self) -> None:
        """Called when screen mounts."""
        # Focus the name input
        self.query_one("#name-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input.id == "name-input":
            self.character_name = event.value
            self._update_validation()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        if event.select.id == "concept-select":
            self.character_concept = event.value
            self._update_validation()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-back":
            self.action_back()
        elif button_id == "btn-confirm":
            self.action_confirm()
        elif button_id and button_id.startswith("btn-"):
            # Attribute buttons
            parts = button_id.split("-")
            if len(parts) >= 3:
                attr_name = parts[1]
                action = parts[2]  # "inc" or "dec"

                if action == "inc":
                    self.increase_attribute(attr_name)
                elif action == "dec":
                    self.decrease_attribute(attr_name)

    def action_back(self) -> None:
        """Go back to menu."""
        if self.app:
            self.app.pop_screen()

    def go_back(self) -> None:
        """Alternative method to go back."""
        self.action_back()

    def action_confirm(self) -> None:
        """Confirm character creation."""
        if self.is_valid():
            character_data = self.get_character_data()
            self.post_message(self.CharacterCreated(character_data))
            # Transition to game
            if self.app:
                # Set character data and start game
                self.app.call_later(lambda: self._start_game_with_character(character_data))
        else:
            self._update_validation()
            self.notify("Please fix validation errors", title="Invalid Character", severity="error")

    def confirm_character(self) -> None:
        """Alternative method to confirm character."""
        self.action_confirm()

    async def _start_game_with_character(self, character_data: Dict[str, Any]) -> None:
        """
        Start the game with the created character.

        Args:
            character_data: Character data dictionary
        """
        if self.app:
            # Store character data
            if hasattr(self.app, "player_character"):
                self.app.player_character = character_data

            # Start new game
            success = await self.app.start_new_game()
            if success:
                # Switch to game screen
                self.app.switch_screen("game")
            else:
                self.notify("Failed to start game", title="Error", severity="error")

    def increase_attribute(self, attr_name: str) -> None:
        """
        Increase an attribute value.

        Args:
            attr_name: Name of the attribute to increase
        """
        if attr_name not in self._attributes:
            return

        current = self._attributes[attr_name]

        # Check if we can increase
        if current >= MAX_ATTRIBUTE:
            return  # Already at max
        if self._remaining_points <= 0:
            return  # No points left

        # Increase attribute
        self._attributes[attr_name] = current + 1
        self._remaining_points -= 1

        self._update_attribute_display(attr_name)
        self._update_points_display()
        self._update_validation()

    def decrease_attribute(self, attr_name: str) -> None:
        """
        Decrease an attribute value.

        Args:
            attr_name: Name of the attribute to decrease
        """
        if attr_name not in self._attributes:
            return

        current = self._attributes[attr_name]

        # Check if we can decrease
        if current <= MIN_ATTRIBUTE:
            return  # Already at min

        # Decrease attribute
        self._attributes[attr_name] = current - 1
        self._remaining_points += 1

        self._update_attribute_display(attr_name)
        self._update_points_display()
        self._update_validation()

    def set_attribute(self, attr_name: str, value: int) -> None:
        """
        Set an attribute to a specific value.

        Args:
            attr_name: Name of the attribute
            value: Value to set

        Raises:
            ValueError: If value is out of range
        """
        if value < MIN_ATTRIBUTE or value > MAX_ATTRIBUTE:
            raise ValueError(f"Attribute value must be between {MIN_ATTRIBUTE} and {MAX_ATTRIBUTE}")

        if attr_name not in self._attributes:
            raise ValueError(f"Unknown attribute: {attr_name}")

        old_value = self._attributes[attr_name]
        point_diff = old_value - value  # Positive if decreasing, negative if increasing

        # Check if we have enough points
        if point_diff < 0 and self._remaining_points < abs(point_diff):
            raise ValueError("Not enough points")

        self._attributes[attr_name] = value
        self._remaining_points += point_diff

        self._update_attribute_display(attr_name)
        self._update_points_display()

    def set_name(self, name: str) -> None:
        """
        Set character name.

        Args:
            name: Character name
        """
        self.character_name = name[:MAX_NAME_LENGTH]
        try:
            name_input = self.query_one("#name-input", Input)
            name_input.value = self.character_name
        except Exception:
            pass

    def set_concept(self, concept) -> None:
        """
        Set character concept.

        Args:
            concept: Concept key (string) or tuple (key, description)
        """
        # Handle tuple input (key, description)
        if isinstance(concept, tuple):
            concept_key = concept[0]
        else:
            concept_key = concept

        valid_concepts = [c[0] for c in AVAILABLE_CONCEPTS]
        if concept_key in valid_concepts:
            self.character_concept = concept_key
            try:
                concept_select = self.query_one("#concept-select", Select)
                concept_select.value = concept_key
            except Exception:
                pass

    def validate_name(self, name: str) -> bool:
        """
        Validate character name.

        Args:
            name: Name to validate

        Returns:
            True if valid, False otherwise
        """
        if not name or not name.strip():
            return False
        if len(name) > MAX_NAME_LENGTH:
            return False
        return True

    def is_valid(self) -> bool:
        """
        Check if character is valid for creation.

        Returns:
            True if valid, False otherwise
        """
        errors = self.get_validation_errors()
        return len(errors) == 0

    def get_validation_errors(self) -> List[str]:
        """
        Get list of validation errors.

        Returns:
            List of error messages
        """
        errors = []

        # Check name
        if not self.character_name or not self.character_name.strip():
            errors.append("Character name is required")
        elif len(self.character_name) > MAX_NAME_LENGTH:
            errors.append(f"Name must be {MAX_NAME_LENGTH} characters or less")

        # Check concept
        if not self.character_concept:
            errors.append("Please select a character concept")

        # Check points (optional: require all points spent)
        # if self._remaining_points > 0:
        #     errors.append(f"You have {self._remaining_points} unspent points")

        return errors

    def get_character_data(self) -> Dict[str, Any]:
        """
        Get character data dictionary.

        Returns:
            Dictionary with character data
        """
        return {
            "name": self.character_name.strip(),
            "concept": self.character_concept,
            "attributes": self._attributes.copy(),
            "remaining_points": self._remaining_points,
        }

    def _format_attribute_value(self, value: int) -> str:
        """
        Format attribute value for display.

        Args:
            value: Attribute value

        Returns:
            Formatted string (e.g., "+2", "-1", "0")
        """
        if value > 0:
            return f"+{value}"
        return str(value)

    def _update_attribute_display(self, attr_name: str) -> None:
        """Update the display for a single attribute."""
        try:
            value_label = self.query_one(f"#attr-{attr_name}-value", Label)
            value_label.update(self._format_attribute_value(self._attributes[attr_name]))
        except Exception:
            pass

    def _update_points_display(self) -> None:
        """Update the points remaining display."""
        try:
            points_label = self.query_one("#points-remaining", Label)
            points_label.update(f"Points Remaining: {self._remaining_points}")

            section_label = self.query_one("#points-label", Label)
            section_label.update(f"Attributes (Points: {self._remaining_points})")
        except Exception:
            pass

    def _update_validation(self) -> None:
        """Update validation error display."""
        errors = self.get_validation_errors()
        self.validation_errors = errors

        try:
            error_widget = self.query_one("#validation-errors", Static)
            if errors:
                error_text = "\n".join(f"• {e}" for e in errors)
                error_widget.update(error_text)
            else:
                error_widget.update("")
        except Exception:
            pass
