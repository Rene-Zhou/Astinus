# CORE - Infrastructure Layer

**Scope:** Settings, Logging, i18n, and Prompt Loading.

## OVERVIEW

The Core module provides the foundational infrastructure for the Astinus engine. It handles centralized configuration management, internationalization (i18n) support, dynamic prompt orchestration, and unified logging settings. 

By centralizing these services, this layer ensures that all high-level agents (GM, Rule, NPC, Lore) remain decoupled from environment-specific details, file paths, and hardcoded string literals. It serves as the "source of truth" for the application's runtime behavior and localization state.

## WHERE TO LOOK

| Component | File | Role |
|-----------|------|------|
| **Settings** | `config.py` | Pydantic-driven configuration with YAML support and legacy migration logic. |
| **I18nService** | `i18n.py` | Centralized localization using dot-notation keys with automatic fallback to default language. |
| **PromptLoader** | `prompt_loader.py` | Jinja2-based prompt template manager supporting multi-language blocks and versioning. |
| **LLMProvider** | `llm_provider.py` | Unified factory for initializing various LLM providers (OpenAI, Anthropic, Google, Ollama). |
| **Logging Config** | `config.py` | Definition of logging formats, file paths, and levels applied globally across the backend. |

## CONVENTIONS

- **Settings Injection**: Never access `os.environ` or hardcode file paths directly. All configurations must be mapped in `config.py` and accessed via the `get_settings()` singleton.
- **I18n-First (No Raw Strings)**: User-facing text must never be hardcoded as raw strings. Always use `get_i18n().get("namespace.key")` to ensure support for both Chinese and English.
- **Lazy Singleton Pattern**: Infrastructure services use lazy initialization. Access them through `get_*()` functions (e.g., `get_i18n()`) rather than importing instances directly.
- **Prompt Isolation**: Prompts must be stored as YAML templates in `src/backend/agents/prompts/` and rendered dynamically via `PromptLoader` to allow for easy tweaking without code changes.

## ANTI-PATTERNS

| Rule | Reason |
|------|--------|
| **NO Hardcoded Configs** | Storing API keys or environment paths in code breaks portability and security. |
| **NO Inline Prompts** | Writing prompt strings inside agent logic makes them hard to update and localize. |
| **NO Direct LLM Init** | Manually creating model objects bypasses the unified configuration and factory logic. |
| **NO Raw Print()** | Using `print()` bypasses the structured logging system, making debugging in production difficult. |

## NOTES

- **Fallback Chain**: The i18n service uses a strict fallback chain: Requested Lang -> Default (cn) -> Missing Placeholder.
- **Jinja2 Strictness**: The `PromptLoader` environment is configured with `StrictUndefined` to catch missing template variables early during the ReAct loop.
- **Legacy Migration**: `config.py` automatically migrates old configuration formats to the new provider-based schema upon loading.
