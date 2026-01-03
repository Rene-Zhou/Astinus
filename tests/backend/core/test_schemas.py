"""Tests for JSON Schema validation."""

import pytest
from jsonschema import ValidationError

from src.backend.core.schemas import load_schema, validate_world_pack


class TestLoadSchema:
    """Test schema loading functionality."""

    def test_load_world_pack_schema(self):
        """Test loading the world_pack schema."""
        schema = load_schema("world_pack")
        assert schema is not None
        assert schema["title"] == "WorldPack"
        assert "$schema" in schema
        assert "definitions" in schema

    def test_load_nonexistent_schema(self):
        """Test loading a nonexistent schema raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Schema not found"):
            load_schema("nonexistent_schema")


class TestValidWorldPack:
    """Test validation with valid world pack data."""

    def test_minimal_valid_world_pack(self):
        """Test minimal valid world pack passes validation."""
        data = {
            "info": {
                "name": {"cn": "测试包", "en": "Test Pack"},
                "description": {"cn": "测试描述", "en": "Test description"},
            },
            "entries": {},
            "npcs": {},
            "locations": {},
        }
        # Should not raise
        validate_world_pack(data)

    def test_complete_valid_world_pack(self):
        """Test complete valid world pack with all fields."""
        data = {
            "info": {
                "name": {"cn": "完整包", "en": "Complete Pack"},
                "description": {"cn": "完整描述", "en": "Complete description"},
                "version": "1.2.3",
                "author": "Test Author",
            },
            "entries": {
                "1": {
                    "uid": 1,
                    "key": ["test"],
                    "secondary_keys": ["secondary"],
                    "content": {"cn": "内容", "en": "Content"},
                    "comment": {"cn": "注释", "en": "Comment"},
                    "constant": True,
                    "selective": False,
                    "order": 50,
                }
            },
            "npcs": {
                "test_npc": {
                    "id": "test_npc",
                    "soul": {
                        "name": "测试NPC",
                        "description": {"cn": "测试描述", "en": "Test description"},
                        "personality": ["friendly", "brave"],
                        "speech_style": {"cn": "友好", "en": "Friendly"},
                        "example_dialogue": [
                            {"user": "你好", "char": "你好！"},
                        ],
                    },
                    "body": {
                        "location": "test_location",
                        "inventory": ["sword"],
                        "relations": {"player": 50},
                        "tags": ["friendly"],
                        "memory": {"event1": ["keyword1"]},
                    },
                }
            },
            "locations": {
                "test_location": {
                    "id": "test_location",
                    "name": {"cn": "测试地点", "en": "Test Location"},
                    "description": {"cn": "描述", "en": "Description"},
                    "connected_locations": ["other_location"],
                    "present_npc_ids": ["test_npc"],
                    "items": ["item1"],
                    "tags": ["safe"],
                }
            },
        }
        # Should not raise
        validate_world_pack(data)


class TestInvalidWorldPack:
    """Test validation with invalid world pack data."""

    def test_missing_required_field_info(self):
        """Test missing 'info' field raises ValidationError."""
        data = {
            "entries": {},
            "npcs": {},
            "locations": {},
        }
        with pytest.raises(ValidationError, match="'info' is a required property"):
            validate_world_pack(data)

    def test_invalid_version_format(self):
        """Test invalid version format raises ValidationError."""
        data = {
            "info": {
                "name": {"cn": "测试", "en": "Test"},
                "description": {"cn": "描述", "en": "Description"},
                "version": "invalid-version",
            },
            "entries": {},
            "npcs": {},
            "locations": {},
        }
        with pytest.raises(ValidationError, match="does not match"):
            validate_world_pack(data)

    def test_missing_localized_string_cn(self):
        """Test missing 'cn' in LocalizedString raises ValidationError."""
        data = {
            "info": {
                "name": {"en": "Test"},  # Missing 'cn'
                "description": {"cn": "描述", "en": "Description"},
            },
            "entries": {},
            "npcs": {},
            "locations": {},
        }
        with pytest.raises(ValidationError, match="'cn' is a required property"):
            validate_world_pack(data)

    def test_invalid_lore_entry_uid_type(self):
        """Test invalid lore entry uid type raises ValidationError."""
        data = {
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
        }
        with pytest.raises(ValidationError, match="is not of type 'integer'"):
            validate_world_pack(data)

    def test_invalid_npc_id_format(self):
        """Test invalid NPC ID format raises ValidationError."""
        data = {
            "info": {
                "name": {"cn": "测试", "en": "Test"},
                "description": {"cn": "描述", "en": "Description"},
            },
            "entries": {},
            "npcs": {
                "InvalidID": {  # Should be snake_case (lowercase + underscores)
                    "id": "InvalidID",
                    "soul": {
                        "name": "NPC",
                        "description": {"cn": "描述", "en": "Description"},
                        "personality": ["friendly"],
                        "speech_style": {"cn": "风格", "en": "Style"},
                    },
                    "body": {"location": "loc"},
                }
            },
            "locations": {},
        }
        with pytest.raises(ValidationError, match="does not match"):
            validate_world_pack(data)

    def test_npc_personality_too_many(self):
        """Test NPC personality with >5 traits raises ValidationError."""
        data = {
            "info": {
                "name": {"cn": "测试", "en": "Test"},
                "description": {"cn": "描述", "en": "Description"},
            },
            "entries": {},
            "npcs": {
                "test_npc": {
                    "id": "test_npc",
                    "soul": {
                        "name": "NPC",
                        "description": {"cn": "描述", "en": "Description"},
                        "personality": ["t1", "t2", "t3", "t4", "t5", "t6"],  # Too many
                        "speech_style": {"cn": "风格", "en": "Style"},
                    },
                    "body": {"location": "loc"},
                }
            },
            "locations": {},
        }
        with pytest.raises(ValidationError, match="is too long"):
            validate_world_pack(data)

    def test_npc_relation_out_of_range(self):
        """Test NPC relation score out of range raises ValidationError."""
        data = {
            "info": {
                "name": {"cn": "测试", "en": "Test"},
                "description": {"cn": "描述", "en": "Description"},
            },
            "entries": {},
            "npcs": {
                "test_npc": {
                    "id": "test_npc",
                    "soul": {
                        "name": "NPC",
                        "description": {"cn": "描述", "en": "Description"},
                        "personality": ["friendly"],
                        "speech_style": {"cn": "风格", "en": "Style"},
                    },
                    "body": {
                        "location": "loc",
                        "relations": {"player": 150},  # Out of range -100 to +100
                    },
                }
            },
            "locations": {},
        }
        with pytest.raises(ValidationError, match="is greater than the maximum"):
            validate_world_pack(data)

    def test_empty_lore_entry_keys(self):
        """Test lore entry with empty key list raises ValidationError."""
        data = {
            "info": {
                "name": {"cn": "测试", "en": "Test"},
                "description": {"cn": "描述", "en": "Description"},
            },
            "entries": {
                "1": {
                    "uid": 1,
                    "key": [],  # Must have at least one key
                    "content": {"cn": "内容", "en": "Content"},
                }
            },
            "npcs": {},
            "locations": {},
        }
        with pytest.raises(ValidationError, match="should be non-empty"):
            validate_world_pack(data)
