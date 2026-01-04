"""
Director Agent - Game pacing and narrative flow management.

Responsible for:
- Tracking narrative arc and pacing
- Suggesting scene transitions
- Managing tension and drama
- Balancing action, dialogue, and exploration
- Providing GM with meta-suggestions
"""

from enum import Enum
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.backend.agents.base import AgentResponse, BaseAgent
from src.backend.core.prompt_loader import get_prompt_loader


class NarrativeBeat(str, Enum):
    """Types of narrative beats in gameplay."""

    HOOK = "hook"  # Opening scene, player attention grab
    SETUP = "setup"  # Establishing situation, characters, stakes
    RISING_ACTION = "rising_action"  # Building tension, complications
    CLIMAX = "climax"  # Peak of tension, major confrontation
    FALLING_ACTION = "falling_action"  # Resolution beginning
    RESOLUTION = "resolution"  # Wrapping up loose ends
    TRANSITION = "transition"  # Moving between scenes/locations
    BREATHER = "breather"  # Rest moment, character development


class PacingSuggestion(str, Enum):
    """Director suggestions for pacing adjustments."""

    SPEED_UP = "speed_up"  # Too slow, need action
    SLOW_DOWN = "slow_down"  # Too fast, need breathing room
    MAINTAIN = "maintain"  # Current pace is good
    BUILD_TENSION = "build_tension"  # Escalate stakes
    RELEASE_TENSION = "release_tension"  # Provide relief
    INTRODUCE_COMPLICATION = "introduce_complication"  # Add new challenge
    ALLOW_REST = "allow_rest"  # Let player recover


