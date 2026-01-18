import { vi } from 'vitest';
import type { GameState, PlayerCharacter, Trait } from '../../src/schemas';

export function createMockPlayerCharacter(
  overrides: Partial<PlayerCharacter> = {}
): PlayerCharacter {
  const defaultTrait: Trait = {
    name: { cn: '勇敢', en: 'Brave' },
    description: { cn: '面对困难不退缩', en: 'Faces difficulties without retreat' },
    positiveAspect: { cn: '勇敢', en: 'Brave' },
    negativeAspect: { cn: '鲁莽', en: 'Rash' },
  };

  return {
    name: '测试玩家',
    concept: { cn: '冒险者', en: 'Adventurer' },
    traits: [defaultTrait],
    fatePoints: 3,
    tags: [],
    ...overrides,
  };
}

export function createMockGameState(overrides: Partial<GameState> = {}): GameState {
  const now = new Date().toISOString();

  return {
    sessionId: 'test-session-id',
    playerName: '玩家',
    createdAt: now,
    updatedAt: now,
    player: createMockPlayerCharacter(),
    currentPhase: 'waiting_input',
    nextAgent: null,
    worldPackId: 'demo_pack',
    currentLocation: 'starting_location',
    activeNpcIds: [],
    discoveredItems: [],
    flags: [],
    gameTime: '00:00',
    turnCount: 0,
    messages: [],
    tempContext: {},
    lastCheckResult: null,
    reactPendingState: null,
    language: 'cn',
    ...overrides,
  };
}

export interface MockAgentResponse {
  content: string;
  success: boolean;
  error?: string;
  metadata?: Record<string, unknown>;
}

export function createMockGMAgent(gameState?: GameState) {
  const state = gameState || createMockGameState();

  return {
    getGameState: vi.fn().mockReturnValue(state),
    process: vi.fn().mockResolvedValue({
      content: '你环顾四周，发现自己身处一间古老的图书馆。',
      success: true,
      metadata: { agent: 'gm_agent', phase: 'narrating' },
    } as MockAgentResponse),
    resumeAfterDice: vi.fn().mockResolvedValue({
      content: '掷骰成功！你顺利完成了动作。',
      success: true,
      metadata: { agent: 'gm_agent', phase: 'narrating' },
    } as MockAgentResponse),
    setStatusCallback: vi.fn(),
  };
}

export function createMockWorldPackLoader() {
  return {
    load: vi.fn().mockResolvedValue({
      info: {
        name: { cn: '测试世界包', en: 'Test World Pack' },
        description: { cn: '测试描述', en: 'Test description' },
        version: '1.0.0',
        author: 'Test Author',
      },
      locations: {
        starting_location: {
          id: 'starting_location',
          name: { cn: '起始地点', en: 'Starting Location' },
          description: { cn: '一个安静的地方', en: 'A quiet place' },
          connectedLocations: [],
          presentNpcIds: [],
          items: [],
          tags: ['starting_area'],
          visibleItems: [],
          hiddenItems: [],
          loreTags: [],
        },
      },
      npcs: {},
      entries: {},
      presetCharacters: [
        {
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
        },
      ],
      regions: {},
    }),
    listAvailable: vi.fn().mockResolvedValue(['demo_pack', 'test_pack']),
  };
}

export function createMockLoreService() {
  return {
    search: vi.fn().mockResolvedValue({
      entries: [],
      total: 0,
    }),
    indexWorldPack: vi.fn().mockResolvedValue(undefined),
  };
}
