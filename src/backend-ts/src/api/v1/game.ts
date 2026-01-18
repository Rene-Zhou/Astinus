import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";
import { v4 as uuidv4 } from "uuid";
import { getAppContext } from "../../index";
import type { GameState, PlayerCharacter, Trait } from "../../schemas";
import { GMAgent } from "../../agents/gm";
import { NPCAgent } from "../../agents/npc";
import { ConfigService } from "../../services/config";
import { LLMFactory } from "../../lib/llm-factory";

const NewGameRequestSchema = z.object({
  world_pack_id: z.string().default("demo_pack"),
  player_name: z.string().default("玩家"),
  preset_character_id: z.string().optional(),
});

const PlayerActionRequestSchema = z.object({
  session_id: z.string(),
  action: z.string(),
  lang: z.enum(["cn", "en"]).default("cn"),
});

const DiceResultRequestSchema = z.object({
  session_id: z.string(),
  rolls: z.array(z.number()),
  total: z.number(),
  outcome: z.string(),
  modifier: z.number().default(0),
});

export const gameRouter = new Hono();

gameRouter.post(
  "/game/new",
  zValidator("json", NewGameRequestSchema),
  async (c) => {
    const request = c.req.valid("json");
    const ctx = getAppContext();

    if (!ctx.worldPackLoader) {
      return c.json(
        { error: "World pack loader not initialized" },
        503
      );
    }

    try {
      const sessionId = uuidv4();

      let worldPack;
      try {
        worldPack = await ctx.worldPackLoader.load(request.world_pack_id);
      } catch (error) {
        const available = await ctx.worldPackLoader.listAvailable();
        return c.json(
          {
            error: `World pack not found: ${request.world_pack_id}. Available: ${available.join(", ")}`,
          },
          404
        );
      }

      let startingLocationId: string | null = null;
      let startingLocation = null;

      for (const [locId, loc] of Object.entries(worldPack.locations)) {
        if (loc.tags?.includes("starting_area")) {
          startingLocationId = locId;
          startingLocation = loc;
          break;
        }
      }

      if (!startingLocationId && Object.keys(worldPack.locations).length > 0) {
        startingLocationId = Object.keys(worldPack.locations)[0] || null;
        startingLocation = startingLocationId ? worldPack.locations[startingLocationId] : null;
      }

      if (!startingLocation) {
        return c.json({ error: "World pack has no locations defined" }, 400);
      }

      const activeNpcIds = startingLocation.present_npc_ids || [];
      const config = ConfigService.getInstance().get();
      
      // Initialize Agents - Require LLM configuration
      if (!config.agents || !config.providers || config.providers.length === 0) {
        return c.json(
          { error: "Game engine not initialized. Configure LLM settings first." },
          503
        );
      }

      let gmModel, npcModel;
      try {
        gmModel = LLMFactory.createModel(config.agents.gm, config.providers);
        npcModel = LLMFactory.createModel(config.agents.npc, config.providers);
        console.log("🤖 Agents initialized with real LLM configuration");
      } catch (err) {
        console.error("❌ Failed to create LLM models:", err);
        return c.json(
          { error: `Failed to initialize AI models: ${err}` },
          503
        );
      }

      let playerCharacter: PlayerCharacter;

      if (request.preset_character_id) {
        const preset = worldPack.preset_characters?.find(
          (p: any) => p.id === request.preset_character_id
        );
        if (!preset) {
          const availableIds = worldPack.preset_characters?.map((p: any) => p.id) || [];
          return c.json(
            {
              error: `Preset character not found: ${request.preset_character_id}. Available: ${availableIds.join(", ")}`,
            },
            400
          );
        }
        playerCharacter = {
          name: preset.name,
          concept: preset.concept,
          traits: preset.traits,
          fate_points: 3,
          tags: [],
        };
      } else {
        const defaultTrait: Trait = {
          name: { cn: "勇敢", en: "Brave" },
          description: {
            cn: "面对困难不退缩",
            en: "Faces difficulties without retreat",
          },
          positive_aspect: { cn: "勇敢", en: "Brave" },
          negative_aspect: { cn: "鲁莽", en: "Rash" },
        };

        playerCharacter = {
          name: request.player_name || "冒险者",
          concept: { cn: "冒险者", en: "Adventurer" },
          traits: [defaultTrait],
          fate_points: 3,
          tags: [],
        };
      }

      const gameState: GameState = {
        session_id: sessionId,
        player_name: request.player_name || "玩家",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        player: playerCharacter,
        current_phase: "waiting_input",
        next_agent: null,
        world_pack_id: request.world_pack_id,
        current_location: startingLocationId || "",
        active_npc_ids: activeNpcIds,
        discovered_items: [],
        flags: [],
        game_time: "00:00",
        turn_count: 0,
        messages: [],
        temp_context: {},
        last_check_result: null,
        react_pending_state: null,
        language: "cn",
      };

      const worldInfo: any = {
        id: request.world_pack_id,
        name: worldPack.info.name,
        description: worldPack.info.description,
        version: worldPack.info.version,
        author: worldPack.info.author,
      };

      if (worldPack.info.setting) {
        worldInfo.setting = worldPack.info.setting;
      }
      if (worldPack.info.player_hook) {
        worldInfo.player_hook = worldPack.info.player_hook;
      }

      const startingScene = {
        location_id: startingLocationId,
        location_name: startingLocation.name,
        description: startingLocation.description, // Aligned with Python backend
        items: startingLocation.items || [],
        connected_locations: [], // Populated below
        npcs: [], // Populated below
        atmosphere: startingLocation.atmosphere, // Add atmosphere if present
      };

      // Populate connected locations
      if (startingLocation.connected_locations) {
        for (const locId of startingLocation.connected_locations) {
          const connectedLoc = worldPack.locations[locId];
          if (connectedLoc) {
            (startingScene.connected_locations as any[]).push({
              id: locId,
              name: connectedLoc.name, // Pass raw LocalizedString object
            });
          }
        }
      }

      // Populate NPCs - Hide names to prevent metagaming
      for (const npcId of activeNpcIds) {
        const npc = Object.values(worldPack.npcs || {}).find((n: any) => n.id === npcId);
        if (npc) {
            const npcInfo: any = { id: npcId };
            // Use appearance if available, otherwise fallback to description
            const soul = (npc as any).soul;
            if (soul.appearance) {
                npcInfo.appearance = soul.appearance;
            } else {
                // Fallback: use description (Python sends full description model_dump)
                npcInfo.appearance = soul.description;
            }
            (startingScene.npcs as any[]).push(npcInfo);
        }
      }

      // NO message push to gameState.messages - Python backend starts empty

      const npcMaxTokens = config.agents?.npc?.max_tokens;
      const gmMaxTokens = config.agents?.gm?.max_tokens;

      const npcAgent = new NPCAgent(npcModel as any, npcMaxTokens);
      const subAgents = {
        npc: npcAgent,
      };

      ctx.gmAgent = new GMAgent(
        gmModel as any,
        subAgents,
        gameState,
        ctx.loreService,
        ctx.worldPackLoader,
        gmMaxTokens
      );

      return c.json({
        session_id: sessionId,
        player: playerCharacter,
        game_state: {
            ...gameState,
            current_phase: gameState.current_phase,
            turn_count: gameState.turn_count,
            active_npc_ids: activeNpcIds,
        },
        world_info: worldInfo,
        starting_scene: startingScene,
        message: "Game session created successfully",
      });
    } catch (error) {
      console.error("Error starting new game:", error);
      return c.json(
        { error: `Failed to start game: ${error}` },
        500
      );
    }
  }
);

