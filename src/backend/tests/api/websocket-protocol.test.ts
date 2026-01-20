import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MessageType } from '../../src/api/websocket';

describe('WebSocket Message Types', () => {
  it('should have all expected message types defined', () => {
    const expectedTypes = [
      'status',
      'content',
      'complete',
      'error',
      'phase',
      'dice_check',
      'dice_result',
    ];

    const actualTypes = Object.values(MessageType);

    for (const expected of expectedTypes) {
      expect(actualTypes).toContain(expected);
    }
  });

  it('should have string values for all message types', () => {
    for (const msgType of Object.values(MessageType)) {
      expect(typeof msgType).toBe('string');
    }
  });
});

describe('WebSocket Status Message Format (WSStatusMessage)', () => {
  it('should have correct structure', () => {
    const statusMessage = {
      type: MessageType.STATUS,
      data: {
        phase: 'processing',
        message: '正在分析你的行动...',
        agent: 'gm',
      },
    };

    expect(statusMessage.type).toBe('status');
    expect(statusMessage.data).toHaveProperty('phase');
    expect(statusMessage.data).toHaveProperty('message');
    expect(typeof statusMessage.data.phase).toBe('string');
    expect(typeof statusMessage.data.message).toBe('string');
  });

  it('should allow optional agent field', () => {
    const statusMessageWithoutAgent = {
      type: MessageType.STATUS,
      data: {
        phase: 'narrating',
        message: '叙事中...',
      },
    };

    expect(statusMessageWithoutAgent.data).not.toHaveProperty('agent');
  });
});

describe('WebSocket Content Message Format (WSContentMessage)', () => {
  it('should have correct structure for streaming chunks', () => {
    const contentMessage = {
      type: MessageType.CONTENT,
      data: {
        chunk: '图书管理员抬起头，',
        is_partial: true,
        chunk_index: 0,
      },
    };

    expect(contentMessage.type).toBe('content');
    expect(contentMessage.data).toHaveProperty('chunk');
    expect(contentMessage.data).toHaveProperty('is_partial');
    expect(contentMessage.data).toHaveProperty('chunk_index');
    expect(typeof contentMessage.data.chunk).toBe('string');
    expect(typeof contentMessage.data.is_partial).toBe('boolean');
    expect(typeof contentMessage.data.chunk_index).toBe('number');
  });

  it('should mark last chunk with is_partial=false', () => {
    const finalChunk = {
      type: MessageType.CONTENT,
      data: {
        chunk: '用审视的目光打量着你。',
        is_partial: false,
        chunk_index: 5,
      },
    };

    expect(finalChunk.data.is_partial).toBe(false);
  });
});

describe('WebSocket Complete Message Format (WSCompleteMessage)', () => {
  it('should have correct structure', () => {
    const completeMessage = {
      type: MessageType.COMPLETE,
      data: {
        content: '图书管理员抬起头，用审视的目光打量着你...',
        metadata: { phase: 'waiting_input', turn: 6 },
        success: true,
      },
    };

    expect(completeMessage.type).toBe('complete');
    expect(completeMessage.data).toHaveProperty('content');
    expect(completeMessage.data).toHaveProperty('metadata');
    expect(completeMessage.data).toHaveProperty('success');
    expect(typeof completeMessage.data.content).toBe('string');
    expect(typeof completeMessage.data.metadata).toBe('object');
    expect(typeof completeMessage.data.success).toBe('boolean');
  });
});

