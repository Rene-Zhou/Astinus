# AGENTS - AI Multi-Agent System

**Generated:** 2026-01-20
**Stack:** Vercel AI SDK | Zod Structured Output | LanceDB Memory

## OVERVIEW

Star Topology implementation where GMAgent is the central orchestrator. Uses ReAct pattern (Reasoning + Acting) via tool calls. Sub-agents receive minimal context slices for information isolation.

## STRUCTURE

```
agents/
├── gm/
│   ├── index.ts      # GMAgent class - ReAct loop, context building
│   └── tools.ts      # Tool definitions: call_agent, search_lore, request_dice_check
├── npc/
│   └── index.ts      # NPCAgent class - Roleplay, memory retrieval
└── tools/            # (Reserved for shared tool utilities)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| **Modify GM behavior** | `gm/index.ts` | `buildSystemPrompt()`, `runReActWithTools()` |
| **Add new tool** | `gm/tools.ts` | Define with Zod schema, add to tools object |
| **Change NPC roleplay** | `npc/index.ts` | System prompt, structured output schema |
| **Context slicing** | `gm/index.ts` | `sliceContextForNpc()`, `prepareAgentContext()` |

## CONVENTIONS

### Star Topology Rules
- **GM is the ONLY hub**: All player input flows through GM first.
- **Context Slices**: Sub-agents get `prepareAgentContext()` output, never full GameState.
- **Synthesis**: GM weaves sub-agent responses into coherent narrative.

### Tool Call Pattern
```typescript
// Tools defined in tools.ts with Zod schemas
const tools = createGMTools({
  subAgents: { npc: npcAgent },
  loreService,
  gameState,
  // ...
});

// ReAct loop in GMAgent.runReActWithTools()
const { text, steps } = await generateText({
  model: llm,
  tools,
  maxSteps: 5,
  // ...
});
```

### Structured Output
All agents return Zod-validated responses:
```typescript
interface AgentResponse {
  content: string;      // Narrative/dialogue
  success: boolean;
  error?: string;
  metadata?: Record<string, unknown>;
}
```

## ANTI-PATTERNS

| Rule | Reason |
|------|--------|
| **GM NEVER roleplays NPCs directly** | Must use `call_agent` tool |
| **NO internal IDs in narrative** | Use descriptions, not `village_well` |
| **NO cross-agent communication** | Agents only talk to GM |
| **NO narrative before tool completion** | Synthesize AFTER all tools resolve |

## AGENT COMMUNICATION FLOW

```
Player Input
    ↓
GMAgent.process()
    ↓
runReActWithTools() ← ReAct Loop
    ↓
┌─────────────────────────────────────┐
│  Tool Calls (parallel possible)     │
│  - search_lore → LoreService        │
│  - call_agent → NPCAgent.process()  │
│  - request_dice_check → Frontend    │
└─────────────────────────────────────┘
    ↓
Synthesize Final Narrative
    ↓
Stream to Frontend (WebSocket)
```

## NOTES

- **Memory**: NPCs use LanceDB `npc_memory_{sessionId}` tables for semantic recall.
- **History**: GM uses `gm_history_{sessionId}` for long conversation retrieval.
- **Max Iterations**: ReAct loop limited to 5 steps to prevent infinite tool chains.
