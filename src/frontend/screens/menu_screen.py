"""
Menu screen - main menu interface.

Displays:
- Game title/logo
- New Game button
- Load Game button
- Settings button
- Quit button

Handles:
- Navigation to character creation
- Load game selection
- Settings configuration
- Application exit
"""

from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Center, Container, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Label, ListItem, ListView, Static


class MenuScreen(Screen):
    """
    Main menu screen.

    Layout:
    - Top: Game title
    - Middle: Menu buttons (New Game, Load Game, Settings, Quit)
    - Bottom: Version info
    """

    TITLE = "Astinus"

    BINDINGS = [
        ("n", "new_game", "New Game"),
        ("l", "load_game", "Load Game"),
        ("s", "settings", "Settings"),
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]

    DEFAULT_CSS = """
    MenuScreen {
        background: $background;
        align: center middle;
    }

    #menu-container {
        width: 60;
        height: auto;
        padding: 2;
        background: $panel;
        border: solid $accent;
    }

    #game-title {
        width: 100%;
        height: 5;
        text-align: center;
        text-style: bold;
        color: $accent;
        padding: 1;
    }

    #subtitle {
        width: 100%;
        height: 2;
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
    }

    .menu-button {
        width: 100%;
        height: 3;
        margin: 1 2;
        background: $primary;
        color: $text;
        border: solid $accent;
        text-align: center;
    }

    .menu-button:hover {
        background: $accent;
        color: $text;
    }

    .menu-button:focus {
        background: $accent;
        border: solid $secondary;
    }

    #version-info {
        width: 100%;
        height: 2;
        text-align: center;
        color: $text-muted;
        margin-top: 2;
    }

    #load-game-list {
        width: 100%;
        height: 15;
        margin: 1 0;
        background: $surface;
        border: solid $primary;
        display: none;
    }

    #load-game-list.visible {
        display: block;
    }

    #no-saves-message {
        width: 100%;
        text-align: center;
        color: $text-muted;
        padding: 2;
    }

    .save-item {
        height: 3;
        padding: 0 1;
    }

    .save-item:hover {
        background: $accent;
    }
    """

    # Reactive state
    menu_mode: str = reactive("main")
    selected_world_pack: Optional[str] = reactive(None)
    saves_list: List[Dict[str, Any]] = reactive([])

    def __init__(self) -> None:
        """Initialize the menu screen."""
        super().__init__()
        self._saves_loaded = False

    def compose(self) -> ComposeResult:
        """Compose the menu screen layout."""
        with Center():
            with Container(id="menu-container"):
                yield Label("⚔️ ASTINUS ⚔️", id="game-title")
                yield Label("AI-Driven Narrative TTRPG", id="subtitle")

                with Vertical(id="menu-buttons"):
                    yield Button("🎮 New Game (N)", id="btn-new-game", classes="menu-button")
                    yield Button("📂 Load Game (L)", id="btn-load-game", classes="menu-button")
                    yield Button("⚙️ Settings (S)", id="btn-settings", classes="menu-button")
                    yield Button("🚪 Quit (Q)", id="btn-quit", classes="menu-button")

                # Load game list (hidden by default)
                with Vertical(id="load-game-list"):
                    yield Label("Select a save:", id="load-list-title")
                    yield ListView(id="saves-listview")
                    yield Label("No saves found", id="no-saves-message")
                    yield Button("← Back", id="btn-back-to-menu", classes="menu-button")

                yield Label("v0.1.0 - Development", id="version-info")

    def on_mount(self) -> None:
        """Called when screen mounts."""
        # Focus the first button
        self.query_one("#btn-new-game", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button presses.

        Args:
            event: Button press event
        """
        button_id = event.button.id

        if button_id == "btn-new-game":
            self.action_new_game()
        elif button_id == "btn-load-game":
            self.action_load_game()
        elif button_id == "btn-settings":
            self.action_settings()
        elif button_id == "btn-quit":
            self.action_quit()
        elif button_id == "btn-back-to-menu":
            self._show_main_menu()

    def action_new_game(self) -> None:
        """Start a new game - navigate to character creation."""
        self.menu_mode = "new_game"
        # Push character creation screen
        if self.app:
            from src.frontend.screens.character_creation import CharacterCreationScreen

            self.app.push_screen(CharacterCreationScreen())

    def action_load_game(self) -> None:
        """Show load game interface."""
        self.menu_mode = "load"
        self._show_load_menu()
        # Fetch saves asynchronously
        if self.app:
            self.app.call_later(self._fetch_saves)

    def action_settings(self) -> None:
        """Show settings interface."""
        self.menu_mode = "settings"
        # TODO: Implement settings screen
        self.notify("Settings not yet implemented", title="Coming Soon")

    def action_quit(self) -> None:
        """Quit the application."""
        if self.app:
            self.app.exit()

    def on_new_game(self) -> None:
        """Handle new game event (alternative handler)."""
        self.action_new_game()

    def on_load_game(self) -> None:
        """Handle load game event (alternative handler)."""
        self.action_load_game()

    def on_settings(self) -> None:
        """Handle settings event (alternative handler)."""
        self.action_settings()

    def on_quit(self) -> None:
        """Handle quit event (alternative handler)."""
        self.action_quit()

    def _show_main_menu(self) -> None:
        """Show the main menu buttons."""
        self.menu_mode = "main"
        # Hide load game list
        load_list = self.query_one("#load-game-list", Vertical)
        load_list.remove_class("visible")
        # Show menu buttons
        menu_buttons = self.query_one("#menu-buttons", Vertical)
        menu_buttons.styles.display = "block"
        # Focus first button
        self.query_one("#btn-new-game", Button).focus()

    def _show_load_menu(self) -> None:
        """Show the load game menu."""
        # Hide main menu buttons
        menu_buttons = self.query_one("#menu-buttons", Vertical)
        menu_buttons.styles.display = "none"
        # Show load game list
        load_list = self.query_one("#load-game-list", Vertical)
        load_list.add_class("visible")

    async def _fetch_saves(self) -> None:
        """Fetch saved games from backend."""
        saves = await self.fetch_saves()
        self.update_save_list(saves)

    async def fetch_saves(self) -> List[Dict[str, Any]]:
        """
        Fetch available saves from backend.

        Returns:
            List of save data dictionaries
        """
        # TODO: Integrate with backend API
        # For now, return empty list
        try:
            # Check if we have an app context
            try:
                app = self.app
                if app and hasattr(app, "client") and app.client:
                    # Future: call app.client.get_saves()
                    pass
            except Exception:
                # No active app context (e.g., in tests)
                pass
        except Exception:
            # Silently handle errors - no logging without app context
            pass

        return []

    def update_save_list(self, saves: List[Dict[str, Any]]) -> None:
        """
        Update the save list display.

        Args:
            saves: List of save data dictionaries
        """
        self.saves_list = saves
        self._saves_loaded = True

        # Get the list view
        listview = self.query_one("#saves-listview", ListView)
        no_saves_msg = self.query_one("#no-saves-message", Label)

        # Clear existing items
        listview.clear()

        if not saves:
            # Show no saves message
            no_saves_msg.styles.display = "block"
            listview.styles.display = "none"
        else:
            # Hide no saves message
            no_saves_msg.styles.display = "none"
            listview.styles.display = "block"

            # Add save items
            for save in saves:
                save_name = save.get("slot_name", "Unknown")
                save_desc = save.get("description", "")
                save_date = save.get("updated_at", "")

                label = f"{save_name}"
                if save_desc:
                    label += f" - {save_desc}"
                if save_date:
                    label += f" ({save_date})"

                listview.append(ListItem(Label(label), id=f"save-{save_name}"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """
        Handle save selection from list.

        Args:
            event: Selection event
        """
        item = event.item
        if item and item.id and item.id.startswith("save-"):
            slot_name = item.id[5:]  # Remove "save-" prefix
            self._load_selected_save(slot_name)

    def _load_selected_save(self, slot_name: str) -> None:
        """
        Load the selected save.

        Args:
            slot_name: Name of the save slot to load
        """
        self.notify(f"Loading save: {slot_name}", title="Loading")
        # TODO: Implement actual save loading
        # if self.app:
        #     self.app.call_later(lambda: self.app.load_game(slot_name))

    def watch_menu_mode(self, old_mode: str, new_mode: str) -> None:
        """
        Watch for menu mode changes.

        Args:
            old_mode: Previous mode
            new_mode: New mode
        """
        try:
            self.log(f"Menu mode changed: {old_mode} -> {new_mode}")
        except Exception:
            # No active app context (e.g., in tests)
            pass
