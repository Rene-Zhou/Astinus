"""
Dice Roller widget for handling dice checks.

Features:
- 2d6 dice system with advantage/disadvantage (3d6kh2/3d6kl2)
- Visual dice display
- Roll result input
- Check information display from backend DiceCheckRequest
"""

import random
from typing import Any, Dict, List, Optional, Tuple

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Label, Static


class DiceRoller(Static):
    """
    A widget for dice rolling and checks.

    Displays:
    - Current check information (intention, modifiers)
    - Virtual dice with 2d6 system
    - Roll button
    - Result with outcome determination
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
        height: auto;
        min-height: 3;
        text-align: center;
        text-style: bold;
        color: $warning;
        border: solid $warning;
        margin-bottom: 1;
        padding: 1;
    }

    .check-details {
        height: auto;
        min-height: 2;
        text-align: center;
        color: $text;
        margin-bottom: 1;
    }

    .dice-container {
        height: auto;
        align: center middle;
        margin: 1 0;
    }

    .dice-display {
        width: auto;
        height: 5;
        text-align: center;
        text-style: bold;
        color: $accent;
        border: solid $accent;
        padding: 1 2;
        margin: 0 1;
    }

    .roll-button {
        width: 100%;
        height: 3;
        text-align: center;
        text-style: bold;
        background: $success;
        color: $text;
        margin: 1 0;
    }

    .result-display {
        height: 3;
        text-align: center;
        text-style: bold;
        color: $accent;
        border: solid $accent;
        margin-top: 1;
    }

    .outcome-display {
        height: 3;
        text-align: center;
        text-style: bold;
        margin-top: 1;
    }

    .outcome-display.critical {
        color: $success;
        background: $success 20%;
    }

    .outcome-display.success {
        color: $success;
    }

    .outcome-display.partial {
        color: $warning;
    }

    .outcome-display.failure {
        color: $error;
    }

    .submit-button {
        width: 100%;
        height: 3;
        margin-top: 1;
        background: $primary;
        color: $text;
    }

    .submit-button:disabled {
        background: $panel;
        color: $text-muted;
    }
    """

    # Reactive properties
    visible: bool = reactive(False)
    check_data: Optional[Dict[str, Any]] = reactive(None)
    roll_result: Optional[int] = reactive(None)
    all_rolls: List[int] = reactive(list)
    kept_rolls: List[int] = reactive(list)
    outcome: str = reactive("")

    class RollDice(Message):
        """Message when dice should be rolled."""

        pass

    class SubmitResult(Message):
        """Message when result should be submitted."""

        def __init__(
            self,
            result: int,
            all_rolls: List[int],
            kept_rolls: List[int],
            outcome: str,
        ) -> None:
            self.result = result
            self.all_rolls = all_rolls
            self.kept_rolls = kept_rolls
            self.outcome = outcome
            super().__init__()

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the dice roller."""
        super().__init__(*args, **kwargs)
        self._dice_formula = "2d6"
        self._num_dice = 2

    def compose(self) -> ComposeResult:
        """Compose the dice roller layout."""
        with Vertical():
            # Check information - intention
            yield Label("Dice Check", id="check-title", classes="check-info")

            # Details - modifiers and instructions
            yield Label("Roll required", id="check-details", classes="check-details")

            # Dice display container
            with Horizontal(classes="dice-container"):
                yield Label("🎲", id="dice-1", classes="dice-display")
                yield Label("🎲", id="dice-2", classes="dice-display")
                yield Label("🎲", id="dice-3", classes="dice-display")

            # Roll button
            yield Button("Roll Dice", id="roll-button", classes="roll-button")

            # Result display
            yield Label("Total: -", id="result-display", classes="result-display")

            # Outcome display
            yield Label("", id="outcome-display", classes="outcome-display")

            # Submit button
            yield Button(
                "Submit Result",
                id="submit-button",
                classes="submit-button",
                disabled=True,
            )

    def on_mount(self) -> None:
        """Called when widget mounts."""
        # Initially hidden
        self.check_visible(False)
        # Hide third dice by default (for 2d6)
        self._update_dice_visibility(2)

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

    def _update_dice_visibility(self, num_dice: int) -> None:
        """
        Update which dice are visible based on roll type.

        Args:
            num_dice: Number of dice to show (2 or 3)
        """
        try:
            dice_3 = self.query_one("#dice-3", Label)
            if num_dice >= 3:
                dice_3.display = True
            else:
                dice_3.display = False
        except Exception:
            pass

    def _parse_dice_formula(self, formula: str) -> Tuple[int, bool, bool]:
        """
        Parse dice formula to determine roll type.

        Args:
            formula: Dice notation (e.g., "2d6", "3d6kh2", "3d6kl2")

        Returns:
            Tuple of (num_dice, has_advantage, has_disadvantage)
        """
        formula = formula.lower()

        # Check for advantage/disadvantage
        has_advantage = "kh2" in formula
        has_disadvantage = "kl2" in formula

        # Extract number of dice
        if "d6" in formula:
            num_str = formula.split("d6")[0]
            try:
                num_dice = int(num_str)
            except ValueError:
                num_dice = 2
        else:
            num_dice = 2

        return num_dice, has_advantage, has_disadvantage

    def show_check(self, check_data: Dict[str, Any]) -> None:
        """
        Show a dice check from DiceCheckRequest.

        Args:
            check_data: DiceCheckRequest data containing:
                - intention: What player is trying to do
                - influencing_factors: {"traits": [...], "tags": [...]}
                - dice_formula: Dice notation
                - instructions: LocalizedString with explanation
        """
        self.check_data = check_data
        self.roll_result = None
        self.all_rolls = []
        self.kept_rolls = []
        self.outcome = ""

        # Parse dice formula
        formula = check_data.get("dice_formula", "2d6")
        self._num_dice, has_advantage, has_disadvantage = self._parse_dice_formula(formula)
        self._dice_formula = formula

        # Update UI
        try:
            # Title - intention
            intention = check_data.get("intention", "Dice Check")
            self.query_one("#check-title", Label).update(intention)

            # Build details string
            details_parts = []

            # Add influencing factors
            factors = check_data.get("influencing_factors", {})
            traits = factors.get("traits", [])
            tags = factors.get("tags", [])

            if traits:
                details_parts.append(f"特性: {', '.join(traits)}")
            if tags:
                details_parts.append(f"状态: {', '.join(tags)}")

            # Add instructions
            instructions = check_data.get("instructions", {})
            if isinstance(instructions, dict):
                instruction_text = instructions.get("cn") or instructions.get("en", "")
            else:
                instruction_text = str(instructions)

            if instruction_text:
                details_parts.append(instruction_text)

            # Add dice formula info
            if has_advantage:
                details_parts.append(f"🎲 {formula} (优势)")
            elif has_disadvantage:
                details_parts.append(f"🎲 {formula} (劣势)")
            else:
                details_parts.append(f"🎲 {formula}")

            details = "\n".join(details_parts) if details_parts else "Roll required"
            self.query_one("#check-details", Label).update(details)

            # Reset displays
            self.query_one("#result-display", Label).update("Total: -")
            self.query_one("#outcome-display", Label).update("")
            self.query_one("#outcome-display", Label).remove_class(
                "critical", "success", "partial", "failure"
            )

            # Reset dice displays
            for i in range(1, 4):
                try:
                    self.query_one(f"#dice-{i}", Label).update("🎲")
                except Exception:
                    pass

            # Update dice visibility
            self._update_dice_visibility(self._num_dice)

            # Enable roll button, disable submit
            self.query_one("#roll-button", Button).disabled = False
            self.query_one("#submit-button", Button).disabled = True

            self.check_visible(True)

        except Exception as e:
            self.log(f"Error showing check: {e}")

    def hide_check(self) -> None:
        """Hide the dice roller."""
        self.check_visible(False)
        self.check_data = None
        self.roll_result = None
        self.all_rolls = []
        self.kept_rolls = []
        self.outcome = ""

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
                self.post_message(
                    self.SubmitResult(
                        result=self.roll_result,
                        all_rolls=list(self.all_rolls),
                        kept_rolls=list(self.kept_rolls),
                        outcome=self.outcome,
                    )
                )

    def _roll_dice(self) -> None:
        """Roll dice according to current formula."""
        # Roll all dice
        rolls = [random.randint(1, 6) for _ in range(self._num_dice)]
        self.all_rolls = rolls

        # Determine kept dice
        _, has_advantage, has_disadvantage = self._parse_dice_formula(self._dice_formula)

        if has_advantage and len(rolls) >= 3:
            # Keep highest 2
            sorted_rolls = sorted(rolls, reverse=True)
            self.kept_rolls = sorted_rolls[:2]
        elif has_disadvantage and len(rolls) >= 3:
            # Keep lowest 2
            sorted_rolls = sorted(rolls)
            self.kept_rolls = sorted_rolls[:2]
        else:
            self.kept_rolls = rolls

        # Calculate total
        total = sum(self.kept_rolls)
        self.roll_result = total

        # Determine outcome based on 2d6 system
        # Critical: 12, Success: 10+, Partial: 7-9, Failure: 6-
        if total >= 12:
            self.outcome = "critical"
            outcome_text = "大成功！"
        elif total >= 10:
            self.outcome = "success"
            outcome_text = "成功"
        elif total >= 7:
            self.outcome = "partial"
            outcome_text = "部分成功"
        else:
            self.outcome = "failure"
            outcome_text = "失败"

        # Update dice displays
        for i, roll in enumerate(rolls):
            try:
                dice_label = self.query_one(f"#dice-{i + 1}", Label)
                # Use different style for kept vs discarded dice
                if roll in self.kept_rolls and self.kept_rolls.count(roll) > 0:
                    dice_label.update(f"[bold]{roll}[/bold]")
                    # Remove one from kept_rolls copy to handle duplicates
                    self.kept_rolls = list(self.kept_rolls)
                else:
                    dice_label.update(f"[dim]{roll}[/dim]")
            except Exception:
                pass

        # Restore kept_rolls
        if has_advantage and len(rolls) >= 3:
            sorted_rolls = sorted(rolls, reverse=True)
            self.kept_rolls = sorted_rolls[:2]
        elif has_disadvantage and len(rolls) >= 3:
            sorted_rolls = sorted(rolls)
            self.kept_rolls = sorted_rolls[:2]
        else:
            self.kept_rolls = rolls

        # Update result display
        if len(self.all_rolls) != len(self.kept_rolls):
            result_text = f"Total: {total} (kept: {self.kept_rolls})"
        else:
            result_text = f"Total: {total}"
        self.query_one("#result-display", Label).update(result_text)

        # Update outcome display with styling
        outcome_label = self.query_one("#outcome-display", Label)
        outcome_label.update(outcome_text)
        outcome_label.remove_class("critical", "success", "partial", "failure")
        outcome_label.add_class(self.outcome)

        # Enable submit button, disable roll button
        self.query_one("#roll-button", Button).disabled = True
        self.query_one("#submit-button", Button).disabled = False

    def set_result(self, result: int, outcome: str = "unknown") -> None:
        """
        Set the roll result manually.

        Args:
            result: The dice result total
            outcome: The outcome string
        """
        self.roll_result = result
        self.outcome = outcome
        self.query_one("#result-display", Label).update(f"Total: {result}")

        # Enable submit button
        self.query_one("#submit-button", Button).disabled = False
