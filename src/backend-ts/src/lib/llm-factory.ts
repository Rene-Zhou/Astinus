import { createOpenAI } from '@ai-sdk/openai';
import { createAnthropic } from '@ai-sdk/anthropic';
import { createGoogleGenerativeAI } from '@ai-sdk/google';
import type { LanguageModel } from 'ai';
import type { AgentConfig, ProviderConfig } from '../schemas/config.js';

export class LLMFactory {
  /**
   * Creates a Vercel AI SDK LanguageModel based on agent and provider configuration
   */
  public static createModel(
    agentConfig: AgentConfig, 
    providers: ProviderConfig[]
  ): LanguageModel {
    const providerConfig = providers.find(p => p.id === agentConfig.provider_id);
    
    if (!providerConfig) {
      throw new Error(`Provider with ID '${agentConfig.provider_id}' not found for agent configuration.`);
    }

    const apiKey = providerConfig.api_key || process.env[`${providerConfig.type.toUpperCase()}_API_KEY`] || '';
    const baseUrl = providerConfig.base_url || undefined;

    switch (providerConfig.type) {
      case 'openai':
        const openai = createOpenAI({
          apiKey,
          baseURL: baseUrl,
        });
        return openai(agentConfig.model);

      case 'anthropic':
        const anthropic = createAnthropic({
          apiKey,
          baseURL: baseUrl,
        });
        return anthropic(agentConfig.model);

      case 'ollama':
        // Ollama usually provides an OpenAI-compatible API
        const ollama = createOpenAI({
          name: 'ollama',
          apiKey: 'ollama', // often not needed but required by types
          baseURL: baseUrl || 'http://localhost:11434/v1',
        });
        return ollama(agentConfig.model);
        
      case 'google':
        console.log(`[LLMFactory] Creating Google model: ${agentConfig.model} with base_url: ${baseUrl || 'default'}`);
        const google = createGoogleGenerativeAI({
          apiKey,
          baseURL: baseUrl,
        });
        return google(agentConfig.model);

      default:
        // Try to treat unknown providers as OpenAI-compatible if they have a base URL
        if (baseUrl) {
          const custom = createOpenAI({
            apiKey,
            baseURL: baseUrl,
          });
          return custom(agentConfig.model);
        }
        throw new Error(`Unsupported provider type: ${providerConfig.type}`);
    }
  }
}
