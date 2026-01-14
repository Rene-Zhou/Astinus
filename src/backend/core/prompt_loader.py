"""
Prompt template loader for agent prompts.

Loads YAML-based prompt templates with support for:
- Jinja2 templating for dynamic content
- Multi-language (cn/en) in single file
- Versioned prompts for A/B testing
"""

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined


class PromptTemplate:
    """
    A prompt template with multi-language support.

    Attributes:
        name: Template name
        data: Raw template data from YAML
        env: Jinja2 environment for rendering

    Examples:
        >>> template = PromptTemplate("rule_agent", data)
        >>> prompt = template.render("cn", action="逃跑")
    """

    def __init__(self, name: str, data: dict[str, Any]):
        """
        Initialize prompt template.

        Args:
            name: Template name (e.g., "rule_agent")
            data: Template data from YAML file
        """
        self.name = name
        self.data = data

        # Create Jinja2 environment
        self.env = Environment(
            autoescape=False,  # Don't escape for prompts
            undefined=StrictUndefined,  # Raise error on undefined variables
            trim_blocks=True,  # Remove first newline after block
            lstrip_blocks=True,  # Strip leading spaces before blocks
        )

    def render(self, lang: str = "cn", **kwargs: Any) -> str:
        """
        Render the prompt template for a specific language.

        Args:
            lang: Language code ("cn" or "en")
            **kwargs: Template variables for Jinja2

        Returns:
            Rendered prompt string

        Raises:
            KeyError: If language not found or required field missing
            jinja2.UndefinedError: If template variable undefined

        Examples:
            >>> template.render("cn", player_name="张伟", action="逃跑")
            "你是规则裁判。玩家张伟想要逃跑。判断是否需要检定。"
        """
        # Get language-specific data
        if lang not in self.data:
            raise KeyError(f"Language '{lang}' not found in template '{self.name}'")

        lang_data = self.data[lang]

        # Build prompt from sections
        sections = []

        # Add role section (required)
        if "role" in lang_data:
            role_template = self.env.from_string(lang_data["role"])
            sections.append(role_template.render(**kwargs))

        # Add guidelines (if present)
        if "guidelines" in lang_data:
            guidelines = lang_data["guidelines"]
            if isinstance(guidelines, list):
                sections.append("\n".join(f"- {g}" for g in guidelines))
            elif isinstance(guidelines, str):
                sections.append(guidelines)

        # Add context (if present and provided)
        if "context" in lang_data and kwargs:
            context_template = self.env.from_string(lang_data["context"])
            sections.append(context_template.render(**kwargs))

        # Add task (required)
        if "task" in lang_data:
            task_template = self.env.from_string(lang_data["task"])
            sections.append(task_template.render(**kwargs))

        # Join sections with double newline
        return "\n\n".join(s for s in sections if s)

    def get_system_message(self, lang: str = "cn", **kwargs: Any) -> str:
        """
        Get the system message portion (role + rules + format + information_control).

        Args:
            lang: Language code
            **kwargs: Template variables

        Returns:
            System message string
        """
        lang_data = self.data.get(lang, {})
        sections = []

        if "role" in lang_data:
            role_template = self.env.from_string(lang_data["role"])
            sections.append(role_template.render(**kwargs))

        if "react_instructions" in lang_data:
            template = self.env.from_string(lang_data["react_instructions"])
            sections.append(template.render(**kwargs))

        if "decision_flow" in lang_data:
            template = self.env.from_string(lang_data["decision_flow"])
            sections.append(template.render(**kwargs))

        if "chain_of_thought" in lang_data:
            template = self.env.from_string(lang_data["chain_of_thought"])
            sections.append(template.render(**kwargs))

        if "npc_rules" in lang_data:
            template = self.env.from_string(lang_data["npc_rules"])
            sections.append(template.render(**kwargs))

        if "scene_transition_rules" in lang_data:
            template = self.env.from_string(lang_data["scene_transition_rules"])
            sections.append(template.render(**kwargs))

        if "response_format" in lang_data:
            template = self.env.from_string(lang_data["response_format"])
            sections.append(template.render(**kwargs))

        if "information_control" in lang_data:
            info_control_template = self.env.from_string(lang_data["information_control"])
            sections.append(info_control_template.render(**kwargs))

        return "\n\n".join(sections)

    def get_user_message(self, lang: str = "cn", **kwargs: Any) -> str:
        """
        Get the user message portion (context + task).

        Args:
            lang: Language code
            **kwargs: Template variables

        Returns:
            User message string
        """
        lang_data = self.data.get(lang, {})
        sections = []

        if "context" in lang_data and kwargs:
            context_template = self.env.from_string(lang_data["context"])
            sections.append(context_template.render(**kwargs))

        if "task" in lang_data:
            task_template = self.env.from_string(lang_data["task"])
            sections.append(task_template.render(**kwargs))

        return "\n\n".join(s for s in sections if s)


