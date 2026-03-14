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
    RESET = "reset"


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
class LLMSpeech:
    """LLM Agent 的一次决策发言记录。

    Attributes:
        tick: 发言所在 tick。
        agent_type: Agent 类型（"governor" | "leader"）。
        agent_id: Agent 唯一 ID。
        agent_name: 显示名称（聚落名 或 "阵营 X"）。
        reasoning: 完整 reasoning 文本（不截断）。
        decision_summary: 一行决策摘要。
    """

    tick: int
    agent_type: str
    agent_id: int
    agent_name: str
    reasoning: str
    decision_summary: str


@dataclass
class MarkovTransition:
    """单次马尔可夫状态转移记录（用于滚动展示）。

    Attributes:
        tick: 发生的 tick。
        agent_id: Agent 唯一 ID。
        personality: 性格标签。
        prev_state: 转移前状态名。
        next_state: 转移后状态名。
        probability: 该转移的概率值。
        hunger: 转移时的饥饿度。
        satisfaction: 转移时的满意度。
        factors: 影响因子描述列表，如 ["饥饿+48%", "税率+27%"]。
        granovetter_triggered: 是否触发了 Granovetter 传染。
    """

    tick: int
    agent_id: int
    personality: str
    prev_state: str
    next_state: str
    probability: float
    hunger: float
    satisfaction: float
    factors: list[str] = field(default_factory=list)
    granovetter_triggered: bool = False


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
        agent_positions: Agent 坐标列表 [(x, y), ...]。
        agent_states: Agent 状态索引列表 [0-6, ...]。
        tile_grid: 地块类型矩阵（二维列表，值为 TileType 序号）。
        grid_width: 网格宽度。
        grid_height: 网格高度。
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
    agent_positions: list[tuple[int, int]] = field(default_factory=list)
    agent_states: list[int] = field(default_factory=list)
    tile_grid: list[list[int]] = field(default_factory=list)
    grid_width: int = 0
    grid_height: int = 0


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
        self._llm_speeches: deque[LLMSpeech] = deque(maxlen=100)
        self._markov_transitions: deque[MarkovTransition] = deque(maxlen=60)
        self._tile_grid_cache: list[list[int]] = []
        self._grid_width: int = 0
        self._grid_height: int = 0
        self._param_version: int = 0
        self._current_params: dict[str, Any] = {}

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

        # Agent 位置与状态（实时地图用）
        agent_positions: list[tuple[int, int]] = []
        agent_states: list[int] = []
        for c in civilians:
            pos = c.pos if c.pos is not None else (0, 0)
            agent_positions.append(pos)
            agent_states.append(int(c.state))

        # 地块网格（首次或变化时缓存）
        tile_grid = self._tile_grid_cache
        grid_w = self._grid_width
        grid_h = self._grid_height
        if not tile_grid and hasattr(engine, "tile_grid"):
            tile_grid, grid_w, grid_h = self._serialize_tile_grid(
                engine.tile_grid,
            )
            self._tile_grid_cache = tile_grid
            self._grid_width = grid_w
            self._grid_height = grid_h

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
            agent_positions=agent_positions,
            agent_states=agent_states,
            tile_grid=tile_grid,
            grid_width=grid_w,
            grid_height=grid_h,
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
    # LLM 发言记录
    # ------------------------------------------------------------------

    def add_speech(self, speech: LLMSpeech) -> None:
        """追加一条 LLM 发言记录。"""
        with self._lock:
            self._llm_speeches.append(speech)

    def get_speeches(self, n: int = 30) -> list[LLMSpeech]:
        """返回最近 n 条 LLM 发言记录。"""
        with self._lock:
            return list(self._llm_speeches)[-n:]

    # ------------------------------------------------------------------
    # 马尔可夫转移滚动缓冲
    # ------------------------------------------------------------------

    def add_markov_transition(self, t: MarkovTransition) -> None:
        """追加一条马尔可夫转移记录。"""
        with self._lock:
            self._markov_transitions.append(t)

    def get_markov_transitions(self, n: int = 30) -> list[MarkovTransition]:
        """返回最近 n 条马尔可夫转移记录。"""
        with self._lock:
            return list(self._markov_transitions)[-n:]

    # ------------------------------------------------------------------
    # 地块网格序列化
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_tile_grid(
        tile_grid: list[list[Any]],
    ) -> tuple[list[list[int]], int, int]:
        """将 Tile 对象网格转换为整数类型矩阵。

        Returns:
            (grid, width, height)
        """
        _TYPE_INDEX = {
            "farmland": 0, "forest": 1, "mine": 2,
            "water": 3, "mountain": 4, "barren": 5, "settlement": 6,
        }
        if not tile_grid:
            return [], 0, 0
        width = len(tile_grid)
        height = len(tile_grid[0]) if tile_grid else 0
        grid: list[list[int]] = []
        for col in tile_grid:
            row_data: list[int] = []
            for tile in col:
                tt = getattr(tile, "tile_type", None)
                val = tt.value if tt else "barren"
                row_data.append(_TYPE_INDEX.get(val, 5))
            grid.append(row_data)
        return grid, width, height

    # ------------------------------------------------------------------
    # 参数同步（服务端 → 前端）
    # ------------------------------------------------------------------

    def bump_param_version(self, params: dict[str, Any]) -> None:
        """递增参数版本号并存储当前参数快照。

        Args:
            params: 所有注册参数的当前值 {config_path: value}。
        """
        with self._lock:
            self._param_version += 1
            self._current_params = params.copy()

    @property
    def param_version(self) -> int:
        """参数版本号（每次服务端批量修改参数后递增）。"""
        with self._lock:
            return self._param_version

    def get_current_params(self) -> dict[str, Any]:
        """返回最新参数快照。"""
        with self._lock:
            return dict(self._current_params)

    def reset(self) -> None:
        """重置所有状态数据（保留事件日志和参数版本号）。"""
        with self._lock:
            self._latest = TickSnapshot()
            self._history.clear()
            self._pending_actions.clear()
            self._trade_routes = []
            self._diplomacy_data = {}
            self._llm_speeches.clear()
            self._markov_transitions.clear()
            self._tile_grid_cache = []
            self._grid_width = 0
            self._grid_height = 0

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
