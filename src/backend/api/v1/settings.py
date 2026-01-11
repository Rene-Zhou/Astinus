"""Settings API v1 routes."""

import time
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.backend.core.config import (
    AgentConfig,
    AgentsConfig,
    ProviderConfig,
    ProviderType,
    Settings,
    get_config_file_path,
    get_provider_id_error_message,
    get_settings,
    is_masked_key,
    mask_api_key,
    reload_settings,
    save_settings_to_file,
    should_update_key,
)
from src.backend.core.llm_provider import LLMConfig
from src.backend.core.llm_provider import LLMProvider as LLMProviderEnum
from src.backend.core.llm_provider import get_llm

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class ProviderConfigResponse(BaseModel):
    """Provider config with masked API key."""

    id: str
    name: str
    type: str
    api_key: str
    base_url: str | None


class AgentConfigResponse(BaseModel):
    """Agent config response."""

    provider_id: str
    model: str
    temperature: float
    max_tokens: int


class AgentsConfigResponse(BaseModel):
    """All agents config response."""

    gm: AgentConfigResponse
    npc: AgentConfigResponse
    rule: AgentConfigResponse
    lore: AgentConfigResponse


class GameSettingsResponse(BaseModel):
    """Game settings subset."""

    default_language: str
    dice: dict[str, Any]


class SettingsResponse(BaseModel):
    """Full settings response with masked keys."""

    providers: list[ProviderConfigResponse]
    agents: AgentsConfigResponse | None
    game: GameSettingsResponse


class ProviderInput(BaseModel):
    """Input for a provider (create/update)."""

    id: str
    name: str
    type: str
    api_key: str = ""
    base_url: str | None = None


class AgentInput(BaseModel):
    """Input for an agent config."""

    provider_id: str
    model: str
    temperature: float = Field(ge=0.0, le=2.0)
    max_tokens: int = Field(ge=1)


class AgentsInput(BaseModel):
    """Input for all agents."""

    gm: AgentInput | None = None
    npc: AgentInput | None = None
    rule: AgentInput | None = None
    lore: AgentInput | None = None


class UpdateSettingsRequest(BaseModel):
    """Request to update settings."""

    providers: list[ProviderInput] | None = None
    agents: AgentsInput | None = None


class TestConnectionRequest(BaseModel):
    """Request to test provider connection."""

    provider_id: str


class TestConnectionResponse(BaseModel):
    """Response from connection test."""

    success: bool
    provider_id: str
    message: str
    latency_ms: int | None = None


class ProviderTypeInfo(BaseModel):
    """Metadata about a provider type."""

    type: str
    name: str
    requires_api_key: bool
    default_base_url: str | None
    placeholder_models: list[str]


class ProviderTypesResponse(BaseModel):
    """List of supported provider types."""

    types: list[ProviderTypeInfo]


PROVIDER_TYPE_METADATA: dict[str, ProviderTypeInfo] = {
    "openai": ProviderTypeInfo(
        type="openai",
        name="OpenAI",
        requires_api_key=True,
        default_base_url="https://api.openai.com/v1",
        placeholder_models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    ),
    "anthropic": ProviderTypeInfo(
        type="anthropic",
        name="Anthropic",
        requires_api_key=True,
        default_base_url="https://api.anthropic.com",
        placeholder_models=[
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
        ],
    ),
    "google": ProviderTypeInfo(
        type="google",
        name="Google AI",
        requires_api_key=True,
        default_base_url=None,
        placeholder_models=[
            "gemini-2.5-pro-preview-05-06",
            "gemini-2.5-flash-preview-05-20",
            "gemini-2.0-flash",
        ],
    ),
    "ollama": ProviderTypeInfo(
        type="ollama",
        name="Ollama (Local)",
        requires_api_key=False,
        default_base_url="http://localhost:11434",
        placeholder_models=["llama3", "mistral", "codellama", "gemma"],
    ),
}


def _build_settings_response(settings: Settings) -> SettingsResponse:
    """Build SettingsResponse from Settings."""
    providers = [
        ProviderConfigResponse(
            id=p.id,
            name=p.name,
            type=p.type.value,
            api_key=mask_api_key(p.api_key),
            base_url=p.base_url,
        )
        for p in settings.providers
    ]

    agents_resp = None
    if settings.agents:
        agents_resp = AgentsConfigResponse(
            gm=AgentConfigResponse(**settings.agents.gm.model_dump()),
            npc=AgentConfigResponse(**settings.agents.npc.model_dump()),
            rule=AgentConfigResponse(**settings.agents.rule.model_dump()),
            lore=AgentConfigResponse(**settings.agents.lore.model_dump()),
        )

    return SettingsResponse(
        providers=providers,
        agents=agents_resp,
        game=GameSettingsResponse(
            default_language=settings.game.default_language,
            dice=settings.game.dice.model_dump(),
        ),
    )


