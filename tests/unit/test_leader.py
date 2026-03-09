"""leader.py 单元测试。

验证首领 Agent 的初始化、感知、决策（回退策略 + 真实 LLM）和应用逻辑。
"""

import mesa
import numpy as np
import pytest

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.behaviors.markov import Personality
from civsim.agents.civilian import Civilian, Profession
from civsim.agents.leader import Leader, LeaderPerception
from civsim.config import CivSimConfig, load_config
from civsim.economy.settlement import Settlement
from civsim.llm.gateway import LLMGateway
from civsim.llm.prompts import validate_leader_decision
from civsim.politics.diplomacy import DiplomacyManager, DiplomaticStatus
from civsim.world.clock import Clock


class MockLeaderModel(mesa.Model):
    """首领测试用简易 Model。"""

    def __init__(self, seed: int | None = None) -> None:
        super().__init__(seed=seed)
        self.grid = mesa.space.MultiGrid(20, 20, torus=False)
        self.clock = Clock(ticks_per_day=4, days_per_season=30)
        self.config = CivSimConfig()
        self.db = None
        self.diplomacy = DiplomacyManager()
        self.leaders: list = []
        self.settlements: dict[int, Settlement] = {
            0: Settlement(
                id=0, name="聚落A", position=(5, 5),
                population=30,
                stockpile={"food": 300.0, "wood": 100.0, "ore": 30.0, "gold": 80.0},
            ),
            1: Settlement(
                id=1, name="聚落B", position=(15, 15),
                population=20,
                stockpile={"food": 200.0, "wood": 80.0, "ore": 20.0, "gold": 50.0},
            ),
        }


def _create_civilians(model: MockLeaderModel, sid: int, count: int) -> list:
    """创建平民放入指定聚落。"""
    civs = []
    pos = model.settlements[sid].position
    for _ in range(count):
        c = Civilian(
            model=model, home_settlement_id=sid,
            personality=Personality.NEUTRAL,
            profession=Profession.FARMER,
            revolt_threshold=0.4,
        )
        model.grid.place_agent(c, pos)
        civs.append(c)
    return civs


class TestLeaderInit:
    """测试首领初始化。"""

    def test_default_attributes(self) -> None:
        """验证首领创建后的默认属性。"""
        model = MockLeaderModel()
        leader = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0, 1],
        )
        model.grid.place_agent(leader, (5, 5))

        assert leader.faction_id == 1
        assert leader.controlled_settlements == [0, 1]
        assert leader.ideology == "务实"
        assert leader.decision_count == 0
        assert leader.last_decision is None

    def test_with_cache_disabled(self) -> None:
        """验证可以禁用缓存。"""
        model = MockLeaderModel()
        leader = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
            cache_enabled=False,
        )
        assert leader.cache is None


class TestLeaderPerception:
    """测试首领感知。"""

    def test_perceive_aggregates_settlements(self) -> None:
        """验证感知聚合所有下属聚落。"""
        model = MockLeaderModel()
        _create_civilians(model, 0, 5)
        _create_civilians(model, 1, 5)
        leader = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0, 1],
        )
        model.grid.place_agent(leader, (5, 5))

        perception = leader.perceive()
        assert perception is not None
        assert perception.faction_id == 1
        assert len(perception.settlements_info) == 2
        assert perception.total_population == 50  # 30 + 20

    def test_perceive_returns_none_without_settlements(self) -> None:
        """验证无聚落属性时返回 None。"""
        model = MockLeaderModel()
        delattr(model, "settlements")
        leader = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
        )
        model.grid.place_agent(leader, (5, 5))

        assert leader.perceive() is None

    def test_perceive_includes_diplomacy(self) -> None:
        """验证感知包含外交状态。"""
        model = MockLeaderModel()
        leader1 = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
        )
        leader2 = Leader(
            model=model, faction_id=2,
            controlled_settlements=[1],
        )
        model.leaders = [leader1, leader2]
        model.grid.place_agent(leader1, (5, 5))
        model.grid.place_agent(leader2, (15, 15))
        model.diplomacy.set_relation(1, 2, DiplomaticStatus.FRIENDLY, tick=0)

        _create_civilians(model, 0, 3)
        perception = leader1.perceive()
        assert perception is not None
        assert 2 in perception.diplomatic_status
        assert perception.diplomatic_status[2] == "FRIENDLY"

    def test_perception_to_features(self) -> None:
        """验证感知转为特征向量。"""
        p = LeaderPerception(
            faction_id=1, year=1, season="春",
            settlements_info=[{"id": 0, "name": "test"}],
            total_population=100,
            total_resources={"food": 500, "wood": 200, "ore": 50, "gold": 80},
            avg_satisfaction=0.7,
            diplomatic_status={}, active_treaties=[],
        )
        features = p.to_features()
        assert features["population"] == 100.0
        assert features["food"] == 500
        assert features["num_settlements"] == 1.0


