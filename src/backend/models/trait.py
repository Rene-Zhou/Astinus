"""
Character trait models.

Traits represent character qualities with both positive and negative aspects,
following the double-edged design from GUIDE.md.
"""

from pydantic import BaseModel, Field

from .i18n import LocalizedString


class Trait(BaseModel):
    """
    Character trait with dual aspects and i18n support.

    A trait represents a defining characteristic of a character. Each trait
    has both a positive aspect (how it helps) and a negative aspect (how it
    hinders), creating interesting roleplay consequences.

    Based on weave's Trait model with added i18n support for all text fields.

    Examples:
        >>> trait = Trait(
        ...     name=LocalizedString(cn="优柔寡断", en="Indecisive"),
        ...     description=LocalizedString(
        ...         cn="在行动前总是会思考许多...",
        ...         en="Always thinks through many scenarios..."
        ...     ),
        ...     positive_aspect=LocalizedString(
        ...         cn="能预演各种可能性，做出更明智的决策",
        ...         en="Can anticipate outcomes and make wiser decisions"
        ...     ),
        ...     negative_aspect=LocalizedString(
        ...         cn="常常因为过度思考而错过最佳时机",
        ...         en="Often misses opportunities due to overthinking"
        ...     )
        ... )
        >>> trait.name.get("cn")
        '优柔寡断'
    """

    name: LocalizedString = Field(..., description="Short label for the trait")
    description: LocalizedString = Field(
        ..., description="Full description of the trait with context"
    )
    positive_aspect: LocalizedString = Field(..., description="How this trait helps the character")
    negative_aspect: LocalizedString = Field(
        ..., description="How this trait hinders the character"
    )

    # Compatibility properties for weave-style access
    @property
    def name_cn(self) -> str:
        """Get Chinese name (for backward compatibility)."""
        return self.name.cn

    @property
    def name_en(self) -> str:
        """Get English name (for backward compatibility)."""
        return self.name.en

    def get_name(self, lang: str = "cn") -> str:
        """Get trait name in specified language."""
        return self.name.get(lang)

    def get_description(self, lang: str = "cn") -> str:
        """Get trait description in specified language."""
        return self.description.get(lang)

    def get_positive(self, lang: str = "cn") -> str:
        """Get positive aspect in specified language."""
        return self.positive_aspect.get(lang)

    def get_negative(self, lang: str = "cn") -> str:
        """Get negative aspect in specified language."""
        return self.negative_aspect.get(lang)

    def __str__(self) -> str:
        """Return Chinese name by default."""
        return self.name.cn

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"Trait(name='{self.name.cn}')"
