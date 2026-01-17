import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";
import { v4 as uuidv4 } from "uuid";
import { getAppContext } from "../../index";
import type { GameState, PlayerCharacter, Trait, Message } from "../../schemas";

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
        startingLocationId = Object.keys(worldPack.locations)[0];
        startingLocation = worldPack.locations[startingLocationId];
      }

      if (!startingLocation) {
        return c.json({ error: "World pack has no locations defined" }, 400);
      }

      const activeNpcIds = startingLocation.present_npc_ids || [];

      let playerCharacter: PlayerCharacter;

      if (request.preset_character_id) {
        const preset = worldPack.preset_characters?.find(
          (p) => p.id === request.preset_character_id
        );
        if (!preset) {
          const availableIds = worldPack.preset_characters?.map((p) => p.id) || [];
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
          name: { cn: "冒险者", en: "Adventurer" },
          concept: { cn: "冒险者", en: "Adventurer" },
          traits: [defaultTrait],
          tags: [],
        };
      }

      const gameState: GameState = {
        session_id: sessionId,
        world_pack_id: request.world_pack_id,
        phase: "waiting_input",
        turn_number: 0,
        current_location: startingLocationId,
        active_npc_ids: activeNpcIds,
        character: playerCharacter,
        messages: [],
        flags: {},
        react_pending_state: null,
      };

      const lang = "cn";
      const locationName =
        startingLocation.name[lang] || startingLocation.name.en || startingLocationId;
      const locationDesc =
        startingLocation.description?.[lang] ||
        startingLocation.description?.en ||
        "";

      const worldInfo = {
        pack_id: worldPack.pack_info.id,
        name: worldPack.pack_info.name[lang] || worldPack.pack_info.name.en,
        description:
          worldPack.pack_info.description?.[lang] ||
          worldPack.pack_info.description?.en ||
          "",
        author: worldPack.pack_info.author || "Unknown",
      };

      const startingScene = {
        location_id: startingLocationId,
        location_name: locationName,
        location_description: locationDesc,
        present_npcs: activeNpcIds.map((npcId) => {
          const npc = worldPack.npcs?.find((n) => n.id === npcId);
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

      return c.json({
        session_id: sessionId,
        player: playerCharacter,
        game_state: gameState,
        world_info: worldInfo,
        starting_scene: startingScene,
        message:
          lang === "cn"
            ? `游戏开始！欢迎来到${locationName}。`
            : `Game started! Welcome to ${locationName}.`,
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

gameRouter.get("/game/state/:sessionId", async (c) => {
  const sessionId = c.req.param("sessionId");
  const ctx = getAppContext();

  if (!ctx.gmAgent) {
    return c.json({ error: "Game engine not initialized" }, 503);
  }

  const gameState = ctx.gmAgent.gameState;

  if (gameState.session_id !== sessionId) {
    return c.json({ error: "Session not found" }, 404);
  }

  return c.json({
    session_id: gameState.session_id,
    phase: gameState.phase,
    turn_number: gameState.turn_number,
    current_location: gameState.current_location,
    active_npc_ids: gameState.active_npc_ids,
    character: gameState.character,
  });
});

gameRouter.get("/world-packs", async (c) => {
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

gameRouter.get("/world-packs/:packId", async (c) => {
  const packId = c.req.param("packId");
  const ctx = getAppContext();

  if (!ctx.worldPackLoader) {
    return c.json({ error: "World pack loader not initialized" }, 503);
  }

  try {
    const worldPack = await ctx.worldPackLoader.load(packId);

    const lang = (c.req.query("lang") as "cn" | "en") || "cn";

    return c.json({
      id: worldPack.pack_info.id,
      name: worldPack.pack_info.name[lang] || worldPack.pack_info.name.en,
      description:
        worldPack.pack_info.description?.[lang] ||
        worldPack.pack_info.description?.en ||
        "",
      author: worldPack.pack_info.author,
      version: worldPack.pack_info.version,
      locations: Object.keys(worldPack.locations).length,
      npcs: worldPack.npcs?.length || 0,
      lore_entries: worldPack.lore?.length || 0,
      preset_characters: worldPack.preset_characters?.length || 0,
    });
  } catch (error) {
    return c.json({ error: `World pack not found: ${packId}` }, 404);
  }
});