@router.get("", response_model=SettingsResponse)
async def get_current_settings():
    """Get current settings with masked API keys."""
    settings = get_settings()
    return _build_settings_response(settings)


@router.put("", response_model=SettingsResponse)
async def update_settings(request: UpdateSettingsRequest):
    """Update settings. Masked API keys are preserved."""
    settings = get_settings()

    if request.providers is not None:
        existing_providers = {p.id: p for p in settings.providers}
        new_providers: list[ProviderConfig] = []

        for p_input in request.providers:
            error = get_provider_id_error_message(p_input.id)
            if error:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid provider ID '{p_input.id}': {error}",
                )

            try:
                provider_type = ProviderType(p_input.type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid provider type '{p_input.type}'",
                )

            old_provider = existing_providers.get(p_input.id)
            old_key = old_provider.api_key if old_provider else None
            new_key = should_update_key(p_input.api_key, old_key)

            new_providers.append(
                ProviderConfig(
                    id=p_input.id,
                    name=p_input.name,
                    type=provider_type,
                    api_key=new_key,
                    base_url=p_input.base_url,
                )
            )

        settings.providers = new_providers

    if request.agents is not None:
        if settings.agents is None:
            from src.backend.core.config import create_default_settings

            settings.agents = create_default_settings().agents

        provider_ids = {p.id for p in settings.providers}

        for agent_name in ["gm", "npc", "rule", "lore"]:
            agent_input = getattr(request.agents, agent_name)
            if agent_input is not None:
                if agent_input.provider_id not in provider_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Agent '{agent_name}' references non-existent provider '{agent_input.provider_id}'",
                    )
                setattr(
                    settings.agents,
                    agent_name,
                    AgentConfig(
                        provider_id=agent_input.provider_id,
                        model=agent_input.model,
                        temperature=agent_input.temperature,
                        max_tokens=agent_input.max_tokens,
                    ),
                )

    validation_errors = settings.validate_agent_provider_references()
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(validation_errors),
        )

    save_settings_to_file(settings)
    reload_settings()

    return _build_settings_response(get_settings())


@router.post("/test", response_model=TestConnectionResponse)
async def test_provider_connection(request: TestConnectionRequest):
    """Test connection to a provider."""
    settings = get_settings()
    provider = settings.get_provider(request.provider_id)

    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{request.provider_id}' not found",
        )

    if not provider.api_key and provider.type != ProviderType.OLLAMA:
        return TestConnectionResponse(
            success=False,
            provider_id=request.provider_id,
            message="API key not configured",
            latency_ms=None,
        )

    try:
        llm_config = LLMConfig(
            provider=LLMProviderEnum(provider.type.value),
            model="gpt-4o-mini" if provider.type == ProviderType.OPENAI else "test",
            temperature=0.0,
            max_tokens=5,
            api_key=provider.api_key,
            base_url=provider.base_url,
        )

        if provider.type == ProviderType.GOOGLE:
            llm_config.model = "gemini-2.0-flash"
        elif provider.type == ProviderType.ANTHROPIC:
            llm_config.model = "claude-3-haiku-20240307"
        elif provider.type == ProviderType.OLLAMA:
            llm_config.model = "llama3"

        llm = get_llm(llm_config)

        start_time = time.time()
        response = llm.invoke("Say 'ok'")
        latency_ms = int((time.time() - start_time) * 1000)

        return TestConnectionResponse(
            success=True,
            provider_id=request.provider_id,
            message=f"Connection successful",
            latency_ms=latency_ms,
        )

    except Exception as e:
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            message = "Invalid API key"
        elif "connection" in error_msg.lower() or "network" in error_msg.lower():
            message = "Connection failed - check network or base URL"
        else:
            message = f"Error: {error_msg[:100]}"

        return TestConnectionResponse(
            success=False,
            provider_id=request.provider_id,
            message=message,
            latency_ms=None,
        )


@router.get("/provider-types", response_model=ProviderTypesResponse)
async def get_provider_types():
    """Get list of supported provider types with metadata."""
    return ProviderTypesResponse(types=list(PROVIDER_TYPE_METADATA.values()))
