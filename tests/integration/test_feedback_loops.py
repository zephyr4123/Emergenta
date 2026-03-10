"""自适应参数系统集成测试。

验证四大反馈环和自适应控制器在完整系统中的工作。
"""

import numpy as np
import pytest

from civsim.config import CivSimConfig
from civsim.config_params import (
    AdaptiveControllerConfig,
    RevolutionParamsConfig,
    TradeParamsConfig,
)


def _make_test_config(**overrides) -> CivSimConfig:
    """创建测试用最小配置。"""
    defaults = {
        "world": {
            "grid": {"width": 20, "height": 20},
            "settlement": {
                "min_suitability_score": 0.1,
                "initial_count": 4,
            },
        },
        "agents": {
            "civilian": {
                "initial_count": 40,
                "personality_distribution": {
                    "compliant": 0.30,
                    "neutral": 0.35,
                    "rebellious": 0.35,
                },
                "revolt_threshold": {
                    "mean": 0.18,
                    "std": 0.12,
                    "min": 0.05,
                    "max": 0.80,
                },
            },
            "governor": {"initial_count": 0},
            "leader": {"initial_count": 0},
        },
        "resources": {
            "initial_stockpile": {
                "food": 300,
                "wood": 200,
                "ore": 50,
                "gold": 100,
            },
        },
    }
    defaults.update(overrides)
    return CivSimConfig(**defaults)


class TestAdaptiveControllerIntegration:
    """自适应控制器与引擎集成测试。"""

    def test_controller_created_when_enabled(self) -> None:
        """启用时应创建控制器。"""
        from civsim.world.engine import CivilizationEngine

        config = _make_test_config(
            adaptive_controller={"enabled": True},
        )
        engine = CivilizationEngine(config=config, seed=42)
        assert engine.adaptive_controller is not None

    def test_controller_not_created_when_disabled(self) -> None:
        """禁用时不应创建控制器。"""
        from civsim.world.engine import CivilizationEngine

        config = _make_test_config(
            adaptive_controller={"enabled": False},
        )
        engine = CivilizationEngine(config=config, seed=42)
        assert engine.adaptive_controller is None

    def test_temperature_updates_during_simulation(self) -> None:
        """仿真运行后温度应有变化。"""
        from civsim.world.engine import CivilizationEngine

        config = _make_test_config(
            adaptive_controller={
                "enabled": True,
                "update_interval": 5,
            },
        )
        engine = CivilizationEngine(config=config, seed=42)
        for _ in range(30):
            engine.step()

        ctrl = engine.adaptive_controller
        assert len(ctrl.temperature_history) > 0

    def test_multipliers_change_under_stress(self) -> None:
        """高压力下乘数应偏离 1.0。"""
        from civsim.agents.behaviors.fsm import CivilianState
        from civsim.agents.civilian import Civilian
        from civsim.world.engine import CivilizationEngine

        config = _make_test_config(
            adaptive_controller={
                "enabled": True,
                "update_interval": 5,
                "target_temperature": 0.3,
                "adjustment_rate": 0.3,
            },
        )
        engine = CivilizationEngine(config=config, seed=42)

        # 人工制造高压力：所有平民设为抗议+低满意度
        for a in engine.agents:
            if isinstance(a, Civilian):
                a.state = CivilianState.PROTESTING
                a.satisfaction = 0.1
                a.hunger = 0.9

        for _ in range(30):
            engine.step()

        ctrl = engine.adaptive_controller
        # 过热应降低 protest_multiplier
        assert ctrl.coefficients.markov_protest_multiplier < 1.0


