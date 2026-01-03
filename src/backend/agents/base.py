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
        default_factory=dict,
        description="Additional information about the response"
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

        return str(response.content)

    def _extract_json_from_response(self, response: str) -> dict[str, Any]:
        """
        Extract JSON from LLM response.

        Handles responses that may have markdown code blocks or
        extra whitespace around JSON.

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

        # Remove markdown code blocks
        response = response.strip()
        if response.startswith("```"):
            # Extract content between ```json and ``` or between ``` and ```
            match = re.search(r"```(?:json)?\n?(.*?)\n?```", response, re.DOTALL)
            if match:
                response = match.group(1).strip()

        # Try to parse JSON
        try:
            result = json.loads(response)
            if not isinstance(result, dict):
                raise ValueError(f"Expected dict, got {type(result)}")
            return result
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON from response: {exc}") from exc

    def __repr__(self) -> str:
        """Return agent representation."""
        return f"{self.__class__.__name__}(name={self.agent_name})"
