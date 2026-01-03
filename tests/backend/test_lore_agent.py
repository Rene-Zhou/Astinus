"""Tests for Lore Agent."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.agents.lore import LoreAgent
from src.backend.services.world import WorldPackLoader


class TestLoreAgent:
    """Test suite for Lore Agent."""

    @pytest.fixture
    def world_loader(self):
        """Create a world pack loader for testing."""
        packs_dir = Path(__file__).parent.parent.parent / "data" / "packs"
        if not (packs_dir / "demo_pack.json").exists():
            pytest.skip("Demo pack not available")
        return WorldPackLoader(packs_dir)

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        return MagicMock()

    @pytest.fixture
    def lore_agent(self, mock_llm, world_loader):
        """Create a Lore Agent for testing."""
        return LoreAgent(mock_llm, world_loader)

    def test_lore_agent_creation(self, lore_agent):
        """Test Lore Agent initialization."""
        assert lore_agent.agent_name == "lore_agent"
        assert lore_agent.world_pack_loader is not None

    @pytest.mark.asyncio
    async def test_process_simple_query(self, lore_agent, world_loader):
        """Test processing a simple lore query."""
        # Load the demo pack
        world_pack = world_loader.load("demo_pack")

        # Query about the manor
        result = await lore_agent.process({
            "query": "幽暗庄园的历史",
            "context": "玩家询问庄园的背景",
            "world_pack_id": "demo_pack",
        })

        assert result.success is True
        assert len(result.content) > 0
        assert "幽暗庄园" in result.content or "庄园" in result.content
        assert result.metadata["query"] == "幽暗庄园的历史"
        assert result.metadata["entries_found"] > 0

    @pytest.mark.asyncio
    async def test_process_keyword_search(self, lore_agent, world_loader):
        """Test searching by specific keywords."""
        # Search for NPC-related lore
        result = await lore_agent.process({
            "query": "管家",
            "context": "玩家询问关于管家的事情",
            "world_pack_id": "demo_pack",
        })

        assert result.success is True
        assert "管家" in result.content
        assert result.metadata["entries_found"] > 0

    @pytest.mark.asyncio
    async def test_process_location_query(self, lore_agent, world_loader):
        """Test querying about locations."""
        result = await lore_agent.process({
            "query": "书房",
            "context": "玩家询问书房的信息",
            "world_pack_id": "demo_pack",
        })

        assert result.success is True
        assert len(result.content) > 0
        # Should find entries related to study/书房

    @pytest.mark.asyncio
    async def test_process_no_query(self, lore_agent):
        """Test error when no query provided."""
        result = await lore_agent.process({
            "context": "玩家询问",
        })

        assert result.success is False
        assert "No query provided" in result.error

    @pytest.mark.asyncio
    async def test_process_invalid_pack(self, lore_agent):
        """Test error with invalid world pack."""
        result = await lore_agent.process({
            "query": "测试",
            "world_pack_id": "nonexistent_pack",
        })

        assert result.success is False
        assert result.error is not None
        assert "World pack not found" in result.error

    def test_extract_search_terms(self, lore_agent):
        """Test extraction of search terms from queries."""
        # Test Chinese query (no spaces, treated as one term)
        terms = lore_agent._extract_search_terms("我想了解暴风城的历史")
        # The whole query is treated as one term since Chinese has no spaces
        assert len(terms) == 1
        assert "我想了解暴风城的历史" in terms

        # Test English query (has spaces, split properly)
        terms = lore_agent._extract_search_terms("Tell me about Stormwind")
        assert "Stormwind" in terms or "about" in terms

        # Test query with punctuation
        terms = lore_agent._extract_search_terms("风暴城！")
        assert len(terms) >= 1

    def test_format_lore_with_entries(self, lore_agent, world_loader):
        """Test formatting lore with actual entries."""
        world_pack = world_loader.load("demo_pack")
        entries = world_pack.search_entries_by_keyword("庄园")

        formatted = lore_agent._format_lore(entries, "庄园", "玩家询问")

        assert len(formatted) > 0
        assert "背景信息" in formatted or "相关" in formatted

    def test_format_lore_no_entries(self, lore_agent):
        """Test formatting when no entries found."""
        formatted = lore_agent._format_lore([], "未知主题", "玩家询问")

        assert "没有找到" in formatted
        assert "未知主题" in formatted

    def test_search_lore(self, lore_agent, world_loader):
        """Test lore search functionality."""
        world_pack = world_loader.load("demo_pack")

        # Search for manor-related entries
        entries = lore_agent._search_lore(
            world_pack,
            "幽暗庄园的历史",
            "玩家询问庄园背景"
        )

        assert len(entries) > 0
        # Should find the constant manor entry
        assert any("庄园" in str(entry.key) for entry in entries)


class TestLoreAgentIntegration:
    """Integration tests for Lore Agent with world packs."""

    @pytest.fixture
    def world_loader(self):
        """Create a world pack loader."""
        packs_dir = Path(__file__).parent.parent / "data" / "packs"
        if not (packs_dir / "demo_pack.json").exists():
            pytest.skip("Demo pack not available")
        return WorldPackLoader(packs_dir)

    @pytest.mark.asyncio
    async def test_full_lore_query_flow(self, world_loader):
        """Test complete lore query flow."""
        # Set fake API key for LLM
        os.environ["OPENAI_API_KEY"] = "sk-test-key"

        from src.backend.core.llm_provider import get_llm

        # Create LLM (will use mock in test env)
        llm = get_llm(
            model="gpt-4o-mini",
            temperature=0.7,
        )

        # Create Lore Agent
        lore_agent = LoreAgent(llm, world_loader)

        # Query about NPC
        result = await lore_agent.process({
            "query": "陈玲是谁",
            "context": "玩家遇到陈玲，想了解她的背景",
            "world_pack_id": "demo_pack",
        })

        assert result.success is True
        assert result.metadata["world_pack_id"] == "demo_pack"
        assert result.metadata["entries_found"] >= 0
