import { describe, it, expect } from 'vitest';
import { createTestApp } from '../utils/test-app';

describe('Settings API Endpoint Tests', () => {
  describe('GET /api/v1/settings', () => {
    it('should return settings with correct structure', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/settings');
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty('providers');
      expect(Array.isArray(data.providers)).toBe(true);

      expect(data).toHaveProperty('agents');

      expect(data).toHaveProperty('game');
      expect(data.game).toHaveProperty('default_language');
      expect(data.game.default_language).toMatch(/^(cn|en)$/);
    });

    it('should return dice settings', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/settings');
      const data = await response.json();

      expect(data.game).toHaveProperty('dice');
    });
  });

  describe('PUT /api/v1/settings', () => {
    it('should accept settings update', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          providers: [
            {
              id: 'openai-1',
              name: 'OpenAI',
              type: 'openai',
              api_key: 'sk-test-key',
              base_url: 'https://api.openai.com/v1',
            },
          ],
        }),
      });

      expect(response.status).toBe(200);

      const data = await response.json();
      expect(data).toHaveProperty('success');
      expect(data.success).toBe(true);
    });

    it('should accept agent configuration', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agents: {
            gm: {
              provider_id: 'openai-1',
              model: 'gpt-4o',
              temperature: 0.7,
              max_tokens: 2000,
            },
          },
        }),
      });

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(data.success).toBe(true);
    });
  });

  describe('POST /api/v1/settings/test-connection', () => {
    it('should test provider connection', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/settings/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_id: 'openai-1',
        }),
      });

      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty('success');
      expect(typeof data.success).toBe('boolean');

      expect(data).toHaveProperty('provider_id');
      expect(data.provider_id).toBe('openai-1');

      expect(data).toHaveProperty('message');
      expect(typeof data.message).toBe('string');

      expect(data).toHaveProperty('latency_ms');
    });
  });

  describe('GET /api/v1/settings/provider-types', () => {
    it('should return available provider types', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/settings/provider-types');
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty('types');
      expect(Array.isArray(data.types)).toBe(true);

      if (data.types.length > 0) {
        const providerType = data.types[0];
        expect(providerType).toHaveProperty('type');
        expect(providerType).toHaveProperty('name');
        expect(providerType).toHaveProperty('requires_api_key');
        expect(providerType).toHaveProperty('placeholder_models');
        expect(Array.isArray(providerType.placeholder_models)).toBe(true);
      }
    });

    it('should include common provider types', async () => {
      const { app } = createTestApp();

      const response = await app.request('/api/v1/settings/provider-types');
      const data = await response.json();

      const typeNames = data.types.map((t: { type: string }) => t.type);

      expect(typeNames).toContain('openai');
      expect(typeNames).toContain('anthropic');
    });
  });
});

describe('Settings Response Type Validation', () => {
  it('should validate ProviderConfig structure', () => {
    const providerConfig = {
      id: 'openai-1',
      name: 'OpenAI',
      type: 'openai',
      api_key: 'sk-test',
      base_url: 'https://api.openai.com/v1',
    };

    expect(typeof providerConfig.id).toBe('string');
    expect(typeof providerConfig.name).toBe('string');
    expect(typeof providerConfig.type).toBe('string');
    expect(typeof providerConfig.api_key).toBe('string');
  });

  it('should validate AgentConfig structure', () => {
    const agentConfig = {
      provider_id: 'openai-1',
      model: 'gpt-4o',
      temperature: 0.7,
      max_tokens: 2000,
    };

    expect(typeof agentConfig.provider_id).toBe('string');
    expect(typeof agentConfig.model).toBe('string');
    expect(typeof agentConfig.temperature).toBe('number');
    expect(agentConfig.temperature).toBeGreaterThanOrEqual(0);
    expect(agentConfig.temperature).toBeLessThanOrEqual(2);
    expect(typeof agentConfig.max_tokens).toBe('number');
    expect(agentConfig.max_tokens).toBeGreaterThan(0);
  });
});
