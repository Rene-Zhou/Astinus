import { describe, it, expect } from 'vitest';
import { createTestApp } from '../utils/test-app';

describe('World Pack API Endpoint Tests', () => {
  describe('GET /api/v1/game/world-packs', () => {
    it('should return list of available world packs', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/game/world-packs');
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty('packs');
      expect(Array.isArray(data.packs)).toBe(true);
      expect(data.packs.length).toBeGreaterThan(0);
    });

    it('should return 503 when world pack loader is not initialized', async () => {
      const { app } = createTestApp({ withWorldPackLoader: false });

      const response = await app.request('/api/v1/game/world-packs');
      expect(response.status).toBe(503);
    });
  });

  describe('GET /api/v1/game/world-pack/:packId', () => {
    it('should return world pack details with correct structure', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/game/world-pack/demo_pack');
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty('id');
      expect(data.id).toBe('demo_pack');

      expect(data).toHaveProperty('info');
      expect(data.info).toHaveProperty('name');
      expect(data.info).toHaveProperty('description');

      expect(data).toHaveProperty('summary');
      expect(data.summary).toHaveProperty('locations');
      expect(data.summary).toHaveProperty('npcs');
      expect(data.summary).toHaveProperty('lore_entries');
      expect(data.summary).toHaveProperty('preset_characters');
      expect(typeof data.summary.locations).toBe('number');
      expect(typeof data.summary.npcs).toBe('number');

      expect(data).toHaveProperty('locations');
      expect(Array.isArray(data.locations)).toBe(true);

      expect(data).toHaveProperty('npcs');
      expect(Array.isArray(data.npcs)).toBe(true);

      expect(data).toHaveProperty('preset_characters');
      expect(Array.isArray(data.preset_characters)).toBe(true);
    });

    it('should return location info with name and tags', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/game/world-pack/demo_pack');
      const data = await response.json();

      if (data.locations.length > 0) {
        const location = data.locations[0];
        expect(location).toHaveProperty('id');
        expect(location).toHaveProperty('name');
        expect(location).toHaveProperty('tags');
        expect(Array.isArray(location.tags)).toBe(true);
      }
    });

    it('should return preset characters with correct structure', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/game/world-pack/demo_pack');
      const data = await response.json();

      if (data.preset_characters.length > 0) {
        const preset = data.preset_characters[0];
        expect(preset).toHaveProperty('id');
        expect(preset).toHaveProperty('name');
        expect(preset).toHaveProperty('concept');
        expect(preset).toHaveProperty('traits');
        expect(Array.isArray(preset.traits)).toBe(true);
      }
    });

    it('should return 404 for non-existent world pack', async () => {
      const { app, mocks } = createTestApp();

      mocks.worldPackLoader?.load.mockRejectedValueOnce(new Error('Not found'));

      const response = await app.request('/api/v1/game/world-pack/non_existent_pack');
      expect(response.status).toBe(404);
    });

    it('should return 503 when world pack loader is not initialized', async () => {
      const { app } = createTestApp({ withWorldPackLoader: false });

      const response = await app.request('/api/v1/game/world-pack/demo_pack');
      expect(response.status).toBe(503);
    });
  });
});

describe('World Pack Info Type Validation', () => {
  it('should validate WorldPackInfo structure', () => {
    const worldPackInfo = {
      name: { cn: '测试世界包', en: 'Test World Pack' },
      description: { cn: '测试描述', en: 'Test description' },
      version: '1.0.0',
      author: 'Test Author',
      setting: {
        era: { cn: '现代', en: 'Modern' },
        genre: { cn: '奇幻', en: 'Fantasy' },
        tone: { cn: '冒险', en: 'Adventure' },
      },
    };

    expect(worldPackInfo.name).toHaveProperty('cn');
    expect(worldPackInfo.name).toHaveProperty('en');
    expect(typeof worldPackInfo.version).toBe('string');
    expect(typeof worldPackInfo.author).toBe('string');
  });

  it('should validate LocationData structure', () => {
    const locationData = {
      id: 'starting_location',
      name: { cn: '起始地点', en: 'Starting Location' },
      description: { cn: '一个安静的地方', en: 'A quiet place' },
      tags: ['starting_area'],
      connectedLocations: [],
      presentNpcIds: [],
    };

    expect(typeof locationData.id).toBe('string');
    expect(locationData.name).toHaveProperty('cn');
    expect(locationData.name).toHaveProperty('en');
    expect(Array.isArray(locationData.tags)).toBe(true);
  });

  it('should validate PresetCharacter structure', () => {
    const presetCharacter = {
      id: 'preset_1',
      name: '预设角色',
      concept: { cn: '战士', en: 'Warrior' },
      traits: [
        {
          name: { cn: '勇敢', en: 'Brave' },
          description: { cn: '勇敢的描述', en: 'Brave description' },
          positiveAspect: { cn: '勇敢', en: 'Brave' },
          negativeAspect: { cn: '鲁莽', en: 'Rash' },
        },
      ],
    };

    expect(typeof presetCharacter.id).toBe('string');
    expect(typeof presetCharacter.name).toBe('string');
    expect(presetCharacter.concept).toHaveProperty('cn');
    expect(presetCharacter.concept).toHaveProperty('en');
    expect(Array.isArray(presetCharacter.traits)).toBe(true);
    expect(presetCharacter.traits.length).toBeGreaterThan(0);

    const trait = presetCharacter.traits[0];
    expect(trait).toHaveProperty('name');
    expect(trait).toHaveProperty('description');
    expect(trait).toHaveProperty('positiveAspect');
    expect(trait).toHaveProperty('negativeAspect');
  });
});

describe('World Pack Selection Flow', () => {
  it('should list packs then get details then start game', async () => {
    const { app } = createTestApp();

    const listResponse = await app.request('/api/v1/game/world-packs');
    expect(listResponse.status).toBe(200);
    const listData = await listResponse.json();
    expect(listData.packs.length).toBeGreaterThan(0);

    const packId = listData.packs[0];

    const detailResponse = await app.request(`/api/v1/game/world-pack/${packId}`);
    expect(detailResponse.status).toBe(200);
    const detailData = await detailResponse.json();
    expect(detailData.id).toBe(packId);

    const newGameResponse = await app.request('/api/v1/game/new', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        world_pack_id: packId,
      }),
    });
    expect(newGameResponse.status).toBe(200);
    const newGameData = await newGameResponse.json();
    expect(newGameData.session_id).toBeTruthy();
  });
});
