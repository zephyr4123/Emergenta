"""革命恢复机制单元测试。"""

import pytest

from civsim.config_params import RevolutionParamsConfig
from civsim.politics.revolution import (
    RecoveryPhase,
    RevolutionEvent,
    RevolutionTracker,
)


class TestRecoveryPhase:
    """RecoveryPhase 数据类测试。"""

    def test_creation(self) -> None:
        phase = RecoveryPhase(
            settlement_id=1,
            remaining_ticks=40,
            satisfaction_boost=0.02,
            vigilance_reduction=0.05,
            trigger_tick=100,
        )
        assert phase.settlement_id == 1
        assert phase.remaining_ticks == 40
        assert phase.satisfaction_boost == 0.02


class TestRevolutionTrackerRecovery:
    """RevolutionTracker 恢复机制测试。"""

    def test_apply_revolution_starts_recovery(self) -> None:
        """apply_revolution 应自动启动恢复阶段。"""
        tracker = RevolutionTracker()
        event = RevolutionEvent(settlement_id=1, trigger_tick=100)

        class FakeSettlement:
            stockpile = {"gold": 100.0, "food": 200.0}
            security_level = 0.8
            tax_rate = 0.3
            faction_id = 1
            governor_id = 10

        s = FakeSettlement()
        tracker.apply_revolution(event, s)

        recovery = tracker.get_recovery(1)
        assert recovery is not None
        assert recovery.remaining_ticks == 40
        assert recovery.satisfaction_boost == 0.02

    def test_update_recovery_decrements(self) -> None:
        """update_recovery 每 tick 递减蜜月期。"""
        tracker = RevolutionTracker()
        tracker.start_recovery(1, tick=100)

        recovery = tracker.get_recovery(1)
        assert recovery.remaining_ticks == 40

        tracker.update_recovery()
        recovery = tracker.get_recovery(1)
        assert recovery.remaining_ticks == 39

    def test_update_recovery_finishes(self) -> None:
        """蜜月期结束后移除恢复阶段。"""
        params = RevolutionParamsConfig(honeymoon_ticks=3)
        tracker = RevolutionTracker(params=params)
        tracker.start_recovery(1, tick=100)

        # 递减 3 次
        tracker.update_recovery()
        tracker.update_recovery()
        finished = tracker.update_recovery()

        assert 1 in finished
        assert tracker.get_recovery(1) is None

    def test_no_recovery_returns_none(self) -> None:
        """无恢复阶段时返回 None。"""
        tracker = RevolutionTracker()
        assert tracker.get_recovery(99) is None

    def test_custom_params(self) -> None:
        """自定义参数应覆盖默认值。"""
        params = RevolutionParamsConfig(
            protest_threshold=0.5,
            duration_ticks=10,
            cooldown_ticks=50,
            honeymoon_ticks=60,
            honeymoon_satisfaction_boost=0.05,
        )
        tracker = RevolutionTracker(params=params)

        # 用自定义阈值测试
        assert not tracker.update(1, 0.45, 0.3)  # 低于自定义阈值

    def test_penalty_multiplier(self) -> None:
        """apply_revolution 应支持 penalty_multiplier。"""
        params = RevolutionParamsConfig(security_penalty=0.4)
        tracker = RevolutionTracker(params=params)
        event = RevolutionEvent(settlement_id=1, trigger_tick=100)

        class FakeSettlement:
            stockpile = {"gold": 100.0, "food": 200.0}
            security_level = 0.8
            tax_rate = 0.3
            faction_id = 1
            governor_id = 10

        s = FakeSettlement()
        tracker.apply_revolution(event, s, penalty_multiplier=0.5)
        # security_penalty * multiplier = 0.4 * 0.5 = 0.2
        assert abs(s.security_level - 0.6) < 0.01

    def test_backward_compat_no_params(self) -> None:
        """不传 params 时使用默认值，行为兼容 V2。"""
        tracker = RevolutionTracker()
        # 默认阈值 0.20
        for _ in range(8):
            tracker.update(1, 0.25, 0.3)
        assert tracker.get_protest_duration(1) >= 8

    def test_recent_revolution_count(self) -> None:
        """recent_revolution_count 应正确统计近期革命。"""
        tracker = RevolutionTracker()
        tracker.trigger_revolution(1, tick=50)
        tracker._cooldown[1] = 0
        tracker.trigger_revolution(2, tick=150)
        tracker._cooldown[2] = 0
        tracker.trigger_revolution(3, tick=300)

        assert tracker.recent_revolution_count(310, lookback=200) == 2
        assert tracker.recent_revolution_count(310, lookback=300) == 3

    def test_active_recoveries(self) -> None:
        """active_recoveries 应返回所有活跃恢复。"""
        tracker = RevolutionTracker()
        tracker.start_recovery(1, tick=100)
        tracker.start_recovery(2, tick=110)

        active = tracker.active_recoveries
        assert len(active) == 2
        assert 1 in active
        assert 2 in active
