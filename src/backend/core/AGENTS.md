# CORE - Foundational Services

**Scope:** Localization, Prompt Management, and Configuration

## OVERVIEW

Foundational services providing i18n support, Jinja2-based prompt orchestration, and Pydantic-driven settings.

## WHERE TO LOOK

| Component | File | Role |
|-----------|------|------|
| **I18nService** | `i18n.py` | Centralized localization with dot-notation keys and fallback to CN |
| **PromptLoader** | `prompt_loader.py` | Jinja2 prompt template manager with multi-language support |
| **Settings** | `config.py` | Pydantic configuration with YAML loading and legacy migration |
| **LLMProvider** | `llm_provider.py` | Unified factory for OpenAI, Anthropic, Google, and Ollama |
| **LocalizedString** | `models/i18n.py` | Foundational utility for multi-language string storage/fallback |

## CONVENTIONS

- **I18n-First**: Never hardcode user-facing strings; use `get_i18n().get()`
- **Prompt Isolation**: All prompts in `agents/prompts/*.yaml`; load via `PromptLoader`
- **Strict Configuration**: Use Pydantic `Settings` for all environment/config variables
- **Lazy Initialization**: Services use `get_*()` functions for singleton access

## ANTI-PATTERNS

| Rule | Reason |
|------|--------|
| NO inline prompt strings | Breaks maintainability and multi-language support |
| NO hardcoded paths | Use `find_config_file()` and `Path` objects |
| NO environment access | All env vars must be mapped in `Settings` (config.py) |
| NO direct model instantiation | Use `get_llm()` factory for consistent configuration |

## NOTES

- **Fallback Chain**: i18n defaults to `cn` if requested language key is missing.
- **Legacy Support**: `config.py` includes migration logic from old `llm` format.
- **Jinja2 Strictness**: `PromptLoader` uses `StrictUndefined` to catch missing variables early.
