"""
Configuration loader for Astinus backend.

Loads settings from config/settings.yaml and provides typed access.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class LLMModelsConfig(BaseModel):
    """Model configurations for different agents."""

    gm: str = Field(default="gpt-4o-mini", description="GM Agent model")
    npc: str = Field(default="gpt-4o-mini", description="NPC Agent model")
    rule: str = Field(default="gpt-4o-mini", description="Rule Agent model")
    lore: str = Field(default="gpt-4o-mini", description="Lore Agent model")


class LLMApiKeysConfig(BaseModel):
    """API keys for different providers."""

    openai: str = Field(default="", description="OpenAI API key")
    anthropic: str = Field(default="", description="Anthropic API key")
    google: str = Field(default="", description="Google API key")


class LLMConfig(BaseModel):
    """LLM configuration section."""

    provider: str = Field(default="openai", description="Primary LLM provider")
    models: LLMModelsConfig = Field(default_factory=LLMModelsConfig)
    api_keys: LLMApiKeysConfig = Field(default_factory=LLMApiKeysConfig)
    temperature: float = Field(default=0.7, description="Sampling temperature")
    max_tokens: int = Field(default=2048, description="Maximum tokens to generate")


class DatabaseConfig(BaseModel):
    """Database configuration section."""

    sqlite_path: str = Field(default="data/saves/game.db")
    chromadb_path: str = Field(default="data/vector_store")
    enable_vector_search: bool = Field(default=False)


class ServerConfig(BaseModel):
    """Server configuration section."""

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    reload: bool = Field(default=True)
    log_level: str = Field(default="info")


class DiceConfig(BaseModel):
    """Dice system configuration."""

    use_advantage_system: bool = Field(default=True)
    show_roll_details: bool = Field(default=True)


class GameConfig(BaseModel):
    """Game configuration section."""

    default_language: str = Field(default="cn")
    packs_directory: str = Field(default="data/packs")
    dice: DiceConfig = Field(default_factory=DiceConfig)


class FrontendConfig(BaseModel):
    """Frontend configuration section."""

    theme: str = Field(default="dark")
    animation_speed: str = Field(default="normal")


class LoggingConfig(BaseModel):
    """Logging configuration section."""

    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file: str = Field(default="logs/astinus.log")


class Settings(BaseModel):
    """Complete application settings."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    game: GameConfig = Field(default_factory=GameConfig)
    frontend: FrontendConfig = Field(default_factory=FrontendConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


def find_config_file() -> Path | None:
    """
    Find the settings.yaml configuration file.

    Searches in the following order:
    1. ASTINUS_CONFIG environment variable
    2. config/settings.yaml relative to project root
    3. ./config/settings.yaml relative to current directory

    Returns:
        Path to config file if found, None otherwise
    """
    # Check environment variable first
    env_path = os.environ.get("ASTINUS_CONFIG")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    # Try to find project root (look for pyproject.toml)
    current = Path(__file__).resolve()
    for parent in current.parents:
        config_path = parent / "config" / "settings.yaml"
        if config_path.exists():
            return config_path
        # Stop at project root
        if (parent / "pyproject.toml").exists():
            break

    # Try current directory
    cwd_config = Path("config/settings.yaml")
    if cwd_config.exists():
        return cwd_config

    return None


def load_settings_from_file(path: Path) -> dict[str, Any]:
    """
    Load settings from a YAML file.

    Args:
        path: Path to the YAML configuration file

    Returns:
        Dictionary of settings
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get application settings.

    Loads from config/settings.yaml if available, otherwise uses defaults.
    Results are cached for performance.

    Returns:
        Settings instance

    Examples:
        >>> settings = get_settings()
        >>> print(settings.llm.provider)
        "google"
    """
    config_path = find_config_file()

    if config_path:
        try:
            data = load_settings_from_file(config_path)
            return Settings.model_validate(data)
        except Exception as e:
            print(f"⚠️ Failed to load config from {config_path}: {e}")
            print("   Using default settings")

    return Settings()


def reset_settings() -> None:
    """
    Reset cached settings.

    Useful for testing or when config file changes.
    """
    get_settings.cache_clear()
