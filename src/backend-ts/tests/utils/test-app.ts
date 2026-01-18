import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { zValidator } from '@hono/zod-validator';
import { z } from 'zod';
import {
  createMockGMAgent,
  createMockWorldPackLoader,
  createMockLoreService,
  createMockGameState,
} from '../mocks/gm-agent.mock';

export interface AppContext {
  gmAgent: ReturnType<typeof createMockGMAgent> | null;
  worldPackLoader: ReturnType<typeof createMockWorldPackLoader> | null;
  vectorStore: null;
  loreService: ReturnType<typeof createMockLoreService> | null;
}

export interface TestAppOptions {
  withGMAgent?: boolean;
  withWorldPackLoader?: boolean;
  withLoreService?: boolean;
  gameStateOverrides?: Parameters<typeof createMockGameState>[0];
}

const UpdateSettingsRequestSchema = z.object({
  providers: z.array(z.object({
    id: z.string(),
    name: z.string(),
    type: z.string(),
    api_key: z.string().default(''),
    base_url: z.string().optional(),
  })).optional(),
  agents: z.object({
    gm: z.object({
      provider_id: z.string(),
      model: z.string(),
      temperature: z.number().min(0).max(2).default(0.7),
      max_tokens: z.number().min(1).default(2000),
    }).optional(),
    npc: z.object({
      provider_id: z.string(),
      model: z.string(),
      temperature: z.number().min(0).max(2).default(0.7),
      max_tokens: z.number().min(1).default(2000),
    }).optional(),
    lore: z.object({
      provider_id: z.string(),
      model: z.string(),
      temperature: z.number().min(0).max(2).default(0.7),
      max_tokens: z.number().min(1).default(2000),
    }).optional(),
  }).optional(),
});

const TestConnectionRequestSchema = z.object({
  provider_id: z.string(),
});

