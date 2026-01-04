"""
Game screen - main game interface.

Displays:
- Character stats
- Chat/narrative log
- Dice roller (when needed)

Handles:
- Player input → WebSocket → GM Agent
- Dice check requests from backend
- Dice result submission
"""

import asyncio
from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from src.frontend.widgets.chat_box import ChatBox
from src.frontend.widgets.dice_roller import DiceRoller
from src.frontend.widgets.stat_block import StatBlock


class GameScreen(Screen):
    """
    Main game screen.

    Layout:
    - Top: Character stat block
    - Middle: Chat/narrative area
    - Bottom: Dice roller (when active)
    """

    DEFAULT_CSS = """
    GameScreen {
        background: $background;
    }

    #game-layout {
        height: 100%;
        width: 100%;
        padding: 1;
    }

    #top-panel {
        height: 10;
        width: 100%;
        margin-bottom: 1;
    }

    #main-panel {
        height: 1fr;
        width: 100%;
    }

    #bottom-panel {
        height: 20;
        width: 100%;
        dock: bottom;
        background: $panel;
        display: none;
    }

    #bottom-panel.visible {
        display: block;
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
    """

    def __init__(self) -> None:
        """Initialize the game screen."""
        super().__init__()

    def compose(self) -> ComposeResult:
        """Compose the game screen layout."""
        with Container(id="game-layout"):
            # Top panel with character stats and navigation
            with Vertical(id="top-panel"):
                with Horizontal(classes="nav-bar"):
                    yield Button("Character (C)", id="btn-character", classes="nav-button")
                    yield Button("Inventory (I)", id="btn-inventory", classes="nav-button")

                yield StatBlock(id="stat-block")

            # Main panel with chat
            with Vertical(id="main-panel"):
                yield ChatBox(id="chat-box", placeholder="Describe your action...")

            # Bottom panel for dice roller (hidden by default)
            with Container(id="bottom-panel"):
                yield DiceRoller(id="dice-roller")

    def on_mount(self) -> None:
        """Called when screen mounts."""
        # Register message handlers
        if self.app and self.app.client:
            self.app.client.add_message_handler(self.handle_message)

    def on_unmount(self) -> None:
        """Called when screen unmounts."""
        # Unregister message handlers
        if self.app and self.app.client:
            self.app.client.remove_message_handler(self.handle_message)

    def handle_message(self, message: Dict[str, Any]) -> None:
        """
        Handle incoming WebSocket messages.

        Args:
            message: Message data with format:
                {"type": "...", "data": {...}}
        """
        message_type = message.get("type")
        data = message.get("data", {})

        if message_type == "status":
            # Status update (processing, narrating, etc.)
            status_message = data.get("message", "")
            if status_message:
                self.add_system_message(f"[dim]{status_message}[/dim]")

        elif message_type == "content":
            # Streaming content chunk
            chunk = data.get("chunk", "")
            if chunk:
                # For streaming, append to existing message
                self._append_streaming_content(chunk)

        elif message_type == "complete":
            # Complete response from server
            content = data.get("content", "")
            success = data.get("success", True)
            if content:
                if success:
                    self.add_gm_message(content)
                else:
                    self.add_system_message(f"[red]{content}[/red]")

        elif message_type == "dice_check":
            # Dice check request from Rule Agent
            check_request = data.get("check_request", {})
            self.show_dice_check(check_request)

        elif message_type == "phase":
            # Game phase change
            phase = data.get("phase", "")
            self.update_phase(phase)

        elif message_type == "error":
            # Error message
            error_msg = data.get("error", "Unknown error")
            self.add_system_message(f"[red]Error: {error_msg}[/red]")

    def add_gm_message(self, text: str) -> None:
        """
        Add a GM message to the chat.

        Args:
            text: Message text
        """
        chat_box = self.query_one("#chat-box", ChatBox)
        chat_box.add_gm_message(text)

    def add_system_message(self, text: str) -> None:
        """
        Add a system message to the chat.

        Args:
            text: Message text
        """
        chat_box = self.query_one("#chat-box", ChatBox)
        chat_box.add_system_message(text)

    def _append_streaming_content(self, chunk: str) -> None:
        """
        Append streaming content chunk.

        For typewriter effect, appends to the current streaming message.

        Args:
            chunk: Content chunk to append
        """
        # For now, just add as message - could enhance for true streaming
        chat_box = self.query_one("#chat-box", ChatBox)
        # Use a streaming-specific method if available, otherwise log
        try:
            if hasattr(chat_box, "append_streaming"):
                chat_box.append_streaming(chunk)
            else:
                # Fallback: accumulate in temp and show on complete
                pass
        except Exception as e:
            self.log(f"Streaming error: {e}")

    def add_player_message(self, text: str) -> None:
        """
        Add a player message to the chat.

        Args:
            text: Message text
        """
        chat_box = self.query_one("#chat-box", ChatBox)
        chat_box.add_player_message(text)

    def show_dice_check(self, check_data: Dict[str, Any]) -> None:
        """
        Show a dice check interface.

        Args:
            check_data: Check information
        """
        dice_roller = self.query_one("#dice-roller", DiceRoller)
        dice_roller.show_check(check_data)

        # Show bottom panel
        bottom_panel = self.query_one("#bottom-panel", Container)
        bottom_panel.add_class("visible")

    def hide_dice_check(self) -> None:
        """Hide the dice check interface."""
        dice_roller = self.query_one("#dice-roller", DiceRoller)
        dice_roller.hide_check()

        # Hide bottom panel
        bottom_panel = self.query_one("#bottom-panel", Container)
        bottom_panel.remove_class("visible")

    def update_character(self, character_data: Dict[str, Any]) -> None:
        """
        Update character information.

        Args:
            character_data: Character data
        """
        stat_block = self.query_one("#stat-block", StatBlock)
        stat_block.update_character(character_data)

    def update_game_state(self, game_state: Dict[str, Any]) -> None:
        """
        Update game state.

        Args:
            game_state: Game state data
        """
        stat_block = self.query_one("#stat-block", StatBlock)
        stat_block.update_game_state(game_state)

    def update_phase(self, phase: str) -> None:
        """
        Update game phase display.

        Args:
            phase: Current game phase
        """
        # This will be handled by the stat block
        pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button presses.

        Args:
            event: Button press event
        """
        button_id = event.button.id

        if button_id == "btn-character":
            self.app.action_switch_to_character()
        elif button_id == "btn-inventory":
            self.app.action_switch_to_inventory()

    def on_chat_box_message_sent(self, event: ChatBox.MessageSent) -> None:
        """
        Handle chat message submission.

        Args:
            event: Message sent event
        """
        text = event.text

        # Add to chat
        self.add_player_message(text)

        # Send to backend
        if self.app:
            asyncio.create_task(self.app.send_player_input(text))

    def on_dice_roller_submit_result(self, event: DiceRoller.SubmitResult) -> None:
        """
        Handle dice result submission.

        Args:
            event: Submit result event containing:
                - result: Total roll value
                - all_rolls: All dice rolled
                - kept_rolls: Dice kept after advantage/disadvantage
                - outcome: Roll outcome string
        """
        result = event.result
        all_rolls = event.all_rolls
        kept_rolls = event.kept_rolls
        outcome = event.outcome

        # Add message showing the roll
        roll_msg = f"🎲 Rolled: {all_rolls}"
        if all_rolls != kept_rolls:
            roll_msg += f" → kept {kept_rolls}"
        roll_msg += f" = {result} ({outcome})"
        self.add_player_message(roll_msg)

        # Hide dice roller
        self.hide_dice_check()

        # Submit result to backend
        if self.app:
            asyncio.create_task(
                self.app.submit_dice_result(
                    result=result,
                    all_rolls=all_rolls,
                    kept_rolls=kept_rolls,
                    outcome=outcome,
                )
            )
