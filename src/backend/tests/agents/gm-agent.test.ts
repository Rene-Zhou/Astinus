import { describe, it, expect, vi, beforeEach } from 'vitest';
import { GMAgent } from '../../src/agents/gm';
import { createMockGameState, createMockWorldPackLoader, createMockLoreService } from '../mocks/gm-agent.mock';
import type { LanguageModel } from 'ai';

// Mock the AI SDK
const mockGenerateText = vi.fn();
vi.mock('ai', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...(actual as object),
    generateText: (...args: any[]) => mockGenerateText(...args),
  };
});

describe('GMAgent', () => {
  let gmAgent: GMAgent;
  let mockGameState: any;
  let mockWorldPackLoader: any;
  let mockLoreService: any;
  let mockLLM: LanguageModel;

  beforeEach(() => {
    vi.clearAllMocks();
    mockGameState = createMockGameState();
    mockWorldPackLoader = createMockWorldPackLoader();
    mockLoreService = createMockLoreService();
    mockLLM = {} as LanguageModel; // We mock the model interface

    gmAgent = new GMAgent(
      mockLLM,
      {}, // subAgents
      mockGameState,
      mockLoreService,
      mockWorldPackLoader,
      undefined // vectorStore
    );
  });

  describe('process', () => {
    it('should return error if no player input', async () => {
      const response = await gmAgent.process({ player_input: '' });
      expect(response.success).toBe(false);
      expect(response.error).toContain('No player input');
    });

    it('should successfully process player input and return narrative', async () => {
      // Mock generateText response for simple narrative
      mockGenerateText.mockResolvedValue({
        text: 'You see a dark cave ahead.',
        finishReason: 'stop',
        steps: [],
      });

      const response = await gmAgent.process({ player_input: 'Look around' });

      expect(response.success).toBe(true);
      expect(response.content).toBe('You see a dark cave ahead.');
      expect(mockGenerateText).toHaveBeenCalled();
      
      // Verify message added to state
      expect(mockGameState.messages).toHaveLength(2); // User + Assistant
      expect(mockGameState.messages[0].content).toBe('Look around');
      expect(mockGameState.messages[1].content).toBe('You see a dark cave ahead.');
      expect(mockGameState.turn_count).toBe(1);
    });

    it('should handle tool calls (e.g. dice check request)', async () => {
      // Mock generateText to return a tool call
      mockGenerateText.mockResolvedValue({
        text: '', // Usually empty when tool calling
        finishReason: 'stop', // SDK usually handles 'tool-calls' then 'stop'
        steps: [
          {
            toolCalls: [
              {
                toolName: 'request_dice_check',
                args: {}, // args are usually parsed, but here we check 'input' in logic
                input: {
                  intention: 'Jump over the pit',
                  influencing_factors: { traits: [], tags: [] },
                  dice_formula: '2d6',
                  instructions: 'Roll agility',
                },
              },
            ],
          },
        ],
      });

      const response = await gmAgent.process({ player_input: 'I jump over' });

      expect(response.success).toBe(true);
      expect(response.content).toBe(''); // Empty content because dice check is pending
      expect(response.metadata?.requires_dice).toBe(true);
      expect(mockGameState.current_phase).toBe('dice_check');
      expect(mockGameState.react_pending_state).toBeDefined();
      expect(mockGameState.react_pending_state.check_request.intention).toBe('Jump over the pit');
    });
  });

  describe('resumeAfterDice', () => {
    it('should fail if no pending state', async () => {
      mockGameState.react_pending_state = null;
      const response = await gmAgent.resumeAfterDice({}, 'cn');
      expect(response.success).toBe(false);
      expect(response.error).toContain('No pending ReAct state');
    });

    it('should resume processing with dice result', async () => {
      // Setup pending state
      mockGameState.react_pending_state = {
        player_input: 'I jump over',
        iteration: 1,
        agent_results: [],
        check_request: { intention: 'Jump over' },
      };
      
      // Mock subsequent narrative generation
      mockGenerateText.mockResolvedValue({
        text: 'You successfully jumped over the pit!',
        finishReason: 'stop',
        steps: [],
      });

      const diceResult = {
        total: 10,
        outcome: 'success',
        intention: 'Jump over',
      };

      const response = await gmAgent.resumeAfterDice(diceResult, 'cn');

      expect(response.success).toBe(true);
      expect(response.content).toBe('You successfully jumped over the pit!');
      expect(mockGameState.current_phase).toBe('waiting_input');
      expect(mockGameState.react_pending_state).toBeNull();
      
      // Verify generateText was called (it would be the second time in a real flow)
      expect(mockGenerateText).toHaveBeenCalled();
    });
  });
});