class PromptLoader:
    """
    Loader for agent prompt templates.

    Loads YAML prompt files from a directory and provides access
    to templates with caching.

    Examples:
        >>> loader = PromptLoader()
        >>> template = loader.get_template("rule_agent")
        >>> prompt = template.render("cn", action="逃跑")
    """

    def __init__(self, prompts_dir: Path | None = None):
        """
        Initialize prompt loader.

        Args:
            prompts_dir: Directory containing prompt YAML files.
                        Defaults to src/backend/agents/prompts/
        """
        if prompts_dir is None:
            # Default to project's prompts directory
            project_root = Path(__file__).parent.parent.parent.parent
            prompts_dir = project_root / "src" / "backend" / "agents" / "prompts"

        self.prompts_dir = Path(prompts_dir)
        self._cache: dict[str, PromptTemplate] = {}

    def get_template(self, name: str) -> PromptTemplate:
        """
        Get a prompt template by name.

        Args:
            name: Template name (filename without .yaml)

        Returns:
            PromptTemplate instance

        Raises:
            FileNotFoundError: If template file doesn't exist
            yaml.YAMLError: If YAML is invalid

        Examples:
            >>> loader = PromptLoader()
            >>> template = loader.get_template("rule_agent")
        """
        # Check cache
        if name in self._cache:
            return self._cache[name]

        # Load from file
        template_path = self.prompts_dir / f"{name}.yaml"

        if not template_path.exists():
            raise FileNotFoundError(
                f"Prompt template not found: {template_path}\n"
                f"Available templates: {self.list_templates()}"
            )

        with open(template_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Create and cache template
        template = PromptTemplate(name, data)
        self._cache[name] = template

        return template

    def list_templates(self) -> list[str]:
        """
        List all available prompt templates.

        Returns:
            List of template names (without .yaml extension)

        Examples:
            >>> loader.list_templates()
            ['rule_agent', 'gm_agent', 'npc_agent']
        """
        if not self.prompts_dir.exists():
            return []

        return [p.stem for p in self.prompts_dir.glob("*.yaml") if p.is_file()]

    def reload(self) -> None:
        """
        Clear cache and reload all templates.

        Useful for development when templates are modified.
        """
        self._cache.clear()


# Global loader instance
_global_loader: PromptLoader | None = None


def get_prompt_loader(prompts_dir: Path | None = None) -> PromptLoader:
    """
    Get global prompt loader instance.

    Args:
        prompts_dir: Optional custom prompts directory

    Returns:
        PromptLoader instance

    Examples:
        >>> loader = get_prompt_loader()
        >>> template = loader.get_template("rule_agent")
    """
    global _global_loader

    if _global_loader is None or prompts_dir is not None:
        _global_loader = PromptLoader(prompts_dir)

    return _global_loader


def reset_prompt_loader() -> None:
    """Reset global prompt loader (mainly for testing)."""
    global _global_loader
    _global_loader = None
