"""Tests for WorldPackLoader with enhanced error messages."""

import json
import tempfile
from pathlib import Path

import pytest

from src.backend.services.vector_store import VectorStoreService
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


class TestWorldPackLoaderVectorIndexing:
    """Test Lore entry vector indexing functionality."""

    @pytest.fixture(autouse=True)
    def reset_vector_store(self):
        """Reset vector store singleton before each test."""
        VectorStoreService.reset_instance()
        yield
        VectorStoreService.reset_instance()

    def test_indexing_disabled_by_default_without_vector_store(self):
        """Test that indexing is skipped when vector_store is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "test.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "测试", "en": "Test"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {
                        "1": {
                            "uid": 1,
                            "key": ["test"],
                            "content": {"cn": "内容", "en": "Content"},
                        }
                    },
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            # Load without vector store - should not raise
            loader = WorldPackLoader(tmpdir, vector_store=None)
            pack = loader.load("test")

            assert pack is not None

    def test_indexing_with_vector_store(self):
        """Test that lore entries are indexed when vector_store is provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "test_pack.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "测试包", "en": "Test Pack"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {
                        "1": {
                            "uid": 1,
                            "key": ["庄园", "manor"],
                            "content": {"cn": "幽暗庄园的背景", "en": "Dark Manor background"},
                            "order": 10,
                            "constant": True,
                        },
                        "2": {
                            "uid": 2,
                            "key": ["密室"],
                            "content": {"cn": "密室的描述", "en": "Secret room description"},
                            "order": 50,
                            "constant": False,
                        }
                    },
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            # Create vector store
            with tempfile.TemporaryDirectory() as db_dir:
                vector_store = VectorStoreService(db_dir)
                loader = WorldPackLoader(tmpdir, vector_store=vector_store)

                # Load pack - should index lore entries
                loader.load("test_pack")

                # Verify documents were added (2 entries × 2 languages = 4 documents)
                collection_name = "lore_entries_test_pack"
                count = vector_store.get_collection_count(collection_name)
                assert count == 4

    def test_indexed_metadata_structure(self):
        """Test that indexed documents have correct metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "meta_test.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "元数据测试", "en": "Metadata Test"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {
                        "1": {
                            "uid": 1,
                            "key": ["key1", "key2"],
                            "content": {"cn": "中文内容", "en": "English content"},
                            "order": 25,
                            "constant": True,
                        }
                    },
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            with tempfile.TemporaryDirectory() as db_dir:
                vector_store = VectorStoreService(db_dir)
                loader = WorldPackLoader(tmpdir, vector_store=vector_store)

                loader.load("meta_test")

                # Search to get metadata
                results = vector_store.search(
                    collection_name="lore_entries_meta_test",
                    query_text="content",
                    n_results=2,
                )

                # Check metadata
                for metadata in results["metadatas"][0]:
                    assert metadata["uid"] == 1
                    assert metadata["keys"] == "key1,key2"
                    assert metadata["order"] == 25
                    assert metadata["constant"] is True
                    assert metadata["lang"] in ["cn", "en"]

    def test_bilingual_indexing(self):
        """Test that both Chinese and English versions are indexed separately."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "bilingual.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "双语测试", "en": "Bilingual Test"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {
                        "1": {
                            "uid": 1,
                            "key": ["测试"],
                            "content": {
                                "cn": "这是中文内容",
                                "en": "This is English content"
                            },
                        }
                    },
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            with tempfile.TemporaryDirectory() as db_dir:
                vector_store = VectorStoreService(db_dir)
                loader = WorldPackLoader(tmpdir, vector_store=vector_store)

                loader.load("bilingual")

                # Search in Chinese
                cn_results = vector_store.search(
                    collection_name="lore_entries_bilingual",
                    query_text="中文",
                    where={"lang": "cn"},
                    n_results=1,
                )

                assert len(cn_results["documents"][0]) == 1
                assert "中文" in cn_results["documents"][0][0]

                # Search in English
                en_results = vector_store.search(
                    collection_name="lore_entries_bilingual",
                    query_text="English",
                    where={"lang": "en"},
                    n_results=1,
                )

                assert len(en_results["documents"][0]) == 1
                assert "English" in en_results["documents"][0][0]

    def test_empty_entries_no_indexing(self):
        """Test that packs with no entries don't create empty collections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "empty.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "空包", "en": "Empty Pack"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {},
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            with tempfile.TemporaryDirectory() as db_dir:
                vector_store = VectorStoreService(db_dir)
                loader = WorldPackLoader(tmpdir, vector_store=vector_store)

                loader.load("empty")

                # Should not create collection for empty entries
                collections = vector_store.list_collections()
                assert "lore_entries_empty" not in collections

    def test_indexing_can_be_disabled(self):
        """Test that indexing can be disabled via enable_vector_indexing flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "no_index.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "无索引", "en": "No Index"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {
                        "1": {
                            "uid": 1,
                            "key": ["test"],
                            "content": {"cn": "内容", "en": "Content"},
                        }
                    },
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            with tempfile.TemporaryDirectory() as db_dir:
                vector_store = VectorStoreService(db_dir)
                loader = WorldPackLoader(
                    tmpdir,
                    vector_store=vector_store,
                    enable_vector_indexing=False,  # Disable indexing
                )

                loader.load("no_index")

                # Collection should not be created
                collections = vector_store.list_collections()
                assert "lore_entries_no_index" not in collections

    def test_multiple_entries_indexed(self):
        """Test indexing multiple lore entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "multi.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "多条目", "en": "Multiple Entries"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {
                        "1": {
                            "uid": 1,
                            "key": ["entry1"],
                            "content": {"cn": "第一条", "en": "Entry one"},
                        },
                        "2": {
                            "uid": 2,
                            "key": ["entry2"],
                            "content": {"cn": "第二条", "en": "Entry two"},
                        },
                        "3": {
                            "uid": 3,
                            "key": ["entry3"],
                            "content": {"cn": "第三条", "en": "Entry three"},
                        }
                    },
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            with tempfile.TemporaryDirectory() as db_dir:
                vector_store = VectorStoreService(db_dir)
                loader = WorldPackLoader(tmpdir, vector_store=vector_store)

                loader.load("multi")

                # Should have 3 entries × 2 languages = 6 documents
                count = vector_store.get_collection_count("lore_entries_multi")
                assert count == 6

    def test_cache_does_not_reindex(self):
        """Test that cached loads don't re-index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "cache_test.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "缓存测试", "en": "Cache Test"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {
                        "1": {
                            "uid": 1,
                            "key": ["test"],
                            "content": {"cn": "内容", "en": "Content"},
                        }
                    },
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            with tempfile.TemporaryDirectory() as db_dir:
                vector_store = VectorStoreService(db_dir)
                loader = WorldPackLoader(tmpdir, vector_store=vector_store)

                # First load - should index
                loader.load("cache_test")
                first_count = vector_store.get_collection_count("lore_entries_cache_test")

                # Second load (cached) - should not re-index
                loader.load("cache_test", use_cache=True)
                second_count = vector_store.get_collection_count("lore_entries_cache_test")

                # Count should be the same (not doubled)
                assert first_count == second_count == 2


