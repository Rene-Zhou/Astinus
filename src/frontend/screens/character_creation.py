"""
Character creation screen - create a new character.

Based on GUIDE.md Section 3 - Pure trait-based system:
- Character name input
- Core concept (free-form one-sentence description)
- 1-3 Traits (each with name, description, positive_aspect, negative_aspect)
- Supports "边玩边建卡" mode where traits can be added later

No numerical attributes, no HP/MP - status tracked via Tags.
"""

from typing import Any, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static, TextArea

# Character creation settings
MAX_NAME_LENGTH = 50
MAX_CONCEPT_LENGTH = 200
MIN_TRAITS = 0  # Support "边玩边建卡" - can start with 0 traits
MAX_TRAITS = 4
INITIAL_FATE_POINTS = 3


class TraitEditor(Static):
    """
    A widget for editing a single trait.

    Each trait has:
    - name: Short label
    - description: Full description
    - positive_aspect: How it helps
    - negative_aspect: How it hinders
    """

    DEFAULT_CSS = """
    TraitEditor {
        width: 100%;
        height: auto;
        padding: 1;
        margin: 1 0;
        border: solid $accent;
        background: $surface;
    }

    TraitEditor .trait-header {
        width: 100%;
        height: 2;
        text-style: bold;
        color: $accent;
    }

    TraitEditor .trait-field-label {
        width: 100%;
        height: 1;
        color: $text-muted;
        margin-top: 1;
    }

    TraitEditor Input {
        width: 100%;
        margin: 0 0 1 0;
    }

    TraitEditor TextArea {
        width: 100%;
        height: 3;
        margin: 0 0 1 0;
    }

    TraitEditor .remove-btn {
        width: 100%;
        height: 3;
        background: $error;
        margin-top: 1;
    }

    TraitEditor .remove-btn:hover {
        background: $error-darken-1;
    }
    """

    def __init__(self, trait_index: int, *args, **kwargs) -> None:
        """
        Initialize the trait editor.

        Args:
            trait_index: Index of this trait (0-3)
        """
        super().__init__(*args, **kwargs)
        self.trait_index = trait_index
        self._name = ""
        self._description = ""
        self._positive = ""
        self._negative = ""

    def compose(self) -> ComposeResult:
        """Compose the trait editor layout."""
        yield Label(
            f"特质 {self.trait_index + 1} / Trait {self.trait_index + 1}", classes="trait-header"
        )

        yield Label("名称 / Name:", classes="trait-field-label")
        yield Input(
            placeholder="例: 优柔寡断 / e.g., Indecisive",
            id=f"trait-{self.trait_index}-name",
        )

        yield Label("描述 / Description:", classes="trait-field-label")
        yield Input(
            placeholder="详细描述这个特质...",
            id=f"trait-{self.trait_index}-desc",
        )

        yield Label("正面 / Positive Aspect:", classes="trait-field-label")
        yield Input(
            placeholder="这个特质如何帮助角色...",
            id=f"trait-{self.trait_index}-positive",
        )

        yield Label("负面 / Negative Aspect:", classes="trait-field-label")
        yield Input(
            placeholder="这个特质如何阻碍角色...",
            id=f"trait-{self.trait_index}-negative",
        )

        yield Button(
            "移除此特质 / Remove Trait",
            id=f"btn-remove-trait-{self.trait_index}",
            classes="remove-btn",
        )

    def get_trait_data(self) -> Optional[Dict[str, Any]]:
        """
        Get trait data if valid.

        Returns:
            Trait data dict or None if empty/invalid
        """
        if not self._name.strip():
            return None

        return {
            "name": {"cn": self._name.strip(), "en": self._name.strip()},
            "description": {"cn": self._description.strip(), "en": self._description.strip()},
            "positive_aspect": {"cn": self._positive.strip(), "en": self._positive.strip()},
            "negative_aspect": {"cn": self._negative.strip(), "en": self._negative.strip()},
        }

    def set_trait_data(self, data: Dict[str, Any]) -> None:
        """
        Set trait data from dict.

        Args:
            data: Trait data dictionary
        """
        name = data.get("name", {})
        self._name = name.get("cn", "") if isinstance(name, dict) else str(name)

        desc = data.get("description", {})
        self._description = desc.get("cn", "") if isinstance(desc, dict) else str(desc)

        pos = data.get("positive_aspect", {})
        self._positive = pos.get("cn", "") if isinstance(pos, dict) else str(pos)

        neg = data.get("negative_aspect", {})
        self._negative = neg.get("cn", "") if isinstance(neg, dict) else str(neg)

        # Update inputs
        try:
            self.query_one(f"#trait-{self.trait_index}-name", Input).value = self._name
            self.query_one(f"#trait-{self.trait_index}-desc", Input).value = self._description
            self.query_one(f"#trait-{self.trait_index}-positive", Input).value = self._positive
            self.query_one(f"#trait-{self.trait_index}-negative", Input).value = self._negative
        except Exception:
            pass

    def is_empty(self) -> bool:
        """Check if all fields are empty."""
        return not any([self._name, self._description, self._positive, self._negative])

    def is_complete(self) -> bool:
        """Check if all required fields are filled."""
        return all(
            [
                self._name.strip(),
                self._description.strip(),
                self._positive.strip(),
                self._negative.strip(),
            ]
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        input_id = event.input.id or ""

        if f"trait-{self.trait_index}-name" in input_id:
            self._name = event.value
        elif f"trait-{self.trait_index}-desc" in input_id:
            self._description = event.value
        elif f"trait-{self.trait_index}-positive" in input_id:
            self._positive = event.value
        elif f"trait-{self.trait_index}-negative" in input_id:
            self._negative = event.value


class CharacterCreationScreen(Screen):
    """
    Character creation screen using trait-based system.

    Based on GUIDE.md Section 3:
    - No numerical attributes
    - Characters defined by concept + traits
    - Supports "边玩边建卡" (create traits during play)

    Layout:
    - Top: Title
    - Middle: Name input, concept input, traits
    - Bottom: Validation and action buttons
    """

    TITLE = "Create Character"

    BINDINGS = [
        ("escape", "back", "Back"),
        ("enter", "confirm", "Confirm"),
    ]

    DEFAULT_CSS = """
    CharacterCreationScreen {
        background: $background;
        align: center middle;
    }

    #creation-container {
        width: 90;
        height: auto;
        max-height: 95%;
        padding: 2;
        background: $panel;
        border: solid $accent;
    }

    #creation-scroll {
        width: 100%;
        height: auto;
        max-height: 80%;
    }

    #creation-title {
        width: 100%;
        height: 3;
        text-align: center;
        text-style: bold;
        color: $accent;
        padding: 1;
    }

    .section-title {
        width: 100%;
        height: 2;
        text-style: bold;
        color: $primary;
        margin-top: 1;
        border-bottom: solid $primary;
    }

    .section-hint {
        width: 100%;
        height: auto;
        color: $text-muted;
        margin-bottom: 1;
    }

    #name-input {
        width: 100%;
        margin: 1 0;
    }

    #concept-input {
        width: 100%;
        margin: 1 0;
    }

    #traits-container {
        width: 100%;
        height: auto;
        padding: 1 0;
    }

    #add-trait-btn {
        width: 100%;
        height: 3;
        background: $success;
        margin: 1 0;
    }

    #add-trait-btn:hover {
        background: $success-darken-1;
    }

    #add-trait-btn:disabled {
        background: $surface;
        color: $text-muted;
    }

    .fate-points-display {
        width: 100%;
        height: 2;
        text-align: center;
        color: $warning;
        text-style: bold;
        margin: 1 0;
    }

    #validation-errors {
        width: 100%;
        min-height: 2;
        color: $error;
        padding: 1;
        margin: 1 0;
    }

    .action-button {
        width: 20;
        height: 3;
        margin: 1;
    }

    #action-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 2;
    }

    #btn-confirm {
        background: $success;
    }

    #btn-confirm:hover {
        background: $success-darken-1;
    }

    #btn-back {
        background: $error;
    }

    #btn-back:hover {
        background: $error-darken-1;
    }

    .mode-toggle {
        width: 100%;
        height: 3;
        margin: 1 0;
        text-align: center;
    }

    #mode-toggle-btn {
        width: 100%;
        background: $primary;
    }

    #mode-toggle-btn:hover {
        background: $primary-darken-1;
    }
    """

    # Reactive state
    character_name: str = reactive("")
    character_concept: str = reactive("")
    trait_count: int = reactive(1)  # Start with 1 trait editor
    build_on_fly_mode: bool = reactive(False)  # 边玩边建卡 mode
    validation_errors: List[str] = reactive(list)

    class CharacterCreated(Message):
        """Message sent when character is created successfully."""

        def __init__(self, character_data: Dict[str, Any]) -> None:
            self.character_data = character_data
            super().__init__()

    def __init__(self) -> None:
        """Initialize the character creation screen."""
        super().__init__()
        self._traits: List[TraitEditor] = []

    def compose(self) -> ComposeResult:
        """Compose the character creation screen layout."""
        with Center():
            with Container(id="creation-container"):
                yield Label("⚔️ 创建角色 / Create Character ⚔️", id="creation-title")

                with ScrollableContainer(id="creation-scroll"):
                    # Name section
                    yield Label("角色名称 / Character Name", classes="section-title")
                    yield Input(
                        placeholder="输入角色名称... / Enter character name...",
                        id="name-input",
                        max_length=MAX_NAME_LENGTH,
                    )

                    # Concept section
                    yield Label("核心概念 / Core Concept", classes="section-title")
                    yield Static(
                        "用一句话描述你的角色（如：失业的建筑师、只会炼金术的法师）",
                        classes="section-hint",
                    )
                    yield Input(
                        placeholder="例: 失业的建筑师 / e.g., Unemployed Architect",
                        id="concept-input",
                        max_length=MAX_CONCEPT_LENGTH,
                    )

                    # Build-on-fly mode toggle
                    yield Label("创建模式 / Creation Mode", classes="section-title")
                    with Horizontal(classes="mode-toggle"):
                        yield Button(
                            "切换到边玩边建卡模式 / Switch to Build-on-Fly Mode",
                            id="mode-toggle-btn",
                        )

                    # Fate points display
                    yield Label(
                        f"⭐ 命运点 / Fate Points: {INITIAL_FATE_POINTS}",
                        id="fate-points-display",
                        classes="fate-points-display",
                    )

                    # Traits section
                    yield Label("角色特质 / Character Traits", classes="section-title")
                    yield Static(
                        "每个特质都有正面和负面两个方面。初始可有1-3个特质，游戏中可获得更多（最多4个）。",
                        classes="section-hint",
                    )

                    with Vertical(id="traits-container"):
                        # Initial trait editor
                        yield TraitEditor(0, id="trait-editor-0")

                    yield Button(
                        "➕ 添加特质 / Add Trait",
                        id="add-trait-btn",
                    )

                # Validation errors
                yield Static("", id="validation-errors")

                # Action buttons
                with Horizontal(id="action-buttons"):
                    yield Button("← 返回 / Back", id="btn-back", classes="action-button")
                    yield Button("确认 ✓ / Confirm", id="btn-confirm", classes="action-button")

    def on_mount(self) -> None:
        """Called when screen mounts."""
        # Focus the name input
        self.query_one("#name-input", Input).focus()
        # Store reference to first trait editor
        self._traits = [self.query_one("#trait-editor-0", TraitEditor)]
        self._update_add_button_state()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        input_id = event.input.id or ""

        if input_id == "name-input":
            self.character_name = event.value
        elif input_id == "concept-input":
            self.character_concept = event.value

        self._update_validation()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id or ""

        if button_id == "btn-back":
            self.action_back()
        elif button_id == "btn-confirm":
            self.action_confirm()
        elif button_id == "add-trait-btn":
            self._add_trait()
        elif button_id == "mode-toggle-btn":
            self._toggle_build_mode()
        elif button_id.startswith("btn-remove-trait-"):
            try:
                trait_index = int(button_id.split("-")[-1])
                self._remove_trait(trait_index)
            except (ValueError, IndexError):
                pass

    def _toggle_build_mode(self) -> None:
        """Toggle 边玩边建卡 mode."""
        self.build_on_fly_mode = not self.build_on_fly_mode

        try:
            btn = self.query_one("#mode-toggle-btn", Button)
            if self.build_on_fly_mode:
                btn.label = "当前: 边玩边建卡模式 ✓ / Current: Build-on-Fly Mode ✓"
                self.notify(
                    "边玩边建卡模式已启用！你可以不填写特质直接开始游戏。",
                    title="模式切换",
                )
            else:
                btn.label = "切换到边玩边建卡模式 / Switch to Build-on-Fly Mode"
                self.notify(
                    "标准模式已启用。请至少填写一个完整的特质。",
                    title="模式切换",
                )
        except Exception:
            pass

        self._update_validation()

    def _add_trait(self) -> None:
        """Add a new trait editor."""
        if len(self._traits) >= MAX_TRAITS:
            self.notify(f"最多只能有 {MAX_TRAITS} 个特质", severity="warning")
            return

        new_index = len(self._traits)
        new_editor = TraitEditor(new_index, id=f"trait-editor-{new_index}")

        try:
            container = self.query_one("#traits-container", Vertical)
            container.mount(new_editor)
            self._traits.append(new_editor)
            self.trait_count = len(self._traits)
            self._update_add_button_state()
            self._update_validation()
        except Exception as e:
            self.log(f"Error adding trait: {e}")

    def _remove_trait(self, trait_index: int) -> None:
        """
        Remove a trait editor.

        Args:
            trait_index: Index of trait to remove
        """
        if len(self._traits) <= MIN_TRAITS and not self.build_on_fly_mode:
            self.notify("至少需要一个特质", severity="warning")
            return

        # Find and remove the trait editor
        for i, editor in enumerate(self._traits):
            if editor.trait_index == trait_index:
                editor.remove()
                self._traits.pop(i)
                break

        # Re-index remaining traits
        self._reindex_traits()
        self.trait_count = len(self._traits)
        self._update_add_button_state()
        self._update_validation()

    def _reindex_traits(self) -> None:
        """Re-index trait editors after removal."""
        # This is a simplified approach - in production you might want to
        # preserve trait data and just update indices
        pass

    def _update_add_button_state(self) -> None:
        """Update the add trait button state."""
        try:
            btn = self.query_one("#add-trait-btn", Button)
            btn.disabled = len(self._traits) >= MAX_TRAITS
        except Exception:
            pass

    def action_back(self) -> None:
        """Go back to menu."""
        if self.app:
            self.app.pop_screen()

    def go_back(self) -> None:
        """Alternative method to go back."""
        self.action_back()

    def action_confirm(self) -> None:
        """Confirm character creation."""
        if self.is_valid():
            character_data = self.get_character_data()
            self.post_message(self.CharacterCreated(character_data))
            # Transition to game
            if self.app:
                self.app.call_later(lambda: self._start_game_with_character(character_data))
        else:
            self._update_validation()
            self.notify(
                "请修正验证错误 / Please fix validation errors",
                title="角色无效 / Invalid Character",
                severity="error",
            )

    def confirm_character(self) -> None:
        """Alternative method to confirm character."""
        self.action_confirm()

    async def _start_game_with_character(self, character_data: Dict[str, Any]) -> None:
        """
        Start the game with the created character.

        Args:
            character_data: Character data dictionary
        """
        if self.app:
            # Store character data
            if hasattr(self.app, "player_character"):
                self.app.player_character = character_data

            # Start new game
            success = await self.app.start_new_game()
            if success:
                self.app.switch_screen("game")
            else:
                self.notify(
                    "无法启动游戏 / Failed to start game",
                    title="错误 / Error",
                    severity="error",
                )

    def set_name(self, name: str) -> None:
        """
        Set character name.

        Args:
            name: Character name
        """
        self.character_name = name[:MAX_NAME_LENGTH]
        try:
            self.query_one("#name-input", Input).value = self.character_name
        except Exception:
            pass

    def set_concept(self, concept: str) -> None:
        """
        Set character concept.

        Args:
            concept: Character concept string
        """
        self.character_concept = concept[:MAX_CONCEPT_LENGTH]
        try:
            self.query_one("#concept-input", Input).value = self.character_concept
        except Exception:
            pass

    def add_trait(self, trait_data: Dict[str, Any]) -> bool:
        """
        Add a trait with data.

        Args:
            trait_data: Trait data dictionary

        Returns:
            True if added successfully
        """
        if len(self._traits) >= MAX_TRAITS:
            return False

        # Add new editor if needed
        if len(self._traits) == 0 or self._traits[-1].is_complete():
            self._add_trait()

        # Set data on the last editor
        if self._traits:
            self._traits[-1].set_trait_data(trait_data)
            return True

        return False

    def validate_name(self, name: str) -> bool:
        """
        Validate character name.

        Args:
            name: Name to validate

        Returns:
            True if valid
        """
        if not name or not name.strip():
            return False
        if len(name) > MAX_NAME_LENGTH:
            return False
        return True

    def validate_concept(self, concept: str) -> bool:
        """
        Validate character concept.

        Args:
            concept: Concept to validate

        Returns:
            True if valid
        """
        if not concept or not concept.strip():
            return False
        if len(concept) > MAX_CONCEPT_LENGTH:
            return False
        return True

    def is_valid(self) -> bool:
        """
        Check if character is valid for creation.

        Returns:
            True if valid
        """
        return len(self.get_validation_errors()) == 0

    def get_validation_errors(self) -> List[str]:
        """
        Get list of validation errors.

        Returns:
            List of error messages
        """
        errors = []

        # Check name
        if not self.character_name or not self.character_name.strip():
            errors.append("角色名称必填 / Character name is required")
        elif len(self.character_name) > MAX_NAME_LENGTH:
            errors.append(f"名称不能超过 {MAX_NAME_LENGTH} 个字符")

        # Check concept
        if not self.character_concept or not self.character_concept.strip():
            errors.append("核心概念必填 / Core concept is required")
        elif len(self.character_concept) > MAX_CONCEPT_LENGTH:
            errors.append(f"概念不能超过 {MAX_CONCEPT_LENGTH} 个字符")

        # Check traits (only if not in build-on-fly mode)
        if not self.build_on_fly_mode:
            valid_traits = [t for t in self._traits if t.get_trait_data() is not None]

            if len(valid_traits) < 1:
                errors.append("至少需要一个完整的特质 / At least one complete trait required")

            # Check for incomplete traits
            for trait in self._traits:
                if not trait.is_empty() and not trait.is_complete():
                    errors.append(f"特质 {trait.trait_index + 1} 未填写完整")

        return errors

    def get_character_data(self) -> Dict[str, Any]:
        """
        Get character data dictionary.

        Returns:
            Dictionary with character data matching backend PlayerCharacter model
        """
        traits = []
        for trait_editor in self._traits:
            trait_data = trait_editor.get_trait_data()
            if trait_data is not None:
                traits.append(trait_data)

        return {
            "name": self.character_name.strip(),
            "concept": {
                "cn": self.character_concept.strip(),
                "en": self.character_concept.strip(),
            },
            "traits": traits,
            "fate_points": INITIAL_FATE_POINTS,
            "tags": [],  # Start with no status tags
            "build_on_fly": self.build_on_fly_mode,
        }

    def get_traits(self) -> List[Dict[str, Any]]:
        """
        Get list of trait data.

        Returns:
            List of trait dictionaries
        """
        return [t.get_trait_data() for t in self._traits if t.get_trait_data() is not None]

    def _update_validation(self) -> None:
        """Update validation error display."""
        errors = self.get_validation_errors()
        self.validation_errors = errors

        try:
            error_widget = self.query_one("#validation-errors", Static)
            if errors:
                error_text = "\n".join(f"• {e}" for e in errors)
                error_widget.update(error_text)
            else:
                error_widget.update("✓ 角色有效 / Character valid")
        except Exception:
            pass


# Compatibility exports for tests
MAX_NAME_LENGTH = MAX_NAME_LENGTH
INITIAL_FATE_POINTS = INITIAL_FATE_POINTS
