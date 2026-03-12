"""革命/政权更替机制。

检测革命触发条件、执行政权更替和聚落状态重置。
含恢复阶段机制：革命后蜜月期满意度提升 + 公民阈值调整。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from civsim.config_params import RevolutionParamsConfig

logger = logging.getLogger(__name__)

# 后向兼容的模块级常量（供未迁移代码引用）
REVOLUTION_PROTEST_THRESHOLD = 0.20
REVOLUTION_SATISFACTION_THRESHOLD = 0.40
REVOLUTION_DURATION_TICKS = 8
REVOLUTION_COOLDOWN_TICKS = 30


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


@dataclass
class RecoveryPhase:
    """革命后恢复阶段。

    Attributes:
        settlement_id: 聚落 ID。
        remaining_ticks: 剩余蜜月期 tick 数。
        satisfaction_boost: 每 tick 满意度提升。
        vigilance_reduction: 公民阈值降低量。
        trigger_tick: 开始 tick。
    """

    settlement_id: int
    remaining_ticks: int
    satisfaction_boost: float
    vigilance_reduction: float
    trigger_tick: int = 0


class RevolutionTracker:
    """革命状态追踪器。

    追踪各聚落的抗议持续时间，判断是否触发革命。
    支持恢复阶段机制。冷却期包含随机扰动避免机械式周期。
    """

    def __init__(
        self,
        params: RevolutionParamsConfig | None = None,
    ) -> None:
        self._params = params or RevolutionParamsConfig()
        self._protest_duration: dict[int, int] = {}
        self._cooldown: dict[int, int] = {}
        self._events: list[RevolutionEvent] = []
        self._recovery: dict[int, RecoveryPhase] = {}
        self._rng = __import__("random").Random()

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
            protest_ratio >= self._params.protest_threshold
            and avg_satisfaction <= self._params.satisfaction_threshold
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
                    self._params.duration_ticks,
                    protest_ratio, avg_satisfaction,
                )
        else:
            # 条件不满足时加速衰减（每 tick -2），避免无限逼近触发
            current = self._protest_duration.get(settlement_id, 0)
            self._protest_duration[settlement_id] = max(
                0, current - 2,
            )

        return (
            self._protest_duration.get(settlement_id, 0)
            >= self._params.duration_ticks
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
        # 冷却期加入 ±30% 随机扰动，打破固定周期
        base_cooldown = self._params.cooldown_ticks
        jitter = self._rng.uniform(-0.3, 0.3)
        self._cooldown[settlement_id] = max(
            5, int(base_cooldown * (1.0 + jitter)),
        )
        logger.warning(
            "革命爆发: 聚落 %d (tick %d) - %s",
            settlement_id, tick, cause,
        )
        return event

    def apply_revolution(
        self,
        event: RevolutionEvent,
        settlement: object,
        penalty_multiplier: float = 1.0,
    ) -> None:
        """应用革命后果到聚落并启动恢复阶段。

        Args:
            event: 革命事件。
            settlement: 聚落对象。
            penalty_multiplier: 惩罚乘数（来自自适应控制器）。
        """
        gold_ratio = self._params.resource_penalty_gold
        food_ratio = self._params.resource_penalty_food
        sec_penalty = self._params.security_penalty * penalty_multiplier

        if hasattr(settlement, "stockpile"):
            settlement.stockpile["gold"] *= gold_ratio
            settlement.stockpile["food"] *= food_ratio
        if hasattr(settlement, "security_level"):
            settlement.security_level = max(
                0.0, settlement.security_level - sec_penalty,
            )
        if hasattr(settlement, "tax_rate"):
            settlement.tax_rate = self._params.post_revolution_tax

        # 人口损失（革命不是免费的重置键）
        pop_loss = self._params.population_loss_ratio
        if pop_loss > 0 and hasattr(settlement, "population"):
            lost = max(1, int(settlement.population * pop_loss))
            settlement.population = max(1, settlement.population - lost)
            logger.info(
                "聚落 %d 革命导致人口损失: -%d (剩余 %d)",
                event.settlement_id, lost, settlement.population,
            )
        if hasattr(settlement, "faction_id"):
            event.old_faction_id = settlement.faction_id
            settlement.faction_id = None
        if hasattr(settlement, "governor_id"):
            event.old_governor_id = settlement.governor_id
            settlement.governor_id = None

        # 启动恢复阶段
        self.start_recovery(
            event.settlement_id, event.trigger_tick,
        )

        # --- 革命后遗症 ---
        # 累积生产力衰减
        decay = self._params.aftermath_productivity_decay
        if decay > 0 and hasattr(settlement, "infrastructure"):
            max_decay = self._params.aftermath_max_cumulative_decay
            new_infra = max(
                1.0 - max_decay,
                settlement.infrastructure * (1.0 - decay),
            )
            settlement.infrastructure = new_infra
            logger.info(
                "聚落 %d 革命后遗症: 基础设施 %.2f→%.2f",
                event.settlement_id,
                settlement.infrastructure + decay,
                new_infra,
            )

        # 外交信任惩罚
        trust_pen = self._params.aftermath_trust_penalty
        if trust_pen > 0 and hasattr(settlement, "faction_id"):
            fid = event.old_faction_id
            if fid is not None and hasattr(settlement, "_model_ref"):
                model = settlement._model_ref
                if hasattr(model, "diplomacy") and model.diplomacy:
                    for other_fid in model.diplomacy.get_all_factions():
                        if other_fid != fid:
                            model.diplomacy.update_trust(
                                fid, other_fid, -trust_pen,
                            )

    def start_recovery(
        self, settlement_id: int, tick: int,
    ) -> None:
        """启动革命后恢复阶段。

        Args:
            settlement_id: 聚落 ID。
            tick: 当前 tick。
        """
        self._recovery[settlement_id] = RecoveryPhase(
            settlement_id=settlement_id,
            remaining_ticks=self._params.honeymoon_ticks,
            satisfaction_boost=self._params.honeymoon_satisfaction_boost,
            vigilance_reduction=self._params.honeymoon_vigilance_reduction,
            trigger_tick=tick,
        )
        logger.info(
            "聚落 %d 进入革命后蜜月期 (%d ticks)",
            settlement_id, self._params.honeymoon_ticks,
        )

    def update_recovery(self) -> list[int]:
        """更新所有恢复阶段，返回已结束恢复的聚落 ID。

        Returns:
            本 tick 结束恢复阶段的聚落 ID 列表。
        """
        finished: list[int] = []
        to_remove: list[int] = []
        for sid, phase in self._recovery.items():
            phase.remaining_ticks -= 1
            if phase.remaining_ticks <= 0:
                to_remove.append(sid)
                finished.append(sid)
        for sid in to_remove:
            del self._recovery[sid]
            logger.info("聚落 %d 蜜月期结束", sid)
        return finished

    def get_recovery(
        self, settlement_id: int,
    ) -> RecoveryPhase | None:
        """获取聚落当前的恢复阶段。

        Args:
            settlement_id: 聚落 ID。

        Returns:
            恢复阶段对象，不在恢复期则返回 None。
        """
        return self._recovery.get(settlement_id)

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

    def recent_revolution_count(
        self, current_tick: int, lookback: int = 200,
    ) -> int:
        """返回近期革命次数。

        Args:
            current_tick: 当前 tick。
            lookback: 回溯 tick 数。

        Returns:
            近 lookback tick 内的革命次数。
        """
        cutoff = current_tick - lookback
        return sum(
            1 for e in self._events if e.trigger_tick >= cutoff
        )

    @property
    def active_recoveries(self) -> dict[int, RecoveryPhase]:
        """返回所有活跃的恢复阶段。"""
        return dict(self._recovery)

