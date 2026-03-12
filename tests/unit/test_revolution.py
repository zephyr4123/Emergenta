"""revolution.py 单元测试。

验证革命追踪器的抗议持续跟踪、触发条件、革命后果应用。
"""

import pytest

from civsim.economy.settlement import Settlement
from civsim.politics.revolution import (
    REVOLUTION_DURATION_TICKS,
    REVOLUTION_PROTEST_THRESHOLD,
    REVOLUTION_SATISFACTION_THRESHOLD,
    RevolutionEvent,
    RevolutionTracker,
)


class TestRevolutionTrackerUpdate:
    """测试革命状态更新。"""

    def test_no_revolution_when_below_thresholds(self) -> None:
        """验证低抗议率/高满意度不触发革命。"""
        rt = RevolutionTracker()
        result = rt.update(0, protest_ratio=0.1, avg_satisfaction=0.6)
        assert result is False
        assert rt.get_protest_duration(0) == 0

    def test_protest_duration_increments(self) -> None:
        """验证满足条件时抗议持续递增。"""
        rt = RevolutionTracker()
        rt.update(0, protest_ratio=0.5, avg_satisfaction=0.2)
        assert rt.get_protest_duration(0) == 1
        rt.update(0, protest_ratio=0.5, avg_satisfaction=0.2)
        assert rt.get_protest_duration(0) == 2

    def test_protest_duration_decreases_when_calm(self) -> None:
        """验证条件不满足时抗议持续加速衰减（每次减 2）。"""
        rt = RevolutionTracker()
        # 累积 5 tick
        for _ in range(5):
            rt.update(0, protest_ratio=0.5, avg_satisfaction=0.2)
        assert rt.get_protest_duration(0) == 5

        # 平息后每次减 2（加速衰减，避免无限逼近触发）
        rt.update(0, protest_ratio=0.1, avg_satisfaction=0.6)
        assert rt.get_protest_duration(0) == 3

    def test_protest_duration_does_not_go_negative(self) -> None:
        """验证递减不会变负数。"""
        rt = RevolutionTracker()
        rt.update(0, protest_ratio=0.1, avg_satisfaction=0.6)
        assert rt.get_protest_duration(0) == 0

    def test_revolution_triggers_after_duration(self) -> None:
        """验证持续满足条件后触发革命。"""
        rt = RevolutionTracker()
        for i in range(REVOLUTION_DURATION_TICKS):
            result = rt.update(0, protest_ratio=0.5, avg_satisfaction=0.2)
            if i < REVOLUTION_DURATION_TICKS - 1:
                assert result is False
        assert result is True

    def test_only_high_protest_not_enough(self) -> None:
        """验证仅高抗议率但满意度不低不触发。"""
        rt = RevolutionTracker()
        result = rt.update(
            0, protest_ratio=0.5,
            avg_satisfaction=0.5,  # 高于阈值
        )
        assert result is False
        assert rt.get_protest_duration(0) == 0

    def test_only_low_satisfaction_not_enough(self) -> None:
        """验证仅低满意度但抗议率不高不触发。"""
        rt = RevolutionTracker()
        result = rt.update(
            0, protest_ratio=0.2,  # 低于阈值
            avg_satisfaction=0.1,
        )
        assert result is False

    def test_multiple_settlements_independent(self) -> None:
        """验证不同聚落独立跟踪。"""
        rt = RevolutionTracker()
        rt.update(0, protest_ratio=0.5, avg_satisfaction=0.2)
        rt.update(1, protest_ratio=0.1, avg_satisfaction=0.6)
        assert rt.get_protest_duration(0) == 1
        assert rt.get_protest_duration(1) == 0


class TestRevolutionTrigger:
    """测试革命触发和记录。"""

    def test_trigger_creates_event(self) -> None:
        """验证触发创建革命事件。"""
        rt = RevolutionTracker()
        ev = rt.trigger_revolution(
            settlement_id=0, tick=100,
            old_faction_id=1, old_governor_id=42,
        )
        assert isinstance(ev, RevolutionEvent)
        assert ev.settlement_id == 0
        assert ev.trigger_tick == 100
        assert ev.old_faction_id == 1

    def test_trigger_resets_counter(self) -> None:
        """验证触发后重置计数器。"""
        rt = RevolutionTracker()
        for _ in range(5):
            rt.update(0, protest_ratio=0.5, avg_satisfaction=0.2)
        assert rt.get_protest_duration(0) == 5

        rt.trigger_revolution(0, tick=100)
        assert rt.get_protest_duration(0) == 0

    def test_revolution_count(self) -> None:
        """验证革命计数。"""
        rt = RevolutionTracker()
        assert rt.revolution_count == 0
        rt.trigger_revolution(0, tick=100)
        rt.trigger_revolution(1, tick=200)
        assert rt.revolution_count == 2

    def test_events_property(self) -> None:
        """验证事件列表属性。"""
        rt = RevolutionTracker()
        rt.trigger_revolution(0, tick=100)
        events = rt.events
        assert len(events) == 1
        # 验证返回的是副本
        events.clear()
        assert rt.revolution_count == 1


class TestRevolutionApply:
    """测试革命后果应用。"""

    def test_apply_reduces_gold_and_food(self) -> None:
        """验证革命减少金币和食物。"""
        rt = RevolutionTracker()
        s = Settlement(
            id=0, name="test", position=(0, 0),
            stockpile={"food": 100.0, "wood": 50.0, "ore": 20.0, "gold": 80.0},
        )
        ev = RevolutionEvent(settlement_id=0, trigger_tick=100)
        rt.apply_revolution(ev, s)
        assert s.stockpile["gold"] == pytest.approx(40.0)
        assert s.stockpile["food"] == pytest.approx(80.0)

    def test_apply_resets_governance(self) -> None:
        """验证革命重置治理参数。"""
        rt = RevolutionTracker()
        s = Settlement(
            id=0, name="test", position=(0, 0),
            tax_rate=0.5, security_level=0.8,
        )
        s.governor_id = 42
        s.faction_id = 1
        ev = RevolutionEvent(settlement_id=0, trigger_tick=100)
        rt.apply_revolution(ev, s)
        assert s.tax_rate == 0.15
        assert s.security_level == pytest.approx(0.4)
        assert s.governor_id is None
        assert s.faction_id is None
