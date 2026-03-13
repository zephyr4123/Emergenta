"""线程安全的仿真状态桥接层。

在仿真线程与 Dash 回调之间传递数据。
仿真线程每 tick 写入快照；Dash 回调按间隔读取最新快照。
上帝模式操作通过 pending_actions 队列注入仿真线程。
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GodAction(Enum):
    """上帝模式操作类型。"""

    INJECT_EVENT = "inject_event"
    SET_PARAMETER = "set_parameter"
    SETTLEMENT_INTERVENE = "settlement_intervene"
    FORCE_DIPLOMACY = "force_diplomacy"
    REPLACE_LEADER = "replace_leader"
    SET_SPEED = "set_speed"
    APPLY_SCENARIO = "apply_scenario"
    PAUSE = "pause"
    RESUME = "resume"
    STEP = "step"


@dataclass
class GodModeAction:
    """上帝模式操作指令。

    Attributes:
        action: 操作类型。
        params: 操作参数字典。
    """

    action: GodAction
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class TickSnapshot:
    """单个 tick 的聚合快照。

    Attributes:
        tick: 当前 tick 编号。
        year: 当前年份。
        season: 当前季节名称。
        day: 当前天数。
        population: 总人口。
        state_counts: 各状态人数 {state_name: count}。
        resources: 总资源 {resource_name: total}。
        settlements: 聚落快照列表。
        avg_satisfaction: 全局平均满意度。
        avg_hunger: 全局平均饥饿度。
        protest_ratio: 全局抗议率。
        revolution_count: 累计革命次数。
        trade_volume: 总贸易量。
        alliance_count: 联盟数。
        war_count: 战争数。
        faction_count: 阵营数。
        events: 本 tick 发生的事件列表。
        adaptive_info: 自适应控制器信息。
    """

    tick: int = 0
    year: int = 0
    season: str = "春"
    day: int = 0
    population: int = 0
    state_counts: dict[str, int] = field(default_factory=dict)
    resources: dict[str, float] = field(default_factory=dict)
    settlements: list[dict[str, Any]] = field(default_factory=list)
    avg_satisfaction: float = 0.0
    avg_hunger: float = 0.0
    protest_ratio: float = 0.0
    revolution_count: int = 0
    trade_volume: float = 0.0
    alliance_count: int = 0
    war_count: int = 0
    faction_count: int = 0
    events: list[str] = field(default_factory=list)
    adaptive_info: dict[str, Any] = field(default_factory=dict)


# 季节中文映射
_SEASON_CN: dict[int, str] = {0: "春", 1: "夏", 2: "秋", 3: "冬"}

# 历史快照最大保留量
_MAX_HISTORY = 5000


class SharedState:
    """线程安全的仿真状态容器。

    仿真线程通过 update_from_engine() 写入数据；
    Dash 回调通过 get_latest() / get_history() 读取数据。
    上帝模式操作通过 enqueue_action() / drain_actions() 传递。
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: TickSnapshot = TickSnapshot()
        self._history: deque[TickSnapshot] = deque(maxlen=_MAX_HISTORY)
        self._pending_actions: deque[GodModeAction] = deque()
        self._is_paused: bool = True
        self._speed: int = 1
        self._is_running: bool = False
        self._event_log: deque[str] = deque(maxlen=500)
        self._trade_routes: list[dict[str, Any]] = []
        self._diplomacy_data: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # 仿真线程写入接口
    # ------------------------------------------------------------------

    def update_from_engine(self, engine: Any) -> None:
        """从引擎提取当前 tick 的聚合数据并存储。

        Args:
            engine: CivilizationEngine 实例。
        """
        snapshot = self._build_snapshot(engine)
        with self._lock:
            self._latest = snapshot
            self._history.append(snapshot)
            self._update_trade_routes(engine)
            self._update_diplomacy_data(engine)

    def _build_snapshot(self, engine: Any) -> TickSnapshot:
        """从引擎构建 TickSnapshot。"""
        from civsim.agents.behaviors.fsm import CivilianState
        from civsim.agents.civilian import Civilian

        civilians = [a for a in engine.agents if isinstance(a, Civilian)]

        # 状态计数
        state_counts: dict[str, int] = {}
        for s in CivilianState:
            state_counts[s.name] = sum(
                1 for c in civilians if c.state == s
            )

        # 资源汇总
        resources: dict[str, float] = {
            "food": 0.0, "wood": 0.0, "ore": 0.0, "gold": 0.0,
        }
        for s in engine.settlements.values():
            for r in resources:
                resources[r] += s.stockpile.get(r, 0.0)

        # 聚落快照
        settlements = []
        for s in engine.settlements.values():
            s_civilians = [
                c for c in civilians if c.home_settlement_id == s.id
            ]
            s_sat = (
                sum(c.satisfaction for c in s_civilians) / len(s_civilians)
                if s_civilians else 0.0
            )
            s_protest = (
                sum(
                    1 for c in s_civilians
                    if c.state == CivilianState.PROTESTING
                ) / len(s_civilians)
                if s_civilians else 0.0
            )
            settlements.append({
                "id": s.id,
                "name": s.name,
                "population": len(s_civilians),
                "food": s.stockpile.get("food", 0.0),
                "wood": s.stockpile.get("wood", 0.0),
                "ore": s.stockpile.get("ore", 0.0),
                "gold": s.stockpile.get("gold", 0.0),
                "tax_rate": s.tax_rate,
                "security_level": s.security_level,
                "satisfaction": s_sat,
                "protest_ratio": s_protest,
                "faction_id": s.faction_id,
                "position": s.position,
            })

        # 全局指标
        pop = len(civilians)
        avg_sat = (
            sum(c.satisfaction for c in civilians) / pop if pop else 0.0
        )
        avg_hunger = (
            sum(c.hunger for c in civilians) / pop if pop else 0.0
        )
        protest = (
            state_counts.get("PROTESTING", 0) / pop if pop else 0.0
        )

        # 外交与贸易
        rev_count = (
            engine.revolution_tracker.revolution_count
            if engine.revolution_tracker else 0
        )
        trade_vol = (
            engine.trade_manager.total_volume
            if engine.trade_manager else 0.0
        )
        alliance_count = 0
        war_count = 0
        if engine.diplomacy:
            from civsim.politics.diplomacy import DiplomaticStatus
            for status in engine.diplomacy._relations.values():
                if status == DiplomaticStatus.ALLIED:
                    alliance_count += 1
                elif status == DiplomaticStatus.WAR:
                    war_count += 1

        faction_ids = {
            s.faction_id for s in engine.settlements.values()
            if s.faction_id is not None
        }

        # 自适应控制器
        adaptive_info: dict[str, Any] = {}
        if engine.adaptive_controller:
            ctrl = engine.adaptive_controller
            adaptive_info = {
                "temperature": (
                    ctrl.temperature_history[-1][1]
                    if ctrl.temperature_history else 0.0
                ),
                "markov_protest_multiplier": (
                    ctrl.coefficients.markov_protest_multiplier
                ),
                "granovetter_burst_multiplier": (
                    ctrl.coefficients.granovetter_burst_multiplier
                ),
                "revolution_cooldown_multiplier": (
                    ctrl.coefficients.revolution_cooldown_multiplier
                ),
                "satisfaction_recovery_multiplier": (
                    ctrl.coefficients.satisfaction_recovery_multiplier
                ),
            }

        season_val = engine.clock.current_season
        season_cn = _SEASON_CN.get(
            season_val.value if hasattr(season_val, "value") else int(season_val),
            "春",
        )

        return TickSnapshot(
            tick=engine.clock.tick,
            year=engine.clock.current_year,
            season=season_cn,
            day=engine.clock.current_day,
            population=pop,
            state_counts=state_counts,
            resources=resources,
            settlements=settlements,
            avg_satisfaction=avg_sat,
            avg_hunger=avg_hunger,
            protest_ratio=protest,
            revolution_count=rev_count,
            trade_volume=trade_vol,
            alliance_count=alliance_count,
            war_count=war_count,
            faction_count=len(faction_ids),
            adaptive_info=adaptive_info,
        )

    def _update_trade_routes(self, engine: Any) -> None:
        """更新贸易路线数据。"""
        if not engine.trade_manager:
            return
        routes = []
        for t in engine.trade_manager.completed_trades[-50:]:
            routes.append({
                "seller_id": t.seller_id,
                "buyer_id": t.buyer_id,
                "resource": t.resource,
                "amount": t.amount,
                "price_gold": t.price_gold,
            })
        self._trade_routes = routes

    def _update_diplomacy_data(self, engine: Any) -> None:
        """更新外交关系数据。"""
        if not engine.diplomacy:
            return
        relations: dict[str, Any] = {}
        for (a, b), status in engine.diplomacy._relations.items():
            key = f"{a}-{b}"
            relations[key] = {
                "faction_a": a,
                "faction_b": b,
                "status": status.name,
                "trust": engine.diplomacy.get_trust(a, b),
            }
        self._diplomacy_data = relations

    # ------------------------------------------------------------------
    # Dash 回调读取接口
    # ------------------------------------------------------------------

    def get_latest(self) -> TickSnapshot:
        """返回最新 tick 快照（线程安全副本）。"""
        with self._lock:
            return self._latest

    def get_history(self, n: int | None = None) -> list[TickSnapshot]:
        """返回历史快照列表。

        Args:
            n: 返回最近 n 条，None 则返回全部。
        """
        with self._lock:
            if n is None:
                return list(self._history)
            return list(self._history)[-n:]

    def get_trade_routes(self) -> list[dict[str, Any]]:
        """返回最近贸易路线。"""
        with self._lock:
            return list(self._trade_routes)

    def get_diplomacy_data(self) -> dict[str, Any]:
        """返回外交关系数据。"""
        with self._lock:
            return dict(self._diplomacy_data)

    @property
    def is_paused(self) -> bool:
        """是否暂停。"""
        with self._lock:
            return self._is_paused

    @is_paused.setter
    def is_paused(self, value: bool) -> None:
        with self._lock:
            self._is_paused = value

    @property
    def speed(self) -> int:
        """仿真速度倍率。"""
        with self._lock:
            return self._speed

    @speed.setter
    def speed(self, value: int) -> None:
        with self._lock:
            self._speed = max(1, min(value, 20))

    @property
    def is_running(self) -> bool:
        """仿真线程是否在运行。"""
        with self._lock:
            return self._is_running

    @is_running.setter
    def is_running(self, value: bool) -> None:
        with self._lock:
            self._is_running = value

    # ------------------------------------------------------------------
    # 事件日志
    # ------------------------------------------------------------------

    def add_event(self, msg: str) -> None:
        """追加事件日志。"""
        with self._lock:
            self._event_log.append(msg)

    def get_event_log(self, n: int = 50) -> list[str]:
        """返回最近 n 条事件日志。"""
        with self._lock:
            return list(self._event_log)[-n:]

    # ------------------------------------------------------------------
    # 上帝模式操作队列
    # ------------------------------------------------------------------

    def enqueue_action(self, action: GodModeAction) -> None:
        """向操作队列追加一条上帝模式指令。"""
        with self._lock:
            self._pending_actions.append(action)

    def drain_actions(self) -> list[GodModeAction]:
        """取出并清空所有待处理的上帝模式指令。"""
        with self._lock:
            actions = list(self._pending_actions)
            self._pending_actions.clear()
            return actions