class DirectorAgent(BaseAgent):
    """
    Director Agent - manages game pacing and narrative flow.

    Responsibilities:
    - Track current narrative beat (setup, rising action, climax, etc.)
    - Suggest pacing adjustments to GM
    - Recommend scene transitions
    - Balance gameplay elements (combat, dialogue, exploration)
    - Monitor player engagement signals

    Examples:
        >>> director = DirectorAgent(llm)
        >>> result = await director.process({
        ...     "recent_events": [...],
        ...     "current_beat": "rising_action",
        ...     "turn_count": 15,
        ...     "player_mood": "engaged"
        ... })
    """

    def __init__(self, llm):
        """
        Initialize Director Agent.

        Args:
            llm: Language model instance
        """
        super().__init__(llm, "director_agent")
        self.prompt_loader = get_prompt_loader()

        # Internal tracking
        self._current_beat = NarrativeBeat.SETUP
        self._tension_level = 3  # 1-10 scale
        self._turns_in_beat = 0
        self._recent_beat_history: list[NarrativeBeat] = []
        self._action_dialogue_ratio = 0.5  # 0 = all dialogue, 1 = all action

    @property
    def current_beat(self) -> NarrativeBeat:
        """Get current narrative beat."""
        return self._current_beat

    @property
    def tension_level(self) -> int:
        """Get current tension level (1-10)."""
        return self._tension_level

    def set_beat(self, beat: NarrativeBeat) -> None:
        """
        Set current narrative beat.

        Args:
            beat: New narrative beat
        """
        if beat != self._current_beat:
            self._recent_beat_history.append(self._current_beat)
            # Keep only last 10 beats
            if len(self._recent_beat_history) > 10:
                self._recent_beat_history = self._recent_beat_history[-10:]
            self._current_beat = beat
            self._turns_in_beat = 0

    def adjust_tension(self, delta: int) -> None:
        """
        Adjust tension level.

        Args:
            delta: Amount to change (-10 to +10)
        """
        self._tension_level = max(1, min(10, self._tension_level + delta))

    async def process(self, input_data: dict[str, Any]) -> AgentResponse:
        """
        Process game state and provide pacing suggestions.

        Args:
            input_data: Context from GM containing:
                - recent_events: List of recent game events
                - current_location: Current scene location
                - turn_count: Total turns elapsed
                - player_input_type: Type of player action (dialogue/action/explore)
                - npcs_present: NPCs in current scene
                - lang: Language code (default: "cn")

        Returns:
            AgentResponse with:
                - content: Narrative suggestion text
                - metadata: beat, tension, pacing_suggestion, scene_suggestion
        """
        # Extract input data
        recent_events = input_data.get("recent_events", [])
        current_location = input_data.get("current_location", "unknown")
        turn_count = input_data.get("turn_count", 0)
        player_input_type = input_data.get("player_input_type", "action")
        npcs_present = input_data.get("npcs_present", [])
        lang = input_data.get("lang", "cn")

        # Update internal tracking
        self._turns_in_beat += 1
        self._update_action_dialogue_ratio(player_input_type)

        # Analyze current state
        analysis = await self._analyze_pacing(
            recent_events=recent_events,
            current_location=current_location,
            turn_count=turn_count,
            npcs_present=npcs_present,
            lang=lang,
        )

        if not analysis["success"]:
            return AgentResponse(
                content="",
                success=False,
                error=analysis.get("error", "Director analysis failed"),
                metadata={"agent": self.agent_name},
            )

        # Apply analysis to internal state
        suggested_beat = analysis.get("suggested_beat")
        if suggested_beat:
            try:
                new_beat = NarrativeBeat(suggested_beat)
                self.set_beat(new_beat)
            except ValueError:
                pass  # Keep current beat if invalid

        tension_change = analysis.get("tension_change", 0)
        if tension_change:
            self.adjust_tension(tension_change)

        # Build response
        return AgentResponse(
            content=analysis.get("suggestion", ""),
            metadata={
                "agent": self.agent_name,
                "current_beat": self._current_beat.value,
                "tension_level": self._tension_level,
                "pacing_suggestion": analysis.get("pacing", PacingSuggestion.MAINTAIN.value),
                "scene_suggestion": analysis.get("scene_suggestion", ""),
                "turns_in_beat": self._turns_in_beat,
                "recommended_elements": analysis.get("recommended_elements", []),
            },
            success=True,
        )

    async def _analyze_pacing(
        self,
        recent_events: list[dict[str, Any]],
        current_location: str,
        turn_count: int,
        npcs_present: list[str],
        lang: str,
    ) -> dict[str, Any]:
        """
        Analyze current game state and suggest pacing.

        Args:
            recent_events: Recent game events
            current_location: Current scene
            turn_count: Total turns
            npcs_present: NPCs in scene
            lang: Language code

        Returns:
            Analysis result with suggestions
        """
        # Build prompt
        messages = self._build_prompt(
            recent_events=recent_events,
            current_location=current_location,
            turn_count=turn_count,
            npcs_present=npcs_present,
            current_beat=self._current_beat.value,
            tension_level=self._tension_level,
            turns_in_beat=self._turns_in_beat,
            lang=lang,
        )

        # Call LLM
        try:
            llm_response = await self._call_llm(messages)
        except Exception as exc:
            return {
                "success": False,
                "error": f"LLM call failed: {exc}",
            }

        # Parse response
        try:
            result = self._extract_json_from_response(llm_response)
            result["success"] = True
            return result
        except ValueError as exc:
            # If JSON parsing fails, provide heuristic-based suggestions
            return self._heuristic_analysis(
                turn_count=turn_count,
                turns_in_beat=self._turns_in_beat,
            )

    def _build_prompt(
        self,
        recent_events: list[dict[str, Any]],
        current_location: str,
        turn_count: int,
        npcs_present: list[str],
        current_beat: str,
        tension_level: int,
        turns_in_beat: int,
        lang: str,
    ) -> list:
        """Build prompt for LLM analysis."""
        # Format recent events
        events_text = (
            "\n".join(f"- {e.get('description', str(e))}" for e in recent_events[-5:])
            if recent_events
            else "None"
        )

        npcs_text = ", ".join(npcs_present) if npcs_present else "None"

        if lang == "cn":
            system_content = """你是一位经验丰富的 TTRPG 游戏导演助手，负责管理游戏节奏和叙事流程。

你的任务是分析当前游戏状态，并提供节奏建议。

叙事节拍类型：
- hook: 开场吸引注意力
- setup: 建立情境、人物、利害关系
- rising_action: 积累张力、增加复杂性
- climax: 张力顶点、主要冲突
- falling_action: 开始解决
- resolution: 收尾
- transition: 场景转换
- breather: 休息时刻、角色发展

节奏建议类型：
- speed_up: 需要加快节奏
- slow_down: 需要放慢节奏
- maintain: 保持当前节奏
- build_tension: 提升紧张感
- release_tension: 释放紧张
- introduce_complication: 引入新挑战
- allow_rest: 让玩家休息

请以 JSON 格式回复：
{
    "suggested_beat": "叙事节拍",
    "pacing": "节奏建议",
    "tension_change": 0,  // -3 到 +3
    "suggestion": "给 GM 的具体建议",
    "scene_suggestion": "场景建议（如需要）",
    "recommended_elements": ["推荐加入的元素"]
}"""

            user_content = f"""当前游戏状态：
- 当前位置: {current_location}
- 总回合数: {turn_count}
- 当前节拍: {current_beat}
- 当前节拍已持续回合: {turns_in_beat}
- 张力等级: {tension_level}/10
- 在场 NPC: {npcs_text}

近期事件：
{events_text}

请分析当前游戏节奏，并提供建议。"""

        else:
            system_content = """You are an experienced TTRPG game director assistant, responsible for managing game pacing and narrative flow.

Your task is to analyze the current game state and provide pacing suggestions.

Narrative beat types:
- hook: Opening attention grab
- setup: Establishing situation, characters, stakes
- rising_action: Building tension, adding complications
- climax: Peak tension, major confrontation
- falling_action: Beginning resolution
- resolution: Wrapping up
- transition: Scene change
- breather: Rest moment, character development

Pacing suggestion types:
- speed_up: Need to pick up pace
- slow_down: Need to slow down
- maintain: Keep current pace
- build_tension: Escalate stakes
- release_tension: Provide relief
- introduce_complication: Add new challenge
- allow_rest: Let player recover

Reply in JSON format:
{
    "suggested_beat": "narrative beat",
    "pacing": "pacing suggestion",
    "tension_change": 0,  // -3 to +3
    "suggestion": "specific suggestion for GM",
    "scene_suggestion": "scene suggestion if needed",
    "recommended_elements": ["recommended elements to add"]
}"""

            user_content = f"""Current game state:
- Location: {current_location}
- Total turns: {turn_count}
- Current beat: {current_beat}
- Turns in current beat: {turns_in_beat}
- Tension level: {tension_level}/10
- NPCs present: {npcs_text}

Recent events:
{events_text}

Please analyze the current game pacing and provide suggestions."""

        return [
            SystemMessage(content=system_content),
            HumanMessage(content=user_content),
        ]

    def _heuristic_analysis(
        self,
        turn_count: int,
        turns_in_beat: int,
    ) -> dict[str, Any]:
        """
        Provide heuristic-based analysis when LLM fails.

        Args:
            turn_count: Total turns elapsed
            turns_in_beat: Turns in current beat

        Returns:
            Heuristic analysis result
        """
        suggestion = ""
        pacing = PacingSuggestion.MAINTAIN.value
        tension_change = 0
        recommended_elements = []

        # Check if current beat has gone on too long
        if turns_in_beat > 10:
            if self._current_beat == NarrativeBeat.SETUP:
                suggestion = "Setup has been long. Consider introducing the first complication."
                pacing = PacingSuggestion.BUILD_TENSION.value
                recommended_elements = ["challenge", "mystery", "conflict"]
            elif self._current_beat == NarrativeBeat.RISING_ACTION:
                suggestion = "Rising action is extended. Consider moving toward climax."
                pacing = PacingSuggestion.BUILD_TENSION.value
                tension_change = 1
            elif self._current_beat == NarrativeBeat.CLIMAX:
                suggestion = "Climax is very long. Consider resolution or twist."
                pacing = PacingSuggestion.RELEASE_TENSION.value
            elif self._current_beat == NarrativeBeat.BREATHER:
                suggestion = "Rest period is lengthy. Consider new hook."
                pacing = PacingSuggestion.SPEED_UP.value
                recommended_elements = ["new character", "discovery", "message"]

        # Check tension level
        if self._tension_level >= 8 and turns_in_beat > 5:
            suggestion = "High tension for extended period. Consider release or climax."
            pacing = PacingSuggestion.RELEASE_TENSION.value
            recommended_elements.append("resolution moment")
        elif self._tension_level <= 2 and turn_count > 10:
            suggestion = "Low tension for a while. Consider adding stakes."
            pacing = PacingSuggestion.BUILD_TENSION.value
            recommended_elements.append("threat")

        # Check action/dialogue balance
        if self._action_dialogue_ratio > 0.8:
            recommended_elements.append("dialogue scene")
        elif self._action_dialogue_ratio < 0.2:
            recommended_elements.append("action sequence")

        return {
            "success": True,
            "suggested_beat": None,  # Keep current
            "pacing": pacing,
            "tension_change": tension_change,
            "suggestion": suggestion or "Continue at current pace.",
            "scene_suggestion": "",
            "recommended_elements": recommended_elements,
        }

    def _update_action_dialogue_ratio(self, input_type: str) -> None:
        """
        Update action/dialogue ratio based on player input type.

        Args:
            input_type: Type of player input (dialogue/action/explore)
        """
        # Exponential moving average
        alpha = 0.2
        if input_type == "dialogue":
            self._action_dialogue_ratio = self._action_dialogue_ratio * (1 - alpha) + 0 * alpha
        elif input_type in ("action", "combat"):
            self._action_dialogue_ratio = self._action_dialogue_ratio * (1 - alpha) + 1 * alpha
        # else: explore - neutral, keep ratio

    def get_state_summary(self) -> dict[str, Any]:
        """
        Get summary of director's current state.

        Returns:
            Dictionary with current state information
        """
        return {
            "current_beat": self._current_beat.value,
            "tension_level": self._tension_level,
            "turns_in_beat": self._turns_in_beat,
            "action_dialogue_ratio": round(self._action_dialogue_ratio, 2),
            "recent_beats": [b.value for b in self._recent_beat_history[-5:]],
        }

    def suggest_next_beat(self) -> NarrativeBeat:
        """
        Suggest logical next narrative beat.

        Returns:
            Suggested next beat based on current state
        """
        # Natural narrative progression
        progression = {
            NarrativeBeat.HOOK: NarrativeBeat.SETUP,
            NarrativeBeat.SETUP: NarrativeBeat.RISING_ACTION,
            NarrativeBeat.RISING_ACTION: NarrativeBeat.CLIMAX,
            NarrativeBeat.CLIMAX: NarrativeBeat.FALLING_ACTION,
            NarrativeBeat.FALLING_ACTION: NarrativeBeat.RESOLUTION,
            NarrativeBeat.RESOLUTION: NarrativeBeat.TRANSITION,
            NarrativeBeat.TRANSITION: NarrativeBeat.HOOK,
            NarrativeBeat.BREATHER: NarrativeBeat.RISING_ACTION,
        }

        # Special case: if tension is high, suggest breather after resolution
        if self._current_beat == NarrativeBeat.RESOLUTION and self._tension_level > 5:
            return NarrativeBeat.BREATHER

        return progression.get(self._current_beat, NarrativeBeat.RISING_ACTION)

    def __repr__(self) -> str:
        """Return agent representation."""
        return f"DirectorAgent(beat={self._current_beat.value}, tension={self._tension_level})"
