"""Tests for WorldPackLoader with enhanced error messages."""

import json
import tempfile
from pathlib import Path

import pytest

from src.backend.services.world import WorldPackLoader


class TestWorldPackLoaderErrorMessages:
    """Test enhanced error messages in WorldPackLoader."""

    def test_file_not_found_shows_absolute_path_and_available_packs(self):
        """Test FileNotFoundError shows full path and lists available packs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = WorldPackLoader(tmpdir)

            # Create a dummy pack so list_available() returns something
            Path(tmpdir).joinpath("existing_pack.json").write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "现有包", "en": "Existing Pack"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {},
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            with pytest.raises(FileNotFoundError) as exc_info:
                loader.load("nonexistent_pack")

            error_msg = str(exc_info.value)
            assert "nonexistent_pack.json" in error_msg
            assert "Available packs: existing_pack" in error_msg

    def test_file_not_found_when_no_packs_available(self):
        """Test FileNotFoundError shows 'none' when no packs exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = WorldPackLoader(tmpdir)

            with pytest.raises(FileNotFoundError) as exc_info:
                loader.load("any_pack")

            error_msg = str(exc_info.value)
            assert "any_pack.json" in error_msg
            assert "Available packs: none" in error_msg

    def test_json_syntax_error_shows_line_and_column(self):
        """Test JSON syntax error shows file, line, and column."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "bad_json.json"
            # Invalid JSON - missing closing brace
            pack_path.write_text('{"info": {"name":', encoding="utf-8")

            loader = WorldPackLoader(tmpdir)

            with pytest.raises(ValueError) as exc_info:
                loader.load("bad_json")

            error_msg = str(exc_info.value)
            assert "Invalid JSON in world pack 'bad_json'" in error_msg
            assert "File:" in error_msg
            assert "bad_json.json" in error_msg
            assert "Line:" in error_msg
            assert "Column:" in error_msg

    def test_schema_validation_error_shows_field_path(self):
        """Test schema validation error shows field path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "invalid_schema.json"
            # Missing required 'info' field
            pack_path.write_text(
                json.dumps({
                    "entries": {},
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            loader = WorldPackLoader(tmpdir)

            with pytest.raises(ValueError) as exc_info:
                loader.load("invalid_schema")

            error_msg = str(exc_info.value)
            assert "Invalid world pack schema in 'invalid_schema'" in error_msg
            assert "File:" in error_msg
            assert "Field: root" in error_msg
            assert "Error:" in error_msg

    def test_schema_validation_nested_field_error(self):
        """Test schema error for nested field shows full path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "nested_error.json"
            # Invalid uid type in lore entry
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "测试", "en": "Test"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {
                        "1": {
                            "uid": "not_an_integer",  # Should be integer
                            "key": ["test"],
                            "content": {"cn": "内容", "en": "Content"},
                        }
                    },
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            loader = WorldPackLoader(tmpdir)

            with pytest.raises(ValueError) as exc_info:
                loader.load("nested_error")

            error_msg = str(exc_info.value)
            assert "Invalid world pack schema in 'nested_error'" in error_msg
            assert "Field: entries -> 1 -> uid" in error_msg

    def test_schema_validation_missing_localized_string_field(self):
        """Test error message for missing required field in LocalizedString."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "missing_cn.json"
            # Missing 'cn' in LocalizedString
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"en": "Test Only"},  # Missing 'cn'
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {},
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            loader = WorldPackLoader(tmpdir)

            with pytest.raises(ValueError) as exc_info:
                loader.load("missing_cn")

            error_msg = str(exc_info.value)
            assert "Invalid world pack schema in 'missing_cn'" in error_msg
            assert "Field: info -> name" in error_msg
            assert "'cn' is a required property" in error_msg

    def test_valid_pack_loads_successfully(self):
        """Test that a valid pack loads without errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "valid_pack.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "有效包", "en": "Valid Pack"},
                        "description": {"cn": "这是一个有效的包", "en": "This is a valid pack"},
                        "version": "1.0.0",
                        "author": "Test Author",
                    },
                    "entries": {},
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            loader = WorldPackLoader(tmpdir)
            pack = loader.load("valid_pack")

            assert pack.info.name.cn == "有效包"
            assert pack.info.name.en == "Valid Pack"
            assert pack.info.version == "1.0.0"
            assert pack.info.author == "Test Author"

    def test_cache_works_after_successful_load(self):
        """Test that cache works and doesn't re-validate on second load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "cached_pack.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "缓存包", "en": "Cached Pack"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {},
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            loader = WorldPackLoader(tmpdir)

            # First load - should parse and validate
            pack1 = loader.load("cached_pack")

            # Delete the file to prove cache is working
            pack_path.unlink()

            # Second load - should use cache (won't fail even though file is gone)
            pack2 = loader.load("cached_pack", use_cache=True)

            assert pack1 is pack2

            # Third load with use_cache=False should fail (file doesn't exist)
            with pytest.raises(FileNotFoundError):
                loader.load("cached_pack", use_cache=False)
