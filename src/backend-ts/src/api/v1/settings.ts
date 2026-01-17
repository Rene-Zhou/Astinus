import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { z } from "zod";

const ProviderInputSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: z.string(),
  api_key: z.string().default(""),
  base_url: z.string().optional(),
});

const AgentInputSchema = z.object({
  provider_id: z.string(),
  model: z.string(),
  temperature: z.number().min(0.0).max(2.0).default(0.7),
  max_tokens: z.number().min(1).default(2000),
});

const AgentsInputSchema = z.object({
  gm: AgentInputSchema.optional(),
  npc: AgentInputSchema.optional(),
  lore: AgentInputSchema.optional(),
});

const UpdateSettingsRequestSchema = z.object({
  providers: z.array(ProviderInputSchema).optional(),
  agents: AgentsInputSchema.optional(),
});

const TestConnectionRequestSchema = z.object({
  provider_id: z.string(),
});

export const settingsRouter = new Hono();

settingsRouter.get("/", async (c) => {
  return c.json({
    providers: [],
    agents: null,
    game: {
      default_language: "cn",
      dice: {
        base_dice: 2,
        bonus_mode: "keep_highest",
        penalty_mode: "keep_lowest",
      },
    },
  });
});

settingsRouter.put(
  "/",
  zValidator("json", UpdateSettingsRequestSchema),
  async (c) => {
    const request = c.req.valid("json");

    return c.json({
      success: true,
      message: "Settings updated (stub implementation)",
      data: request,
    });
  }
);

settingsRouter.post(
  "/test-connection",
  zValidator("json", TestConnectionRequestSchema),
  async (c) => {
    const request = c.req.valid("json");

    return c.json({
      success: true,
      provider_id: request.provider_id,
      message: "Connection test successful (stub implementation)",
      latency_ms: 100,
    });
  }
);

settingsRouter.get("/provider-types", async (c) => {
  return c.json({
    types: [
      {
        type: "openai",
        name: "OpenAI",
        requires_api_key: true,
        default_base_url: "https://api.openai.com/v1",
        placeholder_models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
      },
      {
        type: "anthropic",
        name: "Anthropic",
        requires_api_key: true,
        default_base_url: "https://api.anthropic.com",
        placeholder_models: ["claude-3-5-sonnet-20241022"],
      },
      {
        type: "openai-compatible",
        name: "OpenAI Compatible",
        requires_api_key: true,
        default_base_url: null,
        placeholder_models: ["gpt-4", "gpt-3.5-turbo"],
      },
    ],
  });
});

settingsRouter.get("/providers", async (c) => {
  return c.json({
    providers: [],
  });
});

settingsRouter.get("/agents", async (c) => {
  return c.json({
    gm: null,
    npc: null,
    lore: null,
  });
});
