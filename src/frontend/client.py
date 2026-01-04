"""
HTTP/WebSocket client for communicating with the Astinus backend.

Handles:
- REST API calls for game state
- WebSocket streaming for real-time updates
- Connection management
"""

import asyncio
import json
import logging
from typing import Any, Callable, Optional, Dict, List
from urllib.parse import urljoin

import httpx
import websockets
from websockets.exceptions import ConnectionClosed


class GameClient:
    """
    Client for communicating with Astinus backend.

    Manages HTTP and WebSocket connections to the backend API.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        ws_url: str = "ws://localhost:8000",
    ):
        """
        Initialize the game client.

        Args:
            base_url: Base URL for REST API
            ws_url: Base URL for WebSocket
        """
        self.base_url = base_url
        self.ws_url = ws_url
        self.session_id: Optional[str] = None
        self.player_name: Optional[str] = None
        self.player_data: Optional[Dict[str, Any]] = None
        self.game_state: Optional[Dict[str, Any]] = None

        self._http_client: Optional[httpx.AsyncClient] = None
        self._ws_connection: Optional[websockets.WebSocketServerProtocol] = None
        self._message_handlers: List[Callable[[Dict[str, Any]], None]] = []

    async def connect(self) -> None:
        """Establish HTTP connection to backend."""
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=30.0)
            logging.info(f"Connected to {self.base_url}")

    async def disconnect(self) -> None:
        """Close all connections."""
        if self._ws_connection:
            await self._ws_connection.close()

        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

        logging.info("Disconnected from backend")

    async def start_new_game(self, world_pack_id: str = "demo_pack") -> bool:
        """
        Start a new game session.

        Args:
            world_pack_id: ID of the world pack to load

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.connect()

            # Create new game session via REST API
            response = await self._http_client.post(
                "/api/v1/game/new",
                json={"world_pack_id": world_pack_id},
            )

            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get("session_id")
                self.player_name = data.get("player", {}).get("name", "Player")
                self.player_data = data.get("player")
                self.game_state = data.get("game_state", {})

                logging.info(f"Started new game: {self.session_id}")

                # Connect to WebSocket for real-time updates
                await self._connect_websocket()

                return True
            else:
                logging.error(f"Failed to start game: {response.status_code}")
                return False

        except Exception as e:
            logging.error(f"Error starting game: {e}")
            return False

    async def _connect_websocket(self) -> None:
        """Establish WebSocket connection for real-time updates."""
        if not self.session_id:
            return

        ws_url = f"{self.ws_url}/ws/game/{self.session_id}"

        try:
            self._ws_connection = await websockets.connect(ws_url)

            # Start listening for messages
            asyncio.create_task(self._listen_websocket())

            logging.info(f"WebSocket connected: {ws_url}")

        except Exception as e:
            logging.error(f"WebSocket connection failed: {e}")

    async def _listen_websocket(self) -> None:
        """Listen for messages from the WebSocket."""
        try:
            async for message in self._ws_connection:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logging.error(f"Invalid JSON received: {message}")
                except Exception as e:
                    logging.error(f"Error handling message: {e}")

        except ConnectionClosed:
            logging.info("WebSocket connection closed")
        except Exception as e:
            logging.error(f"WebSocket error: {e}")

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """
        Handle incoming WebSocket messages.

        Args:
            message: Parsed message data
        """
        message_type = message.get("type")

        if message_type == "status":
            # Status update (e.g., "processing", "narrating")
            self.log_message(f"[dim]{message.get('content', '')}[/dim]")

        elif message_type == "content":
            # Narrative content
            content = message.get("content", "")
            self.log_message(content)

        elif message_type == "dice_check":
            # Dice check required
            check_data = message.get("data", {})
            self._handle_dice_check(check_data)

        elif message_type == "phase":
            # Game phase change
            phase = message.get("phase")
            self.log_message(f"[dim]Phase: {phase}[/dim]")

        elif message_type == "error":
            # Error message
            error_msg = message.get("error", "Unknown error")
            self.log_message(f"[red]Error: {error_msg}[/red]")

        # Notify registered handlers
        for handler in self._message_handlers:
            try:
                handler(message)
            except Exception as e:
                logging.error(f"Handler error: {e}")

    def _handle_dice_check(self, check_data: Dict[str, Any]) -> None:
        """
        Handle dice check request.

        Args:
            check_data: Dice check information
        """
        # This will be handled by the UI components
        for handler in self._message_handlers:
            try:
                handler({"type": "dice_check", "data": check_data})
            except Exception as e:
                logging.error(f"Dice check handler error: {e}")

    def log_message(self, message: str) -> None:
        """
        Log a message (to be overridden by UI).

        Args:
            message: Message to log
        """
        print(message)  # Default implementation

    async def send_player_input(self, input_text: str) -> bool:
        """
        Send player input to backend.

        Args:
            input_text: Player's action/description

        Returns:
            True if successful, False otherwise
        """
        if not self._ws_connection or not self.session_id:
            return False

        try:
            message = {
                "type": "player_input",
                "content": input_text,
            }

            await self._ws_connection.send(json.dumps(message))
            return True

        except Exception as e:
            logging.error(f"Failed to send input: {e}")
            return False

    async def submit_dice_result(self, result: int) -> bool:
        """
        Submit dice roll result to backend.

        Args:
            result: The dice roll result

        Returns:
            True if successful, False otherwise
        """
        if not self._ws_connection or not self.session_id:
            return False

        try:
            message = {
                "type": "dice_result",
                "result": result,
            }

            await self._ws_connection.send(json.dumps(message))
            return True

        except Exception as e:
            logging.error(f"Failed to submit dice result: {e}")
            return False

    async def get_game_state(self) -> Optional[Dict[str, Any]]:
        """
        Get current game state via REST API.

        Returns:
            Game state data or None if failed
        """
        if not self._http_client or not self.session_id:
            return None

        try:
            response = await self._http_client.get(
                f"/api/v1/game/{self.session_id}/state"
            )

            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Failed to get game state: {response.status_code}")
                return None

        except Exception as e:
            logging.error(f"Error getting game state: {e}")
            return None

    async def get_character_sheet(self) -> Optional[Dict[str, Any]]:
        """
        Get character sheet data.

        Returns:
            Character data or None if failed
        """
        if not self.player_data:
            return None

        return self.player_data

    async def get_inventory(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get player inventory.

        Returns:
            Inventory items or None if failed
        """
        if not self.player_data:
            return None

        return self.player_data.get("inventory", [])

    def add_message_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Add a message handler callback.

        Args:
            handler: Function to call when messages are received
        """
        self._message_handlers.append(handler)

    def remove_message_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Remove a message handler callback.

        Args:
            handler: Handler to remove
        """
        if handler in self._message_handlers:
            self._message_handlers.remove(handler)


def create_client() -> GameClient:
    """
    Factory function to create a GameClient instance.

    Returns:
        Configured GameClient
    """
    return GameClient()
