"""Settings API v1 routes."""

import time
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.backend.core.config import (
    AgentConfig,
    ProviderConfig,
    ProviderType,
    Settings,
    get_provider_id_error_message,
    get_settings,
    mask_api_key,
    reload_settings,
    save_settings_to_file,
    should_update_key,
)
from src.backend.core.llm_provider import LLMConfig, get_llm
from src.backend.core.llm_provider import LLMProvider as LLMProviderEnum

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
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid provider type '{p_input.type}'",
                ) from exc

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

        for agent_name in ["gm", "npc", "lore"]:
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
        llm.invoke("Say 'ok'")
        latency_ms = int((time.time() - start_time) * 1000)

        return TestConnectionResponse(
            success=True,
            provider_id=request.provider_id,
            message="Connection successful",
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


class ReloadAgentsResponse(BaseModel):
    """Response from agent reload."""

    success: bool
    message: str


@router.post("/reload-agents", response_model=ReloadAgentsResponse)
async def reload_agents():
    """
    Reload all game agents with current settings.

    Use this endpoint after updating provider configuration to apply changes
    without restarting the backend server.
    """
    try:
        import src.backend.main as main_module
        from src.backend.agents.gm import GMAgent
        from src.backend.agents.lore import LoreAgent
        from src.backend.agents.npc import NPCAgent
        from src.backend.core.config import get_settings
        from src.backend.core.llm_provider import create_llm_from_settings
        from src.backend.models.character import PlayerCharacter, Trait
        from src.backend.models.game_state import GameState
        from src.backend.models.i18n import LocalizedString

        settings = get_settings()

        if not settings.is_new_format():
            return ReloadAgentsResponse(
                success=False,
                message="Settings format is outdated. Please restart the backend.",
            )

        if settings.agents is None:
            return ReloadAgentsResponse(
                success=False,
                message="Agents not configured. Please configure agents in settings.",
            )

        validation_errors = settings.validate_agent_provider_references()
        if validation_errors:
            return ReloadAgentsResponse(
                success=False,
                message=f"Configuration errors: {'; '.join(validation_errors)}",
            )

        if main_module.world_pack_loader is None:
            return ReloadAgentsResponse(
                success=False,
                message="World pack loader not initialized. Please restart the backend.",
            )

        default_pack_id = "demo_pack"
        world_pack = main_module.world_pack_loader.load(default_pack_id)
        starting_location_id: str = "unknown"
        active_npc_ids: list[str] = []

        for loc_id, loc in world_pack.locations.items():
            if "starting_area" in loc.tags:
                starting_location_id = loc_id
                break

        if starting_location_id == "unknown" and world_pack.locations:
            starting_location_id = next(iter(world_pack.locations.keys()))

        if starting_location_id in world_pack.locations:
            active_npc_ids = world_pack.locations[starting_location_id].present_npc_ids or []

        llm = create_llm_from_settings("gm")

        default_character = PlayerCharacter(
            name="玩家",
            concept=LocalizedString(
                cn="冒险者",
                en="Adventurer",
            ),
            traits=[
                Trait(
                    name=LocalizedString(cn="勇敢", en="Brave"),
                    description=LocalizedString(
                        cn="面对困难不退缩",
                        en="Faces difficulties without retreat",
                    ),
                    positive_aspect=LocalizedString(cn="勇敢", en="Brave"),
                    negative_aspect=LocalizedString(cn="鲁莽", en="Rash"),
                )
            ],
            tags=[],
        )

        game_state = GameState(
            session_id="default-session",
            world_pack_id=default_pack_id,
            player=default_character,
            current_location=starting_location_id,
            active_npc_ids=active_npc_ids,
        )

        lore_agent = LoreAgent(
            llm=llm,
            world_pack_loader=main_module.world_pack_loader,
            vector_store=main_module.vector_store,
        )

        sub_agents: dict = {
            "lore": lore_agent,
        }

        for npc_id in active_npc_ids:
            npc_data = world_pack.get_npc(npc_id)
            if npc_data:
                npc_agent = NPCAgent(llm=llm, vector_store=main_module.vector_store)
                agent_key = f"npc_{npc_id}"
                sub_agents[agent_key] = npc_agent

        main_module.gm_agent = GMAgent(
            llm=llm,
            sub_agents=sub_agents,
            game_state=game_state,
            world_pack_loader=main_module.world_pack_loader,
            vector_store=main_module.vector_store,
        )

        provider_info = f"{settings.agents.gm.provider_id}/{settings.agents.gm.model}"

        return ReloadAgentsResponse(
            success=True,
            message=f"Agents reloaded successfully. Using provider: {provider_info}",
        )

    except ImportError as exc:
        return ReloadAgentsResponse(
            success=False,
            message=f"Failed to import required modules: {exc}",
        )
    except Exception as exc:
        return ReloadAgentsResponse(
            success=False,
            message=f"Failed to reload agents: {exc}",
        )