gameRouter.post(
  "/game/action",
  zValidator("json", PlayerActionRequestSchema),
  async (c) => {
    const request = c.req.valid("json");
    const ctx = getAppContext();

    if (!ctx.gmAgent) {
      return c.json(
        {
          error: "Game engine not initialized. Configure LLM settings first.",
        },
        503
      );
    }

    try {
      console.log(`[GameAPI] Received action: ${request.action}`);
      const response = await ctx.gmAgent.process({
        player_input: request.action,
        lang: request.lang,
      });
      console.log(`[GameAPI] Process finished. Success: ${response.success}`);

      return c.json({
        success: response.success,
        content: response.content,
        metadata: response.metadata,
        error: response.error,
      });
    } catch (error) {
      console.error("Error processing action:", error);
      return c.json(
        { error: `Failed to process action: ${error}` },
        500
      );
    }
  }
);

gameRouter.post(
  "/game/dice-result",
  zValidator("json", DiceResultRequestSchema),
  async (c) => {
    const request = c.req.valid("json");
    const ctx = getAppContext();

    if (!ctx.gmAgent) {
      return c.json(
        { error: "Game engine not initialized" },
        503
      );
    }

    try {
      const response = await ctx.gmAgent.resumeAfterDice(
        {
          rolls: request.rolls,
          total: request.total,
          outcome: request.outcome,
          modifier: request.modifier,
        },
        "cn"
      );

      return c.json({
        success: response.success,
        content: response.content,
        metadata: response.metadata,
        error: response.error,
      });
    } catch (error) {
      console.error("Error processing dice result:", error);
      return c.json(
        { error: `Failed to process dice result: ${error}` },
        500
      );
    }
  }
);