export function createTestApp(options: TestAppOptions = {}) {
  const {
    withGMAgent = true,
    withWorldPackLoader = true,
    withLoreService = false,
  } = options;

  const mockGameState = createMockGameState(options.gameStateOverrides);
  const mockGMAgent = withGMAgent ? createMockGMAgent(mockGameState) : null;
  const mockWorldPackLoader = withWorldPackLoader
    ? createMockWorldPackLoader()
    : null;
  const mockLoreService = withLoreService ? createMockLoreService() : null;

  const appContext: AppContext = {
    gmAgent: mockGMAgent,
    worldPackLoader: mockWorldPackLoader,
    vectorStore: null,
    loreService: mockLoreService,
  };

  const app = new Hono();

  app.use('*', cors());

  app.get('/', (c) => {
    return c.json({
      name: 'Astinus TTRPG Engine',
      version: '0.1.0',
      status: 'running',
      runtime: 'Node.js + Hono',
      docs: '/docs',
      openapi: '/openapi.json',
    });
  });

  app.get('/health', (c) => {
    const statusInfo = {
      status: appContext.gmAgent ? 'healthy' : 'unhealthy',
      version: '0.1.0',
      agents: {
        gm_agent: appContext.gmAgent !== null,
        rule_agent: appContext.gmAgent !== null,
      },
      services: {
        world_pack_loader: appContext.worldPackLoader !== null,
        vector_store: appContext.vectorStore !== null,
        lore_service: appContext.loreService !== null,
      },
    };

    if (!appContext.gmAgent) {
      return c.json(statusInfo, 503);
    }

    return c.json(statusInfo);
  });

  app.post('/api/v1/game/new', async (c) => {
    if (!appContext.worldPackLoader) {
      return c.json({ error: 'World pack loader not initialized' }, 503);
    }

    const body = await c.req.json().catch(() => ({}));
    const worldPackId = body.world_pack_id || 'demo_pack';
    const presetCharacterId = body.preset_character_id;

    try {
      const worldPack = await mockWorldPackLoader?.load(worldPackId);
      if (!worldPack) {
        return c.json({ error: `World pack not found: ${worldPackId}` }, 404);
      }

      let startingLocationId: string | null = null;
      let startingLocation = null;

      for (const [locId, loc] of Object.entries(worldPack.locations)) {
        if (loc.tags?.includes('starting_area')) {
          startingLocationId = locId;
          startingLocation = loc;
          break;
        }
      }

      if (
        !startingLocationId &&
        Object.keys(worldPack.locations).length > 0
      ) {
        startingLocationId = Object.keys(worldPack.locations)[0] || null;
        startingLocation = startingLocationId
          ? worldPack.locations[startingLocationId]
          : null;
      }

      if (!startingLocation) {
        return c.json({ error: 'World pack has no locations defined' }, 400);
      }

      const sessionId = `test-session-${Date.now()}`;

      let player = mockGameState.player;
      if (presetCharacterId && worldPack.preset_characters) {
        const preset = worldPack.preset_characters.find(
          (p: { id: string }) => p.id === presetCharacterId
        );
        if (preset) {
          player = {
            name: preset.name,
            concept: preset.concept,
            traits: preset.traits,
            fate_points: 3,
            tags: [],
          };
        }
      }

      return c.json({
        session_id: sessionId,
        player: player,
        game_state: {
          current_location: startingLocationId,
          current_phase: 'waiting_input',
          turn_count: 0,
          active_npc_ids: [],
        },
        world_info: {
          pack_id: worldPackId,
          name: worldPack.info.name.cn,
          description: worldPack.info.description?.cn || '',
          author: worldPack.info.author || 'Unknown',
        },
        starting_scene: {
          location_id: startingLocationId,
          location_name: startingLocation.name.cn,
          location_description: startingLocation.description?.cn || '',
          present_npcs: [],
          visible_items: startingLocation.visible_items || [],
        },
        message: `游戏开始！欢迎来到${startingLocation.name.cn}。`,
      });
    } catch (error) {
      return c.json({ error: `Failed to start game: ${error}` }, 500);
    }
  });

  app.post('/api/v1/game/action', async (c) => {
    if (!appContext.gmAgent) {
      return c.json({ error: 'Game engine not initialized' }, 503);
    }

    const body = await c.req.json().catch(() => ({}));
    const playerInput = body.player_input || body.action;

    if (!playerInput) {
      return c.json({ error: 'player_input is required', detail: 'player_input is required' }, 400);
    }

    const response = await mockGMAgent?.process({
      player_input: playerInput,
      lang: body.lang || 'cn',
    });

    return c.json({
      success: response?.success ?? false,
      content: response?.content ?? '',
      metadata: response?.metadata ?? {},
      error: response?.error ?? null,
    });
  });

  app.post('/api/v1/game/dice-result', async (c) => {
    if (!appContext.gmAgent) {
      return c.json({ error: 'Game engine not initialized' }, 503);
    }

    const body = await c.req.json().catch(() => ({}));
    const requiredFields = ['total', 'all_rolls', 'kept_rolls', 'outcome'];

    for (const field of requiredFields) {
      if (!(field in body)) {
        return c.json(
          { error: `Missing required field: ${field}`, detail: `Missing required field: ${field}` },
          400
        );
      }
    }

    const response = await mockGMAgent?.resumeAfterDice(body, body.lang || 'cn');

    return c.json({
      success: response?.success ?? true,
      message: 'Dice result recorded',
      next_phase: 'narrating',
      content: response?.content,
    });
  });

  app.get('/api/v1/game/state/:sessionId', (c) => {
    if (!appContext.gmAgent) {
      return c.json({ error: 'Game engine not initialized' }, 503);
    }

    const sessionId = c.req.param('sessionId');
    const gameState = mockGMAgent?.getGameState();

    if (gameState?.sessionId !== sessionId) {
      return c.json({ error: 'Session not found' }, 404);
    }

    return c.json({
      session_id: gameState.sessionId,
      world_pack_id: gameState.worldPackId,
      player: gameState.player,
      current_location: gameState.currentLocation,
      active_npc_ids: gameState.activeNpcIds,
      current_phase: gameState.current_phase,
      turn_count: gameState.turn_count,
      language: gameState.language,
      messages: gameState.messages.slice(-10),
    });
  });

  app.get('/api/v1/game/messages', (c) => {
    if (!appContext.gmAgent) {
      return c.json({ error: 'Game engine not initialized' }, 503);
    }

    const gameState = mockGMAgent?.getGameState();
    const count = parseInt(c.req.query('count') || '10', 10);
    const messages = gameState?.messages.slice(-count) || [];

    return c.json({
      messages,
      count: messages.length,
    });
  });

  app.post('/api/v1/game/reset', (c) => {
    if (!appContext.gmAgent) {
      return c.json({ error: 'Game engine not initialized' }, 503);
    }

    return c.json({
      success: true,
      message: 'Game state reset',
    });
  });

  app.get('/api/v1/game/world-packs', async (c) => {
    if (!appContext.worldPackLoader) {
      return c.json({ error: 'World pack loader not initialized' }, 503);
    }

    const available = await mockWorldPackLoader?.listAvailable();
    return c.json({ packs: available || [] });
  });

  app.get('/api/v1/game/world-pack/:packId', async (c) => {
    if (!appContext.worldPackLoader) {
      return c.json({ error: 'World pack loader not initialized' }, 503);
    }

    const packId = c.req.param('packId');

    try {
      const worldPack = await mockWorldPackLoader?.load(packId);

      if (!worldPack) {
        return c.json({ error: `World pack not found: ${packId}` }, 404);
      }

      const locations = Object.entries(worldPack.locations).map(
        ([id, location]) => ({
          id,
          name: location.name,
          tags: location.tags || [],
        })
      );

      const npcs = Object.entries(worldPack.npcs || {}).map(([id, npc]) => ({
        id,
        name: (npc as { soul: { name: string } }).soul.name,
        location: (npc as { body?: { location?: string } }).body?.location || 'unknown',
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
    } catch {
      return c.json({ error: `World pack not found: ${packId}` }, 404);
    }
  });

  app.get('/api/v1/settings', (c) => {
    return c.json({
      providers: [],
      agents: null,
      game: {
        default_language: 'cn',
        dice: {
          base_dice: 2,
          bonus_mode: 'keep_highest',
          penalty_mode: 'keep_lowest',
        },
      },
    });
  });

  app.put(
    '/api/v1/settings',
    zValidator('json', UpdateSettingsRequestSchema),
    async (c) => {
      c.req.valid('json');
      return c.json({
        success: true,
        message: 'Settings updated (stub implementation)',
      });
    }
  );

  app.post(
    '/api/v1/settings/test-connection',
    zValidator('json', TestConnectionRequestSchema),
    async (c) => {
      const request = c.req.valid('json');
      return c.json({
        success: true,
        provider_id: request.provider_id,
        message: 'Connection test successful (stub implementation)',
        latency_ms: 100,
      });
    }
  );

  app.get('/api/v1/settings/provider-types', (c) => {
    return c.json({
      types: [
        {
          type: 'openai',
          name: 'OpenAI',
          requires_api_key: true,
          default_base_url: 'https://api.openai.com/v1',
          placeholder_models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
        },
        {
          type: 'anthropic',
          name: 'Anthropic',
          requires_api_key: true,
          default_base_url: 'https://api.anthropic.com',
          placeholder_models: ['claude-3-5-sonnet-20241022'],
        },
        {
          type: 'openai-compatible',
          name: 'OpenAI Compatible',
          requires_api_key: true,
          default_base_url: null,
          placeholder_models: ['gpt-4', 'gpt-3.5-turbo'],
        },
      ],
    });
  });

  return {
    app,
    context: appContext,
    mocks: {
      gmAgent: mockGMAgent,
      worldPackLoader: mockWorldPackLoader,
      loreService: mockLoreService,
      gameState: mockGameState,
    },
  };
}
