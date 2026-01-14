"""
Player character models.

Defines the PlayerCharacter class with pure trait-based design
(no numerical attributes), following GUIDE.md specifications.
"""

from pydantic import BaseModel, Field, field_validator

from .i18n import LocalizedString
from .trait import Trait


class PlayerCharacter(BaseModel):
    """
    Player character - pure trait-based design.

    Based on weave's PlayerCharacter with modifications per GUIDE.md:
    - Uses "tags" instead of "conditions" for status effects
    - Concept field uses LocalizedString for i18n
    - Keeps fate point system from weave (proven mechanic)

    A character is defined by:
    - A core concept (one-sentence description)
    - 1-4 traits (defining characteristics with dual aspects)
    - Tags (status effects like "右腿受伤", "疲惫")
    - Fate points (narrative currency, 3 starting, max 5)

    Examples:
        >>> character = PlayerCharacter(
        ...     name="张伟",
        ...     concept=LocalizedString(cn="失业的建筑师", en="Unemployed Architect"),
        ...     traits=[
        ...         Trait(
        ...             name=LocalizedString(cn="运动健将", en="Athletic"),
        ...             description=LocalizedString(cn="...", en="..."),
        ...             positive_aspect=LocalizedString(cn="...", en="..."),
        ...             negative_aspect=LocalizedString(cn="...", en="...")
        ...         )
        ...     ],
        ...     fate_points=3,
        ...     tags=[]
        ... )
        >>> character.add_tag("右腿受伤")
        >>> "右腿受伤" in character.tags
        True
    """

    name: str = Field(..., description="Character name (proper noun, not localized)")
    concept: LocalizedString = Field(..., description="One-sentence character concept")
    traits: list[Trait] = Field(
        ..., description="Character traits (1-4 traits)", min_length=1, max_length=4
    )
    fate_points: int = Field(default=3, ge=0, le=5, description="Narrative influence points (0-5)")
    tags: list[str] = Field(default_factory=list, description="Status effects and conditions")

    @field_validator("traits")
    @classmethod
    def validate_traits_count(cls, v: list[Trait]) -> list[Trait]:
        """Ensure character has 1-4 traits."""
        if not 1 <= len(v) <= 4:
            raise ValueError("Character must have between 1 and 4 traits")
        return v

    def add_tag(self, tag: str) -> None:
        """
        Add a status tag to the character.

        Args:
            tag: Status effect (e.g., "右腿受伤", "疲惫", "中毒")
        """
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """
        Remove a status tag from the character.

        Args:
            tag: Status effect to remove
        """
        if tag in self.tags:
            self.tags.remove(tag)

    def has_tag(self, tag: str) -> bool:
        """
        Check if character has a specific tag.

        Args:
            tag: Status effect to check

        Returns:
            True if character has the tag
        """
        return tag in self.tags

    def spend_fate_point(self) -> bool:
        """
        Spend a fate point (if available).

        Returns:
            True if fate point was spent, False if none available
        """
        if self.fate_points > 0:
            self.fate_points -= 1
            return True
        return False

    def gain_fate_point(self) -> bool:
        """
        Gain a fate point (up to max 5).

        Returns:
            True if fate point was gained, False if already at max
        """
        if self.fate_points < 5:
            self.fate_points += 1
            return True
        return False

    def get_concept(self, lang: str = "cn") -> str:
        """Get character concept in specified language."""
        return self.concept.get(lang)

    def __str__(self) -> str:
        """Return character name."""
        return self.name

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"PlayerCharacter(name='{self.name}', traits={len(self.traits)}, fate={self.fate_points})"
