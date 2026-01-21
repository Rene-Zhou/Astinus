import { Hono } from 'hono';
import { zValidator } from '@hono/zod-validator';
import { z } from 'zod';
import { getAppContext } from '../../index';
import { getSaveService } from '../../services/save';
import { GMAgent } from '../../agents/gm';
import { NPCAgent } from '../../agents/npc';
import { ConfigService } from '../../services/config';
import { LLMFactory } from '../../lib/llm-factory';

const CreateSaveRequestSchema = z.object({
  slot_name: z.string().min(1).max(128),
  description: z.string().max(512).optional(),
  overwrite: z.boolean().optional().default(false),
});

const LoadSaveRequestSchema = z.object({
  reconnect_websocket: z.boolean().optional().default(true),
});

export const saveRouter = new Hono();

saveRouter.get('/', async (c) => {
  const saveService = getSaveService();

  try {
    const saves = await saveService.listSaves();

    return c.json({
      saves: saves.map((s) => ({
        id: s.id,
        slot_name: s.slotName,
        description: s.description,
        world_pack_id: s.worldPackId,
        current_location: s.currentLocation,
        turn_count: s.turnCount,
        player_name: s.playerName,
        character_name: s.characterName,
        last_message: s.lastMessage,
        is_auto_save: s.isAutoSave,
        created_at: s.createdAt.toISOString(),
        updated_at: s.updatedAt.toISOString(),
      })),
    });
  } catch (error) {
    console.error('[SaveAPI] Failed to list saves:', error);
    return c.json({ error: `Failed to list saves: ${error}` }, 500);
  }
});

saveRouter.post('/', zValidator('json', CreateSaveRequestSchema), async (c) => {
  const request = c.req.valid('json');
  const ctx = getAppContext();

  if (!ctx.gmAgent) {
    return c.json({ error: 'No active game session to save' }, 400);
  }

  const saveService = getSaveService();
  const gameState = ctx.gmAgent.getGameState();

  try {
    const result = await saveService.createSave(gameState, {
      slotName: request.slot_name,
      description: request.description,
      overwrite: request.overwrite,
    });

    if (!result.success) {
      if (result.exists) {
        return c.json(
          {
            error: result.error,
            exists: true,
            existing_id: result.existingId,
          },
          409
        );
      }
      return c.json({ error: result.error }, 400);
    }

    const save = result.save!;
    return c.json({
      success: true,
      save: {
        id: save.id,
        slot_name: save.slotName,
        description: save.description,
        world_pack_id: save.worldPackId,
        current_location: save.currentLocation,
        turn_count: save.turnCount,
        player_name: save.playerName,
        character_name: save.characterName,
        last_message: save.lastMessage,
        is_auto_save: save.isAutoSave,
        created_at: save.createdAt.toISOString(),
        updated_at: save.updatedAt.toISOString(),
      },
    });
  } catch (error) {
    console.error('[SaveAPI] Failed to create save:', error);
    return c.json({ error: `Failed to create save: ${error}` }, 500);
  }
});

saveRouter.post('/:id/load', zValidator('json', LoadSaveRequestSchema), async (c) => {
  const saveId = parseInt(c.req.param('id'), 10);
  if (isNaN(saveId)) {
    return c.json({ error: 'Invalid save ID' }, 400);
  }

  const ctx = getAppContext();
  const saveService = getSaveService();

  try {
    const result = await saveService.loadSave(saveId);

    if (!result.success || !result.gameState) {
      return c.json({ error: result.error || 'Failed to load save' }, 404);
    }

    const gameState = result.gameState;
    const config = ConfigService.getInstance().get();

    if (!config.agents || !config.providers || config.providers.length === 0) {
      return c.json({ error: 'LLM configuration required to restore game' }, 503);
    }

    let gmModel, npcModel;
    try {
      gmModel = LLMFactory.createModel(config.agents.gm, config.providers);
      npcModel = LLMFactory.createModel(config.agents.npc, config.providers);
    } catch (err) {
      console.error('[SaveAPI] Failed to create LLM models:', err);
      return c.json({ error: `Failed to initialize AI models: ${err}` }, 503);
    }

    const npcMaxTokens = config.agents?.npc?.max_tokens;
    const npcAgent = new NPCAgent(npcModel as any, ctx.vectorStore || undefined, npcMaxTokens);
    const subAgents = { npc: npcAgent };

    ctx.gmAgent = new GMAgent(
      gmModel as any,
      subAgents,
      gameState,
      ctx.loreService,
      ctx.worldPackLoader || undefined,
      ctx.vectorStore || undefined
    );

    let worldInfo = null;
    if (ctx.worldPackLoader) {
      try {
        const worldPack = await ctx.worldPackLoader.load(gameState.world_pack_id);
        worldInfo = {
          id: gameState.world_pack_id,
          name: worldPack.info.name,
          description: worldPack.info.description,
          version: worldPack.info.version,
          author: worldPack.info.author,
          setting: worldPack.info.setting,
          player_hook: worldPack.info.player_hook,
        };
      } catch (err) {
        console.error('[SaveAPI] Failed to load world pack:', err);
      }
    }

    return c.json({
      success: true,
      session_id: gameState.session_id,
      game_state: {
        session_id: gameState.session_id,
        world_pack_id: gameState.world_pack_id,
        player_name: gameState.player_name,
        player: gameState.player,
        current_location: gameState.current_location,
        active_npc_ids: gameState.active_npc_ids,
        current_phase: gameState.current_phase,
        turn_count: gameState.turn_count,
        messages: gameState.messages,
      },
      world_info: worldInfo,
    });
  } catch (error) {
    console.error('[SaveAPI] Failed to load save:', error);
    return c.json({ error: `Failed to load save: ${error}` }, 500);
  }
});

saveRouter.delete('/:id', async (c) => {
  const saveId = parseInt(c.req.param('id'), 10);
  if (isNaN(saveId)) {
    return c.json({ error: 'Invalid save ID' }, 400);
  }

  const saveService = getSaveService();

  try {
    const deleted = await saveService.deleteSave(saveId);

    if (!deleted) {
      return c.json({ error: 'Save not found' }, 404);
    }

    return c.json({ success: true });
  } catch (error) {
    console.error('[SaveAPI] Failed to delete save:', error);
    return c.json({ error: `Failed to delete save: ${error}` }, 500);
  }
});
