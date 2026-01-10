"""
FastAPI application entry point for Astinus backend.

Provides REST API and WebSocket endpoints for the TTRPG game engine.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.backend.agents.gm import GMAgent
from src.backend.agents.lore import LoreAgent
from src.backend.agents.npc import NPCAgent
from src.backend.agents.rule import RuleAgent
from src.backend.api import websockets
from src.backend.api.v1 import game
from src.backend.core.config import get_settings
from src.backend.core.llm_provider import LLMConfig, LLMProvider, get_llm
from src.backend.models.character import PlayerCharacter, Trait
from src.backend.models.game_state import GameState
from src.backend.models.i18n import LocalizedString
from src.backend.services.game_logger import init_game_logger
from src.backend.services.vector_store import VectorStoreService
from src.backend.services.world import WorldPackLoader

# Global instances (managed by lifespan)
gm_agent: GMAgent | None = None
world_pack_loader: WorldPackLoader | None = None
vector_store: VectorStoreService | None = None


def get_world_pack_loader() -> WorldPackLoader | None:
    """Get the global world pack loader instance."""
    return world_pack_loader


def get_vector_store() -> VectorStoreService | None:
    """Get the global vector store instance."""
    return vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan management.

    Initializes agents on startup and cleans up on shutdown.
    """
    global gm_agent, world_pack_loader, vector_store

    # Startup
    print("🚀 Starting Astinus backend...")

    init_game_logger(console_output=True, file_output=True)
    print("✅ Debug logger initialized (logs/)")

    # Load settings from config file
    settings = get_settings()

    # Initialize Vector Store
    try:
        vector_store_path = Path("data/vector_store/chroma_db")
        vector_store_path.parent.mkdir(parents=True, exist_ok=True)
        vector_store = VectorStoreService(persist_directory=str(vector_store_path))
        print("✅ Vector store initialized")
    except Exception as exc:
        print(f"⚠️ Vector store initialization failed (continuing without): {exc}")
        vector_store = None

    # Initialize World Pack Loader
    try:
        packs_dir = Path("data/packs")
        world_pack_loader = WorldPackLoader(
            packs_dir=packs_dir,
            vector_store=vector_store,
            enable_vector_indexing=vector_store is not None,
        )
        print(f"✅ World pack loader initialized (packs: {world_pack_loader.list_available()})")
    except Exception as exc:
        print(f"❌ Failed to initialize world pack loader: {exc}")
        raise

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

    # Load default world pack and get starting location
    try:
        default_pack_id = "demo_pack"
        world_pack = world_pack_loader.load(default_pack_id)

        # Find starting location (look for "starting_area" tag or use first location)
        starting_location_id = None
        starting_location = None
        for loc_id, loc in world_pack.locations.items():
            if "starting_area" in loc.tags:
                starting_location_id = loc_id
                starting_location = loc
                break

        # Fallback to first location if no starting_area tag found
        if starting_location_id is None and world_pack.locations:
            starting_location_id = next(iter(world_pack.locations.keys()))
            starting_location = world_pack.locations[starting_location_id]

        if starting_location is None:
            starting_location_id = "unknown"
            active_npc_ids = []
        else:
            active_npc_ids = starting_location.present_npc_ids or []

        print(f"✅ World pack loaded: {default_pack_id}")
        print(f"   Starting location: {starting_location_id}")
        print(f"   Active NPCs: {active_npc_ids}")

    except Exception as exc:
        print(f"⚠️ Failed to load default world pack: {exc}")
        starting_location_id = "unknown"
        active_npc_ids = []

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
            world_pack_id=default_pack_id,
            player=default_character,
            current_location=starting_location_id,
            active_npc_ids=active_npc_ids,
        )

        # Create sub-agents
        rule_agent = RuleAgent(llm)
        lore_agent = LoreAgent(
            llm=llm,
            world_pack_loader=world_pack_loader,
            vector_store=vector_store,
        )

        # Build sub_agents dictionary with rule and lore
        sub_agents: dict = {
            "rule": rule_agent,
            "lore": lore_agent,
        }

        # Register NPC Agents for active NPCs in the scene
        for npc_id in active_npc_ids:
            npc_data = world_pack.get_npc(npc_id)
            if npc_data:
                npc_agent = NPCAgent(llm=llm, vector_store=vector_store)
                # Register with format npc_{npc_id} (e.g., npc_old_guard)
                agent_key = f"npc_{npc_id}"
                sub_agents[agent_key] = npc_agent
                print(f"   Registered NPC agent: {agent_key} ({npc_data.soul.name})")

        # Create GM Agent (central orchestrator)
        gm_agent = GMAgent(
            llm=llm,
            sub_agents=sub_agents,
            game_state=game_state,
            world_pack_loader=world_pack_loader,
            vector_store=vector_store,
        )

        print("✅ Agents initialized")
        print(f"   Sub-agents: {list(gm_agent.sub_agents.keys())}")
    except Exception as exc:
        print(f"❌ Failed to initialize agents: {exc}")
        raise

    print("✅ Astinus backend started successfully")
    print("📝 API documentation: http://localhost:8000/docs")

    yield

    # Shutdown
    print("\n🛑 Shutting down Astinus backend...")
    gm_agent = None
    world_pack_loader = None
    vector_store = None
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
            "rule_agent": gm_agent is not None and "rule" in gm_agent.sub_agents
            if gm_agent
            else False,
            "lore_agent": gm_agent is not None and "lore" in gm_agent.sub_agents
            if gm_agent
            else False,
        },
        "services": {
            "world_pack_loader": world_pack_loader is not None,
            "vector_store": vector_store is not None,
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
