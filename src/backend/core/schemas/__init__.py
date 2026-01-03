"""
JSON Schema definitions for Astinus data models.

Provides JSON Schema validation for world packs and other data structures.
"""

import json
from pathlib import Path
from typing import Any

import jsonschema


def load_schema(schema_name: str) -> dict[str, Any]:
    """
    Load a JSON Schema by name.

    Args:
        schema_name: Name of the schema file (without .json extension)

    Returns:
        Parsed JSON Schema dictionary

    Raises:
        FileNotFoundError: If schema file doesn't exist
        ValueError: If schema file is invalid JSON
    """
    schema_path = Path(__file__).parent / f"{schema_name}.json"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")

    try:
        with open(schema_path, encoding="utf-8") as f:
            result: dict[str, Any] = json.load(f)
            return result
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in schema {schema_name}: {e}") from e


def validate_world_pack(data: dict[str, Any]) -> None:
    """
    Validate world pack data against JSON Schema.

    Args:
        data: World pack data dictionary

    Raises:
        jsonschema.ValidationError: If data doesn't match schema
    """
    schema = load_schema("world_pack")
    jsonschema.validate(instance=data, schema=schema)


__all__ = ["load_schema", "validate_world_pack"]
