"""
Textual TUI Application for Astinus.

Main application entry point that manages screens, state, and UI flow.
"""

from typing import Any, Dict, List, Optional

from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Footer, Header

from src.frontend.client import GameClient
from src.frontend.screens.character_creation import CharacterCreationScreen
from src.frontend.screens.character_screen import CharacterScreen
from src.frontend.screens.game_screen import GameScreen
from src.frontend.screens.inventory_screen import InventoryScreen
from src.frontend.screens.menu_screen import MenuScreen


class AstinusApp(App):
    """
    Main TUI Application for Astinus.

    Manages:
    - Screen navigation (Game, Character, Inventory)
    - Game state (current screen, player data)
    - WebSocket connection to backend
    - UI theming and layout
    """

    # Key bindings displayed in Footer
    BINDINGS = [
        ("g", "switch_to_game", "Game"),
        ("c", "switch_to_character", "Character"),
        ("i", "switch_to_inventory", "Inventory"),
        ("m", "switch_to_menu", "Menu"),
        ("q", "quit", "Quit"),
    ]

    # CSS styles
    CSS = """
    Screen {
        background: $background;
    }

    #main-container {
        height: 100%;
        width: 100%;
    }

    #header {
        height: 3;
        background: $primary;
        color: $text;
        dock: top;
    }

    #footer {
        height: 3;
        background: $primary;
        color: $text;
        dock: bottom;
    }

    #content {
        height: 1fr;
        width: 100%;
        padding: 1;
    }

    .screen-title {
        height: 3;
        text-align: center;
        text-style: bold;
        color: $accent;
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

    .nav-button.active {
        background: $primary;
        color: $text;
    }
    """

    # Reactive state
    current_screen: str = reactive("menu")
    player_name: str = reactive("")
    game_state: str = reactive("")

    def __init__(self):
        """Initialize the TUI application."""
        super().__init__()
        self.client: Optional[GameClient] = None
        self.game_session_id: Optional[str] = None
        self.player_character: Optional[Dict[str, Any]] = None

    async def on_mount(self) -> None:
        """Called when the app starts."""
        # Initialize WebSocket client
        self.client = GameClient()

        # Install screens
        self.install_screen(MenuScreen(), name="menu")
        self.install_screen(GameScreen(), name="game")
        self.install_screen(CharacterScreen(), name="character")
        self.install_screen(InventoryScreen(), name="inventory")

        # Push initial screen (first screen must be pushed, not switched)
        self.push_screen("menu")

    async def on_unmount(self) -> None:
        """Called when the app closes."""
        if self.client:
            await self.client.disconnect()

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        # Header and Footer - Screen content is managed by each Screen
        yield Header()
        yield Footer()

    def action_switch_to_game(self) -> None:
        """Switch to game screen."""
        self.current_screen = "game"
        self.switch_screen("game")

    def action_switch_to_character(self) -> None:
        """Switch to character screen."""
        self.current_screen = "character"
        self.switch_screen("character")

    def action_switch_to_inventory(self) -> None:
        """Switch to inventory screen."""
        self.current_screen = "inventory"
        self.switch_screen("inventory")

    def action_switch_to_menu(self) -> None:
        """Switch to menu screen."""
        self.current_screen = "menu"
        self.switch_screen("menu")

    async def start_new_game(self, world_pack_id: str = "demo_pack") -> bool:
        """
        Start a new game session.

        Args:
            world_pack_id: ID of the world pack to load

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False

        try:
            # Connect to backend
            await self.client.connect()

            # Start new game session
            success = await self.client.start_new_game(world_pack_id)

            if success:
                self.game_session_id = self.client.session_id
                # Update reactive state
                self.player_name = self.client.player_name or "Player"
                self.game_state = "Active"

            return success

        except Exception as e:
            self.log(f"Failed to start game: {e}")
            return False

    async def send_player_input(self, input_text: str) -> bool:
        """
        Send player input to the backend.

        Args:
            input_text: Player's action/description

        Returns:
            True if successful, False otherwise
        """
        if not self.client or not self.game_session_id:
            return False

        try:
            await self.client.send_player_input(input_text)
            return True
        except Exception as e:
            self.log(f"Failed to send input: {e}")
            return False

    async def submit_dice_result(
        self,
        result: int,
        all_rolls: Optional[List[int]] = None,
        kept_rolls: Optional[List[int]] = None,
        outcome: str = "unknown",
    ) -> bool:
        """
        Submit dice roll result to backend.

        Args:
            result: The dice roll total
            all_rolls: All dice rolled
            kept_rolls: Dice kept after advantage/disadvantage
            outcome: Roll outcome string

        Returns:
            True if successful, False otherwise
        """
        if not self.client or not self.game_session_id:
            return False

        try:
            await self.client.submit_dice_result(
                result=result,
                all_rolls=all_rolls,
                kept_rolls=kept_rolls,
                outcome=outcome,
            )
            return True
        except Exception as e:
            self.log(f"Failed to submit dice result: {e}")
            return False


def main() -> None:
    """Entry point for the TUI application."""
    app = AstinusApp()
    app.run()


if __name__ == "__main__":
    main()
