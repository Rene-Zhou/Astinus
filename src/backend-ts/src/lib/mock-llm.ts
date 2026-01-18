import type { LanguageModelV1 } from 'ai';

export const mockLanguageModel: LanguageModelV1 = {
  specificationVersion: 'v1',
  provider: 'mock',
  modelId: 'mock-model',
  defaultObjectGenerationMode: 'json',
  doGenerate: async (options) => {
    // Basic mock logic to handle different request types
    // This is very primitive and assumes the caller handles parsing errors gracefully
    // or that we just get lucky.
    
    // Check if it looks like a GM Action decision (contains "action_type")
    if (options.prompt && JSON.stringify(options.prompt).includes("action_type")) {
        return {
            text: JSON.stringify({
                action_type: "RESPOND",
                content: "（GM AI 未配置，这是 Mock 回复）",
                reasoning: "LLM not configured.",
                agent_name: null,
                agent_context: {},
                check_request: null
            }),
            finishReason: 'stop',
            usage: { promptTokens: 0, completionTokens: 0 },
            rawCall: { rawPrompt: null, rawSettings: {} },
        };
    }

    return {
      text: "Mock LLM Response: Backend is running but no LLM provider is configured.",
      finishReason: 'stop',
      usage: { promptTokens: 0, completionTokens: 0 },
      rawCall: { rawPrompt: null, rawSettings: {} },
    };
  },
  doStream: async () => ({
    stream: new ReadableStream({
      start(controller) {
        controller.enqueue({ type: 'text-delta', textDelta: 'Mock LLM Response' });
        controller.enqueue({ type: 'finish', finishReason: 'stop', usage: { promptTokens: 0, completionTokens: 0 } });
        controller.close();
      },
    }),
    rawCall: { rawPrompt: null, rawSettings: {} },
  }),
};
