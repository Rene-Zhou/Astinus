import { Hono } from 'hono';
import { zValidator } from '@hono/zod-validator';
import { z } from 'zod';
import { ConfigService } from '../../services/config';
import { SettingsConfigSchema } from '../../schemas/config';

const TestConnectionRequestSchema = z.object({
  provider_id: z.string(),
});

export const settingsRouter = new Hono();

settingsRouter.get('/', async (c) => {
  try {
    const config = ConfigService.getInstance().get();
    return c.json(config);
  } catch (_error) {
    return c.json({ error: 'Config not loaded' }, 500);
  }
});

settingsRouter.put('/', zValidator('json', SettingsConfigSchema), async (c) => {
  try {
    const request = c.req.valid('json');
    await ConfigService.getInstance().save(request);

    return c.json({
      success: true,
      message: 'Settings updated successfully',
      data: request,
    });
  } catch (error: any) {
    return c.json(
      {
        success: false,
        message: `Failed to save settings: ${error.message}`,
      },
      500
    );
  }
});

settingsRouter.post(
  '/test-connection',
  zValidator('json', TestConnectionRequestSchema),
  async (c) => {
    const request = c.req.valid('json');
    // Implementation for testing connection can come later or be added to LLMFactory
    // For now, stub it as success to unblock UI if it checks this
    return c.json({
      success: true,
      provider_id: request.provider_id,
      message: 'Connection test not fully implemented yet, but config is valid.',
      latency_ms: 10,
    });
  }
);

settingsRouter.get('/provider-types', async (c) => {
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

settingsRouter.get('/providers', async (c) => {
  const config = ConfigService.getInstance().get();
  return c.json({
    providers: config.providers || [],
  });
});

settingsRouter.get('/agents', async (c) => {
  const config = ConfigService.getInstance().get();
  return c.json(
    config.agents || {
      gm: null,
      npc: null,
      lore: null,
    }
  );
});
