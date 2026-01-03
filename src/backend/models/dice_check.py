"""
Dice check request models.

Defines the DiceCheckRequest schema that Rule Agent generates and
frontend displays to the player, per GUIDE.md specifications.
"""

from typing import Any

from pydantic import BaseModel, Field

from .i18n import LocalizedString


class DiceCheckRequest(BaseModel):
    """
    Request for player to roll dice - sent from Rule Agent to frontend.

    This schema follows the format defined in GUIDE.md (line 390-397).
    The Rule Agent analyzes the player's action and generates this request,
    which the frontend displays to show:
    - What the player is trying to do
    - Which traits/tags are affecting the roll
    - The dice formula (e.g., "2d6", "3d6kl2")
    - Why these modifiers apply

    Examples:
        >>> check = DiceCheckRequest(
        ...     intention="逃离这个房间",
        ...     influencing_factors={
        ...         "traits": [],
        ...         "tags": ["右腿受伤"]
        ...     },
        ...     dice_formula="3d6kl2",
        ...     instructions=LocalizedString(
        ...         cn="由于右腿受伤，你在逃离这个房间的检定上有劣势",
        ...         en="Due to leg injury, you have disadvantage on this check"
        ...     )
        ... )
        >>> check.dice_formula
        '3d6kl2'
    """

    intention: str = Field(
        ..., description="What the player is trying to do (in Chinese)"
    )
    influencing_factors: dict[str, list[str]] = Field(
        ...,
        description="Factors affecting the roll: {'traits': [...], 'tags': [...]}"
    )
    dice_formula: str = Field(
        ...,
        description="Dice notation (e.g., '2d6', '3d6kh2', '3d6kl2')"
    )
    instructions: LocalizedString = Field(
        ..., description="Explanation of why these modifiers apply"
    )

    def to_display(self, lang: str = "cn") -> dict[str, Any]:
        """
        Format for frontend display.

        Args:
            lang: Language code ("cn" or "en")

        Returns:
            Dictionary with all display information:
            - intention: What player is trying
            - factors: Influencing traits/tags
            - dice: Dice formula
            - explanation: Why modifiers apply

        Examples:
            >>> display = check.to_display("cn")
            >>> display["dice"]
            '3d6kl2'
        """
        return {
            "intention": self.intention,
            "factors": self.influencing_factors,
            "dice": self.dice_formula,
            "explanation": self.instructions.get(lang),
        }

    def has_advantage(self) -> bool:
        """
        Check if this is an advantage roll (bonus dice).

        Returns:
            True if dice formula includes "kh2" (keep highest 2)
        """
        return "kh2" in self.dice_formula

    def has_disadvantage(self) -> bool:
        """
        Check if this is a disadvantage roll (penalty dice).

        Returns:
            True if dice formula includes "kl2" (keep lowest 2)
        """
        return "kl2" in self.dice_formula

    def get_dice_count(self) -> int:
        """
        Extract number of dice to roll from formula.

        Returns:
            Number of dice (e.g., 2 for "2d6", 3 for "3d6kh2")
        """
        # Extract number before "d6"
        if "d6" in self.dice_formula:
            num_str = self.dice_formula.split("d6")[0]
            return int(num_str)
        return 2  # Default

    def __str__(self) -> str:
        """Return Chinese display string."""
        display = self.to_display("cn")
        return f"{display['intention']} - {display['dice']} - {display['explanation']}"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"DiceCheckRequest(intention='{self.intention}', dice='{self.dice_formula}')"


class DiceCheckResponse(BaseModel):
    """
    Player's response to a dice check request.

    After the frontend displays the DiceCheckRequest and the player rolls,
    this response is sent back to the backend with the result.

    The player can:
    1. Accept and roll (provides dice result)
    2. Argue for advantage (provides claim about how trait helps)
    3. Cancel the check

    Examples:
        >>> response = DiceCheckResponse(
        ...     action="roll",
        ...     dice_result={
        ...         "all_rolls": [6, 5],
        ...         "kept_rolls": [6, 5],
        ...         "total": 11,
        ...         "outcome": "success"
        ...     }
        ... )
    """

    action: str = Field(
        ...,
        description="Action taken: 'roll', 'argue', or 'cancel'"
    )
    dice_result: dict[str, Any] | None = Field(
        default=None,
        description="DiceResult as dict (if action='roll')"
    )
    argument: str | None = Field(
        default=None,
        description="Player's argument for advantage (if action='argue')"
    )
    trait_claimed: str | None = Field(
        default=None,
        description="Which trait player claims helps (if action='argue')"
    )
