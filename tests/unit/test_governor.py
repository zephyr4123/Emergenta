"""governor.py 单元测试。

验证镇长 Agent 的初始化、感知、决策和应用逻辑。
使用 MockModel 隔离测试镇长行为，同时包含真实 LLM 调用测试。
"""

import mesa
import pytest

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.behaviors.markov import Personality
from civsim.agents.civilian import Civilian, Profession
from civsim.agents.governor import Governor, GovernorPerception
from civsim.config import CivSimConfig, load_config
from civsim.economy.settlement import Settlement
from civsim.llm.gateway import LLMGateway
from civsim.llm.prompts import validate_governor_decision
from civsim.politics.governance import GovernanceAction, apply_governance_action
from civsim.world.clock import Clock


class MockGovernorModel(mesa.Model):
    """镇长测试用简易 Model。"""

    def __init__(
        self,
        width: int = 20,
        height: int = 20,
        seed: int | None = None,
    ) -> None:
        super().__init__(seed=seed)
        self.grid = mesa.space.MultiGrid(width, height, torus=False)
        self.clock = Clock(ticks_per_day=4, days_per_season=30)
        self.config = CivSimConfig()
        self.db = None
        self.settlements: dict[int, Settlement] = {
            0: Settlement(
                id=0,
                name="测试聚落A",
                position=(10, 10),
                population=50,
                stockpile={
                    "food": 500.0,
                    "wood": 200.0,
                    "ore": 50.0,
                    "gold": 100.0,
                },
            ),
        }


def _create_civilians_for_settlement(
    model: MockGovernorModel, count: int = 10
) -> list[Civilian]:
    """创建若干平民并放入聚落。"""
    civilians = []
    for _ in range(count):
        civ = Civilian(
            model=model,
            home_settlement_id=0,
            personality=Personality.NEUTRAL,
            profession=Profession.FARMER,
            revolt_threshold=0.4,
        )
        model.grid.place_agent(civ, (10, 10))
        civilians.append(civ)
    return civilians


class TestGovernorInit:
    """测试镇长初始化。"""

    def test_default_attributes(self) -> None:
        """验证镇长创建后的默认属性。"""
        model = MockGovernorModel()
        gov = Governor(model=model, settlement_id=0)
        model.grid.place_agent(gov, (10, 10))

        assert gov.settlement_id == 0
        assert gov.last_decision is None
        assert gov.decision_count == 0
        assert gov.memory.short_term_count == 0

    def test_with_cache_disabled(self) -> None:
        """验证可以禁用缓存。"""
        model = MockGovernorModel()
        gov = Governor(model=model, settlement_id=0, cache_enabled=False)
        assert gov.cache is None


class TestGovernorPerception:
    """测试镇长感知。"""

    def test_perceive_returns_data(self) -> None:
        """验证感知返回正确的聚落数据。"""
        model = MockGovernorModel()
        _create_civilians_for_settlement(model, count=10)
        gov = Governor(model=model, settlement_id=0)
        model.grid.place_agent(gov, (10, 10))

        perception = gov.perceive()
        assert perception is not None
        assert perception.settlement_name == "测试聚落A"
        assert perception.population == 50
        assert perception.food == 500.0
        assert perception.tax_rate == 0.1

    def test_perceive_with_no_settlement(self) -> None:
        """验证无聚落时返回 None。"""
        model = MockGovernorModel()
        model.settlements = {}
        gov = Governor(model=model, settlement_id=99)
        model.grid.place_agent(gov, (5, 5))

        perception = gov.perceive()
        assert perception is None

    def test_perceive_calculates_protest_ratio(self) -> None:
        """验证感知正确计算抗议率。"""
        model = MockGovernorModel()
        civilians = _create_civilians_for_settlement(model, count=10)
        # 设置 3 个抗议
        for i in range(3):
            civilians[i].state = CivilianState.PROTESTING

        gov = Governor(model=model, settlement_id=0)
        model.grid.place_agent(gov, (10, 10))

        perception = gov.perceive()
        assert perception is not None
        assert perception.protest_ratio == pytest.approx(0.3)

    def test_perception_to_features(self) -> None:
        """验证感知数据转为特征向量。"""
        p = GovernorPerception(
            settlement_name="test",
            population=100,
            food=500.0,
            wood=200.0,
            ore=50.0,
            gold=100.0,
            tax_rate=0.1,
            security_level=0.5,
            satisfaction_avg=0.7,
            protest_ratio=0.05,
            scarcity_index=0.2,
            per_capita_food=5.0,
            season="春",
        )
        features = p.to_features()
        assert features["population"] == 100.0
        assert features["food"] == 500.0
        assert "scarcity_index" in features


