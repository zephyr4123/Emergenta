"""集成测试：镇长 Agent 与平民系统的交互。

验证镇长决策对平民行为、聚落经济和系统动力学的影响。
"""

import pytest

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.civilian import Civilian
from civsim.agents.governor import Governor
from civsim.config import CivSimConfig, load_config
from civsim.llm.gateway import LLMGateway
from civsim.world.engine import CivilizationEngine


def _make_governor_config(enable_governors: bool = True) -> CivSimConfig:
    """构造包含镇长的小型测试配置。"""
    return CivSimConfig(
        world={
            "grid": {"width": 20, "height": 20},
            "map_generation": {"seed": 42},
            "settlement": {"initial_count": 2, "min_suitability_score": 0.0},
        },
        agents={
            "civilian": {"initial_count": 20},
            "governor": {"initial_count": 1 if enable_governors else 0},
        },
        resources={
            "initial_stockpile": {"food": 500, "wood": 200, "ore": 50, "gold": 100},
        },
    )


def _get_civilians(engine: CivilizationEngine) -> list[Civilian]:
    """获取所有平民。"""
    return [a for a in engine.agents if isinstance(a, Civilian)]


def _get_governors(engine: CivilizationEngine) -> list[Governor]:
    """获取所有镇长。"""
    return [a for a in engine.agents if isinstance(a, Governor)]


class TestGovernorSpawning:
    """测试镇长生成。"""

    def test_governors_created_with_settlements(self) -> None:
        """验证启用镇长后每个聚落都有镇长。"""
        config = _make_governor_config(enable_governors=True)
        engine = CivilizationEngine(config=config, seed=42, enable_governors=True)

        governors = _get_governors(engine)
        assert len(governors) == len(engine.settlements)

    def test_governor_linked_to_settlement(self) -> None:
        """验证镇长与聚落正确关联。"""
        config = _make_governor_config(enable_governors=True)
        engine = CivilizationEngine(config=config, seed=42, enable_governors=True)

        for gov in _get_governors(engine):
            assert gov.settlement_id in engine.settlements
            settlement = engine.settlements[gov.settlement_id]
            assert settlement.governor_id == gov.unique_id

    def test_no_governors_without_flag(self) -> None:
        """验证不启用镇长时无镇长创建。"""
        config = _make_governor_config(enable_governors=False)
        engine = CivilizationEngine(config=config, seed=42, enable_governors=False)

        governors = _get_governors(engine)
        assert len(governors) == 0


class TestGovernorTaxEffect:
    """测试镇长加税对平民的影响。"""

    def test_tax_increase_reduces_satisfaction(self) -> None:
        """镇长加税后平民满意度应下降。"""
        config = _make_governor_config()
        engine = CivilizationEngine(config=config, seed=42, enable_governors=True)

        # 记录初始满意度
        civilians = _get_civilians(engine)
        initial_avg_satisfaction = sum(c.satisfaction for c in civilians) / len(civilians)

        # 手动对所有聚落加高税率
        for settlement in engine.settlements.values():
            settlement.tax_rate = 0.8

        # 运行若干 tick
        for _ in range(50):
            engine.step()

        civilians = _get_civilians(engine)
        if civilians:
            final_avg_satisfaction = sum(c.satisfaction for c in civilians) / len(civilians)
            assert final_avg_satisfaction < initial_avg_satisfaction, (
                f"加税后满意度应下降: 初始 {initial_avg_satisfaction:.3f} → "
                f"最终 {final_avg_satisfaction:.3f}"
            )


class TestGovernorSecurityEffect:
    """测试镇长治安投入的影响。"""

    def test_high_security_suppresses_protest(self) -> None:
        """高治安水平应抑制抗议。"""
        config = _make_governor_config()
        engine = CivilizationEngine(config=config, seed=42, enable_governors=True)

        # 设置高治安
        for settlement in engine.settlements.values():
            settlement.security_level = 0.9
            settlement.tax_rate = 0.1  # 低税率

        # 运行足够 tick
        for _ in range(100):
            engine.step()

        civilians = _get_civilians(engine)
        protesting = sum(1 for c in civilians if c.state == CivilianState.PROTESTING)
        # 高治安 + 低税率环境下，抗议应很少
        total = len(civilians)
        if total > 0:
            protest_ratio = protesting / total
            assert protest_ratio < 0.3, (
                f"高治安下抗议率应较低，实际: {protest_ratio:.2%}"
            )


class TestGovernorDecisionCycle:
    """测试镇长决策周期。"""

    def test_fallback_decision_executes_per_season(self) -> None:
        """验证回退策略在每个季度执行。"""
        config = _make_governor_config()
        engine = CivilizationEngine(config=config, seed=42, enable_governors=True)

        # 运行一整个季度 (120 ticks)
        ticks_per_season = (
            config.clock.ticks_per_day * config.clock.days_per_season
        )
        for _ in range(ticks_per_season):
            engine.step()

        governors = _get_governors(engine)
        assert len(governors) > 0
        for gov in governors:
            assert gov.decision_count >= 1, (
                f"镇长 {gov.unique_id} 应至少做出 1 次决策，"
                f"实际: {gov.decision_count}"
            )

    def test_governor_records_memory(self) -> None:
        """验证镇长决策后记录记忆。"""
        config = _make_governor_config()
        engine = CivilizationEngine(config=config, seed=42, enable_governors=True)

        ticks_per_season = (
            config.clock.ticks_per_day * config.clock.days_per_season
        )
        for _ in range(ticks_per_season):
            engine.step()

        governors = _get_governors(engine)
        for gov in governors:
            if gov.decision_count > 0:
                assert gov.memory.short_term_count > 0


class TestGovernorWithRealLLM:
    """测试使用真实 LLM 的镇长决策对系统的影响。"""

    @pytest.fixture()
    def llm_engine(self) -> CivilizationEngine | None:
        """创建使用真实 LLM 的引擎。"""
        try:
            real_config = load_config()
        except FileNotFoundError:
            pytest.skip("找不到 config.yaml")
            return None

        config = _make_governor_config()
        engine = CivilizationEngine(config=config, seed=42, enable_governors=True)

        # 用真实配置覆盖 LLM 网关
        gw = LLMGateway(max_retries=1, timeout=60)
        llm_cfg = real_config.llm
        for role in llm_cfg.models:
            model_cfg = llm_cfg.get_model_config(role)
            gw.register_model(role, model_cfg)
        engine.llm_gateway = gw

        # 更新镇长的网关引用
        for gov in _get_governors(engine):
            gov._gateway = gw

        return engine

    def test_real_llm_full_season(self, llm_engine: CivilizationEngine) -> None:
        """验证使用真实 LLM 运行一个季度无异常。"""
        if llm_engine is None:
            pytest.skip("LLM 引擎不可用")

        ticks_per_season = (
            llm_engine.config.clock.ticks_per_day
            * llm_engine.config.clock.days_per_season
        )
        for _ in range(ticks_per_season):
            llm_engine.step()

        governors = _get_governors(llm_engine)
        for gov in governors:
            assert gov.decision_count >= 1
            assert gov.last_decision is not None
            assert "tax_rate_change" in gov.last_decision

        # 验证 LLM 调用统计
        if llm_engine.llm_gateway:
            stats = llm_engine.llm_gateway.stats
            assert stats.total_calls >= 1
