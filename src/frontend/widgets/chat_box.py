"""
ChatBox widget for displaying game narrative and player input.

Features:
- Auto-scroll narrative log
- Player input field
- Message history
"""

from typing import List, Optional
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from textual.widgets import Input, Label, Static
from textual.message import Message


class ChatBox(Static):
    """
    A widget for chat/narrative display with input.

    Displays:
    - Narrative messages from GM
    - Player actions
    - System messages
    """

    DEFAULT_CSS = """
    ChatBox {
        height: 1fr;
        width: 100%;
        border: solid $accent;
        padding: 1;
    }

    #messages {
        height: 1fr;
        width: 100%;
        overflow-y: auto;
        background: $panel;
        padding: 1;
    }

    .message {
        width: 100%;
        margin-bottom: 1;
        padding: 0 1;
    }

    .message.player {
        color: $success;
        text-align: right;
    }

    .message.gm {
        color: $text;
    }

    .message.system {
        color: $warning;
        text-style: italic;
    }

    .message.dice {
        color: $accent;
        text-align: center;
    }

    #input-container {
        height: 3;
        width: 100%;
        dock: bottom;
        background: $primary;
        padding: 0 1;
    }

    #input {
        width: 100%;
        height: 100%;
    }
    """

    # Reactive messages list
    messages: List[dict] = reactive([])

    class MessageSent(Message):
        """Message sent event."""

        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()

    def __init__(self, placeholder: str = "Enter your action...", *args, **kwargs) -> None:
        """
        Initialize ChatBox.

        Args:
            placeholder: Placeholder text for input field
        """
        super().__init__(*args, **kwargs)
        self.placeholder = placeholder
        self.input_history: List[str] = []
        self.history_index = -1

    def compose(self) -> ComposeResult:
        """Compose the chat box layout."""
        with Vertical():
            # Messages area
            with Vertical(id="messages"):
                yield Static("Welcome to Astinus!", classes="message system")

            # Input area
            with Horizontal(id="input-container"):
                yield Input(placeholder=self.placeholder, id="input")

    def on_mount(self) -> None:
        """Called when widget mounts."""
        # Focus input field
        self.query_one("#input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Handle input submission.

        Args:
            event: Input submission event
        """
        text = event.value.strip()
        if not text:
            return

        # Add to history
        self.input_history.append(text)
        self.history_index = len(self.input_history)

        # Add player message
        self.add_message(text, "player")

        # Clear input
        event.input.value = ""

        # Send message
        self.post_message(self.MessageSent(text))

    def key_up(self) -> None:
        """Navigate input history up."""
        if self.input_history and self.history_index > 0:
            self.history_index -= 1
            input_widget = self.query_one("#input", Input)
            input_widget.value = self.input_history[self.history_index]

    def key_down(self) -> None:
        """Navigate input history down."""
        if self.input_history and self.history_index < len(self.input_history) - 1:
            self.history_index += 1
            input_widget = self.query_one("#input", Input)
            input_widget.value = self.input_history[self.history_index]
        else:
            self.history_index = len(self.input_history)
            input_widget = self.query_one("#input", Input)
            input_widget.value = ""

    def add_message(self, text: str, sender: str = "gm") -> None:
        """
        Add a message to the chat.

        Args:
            text: Message text
            sender: Message sender (player, gm, system, dice)
        """
        message = {
            "text": text,
            "sender": sender,
        }

        self.messages.append(message)

        # Update display
        self._render_messages()

        # Auto-scroll to bottom
        messages_container = self.query_one("#messages", Vertical)
        messages_container.scroll_end(animate=False)

    def add_gm_message(self, text: str) -> None:
        """
        Add a GM narrative message.

        Args:
            text: Message text
        """
        self.add_message(text, "gm")

    def add_player_message(self, text: str) -> None:
        """
        Add a player action message.

        Args:
            text: Message text
        """
        self.add_message(text, "player")

    def add_system_message(self, text: str) -> None:
        """
        Add a system message.

        Args:
            text: Message text
        """
        self.add_message(text, "system")

    def add_dice_message(self, text: str) -> None:
        """
        Add a dice roll message.

        Args:
            text: Message text
        """
        self.add_message(text, "dice")

    def _render_messages(self) -> None:
        """Render all messages to the display."""
        messages_container = self.query_one("#messages", Vertical)

        # Clear existing messages (except welcome)
        for child in list(messages_container.children):
            if child.has_class("message"):
                messages_container.remove_child(child)

        # Add all messages
        for msg in self.messages:
            text = msg["text"]
            sender = msg["sender"]

            message_widget = Static(text, classes=f"message {sender}")
            messages_container.mount(message_widget)

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()
        self._render_messages()
