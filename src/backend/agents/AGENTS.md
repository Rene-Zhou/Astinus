# AGENTS - Multi-Agent Orchestration

**Scope:** AI agent system (GM + sub-agents)

## OVERVIEW

Star topology centered on **GM Agent**. GM orchestrates Rule/NPC/Lore agents via context slicing. Each agent uses LangChain ReAct loops with Jinja2 prompts.

## STRUCTURE

```
agents/
├── prompts/           # Jinja2 templates (*.yaml) - NEVER hardcode
│   ├── gm_agent.yaml
│   ├── rule_agent.yaml
│   ├── npc_agent.yaml
│   └── lore_agent.yaml
├── __pycache__/
└── (agent modules: gm.py, rule_agent.py, npc_agent.py, lore_agent.py)
```

## WHERE TO LOOK

| Task | File |
|------|------|
| Modify GM behavior | `prompts/gm_agent.yaml` |
| Change Rule logic | `prompts/rule_agent.yaml` |
| NPC dialogue rules | `prompts/npc_agent.yaml` |
| Lore retrieval | `prompts/lore_agent.yaml` |
| Agent implementation | `*.py` (gm.py, rule_agent.py, etc.) |

## PROMPT CONVENTIONS

- **ALL prompts** in `prompts/*.yaml` using Jinja2 syntax
- Variables: `{{ variable_name }}`
- System prompts: YAML `system:` field
- NEVER edit prompts in Python files

## ANTI-PATTERNS

| Rule | Reason |
|------|--------|
| NO prompt strings in `.py` | All must be in `prompts/*.yaml` |
| NO full history to sub-agents | Use context slices (GM prepares) |
| NO agent name leakage | Output never shows "Rule Agent says..." |
