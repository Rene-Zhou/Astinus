"""
World Pack loading and management service.

Provides functionality to load, validate, and query world packs from JSON files.
"""

import json
from pathlib import Path

from jsonschema import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError as PydanticValidationError

from src.backend.core.schemas import validate_world_pack
from src.backend.models.world_pack import WorldPack


class WorldPackLoader:
    """
    Service for loading and managing world packs.

    Handles loading world packs from JSON files and provides
    caching for loaded packs.

    Examples:
        >>> loader = WorldPackLoader(Path("data/packs"))
        >>> pack = loader.load("demo_pack")
        >>> npc = pack.get_npc("chen_ling")
    """

    def __init__(self, packs_dir: Path | str):
        """
        Initialize the loader.

        Args:
            packs_dir: Directory containing world pack JSON files
        """
        self.packs_dir = Path(packs_dir)
        self._cache: dict[str, WorldPack] = {}

    def load(self, pack_id: str, use_cache: bool = True) -> WorldPack:
        """
        Load a world pack by ID.

        Args:
            pack_id: The pack identifier (filename without .json)
            use_cache: Whether to use cached version if available

        Returns:
            The loaded WorldPack

        Raises:
            FileNotFoundError: If pack file doesn't exist
            ValueError: If pack file is invalid JSON or schema
        """
        # Check cache first
        if use_cache and pack_id in self._cache:
            return self._cache[pack_id]

        # Find the pack file
        pack_path = self.packs_dir / f"{pack_id}.json"
        if not pack_path.exists():
            raise FileNotFoundError(
                f"World pack not found: {pack_path.absolute()}\n"
                f"Available packs: {', '.join(self.list_available()) or 'none'}"
            )

        # Load and parse JSON
        try:
            with open(pack_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in world pack '{pack_id}':\n"
                f"  File: {pack_path.absolute()}\n"
                f"  Error: {e.msg}\n"
                f"  Line: {e.lineno}, Column: {e.colno}"
            ) from e

        # Validate against JSON Schema
        try:
            validate_world_pack(data)
        except JsonSchemaValidationError as e:
            # Extract field path from schema error
            field_path = " -> ".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
            raise ValueError(
                f"Invalid world pack schema in '{pack_id}':\n"
                f"  File: {pack_path.absolute()}\n"
                f"  Field: {field_path}\n"
                f"  Error: {e.message}"
            ) from e

        # Validate with Pydantic (final type checking)
        try:
            pack = WorldPack.model_validate(data)
        except PydanticValidationError as e:
            # This should rarely happen if JSON Schema is comprehensive
            raise ValueError(
                f"Internal validation error for '{pack_id}':\n"
                f"  File: {pack_path.absolute()}\n"
                f"  Details: {e}"
            ) from e

        # Cache and return
        self._cache[pack_id] = pack
        return pack

    def list_available(self) -> list[str]:
        """
        List all available world pack IDs.

        Returns:
            List of pack IDs (filenames without .json)
        """
        if not self.packs_dir.exists():
            return []

        return [
            f.stem
            for f in self.packs_dir.glob("*.json")
            if f.is_file()
        ]

    def clear_cache(self) -> None:
        """Clear the pack cache."""
        self._cache.clear()

    def reload(self, pack_id: str) -> WorldPack:
        """
        Force reload a pack, bypassing cache.

        Args:
            pack_id: The pack identifier

        Returns:
            The freshly loaded WorldPack
        """
        return self.load(pack_id, use_cache=False)


# Default loader instance (created lazily)
_default_loader: WorldPackLoader | None = None


def get_world_loader(packs_dir: Path | str | None = None) -> WorldPackLoader:
    """
    Get the default world pack loader.

    Args:
        packs_dir: Optional custom packs directory

    Returns:
        WorldPackLoader instance
    """
    global _default_loader

    if packs_dir is not None:
        return WorldPackLoader(packs_dir)

    if _default_loader is None:
        # Default to data/packs relative to project root
        default_dir = Path(__file__).parent.parent.parent.parent / "data" / "packs"
        _default_loader = WorldPackLoader(default_dir)

    return _default_loader
