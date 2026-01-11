"""
LLM provider factory for creating language model instances.

Supports multiple providers (OpenAI, Anthropic, etc.) via configuration.
Provides a unified interface for agent LLM initialization.
"""

from enum import Enum
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class LLMConfig(BaseModel):
    """
    Configuration for LLM initialization.

    Attributes:
        provider: Which LLM provider to use
        model: Model identifier (e.g., "gpt-4", "claude-3-5-sonnet-20241022")
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens to generate
        streaming: Enable streaming responses
        api_key: Optional API key (overrides environment variable)
        base_url: Optional base URL for custom endpoints

    Examples:
        >>> config = LLMConfig(provider="openai", model="gpt-4")
        >>> config = LLMConfig(
        ...     provider="anthropic",
        ...     model="claude-3-5-sonnet-20241022",
        ...     temperature=0.7
        ... )
    """

    provider: LLMProvider = Field(default=LLMProvider.OPENAI, description="LLM provider to use")
    model: str = Field(default="gpt-4o-mini", description="Model identifier")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int | None = Field(default=2000, ge=1, description="Maximum tokens to generate")
    streaming: bool = Field(default=False, description="Enable streaming responses")
    api_key: str | None = Field(default=None, description="API key (overrides env var)")
    base_url: str | None = Field(default=None, description="Custom API base URL")


def get_llm(config: LLMConfig | None = None) -> BaseChatModel:
    """
    Create an LLM instance based on configuration.

    Args:
        config: LLM configuration. If None, uses defaults.

    Returns:
        Configured LLM instance

    Raises:
        ValueError: If provider is not supported or required dependencies missing

    Examples:
        >>> llm = get_llm()  # Default: OpenAI gpt-4o-mini
        >>> llm = get_llm(LLMConfig(provider="anthropic", model="claude-3-5-sonnet-20241022"))
    """
    if config is None:
        config = LLMConfig()

    # Build common kwargs
    kwargs: dict[str, Any] = {
        "model": config.model,
        "temperature": config.temperature,
        "streaming": config.streaming,
    }

    if config.max_tokens is not None:
        kwargs["max_tokens"] = config.max_tokens

    if config.api_key is not None:
        kwargs["api_key"] = config.api_key

    if config.base_url is not None:
        kwargs["base_url"] = config.base_url

    # Create provider-specific instance
    if config.provider == LLMProvider.OPENAI:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ValueError(
                "OpenAI provider requires langchain-openai. Install with: uv add langchain-openai"
            ) from exc

        return ChatOpenAI(**kwargs)

    elif config.provider == LLMProvider.ANTHROPIC:
        try:
            from langchain_anthropic import ChatAnthropic  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValueError(
                "Anthropic provider requires langchain-anthropic. "
                "Install with: uv add langchain-anthropic"
            ) from exc

        # Anthropic uses different parameter names
        anthropic_kwargs = {
            "model": kwargs["model"],
            "temperature": kwargs["temperature"],
            "streaming": kwargs.get("streaming", False),
        }

        if "max_tokens" in kwargs:
            anthropic_kwargs["max_tokens"] = kwargs["max_tokens"]

        if "api_key" in kwargs:
            anthropic_kwargs["anthropic_api_key"] = kwargs["api_key"]

        if "base_url" in kwargs:
            anthropic_kwargs["base_url"] = kwargs["base_url"]

        return ChatAnthropic(**anthropic_kwargs)  # type: ignore[no-any-return]

    elif config.provider == LLMProvider.GOOGLE:
        try:
            from langchain_google_genai import (
                ChatGoogleGenerativeAI,  # type: ignore[import-not-found]
            )
        except ImportError as exc:
            raise ValueError(
                "Google provider requires langchain-google-genai. "
                "Install with: uv add langchain-google-genai"
            ) from exc

        google_kwargs: dict[str, Any] = {
            "model": kwargs["model"],
            "temperature": kwargs["temperature"],
        }

        if "max_tokens" in kwargs:
            google_kwargs["max_output_tokens"] = kwargs["max_tokens"]

        if "api_key" in kwargs:
            google_kwargs["google_api_key"] = kwargs["api_key"]

        return ChatGoogleGenerativeAI(**google_kwargs)  # type: ignore[no-any-return]

    elif config.provider == LLMProvider.OLLAMA:
        try:
            from langchain_ollama import ChatOllama  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ValueError(
                "Ollama provider requires langchain-ollama. Install with: uv add langchain-ollama"
            ) from exc

        ollama_kwargs = {
            "model": kwargs["model"],
            "temperature": kwargs["temperature"],
        }

        if "base_url" in kwargs:
            ollama_kwargs["base_url"] = kwargs["base_url"]

        return ChatOllama(**ollama_kwargs)  # type: ignore[no-any-return]

    else:
        raise ValueError(f"Unsupported provider: {config.provider}")


def get_default_llm() -> BaseChatModel:
    """Get default LLM instance (OpenAI gpt-4o-mini)."""
    return get_llm(LLMConfig())


def create_llm_from_settings(agent_name: str) -> BaseChatModel:
    """Create LLM for an agent using current settings (new format)."""
    from src.backend.core.config import get_settings

    settings = get_settings()

    if not settings.is_new_format():
        api_key = None
        if settings.llm.provider == "openai":
            api_key = settings.llm.api_keys.openai or None
        elif settings.llm.provider == "anthropic":
            api_key = settings.llm.api_keys.anthropic or None
        elif settings.llm.provider == "google":
            api_key = settings.llm.api_keys.google or None

        model = getattr(settings.llm.models, agent_name, "gpt-4o-mini")
        return get_llm(
            LLMConfig(
                provider=LLMProvider(settings.llm.provider),
                model=model,
                temperature=settings.llm.temperature,
                max_tokens=settings.llm.max_tokens,
                api_key=api_key,
            )
        )

    if settings.agents is None:
        raise ValueError("No agents configuration found")

    agent_config = getattr(settings.agents, agent_name, None)
    if agent_config is None:
        raise ValueError(f"Agent '{agent_name}' not found in configuration")

    provider = settings.get_provider(agent_config.provider_id)
    if provider is None:
        raise ValueError(
            f"Provider '{agent_config.provider_id}' not found for agent '{agent_name}'"
        )

    return get_llm(
        LLMConfig(
            provider=LLMProvider(provider.type.value),
            model=agent_config.model,
            temperature=agent_config.temperature,
            max_tokens=agent_config.max_tokens,
            api_key=provider.api_key,
            base_url=provider.base_url,
        )
    )