class TestLeaderFallbackDecision:
    """测试首领回退策略。"""

    def test_fallback_reduces_tax_on_protest(self) -> None:
        """验证高抗议时回退策略降税。"""
        model = MockLeaderModel()
        leader = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
        )
        model.grid.place_agent(leader, (5, 5))

        perception = LeaderPerception(
            faction_id=1, year=1, season="春",
            settlements_info=[{
                "id": 0, "name": "聚落A",
                "population": 30, "food": 300,
                "satisfaction": 0.3, "protest_ratio": 0.5,
            }],
            total_population=30,
            total_resources={"food": 300, "wood": 100, "ore": 30, "gold": 80},
            avg_satisfaction=0.3,
            diplomatic_status={}, active_treaties=[],
        )
        decision = leader._fallback_decision(perception)
        directives = decision["policy_directives"]
        assert len(directives) == 1
        assert directives[0]["tax_change"] < 0

    def test_fallback_proposes_trade_when_stable(self) -> None:
        """验证稳定时回退策略提议贸易。"""
        model = MockLeaderModel()
        leader1 = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
        )
        leader2 = Leader(
            model=model, faction_id=2,
            controlled_settlements=[1],
        )
        model.leaders = [leader1, leader2]
        model.grid.place_agent(leader1, (5, 5))
        model.grid.place_agent(leader2, (15, 15))

        perception = LeaderPerception(
            faction_id=1, year=1, season="春",
            settlements_info=[{
                "id": 0, "name": "聚落A",
                "population": 30, "food": 300,
                "satisfaction": 0.7, "protest_ratio": 0.05,
            }],
            total_population=30,
            total_resources={"food": 300, "wood": 100, "ore": 30, "gold": 80},
            avg_satisfaction=0.7,
            diplomatic_status={2: "NEUTRAL"},
            active_treaties=[],
        )
        decision = leader1._fallback_decision(perception)
        diplo = decision["diplomatic_actions"]
        assert len(diplo) >= 1
        assert diplo[0]["action"] == "propose_trade"


class TestLeaderApplyDecision:
    """测试首领决策应用。"""

    def test_apply_policy_changes_tax(self) -> None:
        """验证政策指令改变聚落税率。"""
        model = MockLeaderModel()
        leader = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
        )
        model.grid.place_agent(leader, (5, 5))

        old_tax = model.settlements[0].tax_rate
        decision = validate_leader_decision({
            "policy_directives": [{
                "settlement_id": 0,
                "tax_change": -0.05,
                "security_change": 0.0,
                "resource_focus": "food",
            }],
            "diplomatic_actions": [],
            "overall_strategy": "test",
            "reasoning": "test",
        })
        leader.apply_decision(decision)
        assert model.settlements[0].tax_rate == pytest.approx(old_tax - 0.05)

    def test_apply_ignores_uncontrolled_settlement(self) -> None:
        """验证不应用到未控制的聚落。"""
        model = MockLeaderModel()
        leader = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],  # 只控制 0
        )
        model.grid.place_agent(leader, (5, 5))

        old_tax = model.settlements[1].tax_rate
        decision = validate_leader_decision({
            "policy_directives": [{
                "settlement_id": 1,  # 不属于该首领
                "tax_change": 0.1,
                "security_change": 0.0,
                "resource_focus": "balanced",
            }],
        })
        leader.apply_decision(decision)
        assert model.settlements[1].tax_rate == old_tax


