"""Tests for NPCAgent."""

import os
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from src.backend.agents.npc import NPCAgent
from src.backend.models.world_pack import NPCBody, NPCData, NPCSoul

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


class TestNPCAgent:
    """Test suite for NPCAgent class."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        return AsyncMock()

    @pytest.fixture
    def sample_npc_data(self) -> NPCData:
        """Create sample NPC data for testing."""
        return NPCData(
            id="chen_ling",
            soul=NPCSoul(
                name="陈玲",
                description={
                    "cn": "图书馆的年轻女馆员，戴着圆框眼镜，说话轻声细语。"
                         "她对古籍有着浓厚的兴趣，经常独自研究馆藏的珍本。",
                    "en": "A young female librarian wearing round glasses, "
                         "speaking softly. She has a deep interest in ancient "
                         "books and often studies rare collections alone.",
                },
                personality=["内向", "细心", "好奇", "善良"],
                speech_style={
                    "cn": "说话轻柔，经常使用书面语，偶尔引用古文。"
                         "紧张时会结巴，习惯用手推眼镜。",
                    "en": "Speaks softly, often uses formal language, "
                         "occasionally quotes classical texts. Stutters when "
                         "nervous, habitually pushes up her glasses.",
                },
                example_dialogue=[
                    {
                        "user": "这里有什么有趣的书吗？",
                        "char": "有...有的。这边有一本《山海经》的明刻本，"
                               "是我们馆的镇馆之宝呢...",
                    }
                ],
            ),
            body=NPCBody(
                location="library_main_hall",
                inventory=["钥匙串", "笔记本"],
                relations={"player": 0},
                tags=["工作中"],
                memory={},
            ),
        )

    @pytest.fixture
    def npc_agent(self, mock_llm) -> NPCAgent:
        """Create NPCAgent instance."""
        return NPCAgent(mock_llm)

    def test_create_npc_agent(self, npc_agent):
        """Test creating NPCAgent."""
        assert npc_agent.agent_name == "npc_agent"
        assert npc_agent.i18n is not None
        assert npc_agent.prompt_loader is not None

    def test_npc_agent_repr(self, npc_agent):
        """Test NPCAgent string representation."""
        assert repr(npc_agent) == "NPCAgent()"

    @pytest.mark.asyncio
    async def test_process_simple_greeting(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test NPC responding to simple greeting."""
        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "你...你好。有什么我能帮你的吗？", '
                   '"emotion": "shy", "action": "推了推眼镜"}'
        )

        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "你好",
            "context": {
                "location": "library_main_hall",
                "time_of_day": "afternoon",
            },
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        assert result.content != ""
        assert result.metadata.get("npc_id") == "chen_ling"
        assert "emotion" in result.metadata

    @pytest.mark.asyncio
    async def test_process_with_relationship_influence(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test NPC response influenced by relationship value."""
        # Update relationship to positive
        sample_npc_data.body.relations["player"] = 50

        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "啊，是你！真高兴又见到你。今天想看什么书？", '
                   '"emotion": "happy", "action": "微笑着放下手中的书"}'
        )

        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "嗨，陈玲",
            "context": {"location": "library_main_hall"},
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        assert result.metadata.get("relationship_level") == 50

    @pytest.mark.asyncio
    async def test_process_with_negative_relationship(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test NPC response with negative relationship."""
        sample_npc_data.body.relations["player"] = -30

        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "...需要什么？", '
                   '"emotion": "cold", "action": "没有抬头看向你"}'
        )

        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "能帮我找本书吗？",
            "context": {"location": "library_main_hall"},
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        assert result.metadata.get("relationship_level") == -30

    @pytest.mark.asyncio
    async def test_process_with_npc_tags(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test NPC response influenced by status tags."""
        sample_npc_data.body.tags = ["受伤", "害怕"]

        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "请...请不要靠近...", '
                   '"emotion": "scared", "action": "后退一步，捂住手臂"}'
        )

        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "你还好吗？",
            "context": {"location": "library_main_hall"},
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        assert "受伤" in sample_npc_data.body.tags

    @pytest.mark.asyncio
    async def test_process_npc_remembers_event(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test NPC references memory in response."""
        sample_npc_data.body.memory = {
            "玩家帮忙找到了失踪的古籍": ["古籍", "帮助"],
        }

        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "上次多亏你帮我找到那本古籍，真是太感谢了！", '
                   '"emotion": "grateful", "action": "真诚地鞠了一躬"}'
        )

        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "还记得我吗？",
            "context": {"location": "library_main_hall"},
        }

        result = await npc_agent.process(input_data)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_process_missing_npc_data(self, npc_agent):
        """Test error when NPC data is missing."""
        input_data = {
            "player_input": "你好",
            "context": {},
        }

        result = await npc_agent.process(input_data)

        assert result.success is False
        assert "npc_data" in result.error.lower()

    @pytest.mark.asyncio
    async def test_process_missing_player_input(
        self, npc_agent, sample_npc_data
    ):
        """Test error when player input is missing."""
        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "context": {},
        }

        result = await npc_agent.process(input_data)

        assert result.success is False
        assert "player_input" in result.error.lower()

    @pytest.mark.asyncio
    async def test_process_invalid_json_response(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test error handling for invalid JSON from LLM."""
        mock_llm.ainvoke.return_value = AIMessage(
            content="这不是有效的JSON {"
        )

        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "你好",
            "context": {},
        }

        result = await npc_agent.process(input_data)

        assert result.success is False
        assert "parse" in result.error.lower() or "json" in result.error.lower()

    @pytest.mark.asyncio
    async def test_build_prompt_includes_soul(
        self, npc_agent, sample_npc_data
    ):
        """Test that prompt includes NPC soul information."""
        messages = npc_agent._build_prompt(
            npc_data=sample_npc_data.model_dump(),
            player_input="你好",
            context={"location": "library_main_hall"},
        )

        assert len(messages) >= 2
        prompt_text = " ".join(str(m.content) for m in messages)

        # Should include NPC identity
        assert "陈玲" in prompt_text
        # Should include personality
        assert "内向" in prompt_text or "shy" in prompt_text.lower()
        # Should include speech style
        assert "轻柔" in prompt_text or "soft" in prompt_text.lower()

    @pytest.mark.asyncio
    async def test_build_prompt_includes_body_state(
        self, npc_agent, sample_npc_data
    ):
        """Test that prompt includes NPC body state."""
        sample_npc_data.body.tags = ["忙碌"]
        sample_npc_data.body.relations["player"] = 30

        messages = npc_agent._build_prompt(
            npc_data=sample_npc_data.model_dump(),
            player_input="能打扰一下吗？",
            context={"location": "library_main_hall"},
        )

        prompt_text = " ".join(str(m.content) for m in messages)

        # Should include current state
        assert "忙碌" in prompt_text or "busy" in prompt_text.lower()

    @pytest.mark.asyncio
    async def test_sync_invoke(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test synchronous invocation."""
        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "你好。", "emotion": "neutral", "action": ""}'
        )

        result = npc_agent.invoke({
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "你好",
            "context": {},
        })

        assert result.success is True

    @pytest.mark.asyncio
    async def test_process_returns_suggested_relation_change(
        self, npc_agent, mock_llm, sample_npc_data
    ):
        """Test NPC can suggest relationship changes."""
        mock_llm.ainvoke.return_value = AIMessage(
            content='{"response": "太感谢你了！", "emotion": "grateful", '
                   '"action": "眼眶湿润", "relation_change": 10}'
        )

        input_data = {
            "npc_data": sample_npc_data.model_dump(),
            "player_input": "我帮你找到了那本书",
            "context": {},
        }

        result = await npc_agent.process(input_data)

        assert result.success is True
        # Relation change should be in metadata if LLM suggests it
        if "relation_change" in result.metadata:
            assert result.metadata["relation_change"] == 10

    @pytest.mark.asyncio
    async def test_language_selection_cn(
        self, npc_agent, sample_npc_data
    ):
        """Test prompt uses Chinese when lang=cn."""
        messages = npc_agent._build_prompt(
            npc_data=sample_npc_data.model_dump(),
            player_input="你好",
            context={},
            lang="cn",
        )

        prompt_text = " ".join(str(m.content) for m in messages)
        # Should use Chinese description
        assert "图书馆" in prompt_text or "馆员" in prompt_text

    @pytest.mark.asyncio
    async def test_language_selection_en(
        self, npc_agent, sample_npc_data
    ):
        """Test prompt uses English when lang=en."""
        messages = npc_agent._build_prompt(
            npc_data=sample_npc_data.model_dump(),
            player_input="Hello",
            context={},
            lang="en",
        )

        prompt_text = " ".join(str(m.content) for m in messages)
        # Should use English description
        assert "librarian" in prompt_text.lower() or "library" in prompt_text.lower()
