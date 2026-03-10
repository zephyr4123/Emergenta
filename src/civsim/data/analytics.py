"""涌现行为检测分析。

检测革命、联盟形成、贸易网络涌现和战争级联等涌现行为。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class EmergenceEvent:
    """涌现事件记录。

    Attributes:
        tick: 检测到的 tick。
        event_type: 涌现类型。
        description: 事件描述。
        involved_factions: 涉及阵营列表。
        metadata: 附加数据。
    """

    tick: int
    event_type: str
    description: str
    involved_factions: list[int] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class EmergenceDetector:
    """涌现行为检测器。

    追踪宏观系统变化，检测涌现行为。
    """

    def __init__(self) -> None:
        self.events: list[EmergenceEvent] = []
        self._prev_alliance_count = 0
        self._prev_trade_volume = 0.0
        self._prev_war_count = 0
        self._prev_revolution_count = 0

    def detect_all(
        self,
        tick: int,
        revolution_events: list | None = None,
        diplomacy_manager: object | None = None,
        trade_manager: object | None = None,
    ) -> list[EmergenceEvent]:
        """运行所有检测器。

        Args:
            tick: 当前 tick。
            revolution_events: 革命事件列表。
            diplomacy_manager: 外交管理器。
            trade_manager: 贸易管理器。

        Returns:
            本次检测到的涌现事件列表。
        """
        detected: list[EmergenceEvent] = []
        detected.extend(self._detect_revolution(tick, revolution_events))
        detected.extend(self._detect_alliance(tick, diplomacy_manager))
        detected.extend(self._detect_trade_network(tick, trade_manager))
        detected.extend(self._detect_war_cascade(tick, diplomacy_manager))
        self.events.extend(detected)
        return detected

    def _detect_revolution(
        self, tick: int, revolution_events: list | None,
    ) -> list[EmergenceEvent]:
        """检测革命涌现（仅处理新增的革命事件）。"""
        if not revolution_events:
            return []
        # 只处理自上次检测以来新增的革命事件
        new_events = revolution_events[self._prev_revolution_count:]
        self._prev_revolution_count = len(revolution_events)
        results = []
        for rev in new_events:
            sid = getattr(rev, "settlement_id", -1)
            results.append(EmergenceEvent(
                tick=tick,
                event_type="revolution",
                description=f"聚落 {sid} 发生革命",
                involved_factions=[
                    getattr(rev, "old_faction_id", -1) or -1,
                ],
                metadata={"settlement_id": sid},
            ))
        return results

    def _detect_alliance(
        self, tick: int, diplomacy_manager: object | None,
    ) -> list[EmergenceEvent]:
        """检测联盟形成涌现。"""
        if diplomacy_manager is None:
            return []

        results = []
        relations = getattr(diplomacy_manager, "_relations", {})
        current_count = sum(
            1 for s in relations.values() if int(s) >= 4  # ALLIED
        )
        if current_count > self._prev_alliance_count:
            new_alliances = current_count - self._prev_alliance_count
            results.append(EmergenceEvent(
                tick=tick,
                event_type="alliance_formation",
                description=f"新增 {new_alliances} 个联盟关系",
                metadata={"alliance_count": current_count},
            ))
        self._prev_alliance_count = current_count
        return results

    def _detect_trade_network(
        self, tick: int, trade_manager: object | None,
    ) -> list[EmergenceEvent]:
        """检测贸易网络涌现（交易量显著增长）。"""
        if trade_manager is None:
            return []

        results = []
        current_volume = getattr(trade_manager, "total_volume", 0.0)
        growth = current_volume - self._prev_trade_volume

        if growth > 50.0 and self._prev_trade_volume > 0:
            results.append(EmergenceEvent(
                tick=tick,
                event_type="trade_network",
                description=f"贸易网络涌现：交易量增长 {growth:.1f}",
                metadata={
                    "total_volume": current_volume,
                    "growth": growth,
                },
            ))
        self._prev_trade_volume = current_volume
        return results

    def _detect_war_cascade(
        self, tick: int, diplomacy_manager: object | None,
    ) -> list[EmergenceEvent]:
        """检测战争级联（多阵营同时进入战争状态）。"""
        if diplomacy_manager is None:
            return []

        results = []
        relations = getattr(diplomacy_manager, "_relations", {})
        current_wars = sum(
            1 for s in relations.values() if int(s) == 0  # WAR
        )
        if current_wars > self._prev_war_count and current_wars >= 2:
            results.append(EmergenceEvent(
                tick=tick,
                event_type="war_cascade",
                description=f"战争级联：{current_wars} 场战争同时进行",
                metadata={"war_count": current_wars},
            ))
        self._prev_war_count = current_wars
        return results

    def get_summary(self) -> dict[str, int]:
        """返回涌现事件统计摘要。"""
        summary: dict[str, int] = {}
        for event in self.events:
            summary[event.event_type] = summary.get(event.event_type, 0) + 1
        return summary

    @property
    def has_emergence(self) -> bool:
        """是否检测到任何涌现事件。"""
        return len(self.events) > 0
