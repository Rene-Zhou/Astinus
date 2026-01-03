"""
Internationalization (i18n) support for multi-language strings.

This module provides the LocalizedString class for storing and accessing
text in multiple languages with fallback support.
"""

from pydantic import BaseModel, Field


class LocalizedString(BaseModel):
    """
    Multi-language string with fallback support.

    Stores text in both Chinese (cn) and English (en), with a get() method
    that returns the requested language or falls back to Chinese.

    Examples:
        >>> text = LocalizedString(cn="你好", en="Hello")
        >>> text.get("cn")
        '你好'
        >>> text.get("en")
        'Hello'
        >>> text.get("fr")  # Falls back to cn
        '你好'
    """

    cn: str = Field(..., description="Chinese (simplified) text")
    en: str = Field(..., description="English text")

    def get(self, lang: str = "cn") -> str:
        """
        Get localized string with fallback.

        Args:
            lang: Language code ("cn" or "en"). Defaults to "cn".

        Returns:
            The text in the requested language, or Chinese if not available.
        """
        if lang == "en" and self.en:
            return self.en
        return self.cn

    def __str__(self) -> str:
        """Return Chinese version by default."""
        return self.cn

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"LocalizedString(cn='{self.cn}', en='{self.en}')"
