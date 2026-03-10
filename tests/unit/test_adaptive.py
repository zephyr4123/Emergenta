"""自适应参数控制器单元测试。"""

import pytest

from civsim.config_params import AdaptiveControllerConfig
from civsim.world.adaptive import (
    AdaptiveCoefficients,
    AdaptiveParameterController,
    SystemMetrics,
    _clamp,
)


class TestClamp:
    """_clamp 辅助函数测试。"""

    def test_within_range(self) -> None:
        assert _clamp(0.5, 0.0, 1.0) == 0.5

    def test_below_min(self) -> None:
        assert _clamp(-0.1, 0.0, 1.0) == 0.0

    def test_above_max(self) -> None:
        assert _clamp(1.5, 0.0, 1.0) == 1.0


class TestSystemMetrics:
    """SystemMetrics 数据类测试。"""

    def test_defaults(self) -> None:
        m = SystemMetrics()
        assert m.tick == 0
        assert m.global_protest_ratio == 0.0
        assert m.avg_satisfaction == 0.5
        assert m.revolution_count == 0

    def test_custom_values(self) -> None:
        m = SystemMetrics(
            tick=100, global_protest_ratio=0.3,
            avg_satisfaction=0.4, revolutions_recent=5,
        )
        assert m.tick == 100
        assert m.global_protest_ratio == 0.3
        assert m.revolutions_recent == 5


class TestAdaptiveCoefficients:
    """AdaptiveCoefficients 默认值测试。"""

    def test_defaults_are_unity(self) -> None:
        c = AdaptiveCoefficients()
        assert c.markov_protest_multiplier == 1.0
        assert c.granovetter_burst_multiplier == 1.0
        assert c.revolution_cooldown_multiplier == 1.0
        assert c.satisfaction_recovery_multiplier == 1.0
        assert c.random_event_multiplier == 1.0