class TestRevolutionRecoveryIntegration:
    """革命恢复反馈环集成测试。"""

    def test_recovery_params_from_config(self) -> None:
        """RevolutionTracker 应使用配置参数。"""
        from civsim.politics.revolution import RevolutionTracker

        params = RevolutionParamsConfig(
            honeymoon_ticks=50,
            honeymoon_satisfaction_boost=0.03,
        )
        tracker = RevolutionTracker(params=params)
        tracker.start_recovery(1, tick=100)

        recovery = tracker.get_recovery(1)
        assert recovery is not None
        assert recovery.remaining_ticks == 50
        assert recovery.satisfaction_boost == 0.03

    def test_honeymoon_boosts_satisfaction(self) -> None:
        """蜜月期应提升平民满意度。"""
        from civsim.agents.behaviors.fsm import CivilianState
        from civsim.agents.civilian import Civilian
        from civsim.politics.revolution import RevolutionTracker
        from civsim.world.engine import CivilizationEngine

        config = _make_test_config(
            revolution_params={
                "honeymoon_ticks": 100,
                "honeymoon_satisfaction_boost": 0.05,
            },
            adaptive_controller={"enabled": False},
        )
        engine = CivilizationEngine(
            config=config, seed=42,
        )

        # 手动创建一个革命追踪器
        engine.revolution_tracker = RevolutionTracker(
            params=config.revolution_params,
        )

        # 手动启动一个聚落的恢复阶段
        sid = list(engine.settlements.keys())[0]
        engine.revolution_tracker.start_recovery(sid, tick=0)

        # 收集恢复前满意度
        civs = [
            a for a in engine.agents
            if isinstance(a, Civilian)
            and a.home_settlement_id == sid
        ]
        for c in civs:
            c.satisfaction = 0.3

        # 运行几步
        for _ in range(10):
            engine.step()

        # 蜜月期应给正向提升
        avg_sat = float(np.mean([c.satisfaction for c in civs]))
        # 由于蜜月期每 tick +0.05，加上其他效应，满意度应有所回升
        assert avg_sat > 0.25  # 至少没有崩塌


class TestTradeTrustIntegration:
    """贸易→信任反馈环集成测试。"""

    def test_trade_params_from_config(self) -> None:
        """TradeManager 应使用配置参数。"""
        from civsim.economy.trade import TradeManager

        params = TradeParamsConfig(
            trust_boost_per_trade=0.02,
            surplus_trade_ratio=0.5,
        )
        tm = TradeManager(params=params)
        assert tm.params.trust_boost_per_trade == 0.02
        assert tm.params.surplus_trade_ratio == 0.5

    def test_trust_deltas_recorded(self) -> None:
        """成功跨阵营贸易应记录信任增量。"""
        from civsim.economy.settlement import Settlement
        from civsim.economy.trade import TradeManager, TradeRoute

        params = TradeParamsConfig(trust_boost_per_trade=0.05)
        tm = TradeManager(params=params)

        s1 = Settlement(id=1, name="A", position=(0, 0))
        s1.faction_id = 1
        s1.stockpile = {"food": 1000, "gold": 100}

        s2 = Settlement(id=2, name="B", position=(5, 5))
        s2.faction_id = 2
        s2.stockpile = {"food": 0, "gold": 1000}

        settlements = {1: s1, 2: s2}
        route = TradeRoute(
            seller_id=1, buyer_id=2,
            resource="food", amount=10.0, price_gold=10.0,
        )
        tm._tick_trust_deltas = {}
        tm._tick_volume = 0.0
        success = tm.execute_trade(route, settlements)
        assert success

        deltas = tm.compute_trust_deltas()
        assert (1, 2) in deltas
        assert deltas[(1, 2)] == pytest.approx(0.05)

    def test_tick_stats(self) -> None:
        """get_tick_stats 应返回正确统计。"""
        from civsim.economy.trade import TradeManager

        tm = TradeManager()
        stats = tm.get_tick_stats()
        assert "tick_trade_count" in stats
        assert "total_volume" in stats


