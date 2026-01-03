"""Tests for BaseAgent class."""

import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from src.backend.agents.base import AgentResponse, BaseAgent
from src.backend.core.llm_provider import LLMConfig, get_llm

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


class SimpleTestAgent(BaseAgent):
    """Simple test agent for testing BaseAgent functionality."""

    def __init__(self, llm):
        super().__init__(llm, "test_agent")
        self.process_called = False
        self.build_prompt_called = False

    async def process(self, input_data: dict) -> AgentResponse:
        """Test process implementation."""
        self.process_called = True

        # Get action from input
        action = input_data.get("action", "unknown")

        # Build prompt and call LLM
        messages = self._build_prompt(input_data)
        response = await self._call_llm(messages)

        return AgentResponse(
            content=response,
            metadata={"agent": self.agent_name, "action": action},
        )

    def _build_prompt(self, input_data: dict) -> list[BaseMessage]:
        """Test prompt builder."""
        self.build_prompt_called = True

        system = SystemMessage(content="You are a test agent")
        human = HumanMessage(content=f"Action: {input_data.get('action', 'none')}")

        return [system, human]


class TestAgentResponse:
    """Test suite for AgentResponse class."""

    def test_create_agent_response(self):
        """Test creating an AgentResponse."""
        response = AgentResponse(
            content="Test response",
            metadata={"agent": "test", "key": "value"},
        )
        assert response.content == "Test response"
        assert response.metadata == {"agent": "test", "key": "value"}
        assert response.success is True
        assert response.error is None

    def test_create_error_response(self):
        """Test creating an error response."""
        response = AgentResponse(
            content="",
            success=False,
            error="Test error",
            metadata={"agent": "test"},
        )
        assert response.content == ""
        assert response.success is False
        assert response.error == "Test error"

    def test_default_metadata(self):
        """Test default empty metadata."""
        response = AgentResponse(content="Test")
        assert response.metadata == {}

    def test_default_success_true(self):
        """Test success defaults to True."""
        response = AgentResponse(content="Test")
        assert response.success is True


class TestBaseAgent:
    """Test suite for BaseAgent class."""

    @pytest.fixture
    def llm(self):
        """Create test LLM instance."""
        config = LLMConfig(model="gpt-4o-mini", api_key="sk-test-key")
        return get_llm(config)

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM for testing."""
        llm = MagicMock()
        llm.ainvoke = AsyncMock(return_value=AIMessage(content="Mock response"))
        return llm

    @pytest.fixture
    def agent(self, mock_llm):
        """Create test agent instance."""
        return SimpleTestAgent(mock_llm)

    def test_create_agent(self, llm):
        """Test creating an agent."""
        agent = SimpleTestAgent(llm)
        assert agent.llm is not None
        assert agent.agent_name == "test_agent"

    def test_agent_repr(self, agent):
        """Test agent string representation."""
        assert repr(agent) == "SimpleTestAgent(name=test_agent)"

    @pytest.mark.asyncio
    async def test_async_invoke(self, agent):
        """Test async invocation."""
        result = await agent.ainvoke({"action": "test"})

        assert isinstance(result, AgentResponse)
        assert result.success is True
        assert result.content == "Mock response"
        assert result.metadata["agent"] == "test_agent"
        assert result.metadata["action"] == "test"

    def test_sync_invoke(self, agent):
        """Test synchronous invocation."""
        result = agent.invoke({"action": "test"})

        assert isinstance(result, AgentResponse)
        assert result.success is True
        assert result.content == "Mock response"
        assert result.metadata["agent"] == "test_agent"

    @pytest.mark.asyncio
    async def test_process_called(self, agent):
        """Test that process() is called during invocation."""
        await agent.ainvoke({"action": "test"})

        assert agent.process_called is True
        assert agent.build_prompt_called is True

    @pytest.mark.asyncio
    async def test_call_llm(self, agent):
        """Test _call_llm() method."""
        messages = [
            SystemMessage(content="System"),
            HumanMessage(content="Hello"),
        ]

        response = await agent._call_llm(messages)

        assert response == "Mock response"
        agent.llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_llm_empty_response(self, mock_llm):
        """Test _call_llm() with empty response."""
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content=""))

        agent = SimpleTestAgent(mock_llm)
        messages = [HumanMessage(content="Test")]

        with pytest.raises(ValueError, match="empty response"):
            await agent._call_llm(messages)

    def test_extract_json_from_response(self, agent):
        """Test JSON extraction from plain JSON."""
        response = '{"key": "value", "number": 42}'
        result = agent._extract_json_from_response(response)

        assert result == {"key": "value", "number": 42}

    def test_extract_json_from_markdown(self, agent):
        """Test JSON extraction from markdown code block."""
        response = """```json
        {
            "key": "value",
            "number": 42
        }
        ```"""

        result = agent._extract_json_from_response(response)
        assert result == {"key": "value", "number": 42}

    def test_extract_json_from_markdown_no_lang(self, agent):
        """Test JSON extraction from code block without language."""
        response = """```
        {"key": "value"}
        ```"""

        result = agent._extract_json_from_response(response)
        assert result == {"key": "value"}

    def test_extract_json_invalid(self, agent):
        """Test JSON extraction with invalid JSON."""
        response = "{invalid json"

        with pytest.raises(ValueError, match="Failed to parse JSON"):
            agent._extract_json_from_response(response)

    @pytest.mark.asyncio
    async def test_error_handling_in_ainvoke(self, mock_llm):
        """Test error handling in async invocation."""

        class FailingAgent(SimpleTestAgent):
            async def process(self, input_data):
                raise RuntimeError("Test error")

        agent = FailingAgent(mock_llm)
        result = await agent.ainvoke({"action": "test"})

        assert result.success is False
        assert "Test error" in result.error
        assert result.metadata["agent"] == "test_agent"
        assert result.metadata["error_type"] == "RuntimeError"

    def test_error_handling_in_invoke(self, mock_llm):
        """Test error handling in sync invocation."""

        class FailingAgent(SimpleTestAgent):
            async def process(self, input_data):
                raise ValueError("Sync test error")

        agent = FailingAgent(mock_llm)
        result = agent.invoke({"action": "test"})

        assert result.success is False
        assert "Sync test error" in result.error

    @pytest.mark.asyncio
    async def test_build_prompt_receives_input(self, agent):
        """Test that _build_prompt receives input data."""
        input_data = {"action": "custom_action", "extra": "data"}
        await agent.ainvoke(input_data)

        assert agent.build_prompt_called is True
        # Check that LLM was called with messages
        assert agent.llm.ainvoke.called

    def test_agent_is_runnable(self, agent):
        """Test that agent implements Runnable interface."""
        # Should have invoke and ainvoke methods
        assert hasattr(agent, "invoke")
        assert hasattr(agent, "ainvoke")
        assert callable(agent.invoke)
        assert callable(agent.ainvoke)
