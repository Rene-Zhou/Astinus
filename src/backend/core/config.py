"""Configuration loader for Astinus backend."""

import os
import re
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

PROVIDER_ID_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")


def validate_provider_id(provider_id: str) -> bool:
    """Validate Provider ID: lowercase alphanumeric and hyphens, 1-32 chars."""
    if not provider_id or len(provider_id) > 32:
        return False
    return bool(PROVIDER_ID_PATTERN.match(provider_id))


def get_provider_id_error_message(provider_id: str) -> str | None:
    """Get error message for invalid Provider ID, or None if valid."""
    if not provider_id:
        return "Provider ID cannot be empty"
    if len(provider_id) > 32:
        return "Provider ID cannot exceed 32 characters"
    if not PROVIDER_ID_PATTERN.match(provider_id):
        if provider_id[0] == "-" or provider_id[-1] == "-":
            return "Provider ID cannot start or end with hyphen"
        return (
            "Provider ID can only contain lowercase letters, numbers, and hyphens. "
            "Example: google-gemini, openai-proxy, local-1"
        )
    return None


def mask_api_key(key: str | None) -> str:
    """Mask API key for safe display: 'AIzaSyBxxx...' -> 'AIza****xxx'."""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}****{key[-3:]}"


def is_masked_key(value: str) -> bool:
    """Check if the value is a masked API key (contains '****')."""
    return "****" in value


def should_update_key(new_key: str, old_key: str | None) -> str | None:
    """Determine the key to save: None=clear, old=keep masked, new=update."""
    if not new_key:
        return None
    if is_masked_key(new_key):
        return old_key
    return new_key


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""

    id: str = Field(..., description="Unique provider identifier")
    name: str = Field(..., description="Display name")
    type: ProviderType = Field(..., description="Provider type")
    api_key: str | None = Field(default=None, description="API key")
    base_url: str | None = Field(default=None, description="Custom API base URL")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        error = get_provider_id_error_message(v)
        if error:
            raise ValueError(error)
        return v

    def to_masked_dict(self) -> dict[str, Any]:
        """Convert to dict with masked API key for frontend."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "api_key": mask_api_key(self.api_key),
            "base_url": self.base_url,
        }


class AgentConfig(BaseModel):
    """Configuration for a single agent's LLM settings."""

    provider_id: str = Field(..., description="Reference to provider ID")
    model: str = Field(..., description="Model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature")
    max_tokens: int = Field(default=2048, ge=1, description="Max tokens")


class AgentsConfig(BaseModel):
    """Configuration for all agents."""

    gm: AgentConfig
    npc: AgentConfig
    rule: AgentConfig
    lore: AgentConfig


class LLMModelsConfig(BaseModel):
    """Legacy: Model names for different agents."""

    gm: str = Field(default="gpt-4o-mini")
    npc: str = Field(default="gpt-4o-mini")
    rule: str = Field(default="gpt-4o-mini")
    lore: str = Field(default="gpt-4o-mini")


class LLMApiKeysConfig(BaseModel):
    """Legacy: API keys for different providers."""

    openai: str = Field(default="")
    anthropic: str = Field(default="")
    google: str = Field(default="")


class LLMConfig(BaseModel):
    """Legacy: LLM configuration section."""

    provider: str = Field(default="openai")
    models: LLMModelsConfig = Field(default_factory=LLMModelsConfig)
    api_keys: LLMApiKeysConfig = Field(default_factory=LLMApiKeysConfig)
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2048)


class DatabaseConfig(BaseModel):
    """Database configuration."""

    sqlite_path: str = Field(default="data/saves/game.db")
    chromadb_path: str = Field(default="data/vector_store")
    enable_vector_search: bool = Field(default=False)


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    reload: bool = Field(default=True)
    log_level: str = Field(default="info")


class DiceConfig(BaseModel):
    """Dice system configuration."""

    use_advantage_system: bool = Field(default=True)
    show_roll_details: bool = Field(default=True)


class GameConfig(BaseModel):
    """Game configuration."""

    default_language: str = Field(default="cn")
    packs_directory: str = Field(default="data/packs")
    dice: DiceConfig = Field(default_factory=DiceConfig)
    conversation_history_length: int = Field(
        default=5, ge=0, le=20, description="Number of recent messages to include in GM context"
    )


class FrontendConfig(BaseModel):
    """Frontend configuration."""

    theme: str = Field(default="dark")
    animation_speed: str = Field(default="normal")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file: str = Field(default="logs/astinus.log")


