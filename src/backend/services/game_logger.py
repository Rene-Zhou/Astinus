"""
Game debug logging service for troubleshooting AI responses and state changes.

Provides structured logging with timestamps for:
- LLM raw responses (complete JSON from AI)
- Game state changes (location transitions, NPC updates)
- Player inputs and GM outputs

Also provides unified logging configuration for the entire application,
ensuring uvicorn, FastAPI, and game logs use the same timestamp format.
"""

import json
import logging
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class UnifiedFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        ct = datetime.fromtimestamp(record.created)
        return ct.strftime("%Y-%m-%d %H:%M:%S") + f".{int(record.msecs):03d}"


def setup_unified_logging(level: str = "INFO", log_file: str | None = None) -> None:
    """
    Configure all Python loggers (uvicorn, fastapi, etc.) to use GameLogger timestamp format.

    Args:
        level: DEBUG, INFO, WARNING, or ERROR
        log_file: Optional file path for persistent logs
    """
    formatter = UnifiedFormatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class LogCategory(str, Enum):
    LLM_RAW = "LLM_RAW"
    STATE_CHANGE = "STATE_CHANGE"
    PLAYER_INPUT = "PLAYER_INPUT"
    GM_OUTPUT = "GM_OUTPUT"
    SCENE_TRANSITION = "SCENE_TRANSITION"
    AGENT_CALL = "AGENT_CALL"


class GameLogger:
    _instance: "GameLogger | None" = None

    def __new__(cls, *args, **kwargs) -> "GameLogger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        log_dir: str = "logs",
        session_id: str | None = None,
        console_output: bool = True,
        file_output: bool = True,
    ):
        if self._initialized:
            return

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.console_output = console_output
        self.file_output = file_output

        self._log_file = self.log_dir / f"game_debug_{self.session_id}.log"
        self._raw_llm_file = self.log_dir / f"llm_raw_{self.session_id}.jsonl"

        self._initialized = True

    def set_session(self, session_id: str) -> None:
        self.session_id = session_id
        self._log_file = self.log_dir / f"game_debug_{session_id}.log"
        self._raw_llm_file = self.log_dir / f"llm_raw_{session_id}.jsonl"

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _format_entry(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> str:
        timestamp = self._timestamp()
        entry = f"[{timestamp}] [{level.value}] [{category.value}] {message}"
        if data:
            data_str = json.dumps(data, ensure_ascii=False, indent=2)
            entry += f"\n{data_str}"
        return entry

    def _write(self, entry: str) -> None:
        if self.console_output:
            print(entry)

        if self.file_output:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(entry + "\n\n")

    def log_llm_raw_response(
        self,
        agent_name: str,
        prompt_summary: str,
        raw_response: str,
        parsed_json: dict[str, Any] | None = None,
    ) -> None:
        entry = self._format_entry(
            LogLevel.DEBUG,
            LogCategory.LLM_RAW,
            f"Agent: {agent_name} | Prompt: {prompt_summary[:100]}...",
            {
                "raw_response": raw_response[:500] + "..."
                if len(raw_response) > 500
                else raw_response
            },
        )
        self._write(entry)

        if self.file_output:
            jsonl_entry = {
                "timestamp": self._timestamp(),
                "agent": agent_name,
                "prompt_summary": prompt_summary[:200],
                "raw_response": raw_response,
                "parsed_json": parsed_json,
            }
            with open(self._raw_llm_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(jsonl_entry, ensure_ascii=False) + "\n")

    def log_state_change(
        self,
        field: str,
        old_value: Any,
        new_value: Any,
        reason: str = "",
    ) -> None:
        entry = self._format_entry(
            LogLevel.INFO,
            LogCategory.STATE_CHANGE,
            f"Field: {field} | {old_value} -> {new_value}",
            {"reason": reason} if reason else None,
        )
        self._write(entry)

    def log_scene_transition(
        self,
        from_location: str,
        to_location: str,
        success: bool,
        npcs_at_new_location: list[str] | None = None,
    ) -> None:
        entry = self._format_entry(
            LogLevel.INFO,
            LogCategory.SCENE_TRANSITION,
            f"{'SUCCESS' if success else 'FAILED'}: {from_location} -> {to_location}",
            {"npcs": npcs_at_new_location} if npcs_at_new_location else None,
        )
        self._write(entry)

    def log_player_input(self, turn: int, content: str) -> None:
        entry = self._format_entry(
            LogLevel.INFO,
            LogCategory.PLAYER_INPUT,
            f"Turn {turn}: {content[:200]}",
        )
        self._write(entry)

    def log_gm_output(
        self,
        turn: int,
        content: str,
        intent: str | None = None,
        agents_called: list[str] | None = None,
    ) -> None:
        entry = self._format_entry(
            LogLevel.INFO,
            LogCategory.GM_OUTPUT,
            f"Turn {turn} | Intent: {intent or 'N/A'}",
            {
                "content_preview": content[:300] + "..." if len(content) > 300 else content,
                "agents_called": agents_called or [],
            },
        )
        self._write(entry)

    def log_agent_call(
        self,
        agent_name: str,
        input_data: dict[str, Any],
        output_summary: str,
        success: bool,
    ) -> None:
        entry = self._format_entry(
            LogLevel.DEBUG,
            LogCategory.AGENT_CALL,
            f"Agent: {agent_name} | Success: {success}",
            {"input_keys": list(input_data.keys()), "output_summary": output_summary[:200]},
        )
        self._write(entry)

    def log_error(self, context: str, error: str, data: dict[str, Any] | None = None) -> None:
        entry = self._format_entry(
            LogLevel.ERROR,
            LogCategory.STATE_CHANGE,
            f"Context: {context} | Error: {error}",
            data,
        )
        self._write(entry)


_logger: GameLogger | None = None


def get_game_logger() -> GameLogger:
    global _logger
    if _logger is None:
        _logger = GameLogger()
    return _logger


def init_game_logger(
    session_id: str | None = None,
    console_output: bool = True,
    file_output: bool = True,
) -> GameLogger:
    global _logger
    GameLogger._instance = None
    _logger = GameLogger(
        log_dir="logs",
        session_id=session_id,
        console_output=console_output,
        file_output=file_output,
    )
    return _logger
