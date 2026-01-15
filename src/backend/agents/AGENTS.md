# AGENTS - Multi-Agent Orchestration

**Scope:** AI agent system (GM + sub-agents)

## OVERVIEW

Star topology centered on **GMAgent** (1240 lines - refactor candidate). GM orchestrates Rule/NPC/Lore/Director agents via **Context Slicing** and a **ReAct Loop** (3-5 iterations).

## CORE AGENTS

- **GMAgent**: Central orchestrator. Parses intent, calls sub-agents, and synthesizes final narrative.
- **DirectorAgent**: Hidden manager tracking narrative beats (hook, climax, etc.), pacing, and tension.
- **RuleAgent**: Handles mechanics, generates dice checks, and processes results.
- **NPCAgent**: Performs roleplay, manages NPC memory, and generates specific dialogue/actions.
- **LoreAgent**: Provides world-building context via vector search.

## KEY PATTERNS

- **Two-Phase Narrative**: GM connects NPC dialogue/actions exactly as generated (no embellishment) to maintain character consistency.
- **Context Slicing**: GM prepares precise, isolated context slices for sub-agents to prevent context bloat and leakage.
- **Dice State Resumption**: ReAct loop saves state during dice checks, resuming only after result is returned.
- **ReAct Loop**: GM iterates (max 3-5 times), using `CALL_AGENT` for sub-tasks and `RESPOND` for final output.

## STRUCTURE

```
agents/
├── prompts/           # Jinja2 templates (*.yaml) - NEVER hardcode
│   ├── gm_agent.yaml
│   ├── director_agent.yaml
│   ├── npc_agent.yaml
│   └── ...
├── gm.py              # Main loop (Refactor needed: 328 lines at 4+ levels deep)
├── director.py        # Narrative pacing and tension logic
├── npc_agent.py       # Roleplay and character dialogue
└── rule_agent.py      # Mechanical resolution
```

## PROMPT CONVENTIONS

- **ALL prompts** in `prompts/*.yaml` using Jinja2 syntax (`{{ variable }}`).
- **NEVER** edit prompts in Python files (use `PromptLoader`).
- System prompts are defined in the `system:` field of YAML templates.

## ANTI-PATTERNS

| Rule | Reason |
|------|--------|
| **NO hardcoded prompts** | All must be in `prompts/*.yaml` for easier tuning |
| **NO full history** | Use context slices to avoid sub-agent confusion/omniscience |
| **NO agent name leaks** | Output never shows "Rule Agent", "Lore Agent", etc. |
| **NO ID exposure** | Internal IDs (e.g., `room_402`) must never appear in narrative |
| **NO NPC real names** | Never use NPC names until the player learns them |