class Settings(BaseModel):
    """Complete application settings with both new and legacy format support."""

    providers: list[ProviderConfig] = Field(default_factory=list)
    agents: AgentsConfig | None = Field(default=None)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    game: GameConfig = Field(default_factory=GameConfig)
    frontend: FrontendConfig = Field(default_factory=FrontendConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    def is_new_format(self) -> bool:
        """Check if using new configuration format (providers + agents)."""
        return len(self.providers) > 0 and self.agents is not None

    def get_provider(self, provider_id: str) -> ProviderConfig | None:
        """Get provider by ID."""
        for provider in self.providers:
            if provider.id == provider_id:
                return provider
        return None

    def get_provider_ids_in_use(self) -> set[str]:
        """Get provider IDs currently used by agents."""
        if not self.agents:
            return set()
        return {
            self.agents.gm.provider_id,
            self.agents.npc.provider_id,
            self.agents.rule.provider_id,
            self.agents.lore.provider_id,
        }

    def validate_agent_provider_references(self) -> list[str]:
        """Validate all agent provider_id references exist. Returns errors."""
        if not self.agents:
            return []

        errors = []
        provider_ids = {p.id for p in self.providers}

        for agent_name in ["gm", "npc", "rule", "lore"]:
            agent_config = getattr(self.agents, agent_name)
            if agent_config.provider_id not in provider_ids:
                errors.append(
                    f"Agent '{agent_name}' references non-existent provider "
                    f"'{agent_config.provider_id}'"
                )

        return errors

    def to_settings_response(self) -> dict[str, Any]:
        """Convert to API response format with masked keys."""
        return {
            "providers": [p.to_masked_dict() for p in self.providers],
            "agents": self.agents.model_dump() if self.agents else None,
            "game": {
                "default_language": self.game.default_language,
                "dice": self.game.dice.model_dump(),
            },
        }


def create_default_settings() -> Settings:
    """Create default settings with an empty default provider."""
    default_provider = ProviderConfig(
        id="default",
        name="Default Provider (Not Configured)",
        type=ProviderType.OPENAI,
        api_key=None,
        base_url=None,
    )

    default_agent = AgentConfig(
        provider_id="default",
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=2048,
    )

    return Settings(
        providers=[default_provider],
        agents=AgentsConfig(
            gm=default_agent.model_copy(),
            npc=default_agent.model_copy(update={"temperature": 0.8}),
            rule=default_agent.model_copy(update={"temperature": 0.3, "max_tokens": 512}),
            lore=default_agent.model_copy(update={"temperature": 0.5, "max_tokens": 1024}),
        ),
    )


def find_config_file() -> Path | None:
    """Find settings.yaml: ASTINUS_CONFIG env, project root, or cwd."""
    env_path = os.environ.get("ASTINUS_CONFIG")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    current = Path(__file__).resolve()
    for parent in current.parents:
        config_path = parent / "config" / "settings.yaml"
        if config_path.exists():
            return config_path
        if (parent / "pyproject.toml").exists():
            break

    cwd_config = Path("config/settings.yaml")
    if cwd_config.exists():
        return cwd_config

    return None


def get_config_file_path() -> Path:
    """Get the project config path (for saving)."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent / "config" / "settings.yaml"
    return Path("config/settings.yaml")


def load_settings_from_file(path: Path) -> dict[str, Any]:
    """Load settings dict from a YAML file."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def save_settings_to_file(settings: Settings, path: Path | None = None) -> None:
    """Save settings to YAML file."""
    if path is None:
        path = get_config_file_path()

    path.parent.mkdir(parents=True, exist_ok=True)

    data: dict[str, Any] = {}

    if settings.is_new_format():
        data["providers"] = [
            {
                "id": p.id,
                "name": p.name,
                "type": p.type.value,
                "api_key": p.api_key or "",
                "base_url": p.base_url,
            }
            for p in settings.providers
        ]
        data["agents"] = settings.agents.model_dump() if settings.agents else None
    else:
        data["llm"] = settings.llm.model_dump()

    data["database"] = settings.database.model_dump()
    data["server"] = settings.server.model_dump()
    data["game"] = settings.game.model_dump()
    data["frontend"] = settings.frontend.model_dump()
    data["logging"] = settings.logging.model_dump()

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def migrate_legacy_settings(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate legacy llm format to new providers+agents format."""
    if "providers" in data and "agents" in data:
        return data

    if "llm" not in data:
        return data

    llm = data["llm"]
    provider = llm.get("provider", "openai")
    api_keys = llm.get("api_keys", {})
    models = llm.get("models", {})
    temperature = llm.get("temperature", 0.7)
    max_tokens = llm.get("max_tokens", 2048)

    provider_id = f"{provider}-default"
    api_key = api_keys.get(provider, "")

    data["providers"] = [
        {
            "id": provider_id,
            "name": f"{provider.title()} (Migrated)",
            "type": provider,
            "api_key": api_key if api_key else None,
            "base_url": None,
        }
    ]

    data["agents"] = {
        "gm": {
            "provider_id": provider_id,
            "model": models.get("gm", "gpt-4o-mini"),
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        "npc": {
            "provider_id": provider_id,
            "model": models.get("npc", "gpt-4o-mini"),
            "temperature": min(temperature + 0.1, 2.0),
            "max_tokens": max_tokens // 2,
        },
        "rule": {
            "provider_id": provider_id,
            "model": models.get("rule", "gpt-4o-mini"),
            "temperature": max(temperature - 0.4, 0.0),
            "max_tokens": max_tokens // 4,
        },
        "lore": {
            "provider_id": provider_id,
            "model": models.get("lore", "gpt-4o-mini"),
            "temperature": max(temperature - 0.2, 0.0),
            "max_tokens": max_tokens // 2,
        },
    }

    return data


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get application settings (cached). Migrates legacy format if needed."""
    config_path = find_config_file()

    if config_path:
        try:
            data = load_settings_from_file(config_path)
            data = migrate_legacy_settings(data)
            return Settings.model_validate(data)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            print("   Using default settings")

    return create_default_settings()


def reset_settings() -> None:
    """Clear cached settings."""
    get_settings.cache_clear()


def reload_settings() -> Settings:
    """Force reload settings from file."""
    reset_settings()
    return get_settings()
