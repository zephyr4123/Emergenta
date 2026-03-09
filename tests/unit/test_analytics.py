"""analytics.py 单元测试。

验证涌现行为检测器的各类检测逻辑。
"""

from civsim.data.analytics import EmergenceDetector, EmergenceEvent
from civsim.politics.revolution import RevolutionEvent


class TestEmergenceEvent:
    """测试涌现事件数据类。"""

    def test_create_event(self) -> None:
        """验证涌现事件创建。"""
        ev = EmergenceEvent(
            tick=100, event_type="revolution",
            description="聚落 0 发生革命",
        )
        assert ev.tick == 100
        assert ev.event_type == "revolution"
        assert ev.involved_factions == []
        assert ev.metadata == {}


class TestEmergenceDetectorRevolution:
    """测试革命涌现检测。"""

    def test_no_events_returns_empty(self) -> None:
        """验证无革命事件返回空。"""
        ed = EmergenceDetector()
        result = ed.detect_all(tick=0, revolution_events=[])
        assert len(result) == 0

    def test_detects_revolution(self) -> None:
        """验证检测到革命事件。"""
        ed = EmergenceDetector()
        rev = RevolutionEvent(
            settlement_id=0, trigger_tick=100, old_faction_id=1,
        )
        result = ed.detect_all(tick=100, revolution_events=[rev])
        rev_events = [e for e in result if e.event_type == "revolution"]
        assert len(rev_events) == 1
        assert rev_events[0].metadata["settlement_id"] == 0


class TestEmergenceDetectorAlliance:
    """测试联盟涌现检测。"""

    def test_detects_new_alliance(self) -> None:
        """验证检测到新联盟。"""
        ed = EmergenceDetector()

        class MockDiplomacy:
            _relations = {(1, 2): 4}  # ALLIED

        result = ed.detect_all(tick=10, diplomacy_manager=MockDiplomacy())
        alliance_events = [
            e for e in result if e.event_type == "alliance_formation"
        ]
        assert len(alliance_events) == 1

    def test_no_detection_if_count_unchanged(self) -> None:
        """验证联盟数不变时不检测。"""
        ed = EmergenceDetector()

        class MockDiplomacy:
            _relations = {(1, 2): 4}

        ed.detect_all(tick=10, diplomacy_manager=MockDiplomacy())
        # 再次调用，数量未变
        result = ed.detect_all(tick=20, diplomacy_manager=MockDiplomacy())
        alliance_events = [
            e for e in result if e.event_type == "alliance_formation"
        ]
        assert len(alliance_events) == 0


class TestEmergenceDetectorTradeNetwork:
    """测试贸易网络涌现检测。"""

    def test_detects_trade_surge(self) -> None:
        """验证检测到贸易量激增。"""
        ed = EmergenceDetector()

        class MockTrade1:
            total_volume = 10.0

        ed.detect_all(tick=1, trade_manager=MockTrade1())
        ed._prev_trade_volume = 10.0  # 确保基线

        class MockTrade2:
            total_volume = 70.0

        result = ed.detect_all(tick=2, trade_manager=MockTrade2())
        trade_events = [
            e for e in result if e.event_type == "trade_network"
        ]
        assert len(trade_events) == 1

    def test_no_detection_small_growth(self) -> None:
        """验证小幅增长不触发。"""
        ed = EmergenceDetector()
        ed._prev_trade_volume = 10.0

        class MockTrade:
            total_volume = 30.0

        result = ed.detect_all(tick=1, trade_manager=MockTrade())
        trade_events = [
            e for e in result if e.event_type == "trade_network"
        ]
        assert len(trade_events) == 0


class TestEmergenceDetectorWarCascade:
    """测试战争级联检测。"""

    def test_detects_war_cascade(self) -> None:
        """验证检测到多场战争。"""
        ed = EmergenceDetector()

        class MockDiplomacy:
            _relations = {(1, 2): 0, (1, 3): 0}  # 两场战争

        result = ed.detect_all(tick=10, diplomacy_manager=MockDiplomacy())
        war_events = [
            e for e in result if e.event_type == "war_cascade"
        ]
        assert len(war_events) == 1

    def test_no_cascade_single_war(self) -> None:
        """验证单场战争不触发级联。"""
        ed = EmergenceDetector()

        class MockDiplomacy:
            _relations = {(1, 2): 0}  # 一场战争

        result = ed.detect_all(tick=10, diplomacy_manager=MockDiplomacy())
        war_events = [
            e for e in result if e.event_type == "war_cascade"
        ]
        assert len(war_events) == 0


class TestEmergenceDetectorSummary:
    """测试汇总功能。"""

    def test_summary_counts(self) -> None:
        """验证事件统计汇总。"""
        ed = EmergenceDetector()
        rev = RevolutionEvent(settlement_id=0, trigger_tick=100)
        ed.detect_all(tick=100, revolution_events=[rev])
        summary = ed.get_summary()
        assert summary.get("revolution", 0) == 1

    def test_has_emergence(self) -> None:
        """验证涌现检测标志。"""
        ed = EmergenceDetector()
        assert ed.has_emergence is False
        rev = RevolutionEvent(settlement_id=0, trigger_tick=100)
        ed.detect_all(tick=100, revolution_events=[rev])
        assert ed.has_emergence is True
