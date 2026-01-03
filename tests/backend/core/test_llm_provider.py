"""Tests for LLM provider factory."""

import os

import pytest

from src.backend.core.llm_provider import (
    LLMConfig,
    LLMProvider,
    get_default_llm,
    get_llm,
)

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


class TestLLMConfig:
    """Test suite for LLMConfig class."""

    def test_create_default_config(self):
        """Test creating config with defaults."""
        config = LLMConfig()
        assert config.provider == LLMProvider.OPENAI
        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.7
        assert config.max_tokens == 2000
        assert config.streaming is False
        assert config.api_key is None
        assert config.base_url is None

    def test_create_openai_config(self):
        """Test creating OpenAI config."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4",
            temperature=0.5,
            max_tokens=1000,
        )
        assert config.provider == LLMProvider.OPENAI
        assert config.model == "gpt-4"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000

    def test_create_anthropic_config(self):
        """Test creating Anthropic config."""
        config = LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            temperature=0.8,
        )
        assert config.provider == LLMProvider.ANTHROPIC
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.temperature == 0.8

    def test_create_ollama_config(self):
        """Test creating Ollama config."""
        config = LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="llama2",
            base_url="http://localhost:11434",
        )
        assert config.provider == LLMProvider.OLLAMA
        assert config.model == "llama2"
        assert config.base_url == "http://localhost:11434"

    def test_temperature_validation(self):
        """Test temperature bounds validation."""
        from pydantic import ValidationError

        # Valid temperatures
        LLMConfig(temperature=0.0)
        LLMConfig(temperature=1.0)
        LLMConfig(temperature=2.0)

        # Invalid temperatures
        with pytest.raises(ValidationError):
            LLMConfig(temperature=-0.1)

        with pytest.raises(ValidationError):
            LLMConfig(temperature=2.1)

    def test_max_tokens_validation(self):
        """Test max_tokens validation."""
        from pydantic import ValidationError

        # Valid
        LLMConfig(max_tokens=1)
        LLMConfig(max_tokens=None)

        # Invalid
        with pytest.raises(ValidationError):
            LLMConfig(max_tokens=0)

        with pytest.raises(ValidationError):
            LLMConfig(max_tokens=-1)

    def test_config_with_api_key(self):
        """Test config with custom API key."""
        config = LLMConfig(api_key="sk-test-key")
        assert config.api_key == "sk-test-key"

    def test_config_with_streaming(self):
        """Test config with streaming enabled."""
        config = LLMConfig(streaming=True)
        assert config.streaming is True


class TestGetLLM:
    """Test suite for get_llm() function."""

    def test_get_default_llm(self):
        """Test getting default LLM."""
        llm = get_default_llm()
        assert llm is not None
        # Should be ChatOpenAI with gpt-4o-mini
        assert "gpt-4o-mini" in str(llm)

    def test_get_llm_with_default_config(self):
        """Test get_llm() with no arguments."""
        llm = get_llm()
        assert llm is not None

    def test_get_llm_with_custom_config(self):
        """Test get_llm() with custom config."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4",
            temperature=0.5,
        )
        llm = get_llm(config)
        assert llm is not None
        # Check model name is in string representation
        assert "gpt-4" in str(llm)

    def test_get_llm_openai_provider(self):
        """Test creating OpenAI LLM."""
        config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4o-mini")
        llm = get_llm(config)
        assert llm is not None
        from langchain_openai import ChatOpenAI

        assert isinstance(llm, ChatOpenAI)

    def test_get_llm_anthropic_provider_missing_dependency(self):
        """Test Anthropic provider without langchain-anthropic installed."""
        config = LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
        )

        # This will fail if langchain-anthropic is not installed
        # We test that it raises the correct error
        try:
            llm = get_llm(config)
            # If successful, check it's the right type
            from langchain_anthropic import ChatAnthropic

            assert isinstance(llm, ChatAnthropic)
        except ValueError as exc:
            assert "langchain-anthropic" in str(exc)

    def test_get_llm_ollama_provider_missing_dependency(self):
        """Test Ollama provider without langchain-ollama installed."""
        config = LLMConfig(provider=LLMProvider.OLLAMA, model="llama2")

        # This will fail if langchain-ollama is not installed
        try:
            llm = get_llm(config)
            # If successful, check it's the right type
            from langchain_ollama import ChatOllama

            assert isinstance(llm, ChatOllama)
        except ValueError as exc:
            assert "langchain-ollama" in str(exc)

    def test_get_llm_with_custom_base_url(self):
        """Test creating LLM with custom base URL."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
            base_url="https://custom.api.com/v1",
        )
        llm = get_llm(config)
        assert llm is not None

    def test_get_llm_with_api_key(self):
        """Test creating LLM with custom API key."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
            api_key="sk-test-key",
        )
        llm = get_llm(config)
        assert llm is not None

    def test_get_llm_with_streaming(self):
        """Test creating LLM with streaming enabled."""
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
            streaming=True,
        )
        llm = get_llm(config)
        assert llm is not None


class TestLLMProvider:
    """Test suite for LLMProvider enum."""

    def test_provider_values(self):
        """Test provider enum values."""
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.ANTHROPIC == "anthropic"
        assert LLMProvider.OLLAMA == "ollama"

    def test_provider_from_string(self):
        """Test creating provider from string."""
        assert LLMProvider("openai") == LLMProvider.OPENAI
        assert LLMProvider("anthropic") == LLMProvider.ANTHROPIC
        assert LLMProvider("ollama") == LLMProvider.OLLAMA