class TestLeaderStep:
    """测试首领 step() 方法。"""

    def test_step_no_decision_at_tick_zero(self) -> None:
        """验证 tick=0 时不执行决策。"""
        model = MockLeaderModel()
        leader = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
        )
        model.grid.place_agent(leader, (5, 5))
        leader.step()
        assert leader.decision_count == 0

    def test_step_decision_at_year_boundary(self) -> None:
        """验证在年度边界时执行决策（使用回退策略）。"""
        model = MockLeaderModel()
        _create_civilians(model, 0, 3)
        leader = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
            gateway=None,
        )
        model.grid.place_agent(leader, (5, 5))

        # 推进到年度边界 (ticks_per_year = 4 * 30 * 4 = 480)
        ticks_per_year = (
            model.clock.ticks_per_day
            * model.clock.days_per_season
            * model.clock.seasons_per_year
        )
        for _ in range(ticks_per_year):
            model.clock.advance()

        leader.step()
        assert leader.decision_count == 1
        assert leader.last_decision is not None


class TestValidateLeaderDecision:
    """测试首领决策验证。"""

    def test_fills_missing_fields(self) -> None:
        """验证填充缺失字段。"""
        result = validate_leader_decision({})
        assert "diplomatic_actions" in result
        assert "policy_directives" in result
        assert "overall_strategy" in result
        assert "reasoning" in result

    def test_clamps_tax_change(self) -> None:
        """验证截断超范围税率变化。"""
        result = validate_leader_decision({
            "policy_directives": [{"tax_change": 0.5}],
        })
        assert result["policy_directives"][0]["tax_change"] == 0.1

    def test_clamps_security_change(self) -> None:
        """验证截断超范围治安变化。"""
        result = validate_leader_decision({
            "policy_directives": [{"security_change": -0.5}],
        })
        assert result["policy_directives"][0]["security_change"] == -0.15

    def test_invalid_action_normalized(self) -> None:
        """验证非法外交行动被修正为 none。"""
        result = validate_leader_decision({
            "diplomatic_actions": [{"action": "invalid_action"}],
        })
        assert result["diplomatic_actions"][0]["action"] == "none"

    def test_reasoning_truncated(self) -> None:
        """验证理由被截断到 300 字符。"""
        result = validate_leader_decision({
            "reasoning": "x" * 500,
        })
        assert len(result["reasoning"]) == 300


class TestLeaderRealLLM:
    """测试真实 LLM 调用的首领决策。"""

    @pytest.fixture()
    def gateway(self) -> LLMGateway | None:
        """创建使用真实配置的 LLM 网关。"""
        try:
            config = load_config()
        except FileNotFoundError:
            pytest.skip("找不到 config.yaml")
            return None

        gw = LLMGateway(max_retries=1, timeout=60)
        llm_cfg = config.llm
        for role in llm_cfg.models:
            model_cfg = llm_cfg.get_model_config(role)
            gw.register_model(role, model_cfg)
        return gw

    def test_real_llm_leader_decision(self, gateway: LLMGateway) -> None:
        """验证真实 LLM 生成的首领决策格式正确。"""
        if gateway is None:
            pytest.skip("LLM 网关不可用")

        model = MockLeaderModel()
        _create_civilians(model, 0, 5)
        _create_civilians(model, 1, 5)
        leader = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0, 1],
            gateway=gateway,
        )
        model.grid.place_agent(leader, (5, 5))

        perception = leader.perceive()
        assert perception is not None

        decision = leader.decide(perception)
        assert decision is not None
        assert "diplomatic_actions" in decision
        assert "policy_directives" in decision
        assert "reasoning" in decision