gameRouter.get("/game/state", async (c) => {
  const ctx = getAppContext();

  if (!ctx.gmAgent) {
    return c.json({ error: "Game engine not initialized" }, 503);
  }

  const gameState = ctx.gmAgent.getGameState();

  return c.json({
    session_id: gameState.session_id,
    current_phase: gameState.current_phase, // Aligned with Python backend (was 'phase')
    turn_number: gameState.turn_count,
    current_location: gameState.current_location,
    active_npc_ids: gameState.active_npc_ids,
    player: gameState.player,
  });
});

gameRouter.get("/game/state/:sessionId", async (c) => {
  const sessionId = c.req.param("sessionId");
  const ctx = getAppContext();

  if (!ctx.gmAgent) {
    return c.json({ error: "Game engine not initialized" }, 503);
  }

  const gameState = ctx.gmAgent.getGameState();

  if (gameState.session_id !== sessionId) {
    return c.json({ error: "Session not found" }, 404);
  }

  return c.json({
    session_id: gameState.session_id,
    current_phase: gameState.current_phase, // Aligned with Python backend (was 'phase')
    turn_number: gameState.turn_count,
    current_location: gameState.current_location,
    active_npc_ids: gameState.active_npc_ids,
    player: gameState.player,
  });
});

  gameRouter.get("/game/world-packs", async (c) => {
  const ctx = getAppContext();

  if (!ctx.worldPackLoader) {
    return c.json({ error: "World pack loader not initialized" }, 503);
  }

  try {
    const available = await ctx.worldPackLoader.listAvailable();
    return c.json({ packs: available });
  } catch (error) {
    return c.json({ error: `Failed to list world packs: ${error}` }, 500);
  }
});

  gameRouter.get("/game/world-pack/:packId", async (c) => {
  const packId = c.req.param("packId");
  const ctx = getAppContext();

  if (!ctx.worldPackLoader) {
    return c.json({ error: "World pack loader not initialized" }, 503);
  }

  try {
    const worldPack = await ctx.worldPackLoader.load(packId);

    const locations = Object.entries(worldPack.locations).map(([id, location]) => ({
      id,
      name: location.name,
      tags: location.tags || [],
    }));

    const npcs = Object.entries(worldPack.npcs || {}).map(([id, npc]) => ({
      id,
      name: npc.soul.name,
      location: npc.body?.location || "unknown",
    }));

    return c.json({
      id: packId,
      info: {
        name: worldPack.info.name,
        description: worldPack.info.description,
        version: worldPack.info.version,
        author: worldPack.info.author,
        setting: worldPack.info.setting,
        player_hook: worldPack.info.player_hook,
      },
      summary: {
        locations: Object.keys(worldPack.locations).length,
        npcs: Object.keys(worldPack.npcs || {}).length,
        lore_entries: Object.keys(worldPack.entries).length,
        preset_characters: worldPack.preset_characters?.length || 0,
      },
      locations,
      npcs,
      preset_characters: worldPack.preset_characters || [],
    });
  } catch (error) {
    return c.json({ error: `World pack not found: ${packId}` }, 404);
  }
});
