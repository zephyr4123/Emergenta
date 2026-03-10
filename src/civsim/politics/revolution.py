"""革命/政权更替机制。

检测革命触发条件、执行政权更替和聚落状态重置。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 革命触发条件阈值
REVOLUTION_PROTEST_THRESHOLD = 0.30
REVOLUTION_SATISFACTION_THRESHOLD = 0.30
REVOLUTION_DURATION_TICKS = 15
REVOLUTION_COOLDOWN_TICKS = 60  # 革命后冷却期


@dataclass
class RevolutionEvent:
    """革命事件记录。

    Attributes:
        settlement_id: 发生革命的聚落 ID。
        trigger_tick: 触发 tick。
        old_faction_id: 旧阵营 ID。
        new_faction_id: 新阵营 ID。
        old_governor_id: 旧镇长 ID。
        cause: 革命原因摘要。
    """

    settlement_id: int
    trigger_tick: int
    old_faction_id: int | None = None
    new_faction_id: int | None = None
    old_governor_id: int | None = None
    cause: str = ""


class RevolutionTracker:
    """革命状态追踪器。

    追踪各聚落的抗议持续时间，判断是否触发革命。
    """

    def __init__(self) -> None:
        self._protest_duration: dict[int, int] = {}
        self._cooldown: dict[int, int] = {}
        self._events: list[RevolutionEvent] = []

    def update(
        self,
        settlement_id: int,
        protest_ratio: float,
        avg_satisfaction: float,
    ) -> bool:
        """更新聚落的革命状态。

        Args:
            settlement_id: 聚落 ID。
            protest_ratio: 当前抗议率。
            avg_satisfaction: 平均满意度。

        Returns:
            是否达到革命触发条件。
        """
        # 冷却期内不累积
        if self._cooldown.get(settlement_id, 0) > 0:
            self._cooldown[settlement_id] -= 1
            return False

        if (
            protest_ratio >= REVOLUTION_PROTEST_THRESHOLD
            and avg_satisfaction <= REVOLUTION_SATISFACTION_THRESHOLD
        ):
            self._protest_duration[settlement_id] = (
                self._protest_duration.get(settlement_id, 0) + 1
            )
            current_duration = self._protest_duration[settlement_id]
            if current_duration % 5 == 0:
                logger.info(
                    "聚落 %d 革命累积: %d/%d ticks "
                    "(抗议率=%.3f, 满意度=%.3f)",
                    settlement_id, current_duration,
                    REVOLUTION_DURATION_TICKS,
                    protest_ratio, avg_satisfaction,
                )
        else:
            current = self._protest_duration.get(settlement_id, 0)
            self._protest_duration[settlement_id] = max(
                0, current - 2,
            )

        return (
            self._protest_duration.get(settlement_id, 0)
            >= REVOLUTION_DURATION_TICKS
        )

    def trigger_revolution(
        self,
        settlement_id: int,
        tick: int,
        old_faction_id: int | None = None,
        old_governor_id: int | None = None,
        cause: str = "民众持续抗议",
    ) -> RevolutionEvent:
        """记录革命事件并重置计数器。

        Args:
            settlement_id: 聚落 ID。
            tick: 当前 tick。
            old_faction_id: 旧阵营 ID。
            old_governor_id: 旧镇长 ID。
            cause: 革命原因。

        Returns:
            革命事件记录。
        """
        event = RevolutionEvent(
            settlement_id=settlement_id,
            trigger_tick=tick,
            old_faction_id=old_faction_id,
            old_governor_id=old_governor_id,
            cause=cause,
        )
        self._events.append(event)
        self._protest_duration[settlement_id] = 0
        self._cooldown[settlement_id] = REVOLUTION_COOLDOWN_TICKS
        logger.warning(
            "革命爆发: 聚落 %d (tick %d) - %s",
            settlement_id, tick, cause,
        )
        return event

    def apply_revolution(
        self, event: RevolutionEvent, settlement: object,
    ) -> None:
        """应用革命后果到聚落。

        Args:
            event: 革命事件。
            settlement: 聚落对象。
        """
        if hasattr(settlement, "stockpile"):
            settlement.stockpile["gold"] *= 0.5
            settlement.stockpile["food"] *= 0.8
        if hasattr(settlement, "security_level"):
            settlement.security_level = max(
                0.0, settlement.security_level - 0.4,
            )
        if hasattr(settlement, "tax_rate"):
            settlement.tax_rate = 0.15
        if hasattr(settlement, "faction_id"):
            event.old_faction_id = settlement.faction_id
            settlement.faction_id = None
        if hasattr(settlement, "governor_id"):
            event.old_governor_id = settlement.governor_id
            settlement.governor_id = None

    def get_protest_duration(self, settlement_id: int) -> int:
        """获取聚落的连续抗议持续 tick 数。"""
        return self._protest_duration.get(settlement_id, 0)

    @property
    def events(self) -> list[RevolutionEvent]:
        """返回所有革命事件记录。"""
        return list(self._events)

    @property
    def revolution_count(self) -> int:
        """返回总革命次数。"""
        return len(self._events)
