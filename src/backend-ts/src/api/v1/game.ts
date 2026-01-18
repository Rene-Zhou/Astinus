import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";
import { v4 as uuidv4 } from "uuid";
import { getAppContext } from "../../index";
import type { GameState, PlayerCharacter, Trait } from "../../schemas";
import { GMAgent } from "../../agents/gm";
import { NPCAgent } from "../../agents/npc";
import { mockLanguageModel } from "../../lib/mock-llm";

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

      const lang = "cn";
      const locationName =
        startingLocation.name[lang] || startingLocation.name.en || startingLocationId;
      const locationDesc =
        startingLocation.description?.[lang] ||
        startingLocation.description?.en ||
        "";

      const worldInfo = {
        pack_id: request.world_pack_id,
        name: worldPack.info.name[lang] || worldPack.info.name.en,
        description:
          worldPack.info.description?.[lang] ||
          worldPack.info.description?.en ||
          "",
        author: worldPack.info.author || "Unknown",
      };

      const startingScene = {
        location_id: startingLocationId,
        location_name: locationName,
        location_description: locationDesc,
        present_npcs: activeNpcIds.map((npcId: any) => {
          const npc = Object.values(worldPack.npcs || {}).find((n: any) => n.id === npcId);
          if (npc) {
            return {
              id: npc.id,
              name: npc.soul.name,
              description:
                npc.soul.description[lang] || npc.soul.description.en || "",
            };
          }
          return { id: npcId, name: npcId, description: "" };
        }),
        visible_items: startingLocation.visible_items || [],
      };

      const message =
        lang === "cn"
          ? `游戏开始！欢迎来到${locationName}。`
          : `Game started! Welcome to ${locationName}.`;

      gameState.messages.push({
        role: "assistant",
        content: message,
        timestamp: new Date().toISOString(),
        turn: 0,
      });

      // Initialize Agents with Mock LLM
      // In a real implementation, this would use a configured LanguageModel based on settings
      const npcAgent = new NPCAgent(mockLanguageModel as any);
      const subAgents = {
        npc: npcAgent,
      };

      ctx.gmAgent = new GMAgent(
        mockLanguageModel as any,
        subAgents,
        gameState,
        ctx.loreService
      );

      return c.json({
        session_id: sessionId,
        player: playerCharacter,
        game_state: gameState,
        world_info: worldInfo,
        starting_scene: startingScene,
        message: message,
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
      const response = await ctx.gmAgent.process({
        player_input: request.action,
        lang: request.lang,
      });

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
    phase: gameState.current_phase,
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
    phase: gameState.current_phase,
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
