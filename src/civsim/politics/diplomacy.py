"""外交系统。

管理阵营间外交关系状态机、条约和信任度。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, IntEnum

from civsim.config_params_ext import DiplomacyParamsConfig

logger = logging.getLogger(__name__)


class DiplomaticStatus(IntEnum):
    """外交关系状态枚举（数值越高越友好）。"""

    WAR = 0
    HOSTILE = 1
    NEUTRAL = 2
    FRIENDLY = 3
    ALLIED = 4


class TreatyType(Enum):
    """条约类型枚举。"""

    TRADE_AGREEMENT = "trade_agreement"
    NON_AGGRESSION = "non_aggression"
    MILITARY_ALLIANCE = "military_alliance"


@dataclass
class Treaty:
    """条约数据。

    Attributes:
        treaty_type: 条约类型。
        faction_a: 阵营 A ID。
        faction_b: 阵营 B ID。
        signed_tick: 签署时的 tick。
        duration_ticks: 持续 tick 数（None 表示永久）。
        terms: 条约条款。
        active: 是否有效。
    """

    treaty_type: TreatyType
    faction_a: int
    faction_b: int
    signed_tick: int
    duration_ticks: int | None = None
    terms: dict = field(default_factory=dict)
    active: bool = True

    def is_expired(self, current_tick: int) -> bool:
        """检查条约是否过期。"""
        if self.duration_ticks is None:
            return False
        return current_tick >= self.signed_tick + self.duration_ticks


class DiplomacyManager:
    """外交关系管理器。

    追踪阵营间的外交状态、条约和信任度。
    """

    def __init__(
        self,
        initial_trust: float = 0.5,
        params: DiplomacyParamsConfig | None = None,
    ) -> None:
        self._params = params or DiplomacyParamsConfig()
        self._relations: dict[tuple[int, int], DiplomaticStatus] = {}
        self._treaties: list[Treaty] = []
        self._trust: dict[tuple[int, int], float] = {}
        self._initial_trust = self._params.initial_trust
        self._randomize_trust = self._params.randomize_trust
        self._event_log: list[dict] = []
        self._rng = __import__("random").Random()

    @staticmethod
    def _key(a: int, b: int) -> tuple[int, int]:
        """生成有序的阵营对键。"""
        return (min(a, b), max(a, b))

    def get_relation(self, a: int, b: int) -> DiplomaticStatus:
        """获取两个阵营间的外交状态。"""
        return self._relations.get(self._key(a, b), DiplomaticStatus.NEUTRAL)

    def set_relation(
        self, a: int, b: int, status: DiplomaticStatus, tick: int = 0,
    ) -> None:
        """设置两个阵营间的外交状态。"""
        key = self._key(a, b)
        old = self._relations.get(key, DiplomaticStatus.NEUTRAL)
        self._relations[key] = status
        if old != status:
            self._event_log.append({
                "tick": tick, "factions": key,
                "old_status": old.name, "new_status": status.name,
            })
            logger.info(
                "外交变更: 阵营%d↔阵营%d %s→%s", a, b, old.name, status.name,
            )

    def get_trust(self, a: int, b: int) -> float:
        """获取两个阵营间的信任度。"""
        key = self._key(a, b)
        if key not in self._trust:
            if self._randomize_trust:
                self._trust[key] = self._rng.uniform(
                    self._params.trust_random_min,
                    self._params.trust_random_max,
                )
            else:
                self._trust[key] = self._initial_trust
        return self._trust[key]

    def update_trust(self, a: int, b: int, delta: float) -> float:
        """更新信任度，返回更新后的值。"""
        key = self._key(a, b)
        current = self._trust.get(key, self._initial_trust)
        new_trust = max(0.0, min(1.0, current + delta))
        self._trust[key] = new_trust
        return new_trust

    def adjust_trust(self, a: int, b: int, delta: float) -> float:
        """调节信任度（update_trust 的别名）。

        Args:
            a: 阵营 A ID。
            b: 阵营 B ID。
            delta: 信任增量。

        Returns:
            更新后的信任度。
        """
        return self.update_trust(a, b, delta)

    def sign_treaty(self, treaty: Treaty) -> None:
        """签署条约。"""
        self._treaties.append(treaty)
        self.update_trust(treaty.faction_a, treaty.faction_b, self._params.treaty_trust_boost)

        if treaty.treaty_type == TreatyType.MILITARY_ALLIANCE:
            self.set_relation(
                treaty.faction_a, treaty.faction_b,
                DiplomaticStatus.ALLIED, treaty.signed_tick,
            )
        elif treaty.treaty_type == TreatyType.TRADE_AGREEMENT:
            current = self.get_relation(treaty.faction_a, treaty.faction_b)
            if current < DiplomaticStatus.FRIENDLY:
                self.set_relation(
                    treaty.faction_a, treaty.faction_b,
                    DiplomaticStatus.FRIENDLY, treaty.signed_tick,
                )

        logger.info(
            "签署条约: %s 阵营%d↔阵营%d",
            treaty.treaty_type.value, treaty.faction_a, treaty.faction_b,
        )

    def break_treaty(
        self, treaty: Treaty, breaker_id: int, tick: int,
    ) -> None:
        """违反/终止条约。降级到 WAR 而非 HOSTILE。"""
        treaty.active = False
        other = (
            treaty.faction_b if breaker_id == treaty.faction_a
            else treaty.faction_a
        )
        self.update_trust(breaker_id, other, self._params.break_treaty_penalty)

        current = self.get_relation(breaker_id, other)
        if current > DiplomaticStatus.WAR:
            self.set_relation(breaker_id, other, DiplomaticStatus.WAR, tick)

        self._event_log.append({
            "tick": tick, "type": "treaty_broken",
            "breaker": breaker_id,
            "treaty_type": treaty.treaty_type.value,
        })

    def get_active_treaties(
        self, faction_id: int | None = None,
    ) -> list[Treaty]:
        """获取活跃条约。"""
        result = [t for t in self._treaties if t.active]
        if faction_id is not None:
            result = [
                t for t in result
                if faction_id in (t.faction_a, t.faction_b)
            ]
        return result

    def expire_treaties(self, current_tick: int) -> list[Treaty]:
        """检查并清理过期条约，返回本次过期列表。"""
        expired = []
        for treaty in self._treaties:
            if treaty.active and treaty.is_expired(current_tick):
                treaty.active = False
                expired.append(treaty)
        return expired

    def get_allies(self, faction_id: int) -> list[int]:
        """获取某阵营的盟友列表。"""
        allies = []
        for (a, b), status in self._relations.items():
            if status >= DiplomaticStatus.ALLIED:
                if a == faction_id:
                    allies.append(b)
                elif b == faction_id:
                    allies.append(a)
        return allies

    def get_enemies(self, faction_id: int) -> list[int]:
        """获取与某阵营处于战争状态的阵营。"""
        enemies = []
        for (a, b), status in self._relations.items():
            if status == DiplomaticStatus.WAR:
                if a == faction_id:
                    enemies.append(b)
                elif b == faction_id:
                    enemies.append(a)
        return enemies

    def count_wars(self) -> int:
        """统计当前活跃战争数。

        Returns:
            处于 WAR 状态的阵营对数量。
        """
        return sum(
            1 for status in self._relations.values()
            if status == DiplomaticStatus.WAR
        )

    def get_relations_dict(self) -> dict[tuple[int, int], int]:
        """返回所有外交关系的整数值字典（用于贸易过滤）。"""
        return {k: int(v) for k, v in self._relations.items()}

    def get_trust_data(self) -> dict[tuple[int, int], float]:
        """返回所有信任度数据字典（用于贸易摩擦）。"""
        return dict(self._trust)

    def decay_trust(self, amount: float | None = None) -> None:
        """全局信任自然衰减，需要主动维护关系。

        Args:
            amount: 每次衰减量。为 None 时使用配置值。
        """
        if amount is None:
            amount = self._params.trust_decay_per_tick
        for key in list(self._trust.keys()):
            self._trust[key] = max(0.0, self._trust[key] - amount)

    def auto_downgrade_relations(self, tick: int) -> None:
        """当信任度过低时自动降级外交关系。

        Args:
            tick: 当前 tick。
        """
        for key, trust in list(self._trust.items()):
            if trust < self._params.downgrade_trust_threshold:
                current = self._relations.get(key, DiplomaticStatus.NEUTRAL)
                if current > DiplomaticStatus.HOSTILE:
                    a, b = key
                    self.set_relation(a, b, DiplomaticStatus.HOSTILE, tick)
                    logger.info(
                        "信任度过低(%.2f)，阵营%d↔阵营%d 自动降级为敌对",
                        trust, a, b,
                    )

    @property
    def event_log(self) -> list[dict]:
        """返回外交事件日志。"""
        return list(self._event_log)
