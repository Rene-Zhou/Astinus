"""Tests for settings API endpoints."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"

from src.backend.main import app


class TestSettingsAPI:

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_settings(self):
        from src.backend.core.config import (
            AgentConfig,
            AgentsConfig,
            ProviderConfig,
            ProviderType,
            Settings,
        )

        return Settings(
            providers=[
                ProviderConfig(
                    id="test-provider",
                    name="Test Provider",
                    type=ProviderType.OPENAI,
                    api_key="sk-test-key-12345678",
                    base_url=None,
                )
            ],
            agents=AgentsConfig(
                gm=AgentConfig(
                    provider_id="test-provider",
                    model="gpt-4o",
                    temperature=0.7,
                    max_tokens=2048,
                ),
                npc=AgentConfig(
                    provider_id="test-provider",
                    model="gpt-4o",
                    temperature=0.8,
                    max_tokens=1024,
                ),
                rule=AgentConfig(
                    provider_id="test-provider",
                    model="gpt-4o",
                    temperature=0.3,
                    max_tokens=512,
                ),
                lore=AgentConfig(
                    provider_id="test-provider",
                    model="gpt-4o",
                    temperature=0.5,
                    max_tokens=1024,
                ),
            ),
        )

    def test_get_settings(self, client, mock_settings):
        with patch(
            "src.backend.api.v1.settings.get_settings", return_value=mock_settings
        ):
            response = client.get("/api/v1/settings")
            assert response.status_code == 200

            data = response.json()
            assert "providers" in data
            assert "agents" in data
            assert len(data["providers"]) == 1
            assert data["providers"][0]["id"] == "test-provider"
            assert data["providers"][0]["api_key"] == "sk-t****678"

    def test_get_provider_types(self, client):
        response = client.get("/api/v1/settings/provider-types")
        assert response.status_code == 200

        data = response.json()
        assert "types" in data
        assert len(data["types"]) == 4

        type_names = [t["type"] for t in data["types"]]
        assert "openai" in type_names
        assert "anthropic" in type_names
        assert "google" in type_names
        assert "ollama" in type_names

    def test_update_settings_add_provider(self, client, mock_settings):
        with patch(
            "src.backend.api.v1.settings.get_settings", return_value=mock_settings
        ), patch(
            "src.backend.api.v1.settings.save_settings_to_file"
        ) as mock_save, patch(
            "src.backend.api.v1.settings.reload_settings"
        ):
            response = client.put(
                "/api/v1/settings",
                json={
                    "providers": [
                        {
                            "id": "test-provider",
                            "name": "Test Provider",
                            "type": "openai",
                            "api_key": "sk-t****678",
                            "base_url": None,
                        },
                        {
                            "id": "new-provider",
                            "name": "New Provider",
                            "type": "anthropic",
                            "api_key": "sk-ant-new-key",
                            "base_url": None,
                        },
                    ]
                },
            )
            assert response.status_code == 200
            mock_save.assert_called_once()

    def test_update_settings_invalid_provider_id(self, client, mock_settings):
        with patch(
            "src.backend.api.v1.settings.get_settings", return_value=mock_settings
        ):
            response = client.put(
                "/api/v1/settings",
                json={
                    "providers": [
                        {
                            "id": "Invalid ID!",
                            "name": "Bad Provider",
                            "type": "openai",
                            "api_key": "",
                            "base_url": None,
                        }
                    ]
                },
            )
            assert response.status_code == 400
            assert "Invalid provider ID" in response.json()["detail"]

    def test_update_settings_invalid_provider_type(self, client, mock_settings):
        with patch(
            "src.backend.api.v1.settings.get_settings", return_value=mock_settings
        ):
            response = client.put(
                "/api/v1/settings",
                json={
                    "providers": [
                        {
                            "id": "test-provider",
                            "name": "Test",
                            "type": "invalid-type",
                            "api_key": "",
                            "base_url": None,
                        }
                    ]
                },
            )
            assert response.status_code == 400
            assert "Invalid provider type" in response.json()["detail"]

    def test_update_settings_agent_references_nonexistent_provider(
        self, client, mock_settings
    ):
        with patch(
            "src.backend.api.v1.settings.get_settings", return_value=mock_settings
        ):
            response = client.put(
                "/api/v1/settings",
                json={
                    "agents": {
                        "gm": {
                            "provider_id": "nonexistent",
                            "model": "gpt-4o",
                            "temperature": 0.7,
                            "max_tokens": 2048,
                        }
                    }
                },
            )
            assert response.status_code == 400
            assert "non-existent provider" in response.json()["detail"]

    def test_test_connection_provider_not_found(self, client, mock_settings):
        with patch(
            "src.backend.api.v1.settings.get_settings", return_value=mock_settings
        ):
            response = client.post(
                "/api/v1/settings/test",
                json={"provider_id": "nonexistent"},
            )
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]


class TestConfigHelpers:

    def test_mask_api_key(self):
        from src.backend.core.config import mask_api_key

        assert mask_api_key("") == ""
        assert mask_api_key("short") == "****"
        assert mask_api_key("sk-1234567890abcdef") == "sk-1****def"

    def test_is_masked_key(self):
        from src.backend.core.config import is_masked_key

        assert is_masked_key("sk-1****def") is True
        assert is_masked_key("****") is True
        assert is_masked_key("sk-real-key") is False
        assert is_masked_key("") is False

    def test_should_update_key(self):
        from src.backend.core.config import should_update_key

        assert should_update_key("", "old-key") is None
        assert should_update_key("sk-1****def", "old-key") == "old-key"
        assert should_update_key("new-key", "old-key") == "new-key"
        assert should_update_key("sk-1****def", None) is None

    def test_provider_id_validation(self):
        from src.backend.core.config import (
            get_provider_id_error_message,
            validate_provider_id,
        )

        assert validate_provider_id("google-gemini") is True
        assert validate_provider_id("openai-1") is True
        assert validate_provider_id("a") is True
        assert validate_provider_id("ab") is True
        assert validate_provider_id("Invalid ID!") is False
        assert validate_provider_id("has spaces") is False
        assert validate_provider_id("-starts-with-dash") is False
        assert validate_provider_id("ends-with-dash-") is False
        assert validate_provider_id("") is False
        assert validate_provider_id("a" * 33) is False

        assert get_provider_id_error_message("google-gemini") is None
        assert get_provider_id_error_message("") is not None
        assert get_provider_id_error_message("Invalid!") is not None


class TestProviderConfig:

    def test_provider_config_validation(self):
        from src.backend.core.config import ProviderConfig, ProviderType

        provider = ProviderConfig(
            id="test-provider",
            name="Test",
            type=ProviderType.OPENAI,
            api_key="sk-test",
            base_url=None,
        )
        assert provider.id == "test-provider"
        assert provider.type == ProviderType.OPENAI

    def test_provider_config_invalid_id(self):
        from pydantic import ValidationError

        from src.backend.core.config import ProviderConfig, ProviderType

        with pytest.raises(ValidationError):
            ProviderConfig(
                id="Invalid ID!",
                name="Test",
                type=ProviderType.OPENAI,
                api_key="",
                base_url=None,
            )


class TestAgentConfig:

    def test_agent_config_validation(self):
        from src.backend.core.config import AgentConfig

        agent = AgentConfig(
            provider_id="test",
            model="gpt-4o",
            temperature=0.7,
            max_tokens=2048,
        )
        assert agent.provider_id == "test"
        assert agent.temperature == 0.7

    def test_agent_config_temperature_bounds(self):
        from pydantic import ValidationError

        from src.backend.core.config import AgentConfig

        with pytest.raises(ValidationError):
            AgentConfig(
                provider_id="test",
                model="gpt-4o",
                temperature=2.5,
                max_tokens=2048,
            )

        with pytest.raises(ValidationError):
            AgentConfig(
                provider_id="test",
                model="gpt-4o",
                temperature=-0.1,
                max_tokens=2048,
            )
