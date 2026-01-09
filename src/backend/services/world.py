"""
World Pack loading and management service.

Provides functionality to load, validate, and query world packs from JSON files.
"""

import json
from pathlib import Path

from jsonschema import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError as PydanticValidationError

from src.backend.core.schemas import validate_world_pack
from src.backend.models.i18n import LocalizedString
from src.backend.models.world_pack import RegionData, WorldPack
from src.backend.services.vector_store import VectorStoreService


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

    def __init__(
        self,
        packs_dir: Path | str,
        vector_store: VectorStoreService | None = None,
        enable_vector_indexing: bool = True,
    ):
        """
        Initialize the loader.

        Args:
            packs_dir: Directory containing world pack JSON files
            vector_store: Optional VectorStoreService for indexing lore entries
            enable_vector_indexing: Whether to index lore entries (default: True)
        """
        self.packs_dir = Path(packs_dir)
        self._cache: dict[str, WorldPack] = {}
        self.vector_store = vector_store
        self.enable_vector_indexing = enable_vector_indexing

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

        # NEW: Migrate old packs to hierarchical schema
        self._migrate_pack_to_hierarchical(pack)

        # Index lore entries if vector indexing is enabled
        if self.enable_vector_indexing and self.vector_store is not None:
            self._index_lore_entries(pack_id, pack)

        # Cache and return
        self._cache[pack_id] = pack
        return pack

    def _index_lore_entries(self, pack_id: str, pack: WorldPack) -> None:
        """
        Index lore entries for vector search.

        Creates separate documents for Chinese and English versions of each entry.

        Args:
            pack_id: World pack identifier
            pack: Loaded WorldPack
        """
        if not pack.entries:
            return

        collection_name = f"lore_entries_{pack_id}"

        # Prepare documents and metadata
        documents = []
        metadatas = []
        ids = []

        for entry in pack.entries.values():
            # Chinese document
            documents.append(entry.content.cn)
            metadatas.append({
                "uid": entry.uid,
                "keys": ",".join(entry.key),  # Store as comma-separated string
                "order": entry.order,
                "lang": "cn",
                "constant": entry.constant,
                # NEW: Location filtering metadata
                "visibility": entry.visibility,
                "applicable_regions": ",".join(entry.applicable_regions),
                "applicable_locations": ",".join(entry.applicable_locations),
            })
            ids.append(f"{pack_id}_lore_{entry.uid}_cn")

            # English document
            documents.append(entry.content.en)
            metadatas.append({
                "uid": entry.uid,
                "keys": ",".join(entry.key),
                "order": entry.order,
                "lang": "en",
                "constant": entry.constant,
                # NEW: Location filtering metadata
                "visibility": entry.visibility,
                "applicable_regions": ",".join(entry.applicable_regions),
                "applicable_locations": ",".join(entry.applicable_locations),
            })
            ids.append(f"{pack_id}_lore_{entry.uid}_en")

        # Add to vector store
        self.vector_store.add_documents(
            collection_name=collection_name,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

    def _migrate_pack_to_hierarchical(self, pack: WorldPack) -> None:
        """
        Migrate old world packs to hierarchical schema.

        Ensures backward compatibility by:
        - Creating default global region if no regions exist
        - Migrating 'items' to 'visible_items' in locations
        - Setting default visibility='basic' for all lore entries

        Args:
            pack: WorldPack to migrate (modified in-place)
        """
        # Create global region if needed
        if not pack.regions:
            pack.regions["_global"] = RegionData(
                id="_global",
                name=LocalizedString(cn="全局区域", en="Global Region"),
                description=pack.info.description,
                narrative_tone=pack.info.setting.tone if pack.info.setting else None,
                location_ids=list(pack.locations.keys()),
            )

        # Migrate locations
        for location in pack.locations.values():
            if not location.region_id:
                location.region_id = "_global"

            if not location.visible_items and location.items:
                location.visible_items = location.items.copy()

        # Ensure lore entries have visibility set
        for entry in pack.entries.values():
            if not hasattr(entry, "visibility"):
                entry.visibility = "basic"

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