class TestGovernorFallbackDecision:
    """测试镇长回退策略（无 LLM 时）。"""

    def test_fallback_with_food_scarcity(self) -> None:
        """食物紧缺时应降税。"""
        model = MockGovernorModel()
        gov = Governor(model=model, settlement_id=0, gateway=None)
        model.grid.place_agent(gov, (10, 10))

        perception = GovernorPerception(
            settlement_name="test",
            population=100,
            food=50.0,
            wood=200.0,
            ore=50.0,
            gold=100.0,
            tax_rate=0.3,
            security_level=0.5,
            satisfaction_avg=0.5,
            protest_ratio=0.05,
            scarcity_index=0.9,
            per_capita_food=0.5,
            season="冬",
        )
        decision = gov._fallback_decision(perception)
        assert decision["tax_rate_change"] < 0

    def test_fallback_with_high_protest(self) -> None:
        """高抗议率时应增加治安。"""
        model = MockGovernorModel()
        gov = Governor(model=model, settlement_id=0, gateway=None)
        model.grid.place_agent(gov, (10, 10))

        perception = GovernorPerception(
            settlement_name="test",
            population=100,
            food=500.0,
            wood=200.0,
            ore=50.0,
            gold=100.0,
            tax_rate=0.2,
            security_level=0.3,
            satisfaction_avg=0.4,
            protest_ratio=0.35,
            scarcity_index=0.1,
            per_capita_food=5.0,
            season="春",
        )
        decision = gov._fallback_decision(perception)
        assert decision["security_change"] > 0

    def test_fallback_stable_situation(self) -> None:
        """稳定局势时可加税。"""
        model = MockGovernorModel()
        gov = Governor(model=model, settlement_id=0, gateway=None)
        model.grid.place_agent(gov, (10, 10))

        perception = GovernorPerception(
            settlement_name="test",
            population=100,
            food=500.0,
            wood=200.0,
            ore=50.0,
            gold=100.0,
            tax_rate=0.1,
            security_level=0.5,
            satisfaction_avg=0.8,
            protest_ratio=0.02,
            scarcity_index=0.1,
            per_capita_food=5.0,
            season="夏",
        )
        decision = gov._fallback_decision(perception)
        assert decision["tax_rate_change"] > 0


class TestGovernorApplyDecision:
    """测试决策应用。"""

    def test_apply_changes_tax_rate(self) -> None:
        """验证决策改变税率。"""
        model = MockGovernorModel()
        gov = Governor(model=model, settlement_id=0)
        model.grid.place_agent(gov, (10, 10))
        model.clock.advance()  # tick=1

        old_tax = model.settlements[0].tax_rate
        decision = validate_governor_decision({
            "tax_rate_change": 0.05,
            "security_change": 0.0,
            "resource_focus": "balanced",
            "reasoning": "测试",
        })
        gov.apply_decision(decision)
        assert model.settlements[0].tax_rate == pytest.approx(old_tax + 0.05)

    def test_apply_changes_security(self) -> None:
        """验证决策改变治安水平。"""
        model = MockGovernorModel()
        gov = Governor(model=model, settlement_id=0)
        model.grid.place_agent(gov, (10, 10))
        model.clock.advance()

        old_sec = model.settlements[0].security_level
        decision = validate_governor_decision({
            "tax_rate_change": 0.0,
            "security_change": 0.1,
            "resource_focus": "food",
            "reasoning": "测试",
        })
        gov.apply_decision(decision)
        assert model.settlements[0].security_level == pytest.approx(old_sec + 0.1)

    def test_apply_clamps_values(self) -> None:
        """验证决策应用后值不越界。"""
        model = MockGovernorModel()
        model.settlements[0].tax_rate = 0.95
        gov = Governor(model=model, settlement_id=0)
        model.grid.place_agent(gov, (10, 10))
        model.clock.advance()

        decision = validate_governor_decision({
            "tax_rate_change": 0.1,
            "security_change": 0.0,
            "resource_focus": "balanced",
            "reasoning": "测试",
        })
        gov.apply_decision(decision)
        assert model.settlements[0].tax_rate <= 1.0


