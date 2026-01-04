"""
Inventory screen.

Displays:
- Player's inventory items
- Item details
"""

from typing import List, Dict, Any, Optional
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Label, Button, Static


class InventoryScreen(Screen):
    """
    Inventory display screen.

    Shows player's items and equipment.
    """

    DEFAULT_CSS = """
    InventoryScreen {
        background: $background;
    }

    #inventory-layout {
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

    .inventory-empty {
        height: 5;
        text-align: center;
        text-style: italic;
        color: $text-muted;
    }

    .item {
        height: 3;
        width: 100%;
        border: solid $accent;
        padding: 0 1;
        margin: 0 0 1 0;
        background: $panel-darken;
    }

    .item-name {
        text-style: bold;
        color: $accent;
    }

    .item-quantity {
        text-align: right;
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        """Initialize the inventory screen."""
        super().__init__()
        self.inventory_items: List[Dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        """Compose the inventory screen layout."""
        with Container(id="inventory-layout"):
            # Navigation
            with Horizontal(classes="nav-bar"):
                yield Button("← Back to Game (G)", id="btn-back", classes="nav-button")

            # Title
            yield Label("Inventory", classes="section-title")

            # Items list
            with Vertical(classes="section"):
                yield Label("Items", classes="section-title")
                yield Static("Inventory is empty", id="inventory-list", classes="inventory-empty")

    def on_mount(self) -> None:
        """Called when screen mounts."""
        self.load_inventory()

    def load_inventory(self) -> None:
        """Load inventory data from backend."""
        if self.app and self.app.client:
            # This would be async in a real implementation
            # For now, use placeholder data
            self.inventory_items = []
            self._render_inventory()

    def _render_inventory(self) -> None:
        """Render inventory to the UI."""
        try:
            inventory_list = self.query_one("#inventory-list", Static)

            if not self.inventory_items:
                inventory_list.update("Inventory is empty")
                return

            # Render items
            items_text = ""
            for item in self.inventory_items:
                name = item.get("name", "Unknown Item")
                quantity = item.get("quantity", 1)

                items_text += f"[bold]{name}[/bold]"
                if quantity > 1:
                    items_text += f" x{quantity}"
                items_text += "\n"

            inventory_list.update(items_text)

        except Exception as e:
            self.log(f"Error rendering inventory: {e}")

    def update_inventory(self, inventory: List[Dict[str, Any]]) -> None:
        """
        Update inventory display.

        Args:
            inventory: List of inventory items
        """
        self.inventory_items = inventory
        self._render_inventory()

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
