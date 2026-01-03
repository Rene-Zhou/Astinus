"""Tests for PromptLoader."""

from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from src.backend.core.prompt_loader import (
    PromptLoader,
    PromptTemplate,
    get_prompt_loader,
    reset_prompt_loader,
)


class TestPromptTemplate:
    """Test suite for PromptTemplate class."""

    @pytest.fixture
    def sample_template_data(self):
        """Create sample template data."""
        return {
            "cn": {
                "role": "你是测试 Agent",
                "guidelines": ["规则1", "规则2"],
                "context": "玩家：{{ player_name }}",
                "task": "执行：{{ action }}",
            },
            "en": {
                "role": "You are a test agent",
                "guidelines": ["Rule 1", "Rule 2"],
                "context": "Player: {{ player_name }}",
                "task": "Execute: {{ action }}",
            },
        }

    def test_create_template(self, sample_template_data):
        """Test creating a prompt template."""
        template = PromptTemplate("test", sample_template_data)
        assert template.name == "test"
        assert template.data == sample_template_data

    def test_render_chinese(self, sample_template_data):
        """Test rendering Chinese prompt."""
        template = PromptTemplate("test", sample_template_data)
        result = template.render("cn", player_name="张伟", action="逃跑")

        assert "你是测试 Agent" in result
        assert "规则1" in result
        assert "规则2" in result
        assert "玩家：张伟" in result
        assert "执行：逃跑" in result

    def test_render_english(self, sample_template_data):
        """Test rendering English prompt."""
        template = PromptTemplate("test", sample_template_data)
        result = template.render("en", player_name="John", action="escape")

        assert "You are a test agent" in result
        assert "Rule 1" in result
        assert "Rule 2" in result
        assert "Player: John" in result
        assert "Execute: escape" in result

    def test_render_missing_language(self, sample_template_data):
        """Test rendering with missing language."""
        template = PromptTemplate("test", sample_template_data)

        with pytest.raises(KeyError, match="Language 'fr' not found"):
            template.render("fr")

    def test_render_missing_variable(self, sample_template_data):
        """Test rendering with missing template variable."""
        from jinja2 import UndefinedError

        template = PromptTemplate("test", sample_template_data)

        # Missing 'action' variable
        with pytest.raises(UndefinedError):
            template.render("cn", player_name="张伟")

    def test_get_system_message(self, sample_template_data):
        """Test getting system message only."""
        template = PromptTemplate("test", sample_template_data)
        result = template.get_system_message("cn")

        assert "你是测试 Agent" in result
        assert "规则1" in result
        assert "规则2" in result
        # Should NOT include context or task
        assert "玩家" not in result
        assert "执行" not in result

    def test_get_user_message(self, sample_template_data):
        """Test getting user message only."""
        template = PromptTemplate("test", sample_template_data)
        result = template.get_user_message("cn", player_name="张伟", action="逃跑")

        # Should include context and task
        assert "玩家：张伟" in result
        assert "执行：逃跑" in result
        # Should NOT include role or guidelines
        assert "你是测试 Agent" not in result
        assert "规则1" not in result

    def test_template_with_list_guidelines(self):
        """Test template with list-based guidelines."""
        data = {
            "cn": {
                "role": "测试",
                "guidelines": ["第一条", "第二条"],
            }
        }
        template = PromptTemplate("test", data)
        result = template.render("cn")

        assert "- 第一条" in result
        assert "- 第二条" in result

    def test_template_with_string_guidelines(self):
        """Test template with string guidelines."""
        data = {
            "cn": {
                "role": "测试",
                "guidelines": "这是单一指导原则",
            }
        }
        template = PromptTemplate("test", data)
        result = template.render("cn")

        assert "这是单一指导原则" in result


