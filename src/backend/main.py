"""
FastAPI application entry point for Astinus backend.

Provides REST API and WebSocket endpoints for the TTRPG game engine.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.backend.agents.gm import GMAgent
from src.backend.agents.rule import RuleAgent
from src.backend.api import websockets
from src.backend.api.v1 import game
from src.backend.core.config import get_settings
from src.backend.core.llm_provider import LLMConfig, LLMProvider, get_llm
from src.backend.models.character import PlayerCharacter, Trait
from src.backend.models.game_state import GameState
from src.backend.models.i18n import LocalizedString

# Global GM Agent instance (managed by lifespan)
gm_agent: GMAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management.

    Initializes agents on startup and cleans up on shutdown.
    """
    global gm_agent

    # Startup
    print("🚀 Starting Astinus backend...")

    # Load settings from config file
    settings = get_settings()

    # Initialize LLM using settings
    try:
        # Get API key for the configured provider
        api_key = None
        if settings.llm.provider == "openai":
            api_key = settings.llm.api_keys.openai or None
        elif settings.llm.provider == "anthropic":
            api_key = settings.llm.api_keys.anthropic or None
        elif settings.llm.provider == "google":
            api_key = settings.llm.api_keys.google or None

        llm_config = LLMConfig(
            provider=LLMProvider(settings.llm.provider),
            model=settings.llm.models.gm,
            temperature=settings.llm.temperature,
            max_tokens=settings.llm.max_tokens,
            api_key=api_key,
        )
        llm = get_llm(llm_config)
        print(f"✅ LLM initialized: {settings.llm.provider}/{llm_config.model}")
    except Exception as exc:
        print(f"❌ Failed to initialize LLM: {exc}")
        raise

    # Initialize agents
    try:
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
            world_pack_id="demo-pack",
            player=default_character,
            current_location="起始地点",
            active_npc_ids=[],
        )

        # Create sub-agents
        rule_agent = RuleAgent(llm)

        # Create GM Agent (central orchestrator)
        gm_agent = GMAgent(
            llm=llm,
            sub_agents={"rule": rule_agent},
            game_state=game_state,
        )

        print("✅ Agents initialized")
    except Exception as exc:
        print(f"❌ Failed to initialize agents: {exc}")
        raise

    print("✅ Astinus backend started successfully")
    print("📝 API documentation: http://localhost:8000/docs")

    yield

    # Shutdown
    print("\n🛑 Shutting down Astinus backend...")
    gm_agent = None
    print("✅ Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Astinus TTRPG Engine",
    description="AI-driven narrative TTRPG engine API",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(game.router)
app.include_router(websockets.router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Astinus TTRPG Engine",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns the status of the backend and its dependencies.
    """
    status_info = {
        "status": "healthy",
        "version": "0.1.0",
        "agents": {
            "gm_agent": gm_agent is not None,
            "rule_agent": gm_agent is not None if gm_agent else False,
        },
    }

    # Check if all components are healthy
    if gm_agent is None:
        status_info["status"] = "unhealthy"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=status_info,
        )

    return status_info


if __name__ == "__main__":
    import uvicorn

    print("Starting Astinus backend server...")
    uvicorn.run(
        "src.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