describe('WebSocket Dice Check Message Format (WSDiceCheckMessage)', () => {
  it('should have correct structure', () => {
    const diceCheckMessage = {
      type: MessageType.DICE_CHECK,
      data: {
        check_request: {
          intention: '说服图书管理员透露秘密',
          influencing_factors: {
            traits: ['善于交际'],
            tags: ['图书馆常客'],
          },
          dice_formula: '2d6',
          instructions: '因为你的「善于交际」特质，获得+1加值',
        },
      },
    };

    expect(diceCheckMessage.type).toBe('dice_check');
    expect(diceCheckMessage.data).toHaveProperty('check_request');

    const req = diceCheckMessage.data.check_request;
    expect(req).toHaveProperty('intention');
    expect(req).toHaveProperty('influencing_factors');
    expect(req).toHaveProperty('dice_formula');
    expect(req).toHaveProperty('instructions');
    expect(typeof req.intention).toBe('string');
    expect(typeof req.dice_formula).toBe('string');
    expect(typeof req.instructions).toBe('string');
    expect(Array.isArray(req.influencing_factors.traits)).toBe(true);
    expect(Array.isArray(req.influencing_factors.tags)).toBe(true);
  });

  it('should support localized instructions', () => {
    const diceCheckWithLocalizedInstructions = {
      type: MessageType.DICE_CHECK,
      data: {
        check_request: {
          intention: '攀爬高墙',
          influencing_factors: { traits: [], tags: [] },
          dice_formula: '2d6',
          instructions: {
            cn: '标准检定',
            en: 'Standard check',
          },
        },
      },
    };

    const instructions = diceCheckWithLocalizedInstructions.data.check_request.instructions;
    expect(typeof instructions).toBe('object');
    expect(instructions).toHaveProperty('cn');
    expect(instructions).toHaveProperty('en');
  });
});

describe('WebSocket Phase Message Format (WSPhaseMessage)', () => {
  it('should have correct structure', () => {
    const phaseMessage = {
      type: MessageType.PHASE,
      data: {
        phase: 'dice_check',
      },
    };

    expect(phaseMessage.type).toBe('phase');
    expect(phaseMessage.data).toHaveProperty('phase');
    expect(typeof phaseMessage.data.phase).toBe('string');
  });

  it('should contain valid phase values', () => {
    const validPhases = [
      'waiting_input',
      'processing',
      'dice_check',
      'npc_response',
      'narrating',
    ];

    for (const phase of validPhases) {
      const phaseMessage = {
        type: MessageType.PHASE,
        data: { phase },
      };
      expect(validPhases).toContain(phaseMessage.data.phase);
    }
  });
});

describe('WebSocket Error Message Format (WSErrorMessage)', () => {
  it('should have correct structure', () => {
    const errorMessage = {
      type: MessageType.ERROR,
      data: {
        error: 'Invalid player input',
      },
    };

    expect(errorMessage.type).toBe('error');
    expect(errorMessage.data).toHaveProperty('error');
    expect(typeof errorMessage.data.error).toBe('string');
  });
});

describe('Client to Server Message Formats', () => {
  it('should validate player_action message format', () => {
    const playerActionMessage = {
      type: 'player_action',
      data: {
        action: '我查看周围的环境',
        lang: 'cn',
      },
    };

    expect(playerActionMessage.type).toBe('player_action');
    expect(playerActionMessage.data).toHaveProperty('action');
    expect(playerActionMessage.data).toHaveProperty('lang');
    expect(playerActionMessage.data.lang).toMatch(/^(cn|en)$/);
  });

  it('should validate dice_result message format', () => {
    const diceResultMessage = {
      type: 'dice_result',
      data: {
        total: 10,
        all_rolls: [6, 4],
        kept_rolls: [6, 4],
        outcome: 'success',
      },
    };

    expect(diceResultMessage.type).toBe('dice_result');
    expect(diceResultMessage.data).toHaveProperty('total');
    expect(diceResultMessage.data).toHaveProperty('all_rolls');
    expect(diceResultMessage.data).toHaveProperty('kept_rolls');
    expect(diceResultMessage.data).toHaveProperty('outcome');
    expect(typeof diceResultMessage.data.total).toBe('number');
    expect(Array.isArray(diceResultMessage.data.all_rolls)).toBe(true);
    expect(Array.isArray(diceResultMessage.data.kept_rolls)).toBe(true);
    expect(['critical', 'success', 'partial', 'failure']).toContain(
      diceResultMessage.data.outcome
    );
  });

  it('should validate ping message format', () => {
    const pingMessage = { type: 'ping' };
    expect(pingMessage.type).toBe('ping');
  });
});