class TestPromptLoader:
    """Test suite for PromptLoader class."""

    @pytest.fixture
    def temp_prompts_dir(self, tmp_path):
        """Create temporary prompts directory with sample files."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()

        # Create sample prompt files
        sample1 = {
            "cn": {
                "role": "你是 Agent 1",
                "task": "任务1",
            },
            "en": {
                "role": "You are Agent 1",
                "task": "Task 1",
            },
        }

        sample2 = {
            "cn": {
                "role": "你是 Agent 2",
                "task": "执行：{{ action }}",
            },
        }

        with open(prompts_dir / "agent1.yaml", "w") as f:
            yaml.dump(sample1, f, allow_unicode=True)

        with open(prompts_dir / "agent2.yaml", "w") as f:
            yaml.dump(sample2, f, allow_unicode=True)

        return prompts_dir

    def test_create_loader(self, temp_prompts_dir):
        """Test creating a prompt loader."""
        loader = PromptLoader(temp_prompts_dir)
        assert loader.prompts_dir == temp_prompts_dir

    def test_get_template(self, temp_prompts_dir):
        """Test getting a template."""
        loader = PromptLoader(temp_prompts_dir)
        template = loader.get_template("agent1")

        assert isinstance(template, PromptTemplate)
        assert template.name == "agent1"

    def test_get_template_caching(self, temp_prompts_dir):
        """Test that templates are cached."""
        loader = PromptLoader(temp_prompts_dir)

        template1 = loader.get_template("agent1")
        template2 = loader.get_template("agent1")

        # Should return same instance (cached)
        assert template1 is template2

    def test_get_template_not_found(self, temp_prompts_dir):
        """Test getting non-existent template."""
        loader = PromptLoader(temp_prompts_dir)

        with pytest.raises(FileNotFoundError, match="Prompt template not found"):
            loader.get_template("nonexistent")

    def test_list_templates(self, temp_prompts_dir):
        """Test listing available templates."""
        loader = PromptLoader(temp_prompts_dir)
        templates = loader.list_templates()

        assert "agent1" in templates
        assert "agent2" in templates
        assert len(templates) == 2

    def test_list_templates_empty_dir(self, tmp_path):
        """Test listing templates in empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        loader = PromptLoader(empty_dir)
        templates = loader.list_templates()

        assert templates == []

    def test_reload_clears_cache(self, temp_prompts_dir):
        """Test that reload clears the cache."""
        loader = PromptLoader(temp_prompts_dir)

        template1 = loader.get_template("agent1")
        loader.reload()
        template2 = loader.get_template("agent1")

        # Should be different instances after reload
        assert template1 is not template2

    def test_template_rendering_from_file(self, temp_prompts_dir):
        """Test rendering a template loaded from file."""
        loader = PromptLoader(temp_prompts_dir)
        template = loader.get_template("agent2")

        result = template.render("cn", action="测试")
        assert "执行：测试" in result


class TestPromptLoaderGlobal:
    """Test suite for global prompt loader functions."""

    def test_get_prompt_loader_singleton(self):
        """Test that get_prompt_loader returns singleton."""
        reset_prompt_loader()

        loader1 = get_prompt_loader()
        loader2 = get_prompt_loader()

        assert loader1 is loader2

    def test_reset_prompt_loader(self):
        """Test resetting global prompt loader."""
        loader1 = get_prompt_loader()
        reset_prompt_loader()
        loader2 = get_prompt_loader()

        assert loader1 is not loader2

    def test_get_prompt_loader_custom_dir(self, tmp_path):
        """Test get_prompt_loader with custom directory."""
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()

        loader = get_prompt_loader(custom_dir)
        assert loader.prompts_dir == custom_dir


class TestRealPromptTemplates:
    """Test suite for real prompt templates in the project."""

    @pytest.fixture(autouse=True)
    def reset_loader(self):
        """Reset global loader before each test in this class."""
        reset_prompt_loader()
        yield
        reset_prompt_loader()

    def test_rule_agent_template_exists(self):
        """Test that rule_agent template exists."""
        loader = get_prompt_loader()
        templates = loader.list_templates()

        assert "rule_agent" in templates

    def test_rule_agent_template_has_both_languages(self):
        """Test that rule_agent has cn and en."""
        loader = get_prompt_loader()
        template = loader.get_template("rule_agent")

        assert "cn" in template.data
        assert "en" in template.data

    def test_rule_agent_renders_chinese(self):
        """Test rendering rule_agent in Chinese."""
        loader = get_prompt_loader()
        template = loader.get_template("rule_agent")

        result = template.render(
            "cn",
            character_name="张伟",
            traits=["运动健将", "口才"],
            tags=["右腿受伤"],
            action="逃离房间",
            argument="",  # Optional field
        )

        assert "规则裁判" in result
        assert "张伟" in result
        assert "右腿受伤" in result
        assert "逃离房间" in result

    def test_rule_agent_renders_english(self):
        """Test rendering rule_agent in English."""
        loader = get_prompt_loader()
        template = loader.get_template("rule_agent")

        result = template.render(
            "en",
            character_name="John",
            traits=["Athletic", "Charismatic"],
            tags=["Injured leg"],
            action="Escape the room",
            argument="",  # Optional field
        )

        assert "Rule Agent" in result
        assert "John" in result
        assert "Injured leg" in result
        assert "Escape the room" in result

    def test_gm_agent_template_exists(self):
        """Test that gm_agent template exists."""
        loader = get_prompt_loader()
        templates = loader.list_templates()

        assert "gm_agent" in templates

    def test_gm_agent_renders(self):
        """Test rendering gm_agent."""
        loader = get_prompt_loader()
        template = loader.get_template("gm_agent")

        result = template.render(
            "cn",
            current_location="暗室",
            active_npcs=["陈玲", "李明"],
            game_phase="等待输入",
            turn_count=5,
            player_input="我要查看房间",
        )

        assert "GM Agent" in result
        assert "暗室" in result
        assert "陈玲" in result
        assert "我要查看房间" in result