class TestWorldPackMigration:
    """Test suite for hierarchical schema migration."""

    def test_migration_creates_global_region_for_old_pack(self):
        """Test that old packs without regions get a default global region."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "old_pack.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "旧包", "en": "Old Pack"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {
                        "1": {
                            "uid": 1,
                            "key": ["test"],
                            "content": {"cn": "内容", "en": "Content"},
                        }
                    },
                    "npcs": {},
                    "locations": {
                        "old_location": {
                            "id": "old_location",
                            "name": {"cn": "旧地点", "en": "Old Location"},
                            "description": {"cn": "描述", "en": "Desc"},
                        }
                    },
                }),
                encoding="utf-8",
            )

            loader = WorldPackLoader(tmpdir)
            pack = loader.load("old_pack")

            assert len(pack.regions) == 1
            assert "_global" in pack.regions
            assert pack.regions["_global"].name.get("cn") == "全局区域"

    def test_migration_sets_location_region_id(self):
        """Test that migrated locations get region_id set to _global."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "old_pack.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "旧包", "en": "Old Pack"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {},
                    "npcs": {},
                    "locations": {
                        "old_location": {
                            "id": "old_location",
                            "name": {"cn": "旧地点", "en": "Old Location"},
                            "description": {"cn": "描述", "en": "Desc"},
                        }
                    },
                }),
                encoding="utf-8",
            )

            loader = WorldPackLoader(tmpdir)
            pack = loader.load("old_pack")

            location = pack.get_location("old_location")
            assert location.region_id == "_global"

    def test_migration_moves_items_to_visible_items(self):
        """Test that items are migrated to visible_items."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "old_pack.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "旧包", "en": "Old Pack"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {},
                    "npcs": {},
                    "locations": {
                        "old_location": {
                            "id": "old_location",
                            "name": {"cn": "旧地点", "en": "Old Location"},
                            "description": {"cn": "描述", "en": "Desc"},
                            "items": ["sword", "shield"],
                        }
                    },
                }),
                encoding="utf-8",
            )

            loader = WorldPackLoader(tmpdir)
            pack = loader.load("old_pack")

            location = pack.get_location("old_location")
            assert location.visible_items == ["sword", "shield"]

    def test_migration_preserves_existing_regions(self):
        """Test that packs with regions are not migrated."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "new_pack.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "新包", "en": "New Pack"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {},
                    "npcs": {},
                    "locations": {
                        "new_location": {
                            "id": "new_location",
                            "name": {"cn": "新地点", "en": "New Location"},
                            "description": {"cn": "描述", "en": "Desc"},
                            "region_id": "custom_region",
                        }
                    },
                    "regions": {
                        "custom_region": {
                            "id": "custom_region",
                            "name": {"cn": "自定义区域", "en": "Custom Region"},
                            "description": {"cn": "描述", "en": "Desc"},
                        }
                    },
                }),
                encoding="utf-8",
            )

            loader = WorldPackLoader(tmpdir)
            pack = loader.load("new_pack")

            assert len(pack.regions) == 1
            assert "custom_region" in pack.regions
            assert "_global" not in pack.regions

    def test_migration_sets_default_visibility(self):
        """Test that lore entries get default visibility='basic'."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "old_pack.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "旧包", "en": "Old Pack"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {
                        "1": {
                            "uid": 1,
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
            pack = loader.load("old_pack")

            entry = pack.get_entry(1)
            assert entry.visibility == "basic"

    def test_migration_vector_indexing_includes_new_metadata(self):
        """Test that vector indexing includes new location filtering metadata."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "test_pack.json"
            pack_path.write_text(
                json.dumps({
                    "info": {
                        "name": {"cn": "测试包", "en": "Test Pack"},
                        "description": {"cn": "描述", "en": "Description"},
                    },
                    "entries": {
                        "1": {
                            "uid": 1,
                            "key": ["test"],
                            "content": {"cn": "内容", "en": "Content"},
                            "visibility": "basic",
                            "applicable_regions": ["region1"],
                            "applicable_locations": ["loc1"],
                        }
                    },
                    "npcs": {},
                    "locations": {},
                }),
                encoding="utf-8",
            )

            with tempfile.TemporaryDirectory() as db_dir:
                vector_store = VectorStoreService(db_dir)
                loader = WorldPackLoader(tmpdir, vector_store=vector_store)

                loader.load("test_pack")

                results = vector_store.search(
                    collection_name="lore_entries_test_pack",
                    query_text="test",
                    n_results=2,
                )

                for metadata in results["metadatas"][0]:
                    assert "visibility" in metadata
                    assert "applicable_regions" in metadata
                    assert "applicable_locations" in metadata