class TestAdaptiveParameterController:
    """AdaptiveParameterController 核心逻辑测试。"""

    def test_should_update_respects_interval(self) -> None:
        ctrl = AdaptiveParameterController(
            AdaptiveControllerConfig(update_interval=10),
        )
        assert not ctrl.should_update(0)  # tick 0 不更新
        assert ctrl.should_update(10)
        ctrl._last_update_tick = 10
        assert not ctrl.should_update(15)
        assert ctrl.should_update(20)

    def test_should_update_disabled(self) -> None:
        ctrl = AdaptiveParameterController(
            AdaptiveControllerConfig(enabled=False),
        )
        assert not ctrl.should_update(100)

    def test_temperature_calm_system(self) -> None:
        """平静系统（低抗议、高满意度）→ 低温度。"""
        ctrl = AdaptiveParameterController()
        metrics = SystemMetrics(
            tick=10,
            global_protest_ratio=0.02,
            avg_satisfaction=0.8,
            revolutions_recent=0,
            active_wars=0,
            collapsed_settlements=0,
            total_settlements=8,
        )
        temp = ctrl.compute_temperature(metrics)
        assert temp < 0.15

    def test_temperature_hot_system(self) -> None:
        """过热系统（高抗议、低满意度、多革命）→ 高温度。"""
        ctrl = AdaptiveParameterController()
        metrics = SystemMetrics(
            tick=100,
            global_protest_ratio=0.6,
            avg_satisfaction=0.2,
            revolutions_recent=8,
            active_wars=2,
            collapsed_settlements=3,
            total_settlements=8,
        )
        temp = ctrl.compute_temperature(metrics)
        assert temp > 0.5

    def test_update_overheated_reduces_protest_mult(self) -> None:
        """过热时更新应降低抗议乘数。"""
        ctrl = AdaptiveParameterController(
            AdaptiveControllerConfig(target_temperature=0.3),
        )
        initial_protest = ctrl.coefficients.markov_protest_multiplier
        hot_metrics = SystemMetrics(
            tick=10,
            global_protest_ratio=0.5,
            avg_satisfaction=0.2,
            revolutions_recent=10,
            active_wars=2,
            total_settlements=8,
        )
        ctrl.update(hot_metrics)
        assert ctrl.coefficients.markov_protest_multiplier < initial_protest

    def test_update_overheated_increases_recovery_mult(self) -> None:
        """过热时更新应提高满意度恢复乘数。"""
        ctrl = AdaptiveParameterController(
            AdaptiveControllerConfig(target_temperature=0.3),
        )
        initial_recovery = ctrl.coefficients.satisfaction_recovery_multiplier
        hot_metrics = SystemMetrics(
            tick=10,
            global_protest_ratio=0.5,
            avg_satisfaction=0.2,
            revolutions_recent=10,
            total_settlements=8,
        )
        ctrl.update(hot_metrics)
        assert (
            ctrl.coefficients.satisfaction_recovery_multiplier
            > initial_recovery
        )

    def test_update_cold_increases_protest_mult(self) -> None:
        """过冷时更新应提高抗议乘数。"""
        ctrl = AdaptiveParameterController(
            AdaptiveControllerConfig(target_temperature=0.3),
        )
        initial_protest = ctrl.coefficients.markov_protest_multiplier
        cold_metrics = SystemMetrics(
            tick=10,
            global_protest_ratio=0.0,
            avg_satisfaction=0.9,
            revolutions_recent=0,
            active_wars=0,
            total_settlements=8,
        )
        ctrl.update(cold_metrics)
        assert ctrl.coefficients.markov_protest_multiplier > initial_protest

    def test_multipliers_stay_within_bounds(self) -> None:
        """多次极端更新后乘数应在合法范围内。"""
        ctrl = AdaptiveParameterController(
            AdaptiveControllerConfig(
                min_multiplier=0.3,
                max_multiplier=2.0,
                adjustment_rate=0.5,
            ),
        )
        extreme_hot = SystemMetrics(
            tick=0,
            global_protest_ratio=1.0,
            avg_satisfaction=0.0,
            revolutions_recent=20,
            active_wars=4,
            collapsed_settlements=8,
            total_settlements=8,
        )
        for i in range(50):
            extreme_hot.tick = (i + 1) * 10
            ctrl._last_update_tick = extreme_hot.tick - 10
            ctrl.update(extreme_hot)

        c = ctrl.coefficients
        assert c.markov_protest_multiplier >= 0.3
        assert c.markov_protest_multiplier <= 2.0
        assert c.granovetter_burst_multiplier >= 0.3
        assert c.satisfaction_recovery_multiplier <= 2.0

    def test_temperature_history_capped(self) -> None:
        """温度历史应限制在 100 条内。"""
        ctrl = AdaptiveParameterController()
        m = SystemMetrics(tick=0, total_settlements=1)
        for i in range(150):
            m.tick = i * 10
            ctrl._last_update_tick = m.tick - 10
            ctrl.update(m)

        assert len(ctrl.temperature_history) <= 100

    def test_get_global_context(self) -> None:
        """get_global_context 应返回预期字段。"""
        ctrl = AdaptiveParameterController()
        m = SystemMetrics(tick=10, total_settlements=1)
        ctrl.update(m)

        ctx = ctrl.get_global_context()
        assert "system_temperature" in ctx
        assert "avg_temperature_recent" in ctx
        assert "protest_multiplier" in ctx
        assert "recovery_multiplier" in ctx
        assert "target_temperature" in ctx

    def test_at_target_no_large_change(self) -> None:
        """温度接近目标时乘数变化应较小。"""
        ctrl = AdaptiveParameterController(
            AdaptiveControllerConfig(target_temperature=0.3),
        )
        # 构造温度 ≈ 0.3 的 metrics
        m = SystemMetrics(
            tick=10,
            global_protest_ratio=0.15,
            avg_satisfaction=0.5,
            revolutions_recent=2,
            total_settlements=8,
        )
        ctrl.update(m)
        c = ctrl.coefficients
        # 变化应很小（在 0.9~1.1 范围内）
        assert 0.85 <= c.markov_protest_multiplier <= 1.15

    def test_default_config(self) -> None:
        """不传 config 时使用默认配置。"""
        ctrl = AdaptiveParameterController()
        assert ctrl.config.enabled is True
        assert ctrl.config.target_temperature == 0.30