class TestGovernorStep:
    """测试镇长 step() 方法。"""

    def test_step_no_decision_at_tick_zero(self) -> None:
        """验证 tick=0 时不执行决策。"""
        model = MockGovernorModel()
        gov = Governor(model=model, settlement_id=0, gateway=None)
        model.grid.place_agent(gov, (10, 10))
        gov.step()
        assert gov.decision_count == 0

    def test_step_decision_at_season_boundary(self) -> None:
        """验证在季度边界时执行决策（使用回退策略）。"""
        model = MockGovernorModel()
        _create_civilians_for_settlement(model, count=5)
        gov = Governor(model=model, settlement_id=0, gateway=None)
        model.grid.place_agent(gov, (10, 10))
        # 将偏移置零，确保决策恰好在 tick=120 触发
        gov.decision_offset = 0

        # 推进到第一个季度边界 (ticks_per_season = 4 * 30 = 120)
        for _ in range(120):
            model.clock.advance()

        gov.step()
        assert gov.decision_count == 1
        assert gov.last_decision is not None

    def test_step_no_decision_mid_season(self) -> None:
        """验证季度中间不执行决策。"""
        model = MockGovernorModel()
        gov = Governor(model=model, settlement_id=0, gateway=None)
        model.grid.place_agent(gov, (10, 10))

        model.clock.advance()  # tick=1
        gov.step()
        assert gov.decision_count == 0

    def test_step_records_memory(self) -> None:
        """验证决策后记录到记忆系统。"""
        model = MockGovernorModel()
        _create_civilians_for_settlement(model, count=5)
        gov = Governor(model=model, settlement_id=0, gateway=None)
        model.grid.place_agent(gov, (10, 10))
        gov.decision_offset = 0

        for _ in range(120):
            model.clock.advance()
        gov.step()

        assert gov.memory.short_term_count == 1


class TestGovernanceModule:
    """测试 politics/governance.py 模块。"""

    def test_governance_action_from_decision(self) -> None:
        """验证从决策字典创建 GovernanceAction。"""
        decision = {
            "tax_rate_change": 0.05,
            "security_change": -0.1,
            "resource_focus": "food",
            "reasoning": "食物紧缺",
        }
        action = GovernanceAction.from_decision(decision)
        assert action.tax_rate_change == 0.05
        assert action.security_change == -0.1
        assert action.resource_focus == "food"

    def test_apply_governance_action(self) -> None:
        """验证治理行动应用到聚落。"""
        settlement = Settlement(
            id=0, name="test", position=(0, 0),
            tax_rate=0.2, security_level=0.5,
        )
        action = GovernanceAction(
            tax_rate_change=0.05,
            security_change=0.1,
        )
        changes = apply_governance_action(settlement, action)
        assert settlement.tax_rate == pytest.approx(0.25)
        assert settlement.security_level == pytest.approx(0.6)
        assert changes["tax_rate_old"] == pytest.approx(0.2)

    def test_apply_clamps_to_range(self) -> None:
        """验证应用时截断到 [0, 1] 范围。"""
        settlement = Settlement(
            id=0, name="test", position=(0, 0),
            tax_rate=0.95, security_level=0.05,
        )
        action = GovernanceAction(
            tax_rate_change=0.1,
            security_change=-0.15,
        )
        apply_governance_action(settlement, action)
        assert settlement.tax_rate <= 1.0
        assert settlement.security_level >= 0.0

    def test_validate_decision_clamps_values(self) -> None:
        """验证决策验证截断超范围值。"""
        raw = {
            "tax_rate_change": 0.5,  # 超范围
            "security_change": -0.5,  # 超范围
            "resource_focus": "food",
            "reasoning": "test",
        }
        result = validate_governor_decision(raw)
        assert result["tax_rate_change"] == 0.1
        assert result["security_change"] == -0.15

    def test_validate_decision_missing_field_raises(self) -> None:
        """验证缺少字段时报错。"""
        with pytest.raises(ValueError, match="缺少必要字段"):
            validate_governor_decision({"tax_rate_change": 0.0})


class TestGovernorRealLLM:
    """测试真实 LLM 调用的镇长决策。"""

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

    def test_real_llm_governor_decision(self, gateway: LLMGateway) -> None:
        """验证真实 LLM 生成的镇长决策格式正确。"""
        if gateway is None:
            pytest.skip("LLM 网关不可用")

        model = MockGovernorModel()
        _create_civilians_for_settlement(model, count=10)
        gov = Governor(model=model, settlement_id=0, gateway=gateway)
        model.grid.place_agent(gov, (10, 10))

        perception = gov.perceive()
        assert perception is not None

        decision = gov.decide(perception)
        assert decision is not None
        assert "tax_rate_change" in decision
        assert "security_change" in decision
        assert "resource_focus" in decision
        assert "reasoning" in decision
        assert -0.1 <= decision["tax_rate_change"] <= 0.1
        assert -0.15 <= decision["security_change"] <= 0.15
