"""
Frontend screens for Astinus TUI.

Different views and screens for the game interface.
"""

from .game_screen import GameScreen
from .character_screen import CharacterScreen
from .inventory_screen import InventoryScreen

__all__ = [
    "GameScreen",
    "CharacterScreen",
    "InventoryScreen",
]
