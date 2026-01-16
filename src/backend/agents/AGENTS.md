# AGENTS - Multi-Agent Orchestration

**Scope:** AI agent system (GM + sub-agents)

## OVERVIEW

The application follows a **Star Topology** with `GMAgent` as the central orchestrator. It executes a **ReAct loop** (3-5 iterations) to process player intent, delegating specialized tasks to sub-agents via **Context Slicing** before synthesizing the final narrative response.

## STRUCTURE

```text
src/backend/agents/
├── prompts/          # Jinja2 templates (*.yaml) - NEVER hardcoded
│   ├── gm_agent.yaml
│   ├── npc_agent.yaml
│   └── ...
├── base.py           # Abstract base class for all agents
├── gm.py             # CORE: Orchestrator & ReAct loop (1240 lines, REFACTOR NEEDED)
├── director.py       # Narrative pacing and tension manager
├── npc.py            # Character roleplay and dialogue
├── rule.py           # TTRPG mechanics and dice check generation
└── lore.py           # World-building and vector search retrieval
```

## WHERE TO LOOK

- **Orchestration Logic**: `GMAgent.run()` in `gm.py` contains the primary ReAct loop.
- **Sub-agent Delegation**: Look for `_call_sub_agent` patterns in `gm.py`.
- **Context Preparation**: Each sub-agent file (e.g., `npc.py`) defines its own `prepare_context` method to filter data.
- **Prompts**: `prompts/` directory contains all LLM instructions; no raw strings in `.py` files.

## CONVENTIONS

- **Jinja2 Prompts**: Use `{{ variable }}` for all dynamic content.
- **Context Slicing**: GM must isolate sub-agent context (e.g., NPC Agent doesn't see other NPCs' secrets).
- **Asynchronous IO**: All agent calls and service interactions must be `async`.
- **Stateless sub-agents**: Sub-agents should rely on the context slice provided by the GM.

## ANTI-PATTERNS

| Rule | Reason |
|------|--------|
| **NO AI Dice Rolls** | Only players/system roll dice to ensure mechanical transparency. |
| **NO ID Exposure** | Internal database IDs (e.g., `room_101`) must never leak to narrative. |
| **NO Agent Name Leaks** | Players see "The Narrator" or "NPC Name", never "Rule Agent". |
| **NO Hardcoded Prompts** | All LLM instructions must reside in `prompts/*.yaml`. |
| **NO Full History** | Sub-agents should only receive relevant "slices" to prevent context bloat. |
