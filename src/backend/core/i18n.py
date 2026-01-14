"""
Internationalization (i18n) service for loading localized strings.

This module provides a centralized service for loading and accessing
localized strings from JSON files in the locale/ directory.
"""

import json
from pathlib import Path
from typing import Any


class I18nService:
    """
    Centralized localization service.

    Loads all JSON files from locale/{lang}/ directories on initialization
    and provides a get() method to retrieve localized strings with fallback.

    The service follows a fallback chain:
    1. Requested language
    2. Default language (cn)
    3. Error placeholder "[MISSING: key]"

    Examples:
        >>> i18n = I18nService(default_lang="cn")
        >>> i18n.get("system.dice.outcome.critical", lang="cn")
        '大成功'
        >>> i18n.get("system.dice.outcome.critical", lang="en")
        'Critical Success'
        >>> i18n.get("system.dice.outcome.critical", lang="fr")  # Fallback to cn
        '大成功'
    """

    def __init__(self, default_lang: str = "cn", locale_dir: Path | None = None):
        """
        Initialize the i18n service.

        Args:
            default_lang: Default language code (used for fallback)
            locale_dir: Path to locale directory (defaults to project's locale/)
        """
        self.default_lang = default_lang
        self._cache: dict[str, dict[str, Any]] = {}

        # Determine locale directory
        if locale_dir is None:
            # Assume we're in src/backend/core, go up to project root
            project_root = Path(__file__).parent.parent.parent.parent
            locale_dir = project_root / "locale"

        self.locale_dir = Path(locale_dir)

        # Load all locale files
        self._load_all()

    def _load_all(self) -> None:
        """Load all JSON files from locale directories."""
        if not self.locale_dir.exists():
            raise FileNotFoundError(f"Locale directory not found: {self.locale_dir}")

        # Load for each supported language
        for lang_code in ["cn", "en"]:
            lang_dir = self.locale_dir / lang_code
            if not lang_dir.exists():
                continue

            # Load all JSON files in this language directory
            for json_file in lang_dir.glob("*.json"):
                namespace = json_file.stem  # e.g., "common", "system"
                cache_key = f"{lang_code}.{namespace}"

                try:
                    with open(json_file, encoding="utf-8") as f:
                        self._cache[cache_key] = json.load(f)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON in {json_file}: {exc}") from exc

    def get(self, key: str, lang: str | None = None, **kwargs: Any) -> str:
        """
        Get localized string with fallback.

        Args:
            key: Dot-separated key (e.g., "system.dice.outcome.critical")
            lang: Language code (cn/en). If None, uses default_lang.
            **kwargs: Optional format arguments for string interpolation

        Returns:
            Localized string, or fallback if not found

        Examples:
            >>> i18n.get("system.dice.outcome.critical", lang="cn")
            '大成功'
            >>> i18n.get("system.error.not_found", player="张伟")
            '玩家 张伟 未找到'
        """
        lang = lang or self.default_lang

        try:
            # Parse key: "system.dice.outcome.critical"
            # -> namespace="system", path=["dice", "outcome", "critical"]
            parts = key.split(".")
            if len(parts) < 2:
                raise KeyError(f"Invalid key format: {key}")

            namespace = parts[0]
            path = parts[1:]

            # Get data from cache
            cache_key = f"{lang}.{namespace}"
            data = self._cache.get(cache_key)

            if data is None:
                raise KeyError(f"Namespace not found: {cache_key}")

            # Navigate through nested structure
            for segment in path:
                data = data[segment]

            # If data is a string, return it (with optional formatting)
            if isinstance(data, str):
                return data.format(**kwargs) if kwargs else data

            # If data is not a string, something is wrong
            raise ValueError(f"Key '{key}' does not point to a string: {type(data)}")

        except (KeyError, TypeError):
            # Fallback to default language if different
            if lang != self.default_lang:
                try:
                    return self.get(key, self.default_lang, **kwargs)
                except (KeyError, TypeError, ValueError):
                    pass  # Fall through to error placeholder

            # Return error placeholder
            return f"[MISSING: {key}]"

    def has_key(self, key: str, lang: str | None = None) -> bool:
        """
        Check if a key exists.

        Args:
            key: Dot-separated key
            lang: Language code (cn/en)

        Returns:
            True if key exists
        """
        result = self.get(key, lang)
        return not result.startswith("[MISSING:")

    def get_namespace(self, namespace: str, lang: str | None = None) -> dict[str, Any]:
        """
        Get entire namespace as dictionary.

        Args:
            namespace: Namespace name (e.g., "system", "common")
            lang: Language code

        Returns:
            Dictionary with all keys in namespace

        Examples:
            >>> dice_text = i18n.get_namespace("system.dice", lang="cn")
            >>> dice_text["outcome"]["critical"]
            '大成功'
        """
        lang = lang or self.default_lang
        cache_key = f"{lang}.{namespace}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try to navigate if it's a nested namespace
        try:
            parts = namespace.split(".")
            if len(parts) < 2:
                raise KeyError(f"Namespace not found: {namespace}")

            root_namespace = parts[0]
            path = parts[1:]

            cache_key = f"{lang}.{root_namespace}"
            data = self._cache.get(cache_key)

            if data is None:
                raise KeyError(f"Root namespace not found: {root_namespace}")

            # Navigate to nested namespace
            for segment in path:
                data = data[segment]

            return data

        except (KeyError, TypeError):
            if lang != self.default_lang:
                return self.get_namespace(namespace, self.default_lang)
            return {}

    def reload(self) -> None:
        """Reload all locale files from disk."""
        self._cache.clear()
        self._load_all()


# Global singleton instance
# This can be imported and used throughout the application
_global_i18n: I18nService | None = None


def get_i18n() -> I18nService:
    """
    Get the global i18n service instance.

    Creates the instance on first call (lazy initialization).

    Returns:
        Global I18nService instance
    """
    global _global_i18n
    if _global_i18n is None:
        _global_i18n = I18nService()
    return _global_i18n


def reset_i18n() -> None:
    """Reset the global i18n instance (useful for testing)."""
    global _global_i18n
    _global_i18n = None