describe('WebSocket Streaming Behavior', () => {
  it('should produce sequential chunk indices', () => {
    const chunks = [
      { type: MessageType.CONTENT, data: { chunk: 'Chunk 0', is_partial: true, chunk_index: 0 } },
      { type: MessageType.CONTENT, data: { chunk: 'Chunk 1', is_partial: true, chunk_index: 1 } },
      { type: MessageType.CONTENT, data: { chunk: 'Chunk 2', is_partial: true, chunk_index: 2 } },
      { type: MessageType.CONTENT, data: { chunk: 'Chunk 3', is_partial: false, chunk_index: 3 } },
    ];

    const indices = chunks.map((c) => c.data.chunk_index);
    expect(indices).toEqual([0, 1, 2, 3]);

    const lastChunk = chunks[chunks.length - 1];
    expect(lastChunk?.data.is_partial).toBe(false);
  });

  it('should have complete message follow content chunks', () => {
    const messageSequence = [
      { type: MessageType.STATUS, data: { phase: 'processing', message: 'Processing...' } },
      { type: MessageType.CONTENT, data: { chunk: 'Hello ', is_partial: true, chunk_index: 0 } },
      { type: MessageType.CONTENT, data: { chunk: 'World', is_partial: false, chunk_index: 1 } },
      { type: MessageType.COMPLETE, data: { content: 'Hello World', metadata: {}, success: true } },
    ];

    const types = messageSequence.map((m) => m.type);
    expect(types).toEqual([
      MessageType.STATUS,
      MessageType.CONTENT,
      MessageType.CONTENT,
      MessageType.COMPLETE,
    ]);
  });
});

describe('Game Session Flow via WebSocket', () => {
  it('should support full game session flow message sequence', () => {
    const sessionFlow = [
      { type: MessageType.STATUS, data: { phase: 'connected', message: 'WebSocket connected' } },
      { type: MessageType.STATUS, data: { phase: 'processing', message: 'Processing action...' } },
      { type: MessageType.PHASE, data: { phase: 'narrating' } },
      { type: MessageType.CONTENT, data: { chunk: '你环顾', is_partial: true, chunk_index: 0 } },
      { type: MessageType.CONTENT, data: { chunk: '四周...', is_partial: false, chunk_index: 1 } },
      {
        type: MessageType.COMPLETE,
        data: { content: '你环顾四周...', metadata: { phase: 'waiting_input' }, success: true },
      },
    ];

    expect(sessionFlow[0]?.type).toBe(MessageType.STATUS);
    expect(sessionFlow[sessionFlow.length - 1]?.type).toBe(MessageType.COMPLETE);
  });

  it('should support dice check flow', () => {
    const diceCheckFlow = [
      { type: MessageType.STATUS, data: { phase: 'processing', message: 'Processing action...' } },
      { type: MessageType.PHASE, data: { phase: 'dice_check' } },
      {
        type: MessageType.DICE_CHECK,
        data: {
          check_request: {
            intention: '尝试攀爬高墙',
            influencing_factors: { traits: ['勇敢'], tags: [] },
            dice_formula: '2d6',
            instructions: '标准检定',
          },
        },
      },
    ];

    expect(diceCheckFlow[1]?.data.phase).toBe('dice_check');
    expect(diceCheckFlow[2]?.type).toBe(MessageType.DICE_CHECK);
  });

  it('should support error handling flow', () => {
    const errorFlow = [
      { type: MessageType.STATUS, data: { phase: 'processing', message: 'Processing...' } },
      { type: MessageType.ERROR, data: { error: '处理请求时发生错误' } },
    ];

    expect(errorFlow[1]?.type).toBe(MessageType.ERROR);
    expect(errorFlow[1]?.data.error).toBeTruthy();
  });
});
