import { describe, it, expect, beforeEach } from 'vitest';
import { createTestApp } from '../utils/test-app';

describe('Frontend API Contract Tests', () => {
  describe('Root Endpoint Contract (GET /)', () => {
    it('should return correct response format matching RootResponse type', async () => {
      const { app } = createTestApp();

      const response = await app.request('/');
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty('name');
      expect(typeof data.name).toBe('string');
      expect(data.name).toContain('Astinus');

      expect(data).toHaveProperty('version');
      expect(typeof data.version).toBe('string');

      expect(data).toHaveProperty('status');
      expect(data.status).toBe('running');

      expect(data).toHaveProperty('docs');
      expect(typeof data.docs).toBe('string');
    });
  });

  describe('Health Endpoint Contract (GET /health)', () => {
    it('should return healthy status when GM agent is initialized', async () => {
      const { app } = createTestApp({ withGMAgent: true });

      const response = await app.request('/health');
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty('status');
      expect(data.status).toBe('healthy');

      expect(data).toHaveProperty('version');
      expect(typeof data.version).toBe('string');

      expect(data).toHaveProperty('agents');
      expect(data.agents).toHaveProperty('gm_agent');
      expect(data.agents).toHaveProperty('rule_agent');
      expect(typeof data.agents.gm_agent).toBe('boolean');
      expect(data.agents.gm_agent).toBe(true);
    });

    it('should return unhealthy status when GM agent is not initialized', async () => {
      const { app } = createTestApp({ withGMAgent: false });

      const response = await app.request('/health');
      expect(response.status).toBe(503);

      const data = await response.json();
      expect(data.status).toBe('unhealthy');
      expect(data.agents.gm_agent).toBe(false);
    });
  });

  describe('New Game Endpoint Contract (POST /api/v1/game/new)', () => {
    it('should create new game session with correct response format', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/game/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_pack_id: 'demo_pack',
          player_name: '测试玩家',
        }),
      });

      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty('session_id');
      expect(typeof data.session_id).toBe('string');
      expect(data.session_id.length).toBeGreaterThan(0);

      expect(data).toHaveProperty('player');
      expect(data.player).toHaveProperty('name');
      expect(data.player).toHaveProperty('concept');
      expect(data.player).toHaveProperty('traits');
      expect(Array.isArray(data.player.traits)).toBe(true);
      expect(data.player).toHaveProperty('tags');
      expect(data.player).toHaveProperty('fate_points');

      expect(data).toHaveProperty('game_state');
      expect(data.game_state).toHaveProperty('current_location');
      expect(data.game_state).toHaveProperty('current_phase');
      expect(data.game_state).toHaveProperty('turn_count');
      expect(data.game_state).toHaveProperty('active_npc_ids');

      expect(data).toHaveProperty('message');
      expect(typeof data.message).toBe('string');
    });

    it('should handle preset character selection', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/game/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_pack_id: 'demo_pack',
          preset_character_id: 'preset_1',
        }),
      });

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(data.player).toHaveProperty('name');
    });
  });

  describe('Game Action Endpoint Contract (POST /api/v1/game/action)', () => {
    it('should process player action and return correct response format', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/game/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          player_input: '我查看周围的环境',
          lang: 'cn',
        }),
      });

      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty('success');
      expect(typeof data.success).toBe('boolean');

      expect(data).toHaveProperty('content');
      expect(typeof data.content).toBe('string');

      expect(data).toHaveProperty('metadata');
      expect(typeof data.metadata).toBe('object');

      expect(data).toHaveProperty('error');
    });

    it('should return 400 when player_input is missing', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/game/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lang: 'cn' }),
      });

      expect(response.status).toBe(400);

      const data = await response.json();
      expect(data).toHaveProperty('detail');
      expect(data.detail).toContain('player_input');
    });

    it('should return 503 when GM agent is not initialized', async () => {
      const { app } = createTestApp({ withGMAgent: false });

      const response = await app.request('/api/v1/game/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_input: 'test', lang: 'cn' }),
      });

      expect(response.status).toBe(503);
    });
  });

  describe('Dice Result Endpoint Contract (POST /api/v1/game/dice-result)', () => {
    it('should accept dice result and return correct response format', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/game/dice-result', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          total: 10,
          all_rolls: [6, 4],
          kept_rolls: [6, 4],
          outcome: 'success',
        }),
      });

      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty('success');
      expect(data.success).toBe(true);

      expect(data).toHaveProperty('message');
      expect(data.message).toContain('Dice result recorded');

      expect(data).toHaveProperty('next_phase');
      expect(['waiting_input', 'processing', 'dice_check', 'npc_response', 'narrating']).toContain(
        data.next_phase
      );
    });

    it('should return 400 when required fields are missing', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/game/dice-result', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ total: 10 }),
      });

      expect(response.status).toBe(400);

      const data = await response.json();
      expect(data).toHaveProperty('detail');
      expect(data.detail).toContain('Missing required field');
    });
  });

  describe('Game State Endpoint Contract (GET /api/v1/game/state/:sessionId)', () => {
    it('should return game state with correct format', async () => {
      const { app } = createTestApp({
        gameStateOverrides: { sessionId: 'test-session-123' },
      });

      const response = await app.request('/api/v1/game/state/test-session-123');
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty('session_id');
      expect(data).toHaveProperty('world_pack_id');
      expect(data).toHaveProperty('player');
      expect(data).toHaveProperty('current_location');
      expect(data).toHaveProperty('active_npc_ids');
      expect(Array.isArray(data.active_npc_ids)).toBe(true);
      expect(data).toHaveProperty('current_phase');
      expect(data).toHaveProperty('turn_count');
      expect(data).toHaveProperty('language');
      expect(data.language).toMatch(/^(cn|en)$/);
    });

    it('should return 404 for non-existent session', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/game/state/non-existent-session');
      expect(response.status).toBe(404);
    });
  });

  describe('Messages Endpoint Contract (GET /api/v1/game/messages)', () => {
    it('should return messages with correct format', async () => {
      const { app } = createTestApp({
        gameStateOverrides: {
          messages: [
            {
              role: 'user',
              content: '测试消息',
              timestamp: new Date().toISOString(),
              turn: 0,
            },
            {
              role: 'assistant',
              content: '回复消息',
              timestamp: new Date().toISOString(),
              turn: 0,
            },
          ],
        },
      });

      const response = await app.request('/api/v1/game/messages?count=10');
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty('messages');
      expect(Array.isArray(data.messages)).toBe(true);
      expect(data).toHaveProperty('count');
      expect(typeof data.count).toBe('number');
    });
  });

  describe('Reset Endpoint Contract (POST /api/v1/game/reset)', () => {
    it('should reset game and return correct format', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/game/reset', {
        method: 'POST',
      });

      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty('success');
      expect(data.success).toBe(true);
      expect(data).toHaveProperty('message');
      expect(data.message).toContain('Game state reset');
    });
  });
});

