"""
Dice Roller widget for handling dice checks.

Features:
- Visual dice display
- Roll result input
- Check information display
"""

import random
from typing import Dict, Any, Optional, Callable
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Center
from textual.reactive import reactive
from textual.widgets import Static, Label, Button
from textual.message import Message


class DiceRoller(Static):
    """
    A widget for dice rolling and checks.

    Displays:
    - Current check information
    - Virtual dice
    - Roll button
    """

    DEFAULT_CSS = """
    DiceRoller {
        width: 100%;
        height: 100%;
        border: solid $warning;
        padding: 1;
        background: $panel;
        visibility: hidden;
    }

    DiceRoller.visible {
        visibility: visible;
    }

    .check-info {
        height: 3;
        text-align: center;
        text-style: bold;
        color: $warning;
        border: solid $warning;
        margin-bottom: 1;
    }

    .dice-display {
        height: 8;
        text-align: center;
        text-style: bold;
        font-size: 4;
        color: $accent;
        border: solid $accent;
        margin: 1 0;
    }

    .roll-button {
        height: 4;
        text-align: center;
        text-style: bold;
        background: $success;
        color: $text;
    }

    .result-display {
        height: 3;
        text-align: center;
        text-style: bold;
        color: $info;
        border: solid $info;
        margin-top: 1;
    }

    .submit-button {
        height: 3;
        margin: 0 10;
        background: $primary;
        color: $text;
    }
    """

    # Reactive properties
    visible: bool = reactive(False)
    check_data: Optional[Dict[str, Any]] = reactive(None)
    roll_result: Optional[int] = reactive(None)

    class RollDice(Message):
        """Message when dice should be rolled."""

        pass

    class SubmitResult(Message):
        """Message when result should be submitted."""

        def __init__(self, result: int) -> None:
            self.result = result
            super().__init__()

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the dice roller."""
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        """Compose the dice roller layout."""
        with Vertical():
            # Check information
            yield Label("Dice Check", id="check-title", classes="check-info")
            yield Label("Roll required", id="check-details", classes="check-info")

            # Dice display
            yield Label("🎲", id="dice-display", classes="dice-display")

            # Roll button
            yield Button("Roll Dice", id="roll-button", classes="roll-button")

            # Result display
            yield Label("Result: -", id="result-display", classes="result-display")

            # Submit button
            yield Button("Submit Result", id="submit-button", classes="submit-button")

    def on_mount(self) -> None:
        """Called when widget mounts."""
        # Initially hidden
        self.check_visible(False)

    def watch_visible(self, visible: bool) -> None:
        """React to visibility changes."""
        if visible:
            self.add_class("visible")
        else:
            self.remove_class("visible")

    def check_visible(self, visible: bool) -> None:
        """
        Show or hide the dice roller.

        Args:
            visible: Whether to show the widget
        """
        self.visible = visible

    def show_check(self, check_data: Dict[str, Any]) -> None:
        """
        Show a dice check.

        Args:
            check_data: Check information
        """
        self.check_data = check_data
        self.roll_result = None

        # Update UI
        try:
            title = check_data.get("title", "Dice Check")
            self.query_one("#check-title", Label).update(title)

            details = check_data.get("details", "Roll required")
            self.query_one("#check-details", Label).update(details)

            self.query_one("#result-display", Label).update("Result: -")
            self.query_one("#dice-display", Label).update("🎲")

            self.check_visible(True)

        except Exception as e:
            self.log(f"Error showing check: {e}")

    def hide_check(self) -> None:
        """Hide the dice roller."""
        self.check_visible(False)
        self.check_data = None
        self.roll_result = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button presses.

        Args:
            event: Button press event
        """
        button_id = event.button.id

        if button_id == "roll-button":
            self._roll_dice()
        elif button_id == "submit-button":
            if self.roll_result is not None:
                self.post_message(self.SubmitResult(self.roll_result))

    def _roll_dice(self) -> None:
        """Roll a d20 dice."""
        # Generate random roll
        result = random.randint(1, 20)

        # Update UI
        self.roll_result = result
        self.query_one("#dice-display", Label).update(str(result))
        self.query_one("#result-display", Label).update(f"Result: {result}")

        # Animate (optional - could add fancy animation here)

    def set_result(self, result: int) -> None:
        """
        Set the roll result (for manual entry).

        Args:
            result: The dice result
        """
        self.roll_result = result
        self.query_one("#dice-display", Label).update(str(result))
        self.query_one("#result-display", Label).update(f"Result: {result}")
