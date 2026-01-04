"""
Base agent class for Astinus multi-agent system.

Implements LangChain Runnable interface while maintaining familiar
async process() pattern from weave reference project.
"""

from abc import ABC, abstractmethod
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import Runnable
from langchain_core.runnables.config import RunnableConfig
from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """
    Standard response format from all agents.

    Attributes:
        content: Main response content
        metadata: Additional information (agent name, reasoning, etc.)
        success: Whether the operation succeeded
        error: Error message if failed

    Examples:
        >>> response = AgentResponse(
        ...     content="Player should roll 3d6kl2",
        ...     metadata={"agent": "rule", "check_type": "disadvantage"}
        ... )
    """

    content: str = Field(..., description="Main response content")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional information about the response"
    )
    success: bool = Field(default=True, description="Whether operation succeeded")
    error: str | None = Field(default=None, description="Error message if failed")


class BaseAgent(Runnable[dict[str, Any], AgentResponse], ABC):
    """
    Base class for all Astinus agents.

    Implements LangChain Runnable interface for compatibility with LangChain
    ecosystem, while providing a familiar async process() pattern.

    Design Principles:
    - Star topology: Agents are stateless, receive sliced context
    - GM Agent owns global state, sub-agents work on isolated slices
    - Each agent has specific responsibilities (Rule, NPC, Lore, etc.)

    Subclasses must implement:
    - process(): Main agent logic
    - _build_prompt(): Construct prompts for LLM

    Examples:
        >>> class MyAgent(BaseAgent):
        ...     def __init__(self, llm):
        ...         self.llm = llm
        ...         self.agent_name = "my_agent"
        ...
        ...     async def process(self, input_data):
        ...         # Agent logic here
        ...         return AgentResponse(content="Done")
        ...
        ...     def _build_prompt(self, input_data):
        ...         return [HumanMessage(content="Hello")]
        ...
        >>> agent = MyAgent(llm)
        >>> result = agent.invoke({"action": "test"})
    """

    def __init__(self, llm: BaseChatModel, agent_name: str):
        """
        Initialize base agent.

        Args:
            llm: Language model instance
            agent_name: Unique identifier for this agent
        """
        super().__init__()
        self.llm = llm
        self.agent_name = agent_name

    # LangChain Runnable interface implementation

    def invoke(
        self,
        input: dict[str, Any],
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """
        Synchronous invocation (LangChain Runnable interface).

        This is the main entry point for LangChain compatibility.
        Internally calls the async process() method.

        Args:
            input: Input data dictionary
            config: Optional LangChain config
            **kwargs: Additional arguments

        Returns:
            AgentResponse with result or error
        """
        import asyncio

        try:
            # Try to get the running event loop
            try:
                asyncio.get_running_loop()
                # We're in an async context - this shouldn't be called sync
                # But if it is, we need to handle it
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.process(input))
                    return future.result()
            except RuntimeError:
                # No running loop - we can use asyncio.run safely
                return asyncio.run(self.process(input))
        except Exception as exc:
            return AgentResponse(
                content="",
                success=False,
                error=f"{self.agent_name} error: {str(exc)}",
                metadata={"agent": self.agent_name, "error_type": type(exc).__name__},
            )

    async def ainvoke(
        self,
        input: dict[str, Any],
        config: RunnableConfig | None = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """
        Asynchronous invocation (LangChain Runnable interface).

        Args:
            input: Input data dictionary
            config: Optional LangChain config
            **kwargs: Additional arguments

        Returns:
            AgentResponse with result or error
        """
        try:
            return await self.process(input)
        except Exception as exc:
            return AgentResponse(
                content="",
                success=False,
                error=f"{self.agent_name} error: {str(exc)}",
                metadata={"agent": self.agent_name, "error_type": type(exc).__name__},
            )

    # Agent implementation interface

    @abstractmethod
    async def process(self, input_data: dict[str, Any]) -> AgentResponse:
        """
        Main agent processing logic.

        This is where agent-specific logic lives. Subclasses must implement
        this method with their own behavior.

        Args:
            input_data: Context slice from GM (or user input for GM)

        Returns:
            AgentResponse with result

        Examples:
            >>> async def process(self, input_data):
            ...     action = input_data["action"]
            ...     # Analyze action, build prompt, call LLM
            ...     messages = self._build_prompt(input_data)
            ...     response = await self._call_llm(messages)
            ...     return AgentResponse(content=response)
        """
        raise NotImplementedError

    @abstractmethod
    def _build_prompt(self, input_data: dict[str, Any]) -> list[BaseMessage]:
        """
        Build prompt messages for LLM.

        Constructs the message list to send to the language model.
        Typically includes system message (role/guidelines) and
        human message (current task).

        Args:
            input_data: Context data for prompt construction

        Returns:
            List of messages for LLM

        Examples:
            >>> def _build_prompt(self, input_data):
            ...     system = SystemMessage(content="You are a rule judge")
            ...     human = HumanMessage(content=f"Action: {input_data['action']}")
            ...     return [system, human]
        """
        raise NotImplementedError

    async def _call_llm(
        self,
        messages: list[BaseMessage],
        **kwargs: Any,
    ) -> str:
        """
        Call the language model with messages.

        Wrapper around LLM invocation with error handling and
        response extraction.

        Args:
            messages: List of messages to send to LLM
            **kwargs: Additional LLM parameters (temperature, etc.)

        Returns:
            LLM response content as string

        Raises:
            ValueError: If LLM returns empty response

        Examples:
            >>> messages = [
            ...     SystemMessage(content="You are helpful"),
            ...     HumanMessage(content="Say hello")
            ... ]
            >>> response = await self._call_llm(messages)
            >>> print(response)  # "Hello! How can I help you?"
        """
        # Call LLM asynchronously
        response: AIMessage = await self.llm.ainvoke(messages, **kwargs)

        # Extract content
        if not response.content:
            raise ValueError("LLM returned empty response")

        # Handle different response formats
        # Some models (like Gemini) return content as a list of dicts
        # e.g., [{'type': 'text', 'text': 'actual content'}]
        content = response.content
        if isinstance(content, list):
            # Extract text from list format
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            content = "".join(text_parts)

        if not content:
            raise ValueError("LLM returned empty response after content extraction")

        return str(content)

    def _extract_json_from_response(self, response: str) -> dict[str, Any]:
        """
        Extract JSON from LLM response.

        Handles responses that may have:
        - Markdown code blocks (```json ... ```)
        - Extra text before/after JSON
        - Single quotes instead of double quotes
        - Trailing commas
        - Other common LLM output quirks

        Args:
            response: Raw LLM response string

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If JSON cannot be extracted or parsed

        Examples:
            >>> response = '''```json
            ... {"key": "value"}
            ... ```'''
            >>> result = agent._extract_json_from_response(response)
            >>> result
            {'key': 'value'}
        """
        import json
        import re

        original_response = response
        response = response.strip()

        # Strategy 1: Try direct parse first (fastest path)
        try:
            result = json.loads(response)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from markdown code blocks
        # Match ```json ... ``` or ``` ... ```
        code_block_patterns = [
            r"```json\s*\n?(.*?)\n?\s*```",
            r"```\s*\n?(.*?)\n?\s*```",
        ]
        for pattern in code_block_patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                try:
                    result = json.loads(content)
                    if isinstance(result, dict):
                        return result
                except json.JSONDecodeError:
                    # Try fixing common issues
                    fixed = self._fix_json_string(content)
                    try:
                        result = json.loads(fixed)
                        if isinstance(result, dict):
                            return result
                    except json.JSONDecodeError:
                        pass

        # Strategy 3: Find JSON object by matching braces
        json_content = self._extract_json_object(response)
        if json_content:
            try:
                result = json.loads(json_content)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                # Try fixing common issues
                fixed = self._fix_json_string(json_content)
                try:
                    result = json.loads(fixed)
                    if isinstance(result, dict):
                        return result
                except json.JSONDecodeError:
                    pass

        # Strategy 4: Try fixing the entire response
        fixed = self._fix_json_string(response)
        try:
            result = json.loads(fixed)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

        # All strategies failed
        # Provide helpful error message
        preview = (
            original_response[:200] + "..." if len(original_response) > 200 else original_response
        )
        raise ValueError(f"Failed to parse JSON from response. Response preview: {preview}")

    def _extract_json_object(self, text: str) -> str | None:
        """
        Extract the first JSON object from text by matching braces.

        Args:
            text: Text that may contain a JSON object

        Returns:
            Extracted JSON string or None if not found
        """
        # Find the first { and match to its closing }
        start = text.find("{")
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]

        return None

    def _fix_json_string(self, json_str: str) -> str:
        """
        Attempt to fix common JSON issues from LLM output.

        Fixes:
        - Single quotes -> double quotes (carefully)
        - Trailing commas
        - Unquoted keys (simple cases)

        Args:
            json_str: Potentially malformed JSON string

        Returns:
            Fixed JSON string (may still be invalid)
        """
        import re

        result = json_str.strip()

        # Fix 1: Replace single quotes with double quotes
        # This is tricky because we need to handle:
        # - {'key': 'value'} -> {"key": "value"}
        # - But not "it's" -> "it"s"
        # Use a simple heuristic: replace ' with " when it looks like JSON structure

        # Pattern to match single-quoted strings in JSON-like structures
        # Match: 'text' where text doesn't contain unescaped single quotes
        def replace_single_quotes(match: re.Match) -> str:
            content = match.group(1)
            # Escape any double quotes inside
            content = content.replace('"', '\\"')
            return f'"{content}"'

        # Replace 'key' patterns (single-quoted strings)
        result = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", replace_single_quotes, result)

        # Fix 2: Remove trailing commas before } or ]
        result = re.sub(r",\s*([}\]])", r"\1", result)

        # Fix 3: Add quotes to unquoted keys (simple alphanumeric keys only)
        # Match: {key: or , key: where key is unquoted
        result = re.sub(r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', result)

        return result

    def __repr__(self) -> str:
        """Return agent representation."""
        return f"{self.__class__.__name__}(name={self.agent_name})"