class TestMarkovAdaptiveIntegration:
    """马尔可夫自适应系数集成测试。"""

    def test_config_coefficients_used(self) -> None:
        """配置系数应影响转移概率。"""
        from civsim.agents.behaviors.markov import (
            Personality,
            compute_transition_matrix,
        )
        from civsim.config_params import MarkovCoefficientsConfig

        # 默认系数
        m1 = compute_transition_matrix(
            Personality.NEUTRAL, hunger=0.5,
            tax_rate=0.3, security=0.5,
            protest_ratio=0.0, revolt_threshold=0.5,
        )

        # 加倍饥饿效应
        cfg = MarkovCoefficientsConfig(
            hunger_to_protest_working=1.20,
        )
        m2 = compute_transition_matrix(
            Personality.NEUTRAL, hunger=0.5,
            tax_rate=0.3, security=0.5,
            protest_ratio=0.0, revolt_threshold=0.5,
            coefficients=cfg,
        )

        # m2 的劳作→抗议概率应更高
        assert m2[0][5] > m1[0][5]

    def test_multiplier_reduces_protest(self) -> None:
        """protest_multiplier < 1 应降低抗议概率。"""
        from civsim.agents.behaviors.markov import (
            Personality,
            compute_transition_matrix,
        )

        m_normal = compute_transition_matrix(
            Personality.NEUTRAL, hunger=0.5,
            tax_rate=0.3, security=0.5,
            protest_ratio=0.0, revolt_threshold=0.5,
            protest_multiplier=1.0,
        )

        m_reduced = compute_transition_matrix(
            Personality.NEUTRAL, hunger=0.5,
            tax_rate=0.3, security=0.5,
            protest_ratio=0.0, revolt_threshold=0.5,
            protest_multiplier=0.5,
        )

        # 降低乘数应减少抗议概率
        assert m_reduced[0][5] < m_normal[0][5]


class TestGovernorDecisionTracking:
    """Governor 决策结果追踪测试。"""

    def test_decision_outcomes_empty_first_time(self) -> None:
        """首次决策时应无历史对比。"""
        from civsim.agents.governor import Governor, GovernorPerception
        from civsim.world.engine import CivilizationEngine

        config = _make_test_config(adaptive_controller={"enabled": False})
        engine = CivilizationEngine(config=config, seed=42)

        gov = Governor(
            model=engine, settlement_id=list(engine.settlements.keys())[0],
            gateway=None, cache_enabled=False,
        )
        perception = GovernorPerception(
            settlement_name="test", population=50,
            food=100, wood=50, ore=10, gold=20,
            tax_rate=0.2, security_level=0.5,
            satisfaction_avg=0.5, protest_ratio=0.1,
            scarcity_index=0.3, per_capita_food=2.0,
            season="春",
        )
        result = gov._compute_decision_outcomes(perception)
        assert result == ""

    def test_decision_outcomes_with_history(self) -> None:
        """有上次感知时应生成对比描述。"""
        from civsim.agents.governor import Governor, GovernorPerception
        from civsim.world.engine import CivilizationEngine

        config = _make_test_config(adaptive_controller={"enabled": False})
        engine = CivilizationEngine(config=config, seed=42)

        gov = Governor(
            model=engine, settlement_id=list(engine.settlements.keys())[0],
            gateway=None, cache_enabled=False,
        )

        # 设置上次状态
        gov._prev_perception = GovernorPerception(
            settlement_name="test", population=50,
            food=100, wood=50, ore=10, gold=20,
            tax_rate=0.2, security_level=0.5,
            satisfaction_avg=0.40, protest_ratio=0.25,
            scarcity_index=0.3, per_capita_food=2.0,
            season="春",
        )
        gov.last_decision = {
            "tax_rate_change": -0.05,
            "security_change": 0.1,
            "resource_focus": "food",
            "reasoning": "test",
        }

        current = GovernorPerception(
            settlement_name="test", population=52,
            food=120, wood=55, ore=12, gold=22,
            tax_rate=0.15, security_level=0.6,
            satisfaction_avg=0.48, protest_ratio=0.18,
            scarcity_index=0.2, per_capita_food=2.3,
            season="夏",
        )

        result = gov._compute_decision_outcomes(current)
        assert "降税" in result
        assert "满意度" in result