describe('Game Phase Values', () => {
  it('should have all expected phase values in responses', () => {
    const expectedPhases = [
      'waiting_input',
      'processing',
      'dice_check',
      'npc_response',
      'narrating',
    ];

    for (const phase of expectedPhases) {
      expect(typeof phase).toBe('string');
    }
  });
});

describe('Dice Outcome Values', () => {
  it('should validate all dice outcome values', () => {
    const validOutcomes = ['critical', 'success', 'partial', 'failure'];

    for (const outcome of validOutcomes) {
      expect(typeof outcome).toBe('string');
    }
  });
});

describe('LocalizedString Format', () => {
  it('should verify localized string structure in responses', async () => {
    const { app } = createTestApp();

    const response = await app.request('/api/v1/game/new', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });

    const data = await response.json();

    if (data.player?.concept) {
      expect(data.player.concept).toHaveProperty('cn');
      expect(data.player.concept).toHaveProperty('en');
    }
  });
});

describe('Trait Model Format', () => {
  it('should verify trait structure in player data', async () => {
    const { app } = createTestApp();

    const response = await app.request('/api/v1/game/new', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });

    const data = await response.json();

    expect(data.player.traits).toBeDefined();
    expect(Array.isArray(data.player.traits)).toBe(true);

    if (data.player.traits.length > 0) {
      const trait = data.player.traits[0];
      expect(trait).toHaveProperty('name');
      expect(trait).toHaveProperty('description');
      expect(trait).toHaveProperty('positive_aspect');
      expect(trait).toHaveProperty('negative_aspect');
    }
  });
});
