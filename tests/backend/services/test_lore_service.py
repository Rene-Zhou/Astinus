"""Tests for Lore Service."""

from pathlib import Path

import pytest

from src.backend.services.lore import LoreService
from src.backend.services.world import WorldPackLoader


class TestLoreService:
    """Test suite for Lore Service."""

    @pytest.fixture
    def world_loader(self):
        """Create a world pack loader for testing."""
        packs_dir = Path(__file__).parent.parent.parent / "data" / "packs"
        if not (packs_dir / "demo_pack.json").exists():
            pytest.skip("Demo pack not available")
        return WorldPackLoader(packs_dir)

    @pytest.fixture
    def lore_service(self, world_loader):
        """Create a Lore Service for testing."""
        return LoreService(world_loader, vector_store=None)

    def test_lore_service_creation(self, lore_service, world_loader):
        """Test Lore Service initialization."""
        assert lore_service.world_pack_loader is not None
        assert lore_service.world_pack_loader == world_loader

    def test_search_simple_query(self, lore_service, world_loader):
        """Test searching for simple lore query."""
        world_loader.load("demo_pack")

        result = lore_service.search(
            query="幽暗庄园的历史",
            context="玩家询问庄园的背景",
            world_pack_id="demo_pack",
            lang="cn",
        )

        assert len(result) > 0
        assert "幽暗庄园" in result or "庄园" in result
        assert "背景信息" in result

    def test_search_keyword_search(self, lore_service):
        """Test searching by specific keywords."""
        result = lore_service.search(
            query="管家",
            context="玩家询问关于管家的事情",
            world_pack_id="demo_pack",
            lang="cn",
        )

        assert len(result) > 0
        assert "管家" in result

    def test_search_location_query(self, lore_service):
        """Test querying about locations."""
        result = lore_service.search(
            query="书房",
            context="玩家询问书房的信息",
            world_pack_id="demo_pack",
            lang="cn",
        )

        assert len(result) > 0
        assert "背景信息" in result or "related" in result

    def test_search_no_query(self, lore_service):
        """Test error when no query provided."""
        result = lore_service.search(
            context="玩家询问",
            lang="cn",
        )

        assert "未提供查询" in result or "No query provided" in result

    def test_search_invalid_pack(self, lore_service):
        """Test error with invalid world pack."""
        result = lore_service.search(
            query="测试",
            world_pack_id="nonexistent_pack",
            lang="cn",
        )

        assert "出错" in result or "Error" in result

    def test_extract_search_terms(self, lore_service):
        """Test extraction of search terms from queries."""
        # Test Chinese query (treated as one term by jieba)
        terms = lore_service._extract_search_terms("我想了解暴风城的历史")
        assert len(terms) >= 1
        assert "历史" in terms or "暴风城" in terms

        # Test English query (has spaces, split properly)
        terms = lore_service._extract_search_terms("Tell me about Stormwind")
        assert "Stormwind" in terms or "about" in terms

        # Test query with punctuation
        terms = lore_service._extract_search_terms("风暴城！")
        assert len(terms) >= 1

    def test_format_lore_with_entries(self, lore_service, world_loader):
        """Test formatting lore with actual entries."""
        world_pack = world_loader.load("demo_pack")
        entries = world_pack.search_entries_by_keyword("庄园")

        formatted = lore_service._format_lore(entries, "庄园", "玩家询问", lang="cn")

        assert len(formatted) > 0
        assert "背景信息" in formatted

    def test_format_lore_no_entries(self, lore_service):
        """Test formatting when no entries found."""
        formatted = lore_service._format_lore([], "未知主题", "玩家询问", lang="cn")

        assert "没有找到" in formatted
        assert "未知主题" in formatted

    def test_search_lore(self, lore_service, world_loader):
        """Test lore search functionality."""
        world_pack = world_loader.load("demo_pack")

        entries = lore_service._search_lore(world_pack, "幽暗庄园的历史", "玩家询问庄园背景")

        assert len(entries) > 0
        assert any("庄园" in str(entry.key) for entry in entries)


class TestLoreServiceIntegration:
    """Integration tests for Lore Service with world packs."""

    @pytest.fixture
    def world_loader(self):
        """Create a world pack loader."""
        packs_dir = Path(__file__).parent.parent / "data" / "packs"
        if not (packs_dir / "demo_pack.json").exists():
            pytest.skip("Demo pack not available")
        return WorldPackLoader(packs_dir)

    @pytest.fixture
    def lore_service(self, world_loader):
        """Create a Lore Service for integration testing."""
        return LoreService(world_loader, vector_store=None)

    def test_full_lore_query_flow(self, lore_service):
        """Test complete lore query flow."""
        result = lore_service.search(
            query="陈玲是谁",
            context="玩家遇到陈玲，想了解她的背景",
            world_pack_id="demo_pack",
            lang="cn",
        )

        assert len(result) > 0
        assert "陈玲" in result or "背景信息" in result
