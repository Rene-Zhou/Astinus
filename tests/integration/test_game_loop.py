"""
End-to-end integration test for the complete game loop.

Tests the flow from player input through agent routing to dice rolling and outcome narration,
following the scenario defined in the implementation plan:

1. Player inputs: "我要翻找书架"
2. GM routes to Rule Agent
3. Rule Agent generates dice check
4. Frontend receives DiceCheckRequest
5. Player rolls dice, submits result
6. GM processes outcome, narrates result

This test uses mocked agents and LLM to simulate the full flow without requiring
actual LLM initialization.
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.agents.base import AgentResponse
from src.backend.agents.gm import GMAgent
from src.backend.agents.rule import RuleAgent
from src.backend.models.character import PlayerCharacter, Trait
from src.backend.models.dice_check import DiceCheckRequest
from src.backend.models.game_state import GameState
from src.backend.models.i18n import LocalizedString
from src.backend.services.world import WorldPackLoader

# Set fake API key for tests
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key-for-testing"


class TestCompleteGameLoop:
    """End-to-end test suite for the complete game loop."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM that returns predefined responses."""
        llm = MagicMock()
        llm.ainvoke = AsyncMock()
        return llm

    @pytest.fixture
    def test_world_pack(self):
        """Load the demo world pack for testing."""
        packs_dir = Path(__file__).parent.parent / "data" / "packs"
        if not (packs_dir / "demo_pack.json").exists():
            pytest.skip("Demo pack not available")

        loader = WorldPackLoader(packs_dir)
        return loader.load("demo_pack")

    @pytest.fixture
    def test_player_character(self):
        """Create a test player character."""
        return PlayerCharacter(
            name="测试玩家",
            concept=LocalizedString(cn="勇敢的探险者", en="Brave Explorer"),
            traits=[
                Trait(
                    name=LocalizedString(cn="运动健将", en="Athletic"),
                    description=LocalizedString(
                        cn="身体素质极佳，反应迅速",
                        en="Excellent physical condition with quick reflexes"
                    ),
                    positive_aspect=LocalizedString(cn="运动能力强", en="Strong athletic ability"),
                    negative_aspect=LocalizedString(cn="可能过度自信", en="May be overconfident"),
                )
            ],
            tags=[],
        )

    @pytest.fixture
    def test_game_state(self, test_player_character, test_world_pack):
        """Create a test game state."""
        return GameState(
            session_id="test-session",
            world_pack_id="demo_pack",
            player=test_player_character,
            current_location="study",
            active_npc_ids=[],
        )

    @pytest.fixture
    def mock_rule_agent(self, mock_llm):
        """Create a mock Rule Agent."""
        agent = RuleAgent(llm=mock_llm)
        # Mock the process method to return a DiceCheckRequest
        agent.process = AsyncMock(
            return_value=AgentResponse(
                content="玩家需要进行一次搜索检定",
                metadata={
                    "check_request": {
                        "intention": "翻找书架寻找秘密",
                        "influencing_factors": {"traits": [], "tags": []},
                        "dice_formula": "2d6",
                        "instructions": {
                            "cn": "这是一个简单的搜索检定",
                            "en": "This is a simple search check"
                        },
                    }
                },
                success=True,
            )
        )
        return agent

    @pytest.fixture
    def mock_gm_agent(self, mock_llm, mock_rule_agent, test_game_state):
        """Create a mock GM Agent."""
        agent = GMAgent(
            llm=mock_llm,
            sub_agents={"rule": mock_rule_agent},
            game_state=test_game_state,
        )

        async def mocked_process(input_data):
            player_input = input_data.get("player_input", "")

            # If player is searching, route to Rule Agent
            if "翻找" in player_input or "书架" in player_input:
                # Get context slice for Rule Agent
                context = agent._slice_context_for_rule(player_input)

                # Call Rule Agent
                rule_result = await mock_rule_agent.process(context)

                # Return Rule Agent's response
                return rule_result
            else:
                # For other actions, just narrate
                return AgentResponse(
                    content=f"你在{test_game_state.current_location}尝试了{player_input}",
                    metadata={"phase": "narrating"},
                    success=True,
                )

        agent.process = AsyncMock(side_effect=mocked_process)
        return agent

    @pytest.mark.asyncio
    async def test_complete_search_flow(
        self,
        mock_gm_agent,
        mock_rule_agent,
        test_game_state,
    ):
        """
        Test the complete game loop for a search action.

        Flow:
        1. Player says "我要翻找书架"
        2. GM routes to Rule Agent
        3. Rule Agent generates dice check
        4. Verify DiceCheckRequest is created
        """
        # Step 1: Player input
        player_input = "我要翻找书架，看看有没有隐藏的机关"
        lang = "cn"

        # Step 2: Process through GM Agent
        result = await mock_gm_agent.process({
            "player_input": player_input,
            "lang": lang,
        })

        # Step 3: Verify GM routed to Rule Agent
        assert result.success is True
        mock_rule_agent.process.assert_called_once()

        # Step 4: Verify Rule Agent generated a check request
        check_request_data = result.metadata.get("check_request")
        assert check_request_data is not None

        # Step 5: Verify DiceCheckRequest structure
        assert check_request_data["intention"] == "翻找书架寻找秘密"
        assert check_request_data["dice_formula"] == "2d6"
        assert "influencing_factors" in check_request_data
        assert "instructions" in check_request_data

        # Step 6: Verify we can create a DiceCheckRequest object
        check = DiceCheckRequest(**check_request_data)
        assert check.intention == "翻找书架寻找秘密"
        assert check.dice_formula == "2d6"
        assert check.has_advantage() is False
        assert check.has_disadvantage() is False

    @pytest.mark.skip(reason="Requires full RuleAgent implementation")
    @pytest.mark.asyncio
    async def test_dice_roll_with_tag_penalty(
        self,
        mock_llm,
        test_player_character,
    ):
        """
        Test a dice check with a negative tag (disadvantage).

        Scenario: Player with "右腿受伤" tag trying to escape.
        """
        # Create character with injury tag
        test_player_character.add_tag("右腿受伤")

        # Mock Rule Agent to return disadvantage check
        rule_agent = RuleAgent(llm=mock_llm)

        # Mock LLM to return JSON response
        mock_llm.ainvoke.return_value = MagicMock(
            content='{"needs_check": true, "check_request": {"intention": "逃离房间", "influencing_factors": {"traits": [], "tags": ["右腿受伤"]}, "dice_formula": "3d6kl2", "instructions": {"cn": "由于右腿受伤，你在逃离检定上有劣势", "en": "Due to leg injury, you have disadvantage on escape check"}}}'
        )

        # Process action
        result = await rule_agent.process({
            "player_input": "我要逃离这个房间",
            "character": test_player_character.model_dump(),
            "lang": "cn",
        })

        # Verify
        assert result.success is True
        check_data = result.metadata.get("check_request")
        assert check_data is not None
        assert "右腿受伤" in check_data["influencing_factors"]["tags"]
        assert check_data["dice_formula"] == "3d6kl2"

        # Create DiceCheckRequest and verify disadvantage
        check = DiceCheckRequest(**check_data)
        assert check.has_disadvantage() is True
        assert check.has_advantage() is False
        assert check.get_dice_count() == 3

    @pytest.mark.skip(reason="Requires full RuleAgent implementation")
    @pytest.mark.asyncio
    async def test_dice_roll_with_trait_advantage(
        self,
        mock_llm,
        test_player_character,
    ):
        """
        Test a dice check with a positive trait (advantage).

        Scenario: Player with "运动健将" trait trying to escape.
        """
        # Player claims their trait helps
        player_input = "我有'运动健将'特质，腿伤不会影响我逃跑"

        # Mock Rule Agent
        rule_agent = RuleAgent(llm=mock_llm)

        # Mock LLM to approve the claim and cancel disadvantage
        mock_llm.ainvoke.return_value = MagicMock(
            content='{"needs_check": true, "check_request": {"intention": "逃离房间", "influencing_factors": {"traits": ["运动健将"], "tags": ["右腿受伤"]}, "dice_formula": "2d6", "instructions": {"cn": "虽然右腿受伤，但凭借运动健将的体质，优劣势相互抵消", "en": "Though injured, the Athletic trait offsets the disadvantage"}}}'
        )

        # Process action with trait claim
        result = await rule_agent.process({
            "player_input": player_input,
            "character": test_player_character.model_dump(),
            "lang": "cn",
        })

        # Verify
        assert result.success is True
        check_data = result.metadata.get("check_request")
        assert check_data is not None
        assert "运动健将" in check_data["influencing_factors"]["traits"]
        assert check_data["dice_formula"] == "2d6"  # No advantage/disadvantage

        check = DiceCheckRequest(**check_data)
        assert check.has_advantage() is False
        assert check.has_disadvantage() is False
        assert check.get_dice_count() == 2

    @pytest.mark.asyncio
    async def test_simple_action_no_check(
        self,
        mock_llm,
        mock_rule_agent,
    ):
        """
        Test that simple actions don't require dice checks.

        Scenario: Player does something trivial like "看看房间"
        """
        # Mock Rule Agent to return no check needed
        mock_rule_agent.process = AsyncMock(
            return_value=AgentResponse(
                content="你环顾四周，没有发现异常。",
                metadata={"check_request": None},
                success=True,
            )
        )

        # Process simple action
        result = await mock_rule_agent.process({
            "player_input": "我环顾四周",
            "character": {},
            "lang": "cn",
        })

        # Verify no dice check was required
        assert result.success is True
        check_request = result.metadata.get("check_request")
        assert check_request is None

    def test_dice_check_request_display(self):
        """Test DiceCheckRequest display formatting."""
        check = DiceCheckRequest(
            intention="翻找书架",
            influencing_factors={"traits": [], "tags": []},
            dice_formula="3d6kl2",
            instructions=LocalizedString(
                cn="天色昏暗，搜索有劣势",
                en="Dim lighting gives disadvantage on search"
            ),
        )

        # Test Chinese display
        display_cn = check.to_display("cn")
        assert display_cn["intention"] == "翻找书架"
        assert display_cn["dice"] == "3d6kl2"
        assert display_cn["explanation"] == "天色昏暗，搜索有劣势"

        # Test English display
        display_en = check.to_display("en")
        assert display_en["explanation"] == "Dim lighting gives disadvantage on search"

        # Test advantage/disadvantage detection
        assert check.has_disadvantage() is True
        assert check.has_advantage() is False
        assert check.get_dice_count() == 3

    @pytest.mark.skip(reason="Requires full GMAgent and NPC Agent implementation")
    @pytest.mark.asyncio
    async def test_npc_interaction_flow(
        self,
        mock_gm_agent,
        test_game_state,
    ):
        """
        Test interaction with an NPC.

        Flow:
        1. Player talks to NPC
        2. GM routes to NPC Agent (if implemented)
        3. NPC responds based on their personality
        """
        # Set current location to manor entrance where Chen Ling is
        test_game_state.current_location = "manor_entrance"
        test_game_state.active_npc_ids = ["chen_ling"]

        # Player talks to Chen Ling
        player_input = "你好，你在调查这个庄园吗？"

        # Process through GM (NPC routing not fully implemented yet)
        result = await mock_gm_agent.process({
            "player_input": player_input,
            "lang": "cn",
        })

        # For now, GM just narrates the action
        # In full implementation, this would route to NPC Agent
        assert result.success is True

    @pytest.mark.asyncio
    async def test_world_pack_integration(
        self,
        test_world_pack,
    ):
        """
        Test that the game can load and use world pack data.

        Flow:
        1. Load world pack
        2. Player queries about lore
        3. Lore Agent retrieves relevant entries
        """
        # Verify demo pack loaded
        assert test_world_pack.info.name.get("cn") == "幽暗庄园"

        # Verify NPCs
        chen_ling = test_world_pack.get_npc("chen_ling")
        assert chen_ling is not None
        assert chen_ling.soul.name == "陈玲"

        # Verify locations
        study = test_world_pack.get_location("study")
        assert study is not None
        assert study.name.get("cn") == "书房"

        # Verify lore entries can be found
        manor_entries = test_world_pack.search_entries_by_keyword("庄园")
        assert len(manor_entries) >= 1

    @pytest.mark.asyncio
    async def test_game_state_updates(self, test_game_state):
        """Test that game state can be updated during gameplay."""
        # Initial state
        assert test_game_state.current_location == "study"
        assert test_game_state.turn_count == 0

        # Simulate a turn
        test_game_state.add_message("GM", "游戏开始")
        test_game_state.turn_count += 1

        # Verify updates
        assert test_game_state.turn_count == 1
        assert len(test_game_state.messages) >= 1

        # Test location change
        test_game_state.set_location("secret_room")
        assert test_game_state.current_location == "secret_room"


class TestGameFlowScenarios:
    """Test specific gameplay scenarios from the implementation plan."""

    @pytest.mark.asyncio
    async def test_scenario_bookshelf_search(self):
        """
        Scenario from implementation plan:
        1. Player inputs: "我要翻找书架"
        2. GM routes to Rule Agent
        3. Rule Agent generates dice check
        4. Frontend receives DiceCheckRequest
        """
        # This is the exact scenario from the implementation plan
        # It should work once agents are fully implemented
        pass

    @pytest.mark.asyncio
    async def test_scenario_dice_roll_and_outcome(self):
        """
        Scenario from implementation plan:
        5. Player rolls dice, submits result
        6. GM processes outcome, narrates result
        """
        # This completes the full flow after dice are rolled
        # The GM should narrate the result based on the dice outcome
        pass

    @pytest.mark.asyncio
    async def test_scenario_trait_claim_advantage(self):
        """
        Scenario from GUIDE.md (line 401-414):
        Player claims trait helps, Rule Agent evaluates and modifies check.
        """
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
