"""
Game screen - main game interface.

Displays:
- Character stats
- Chat/narrative log
- Dice roller (when needed)
"""

from typing import Dict, Any, Optional
import asyncio
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Label, Button, Static

from src.frontend.widgets.chat_box import ChatBox
from src.frontend.widgets.stat_block import StatBlock
from src.frontend.widgets.dice_roller import DiceRoller


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
        height: 0;
        width: 100%;
        dock: bottom;
        background: $panel;
    }

    #bottom-panel.visible {
        height: 20;
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
            message: Message data
        """
        message_type = message.get("type")

        if message_type == "status":
            # Status update
            content = message.get("content", "")
            self.add_system_message(content)

        elif message_type == "content":
            # Narrative content
            content = message.get("content", "")
            self.add_gm_message(content)

        elif message_type == "dice_check":
            # Dice check required
            check_data = message.get("data", {})
            self.show_dice_check(check_data)

        elif message_type == "phase":
            # Game phase change
            phase = message.get("phase")
            self.update_phase(phase)

        elif message_type == "error":
            # Error message
            error_msg = message.get("error", "Unknown error")
            self.add_system_message(f"Error: {error_msg}")

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
            event: Submit result event
        """
        result = event.result

        # Hide dice roller
        self.hide_dice_check()

        # Submit result to backend
        if self.app:
            asyncio.create_task(self.app.submit_dice_result(result))
