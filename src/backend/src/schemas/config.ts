import { z } from 'zod';

export const ProviderConfigSchema = z.object({
  id: z.string(),
  name: z.string().optional(),
  type: z.enum(['openai', 'anthropic', 'google', 'ollama', 'custom']).or(z.string()),
  api_key: z.string().nullable().optional(),
  base_url: z.string().nullable().optional(),
});

export type ProviderConfig = z.infer<typeof ProviderConfigSchema>;

export const AgentConfigSchema = z.object({
  provider_id: z.string(),
  model: z.string(),
  temperature: z.number().optional().default(0.7),
  max_tokens: z.number().optional().default(1024),
});

export type AgentConfig = z.infer<typeof AgentConfigSchema>;

export const AgentsConfigSchema = z.object({
  gm: AgentConfigSchema,
  npc: AgentConfigSchema,
  rule: AgentConfigSchema.optional(),
  lore: AgentConfigSchema.optional(),
});

export type AgentsConfig = z.infer<typeof AgentsConfigSchema>;

// Legacy format support
export const LegacyLLMConfigSchema = z
  .object({
    provider: z.string(),
    models: z.record(z.string()),
    api_keys: z.record(z.string()),
    temperature: z.number().optional(),
    max_tokens: z.number().optional(),
  })
  .optional();

export const SettingsConfigSchema = z
  .object({
    providers: z.array(ProviderConfigSchema).default([]),
    agents: AgentsConfigSchema.optional(),
    llm: LegacyLLMConfigSchema,
    // Other sections can be added as needed, allowing unknown keys for now
  })
  .passthrough();

export type SettingsConfig = z.infer<typeof SettingsConfigSchema>;
