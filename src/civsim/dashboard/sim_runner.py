"""后台仿真线程管理器。

在独立线程中运行 CivilizationEngine.step()，
通过 SharedState 与 Dash 前端交换数据和控制指令。
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from civsim.config import CivSimConfig, load_config
from civsim.dashboard.shared_state import (
    GodAction,
    GodModeAction,
    SharedState,
)
from civsim.world.engine import CivilizationEngine

logger = logging.getLogger(__name__)


class SimulationRunner:
    """后台仿真运行器。

    在独立守护线程中循环执行 engine.step()，
    支持暂停、恢复、单步、速度调节和上帝模式操作注入。

    Attributes:
        engine: CivilizationEngine 实例。
        state: 共享状态对象。
        config: 仿真配置。
    """

    def __init__(
        self,
        config: CivSimConfig | None = None,
        config_path: str | None = None,
        seed: int | None = None,
        enable_governors: bool = True,
        enable_leaders: bool = True,
        enable_db: bool = False,
    ) -> None:
        self.config = config or load_config(config_path)
        self.state = SharedState()
        self.engine = CivilizationEngine(
            config=self.config,
            seed=seed,
            enable_governors=enable_governors,
            enable_leaders=enable_leaders,
            enable_db=enable_db,
        )
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._step_event = threading.Event()
        # 初始快照
        self.state.update_from_engine(self.engine)
        self.state.add_event(
            f"仿真初始化完成: {len(list(self.engine.agents))} 个Agent, "
            f"{len(self.engine.settlements)} 个聚落"
        )

    # ------------------------------------------------------------------
    # 线程生命周期
    # ------------------------------------------------------------------

    def start(self) -> None:
        """启动后台仿真线程（暂停状态）。"""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("仿真线程已在运行")
            return
        self._stop_event.clear()
        self.state.is_running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            name="sim-runner",
            daemon=True,
        )
        self._thread.start()
        logger.info("仿真线程已启动")

    def stop(self) -> None:
        """停止仿真线程。"""
        self._stop_event.set()
        self._step_event.set()  # 解除可能的等待
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        self.state.is_running = False
        logger.info("仿真线程已停止")

    def resume(self) -> None:
        """恢复仿真运行。"""
        self.state.is_paused = False
        self.state.add_event("▶ 仿真恢复运行")

    def pause(self) -> None:
        """暂停仿真。"""
        self.state.is_paused = True
        self.state.add_event("⏸ 仿真已暂停")

    def step_once(self) -> None:
        """执行单步（一个 tick）。"""
        self._step_event.set()

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        """后台仿真主循环。"""
        logger.info("仿真主循环开始")
        while not self._stop_event.is_set():
            # 处理上帝模式操作（无论是否暂停，优先处理）
            # 这样 RESUME/PAUSE 操作能立即改变 is_paused 状态
            self._process_god_actions()

            if self.state.is_paused:
                # 暂停状态：等待单步信号
                # 用短超时轮询，以便及时响应 RESUME 操作
                triggered = self._step_event.wait(timeout=0.05)
                if triggered:
                    self._step_event.clear()
                    self._execute_tick()
                continue

            # 运行状态：按速度执行 tick
            self._execute_tick()
            delay = self._compute_delay()
            if delay > 0:
                self._stop_event.wait(timeout=delay)

        logger.info("仿真主循环结束")

    def _execute_tick(self) -> None:
        """执行一个 tick 并更新共享状态。"""
        try:
            tick_before = self.engine.clock.tick
            self.engine.step()
            self.state.update_from_engine(self.engine)
            self._log_tick_events(tick_before)
        except Exception:
            logger.exception("tick %d 执行异常", self.engine.clock.tick)
            self.state.add_event(
                f"⚠ Tick {self.engine.clock.tick} 执行异常"
            )

    def _compute_delay(self) -> float:
        """根据速度倍率计算 tick 间延时（秒）。"""
        speed = self.state.speed
        # 速度 1 = 0.2s, 速度 5 = 0.04s, 速度 10+ = 0
        if speed >= 10:
            return 0.0
        return max(0.01, 0.2 / speed)

    def _log_tick_events(self, tick_before: int) -> None:
        """记录本 tick 的关键事件到事件日志。"""
        snap = self.state.get_latest()
        tick = snap.tick

        # 季节/年份变化
        if tick > 0 and tick_before < tick:
            if tick % (self.config.clock.ticks_per_day
                       * self.config.clock.days_per_season) == 0:
                self.state.add_event(
                    f"[Tick {tick}] 季节更替 → {snap.season}"
                )

        # 革命事件
        if self.engine.revolution_tracker:
            for ev in self.engine.revolution_tracker.events:
                if ev.trigger_tick == self.engine.clock.tick:
                    sid = ev.settlement_id
                    name = self.engine.settlements.get(sid)
                    sname = name.name if name else f"#{sid}"
                    self.state.add_event(
                        f"[Tick {tick}] ⚡ 革命爆发 @ {sname}"
                    )

        # 涌现事件
        if self.engine.emergence_detector:
            for ev in self.engine.emergence_detector.events:
                if ev.tick == self.engine.clock.tick:
                    self.state.add_event(
                        f"[Tick {tick}] 🌐 {ev.description}"
                    )

    # ------------------------------------------------------------------
    # 上帝模式操作处理
    # ------------------------------------------------------------------

    def _process_god_actions(self) -> None:
        """处理所有待处理的上帝模式操作。"""
        actions = self.state.drain_actions()
        for action in actions:
            self._apply_god_action(action)

    def _apply_god_action(self, action: GodModeAction) -> None:
        """执行单个上帝模式操作。"""
        handler = _GOD_ACTION_HANDLERS.get(action.action)
        if handler:
            try:
                handler(self, action.params)
            except Exception:
                logger.exception(
                    "上帝模式操作执行失败: %s", action.action
                )
                self.state.add_event(
                    f"⚠ 操作失败: {action.action.value}"
                )
        else:
            logger.warning("未知的上帝模式操作: %s", action.action)

    # --- 各操作处理器 ---

    def _handle_pause(self, params: dict[str, Any]) -> None:
        self.pause()

    def _handle_resume(self, params: dict[str, Any]) -> None:
        self.resume()

    def _handle_step(self, params: dict[str, Any]) -> None:
        self.step_once()

    def _handle_set_speed(self, params: dict[str, Any]) -> None:
        speed = params.get("speed", 1)
        self.state.speed = int(speed)
        self.state.add_event(f"⏩ 速度调整为 {self.state.speed}x")

    def _handle_inject_event(self, params: dict[str, Any]) -> None:
        """注入随机事件到指定聚落。"""
        event_name = params.get("event_name", "")
        settlement_id = params.get("settlement_id")
        if settlement_id is None:
            return

        settlement = self.engine.settlements.get(settlement_id)
        if settlement is None:
            self.state.add_event(f"⚠ 聚落 #{settlement_id} 不存在")
            return

        self._apply_injected_event(event_name, settlement)
        self.state.add_event(
            f"🎭 注入事件 [{event_name}] → {settlement.name}"
        )

    def _apply_injected_event(
        self, event_name: str, settlement: Any,
    ) -> None:
        """将注入事件应用到聚落。"""
        if event_name == "旱灾":
            settlement.stockpile["food"] *= 0.3
        elif event_name == "瘟疫":
            loss = max(1, int(settlement.population * 0.1))
            self.engine._kill_civilians(settlement.id, loss)
        elif event_name == "丰收":
            settlement.stockpile["food"] *= 2.0
        elif event_name == "流寇":
            settlement.stockpile["gold"] *= 0.7
        elif event_name == "矿脉发现":
            settlement.stockpile["ore"] += 200

    def _handle_set_parameter(self, params: dict[str, Any]) -> None:
        """动态调整运行时参数。"""
        param_name = params.get("param_name", "")
        value = params.get("value")
        if value is None:
            return

        if param_name == "target_temperature" and self.engine.adaptive_controller:
            self.engine.adaptive_controller.config.target_temperature = float(
                value,
            )
            self.state.add_event(
                f"🌡 目标温度调整为 {value}"
            )
        elif param_name == "food_regen":
            self.config.resources.regeneration.farmland_per_tick = float(value)
            self.state.add_event(f"🌾 食物再生率 → {value}")
        elif param_name == "food_consumption":
            self.config.resources.consumption.food_per_civilian_per_tick = float(
                value,
            )
            self.state.add_event(f"🍽 食物消耗率 → {value}")

    def _handle_settlement_intervene(
        self, params: dict[str, Any],
    ) -> None:
        """聚落干预：直接修改聚落资源/参数。"""
        sid = params.get("settlement_id")
        settlement = self.engine.settlements.get(sid)
        if settlement is None:
            return

        for resource in ("food", "wood", "ore", "gold"):
            delta = params.get(f"add_{resource}", 0)
            if delta:
                settlement.stockpile[resource] = max(
                    0.0,
                    settlement.stockpile.get(resource, 0.0) + float(delta),
                )

        if "tax_rate" in params:
            settlement.tax_rate = max(
                0.0, min(1.0, float(params["tax_rate"])),
            )
        if "security_level" in params:
            settlement.security_level = max(
                0.0, min(1.0, float(params["security_level"])),
            )

        self.state.add_event(
            f"🏛 干预聚落 {settlement.name}: {params}"
        )

    def _handle_force_diplomacy(self, params: dict[str, Any]) -> None:
        """强制外交操作。"""
        if not self.engine.diplomacy:
            self.state.add_event("⚠ 外交系统未启用")
            return

        from civsim.politics.diplomacy import DiplomaticStatus

        faction_a = params.get("faction_a")
        faction_b = params.get("faction_b")
        new_status = params.get("status", "")

        status_map = {s.name: s for s in DiplomaticStatus}
        status = status_map.get(new_status.upper())
        if status is None:
            self.state.add_event(f"⚠ 无效的外交状态: {new_status}")
            return

        self.engine.diplomacy.set_relation(
            faction_a, faction_b, status, tick=self.engine.clock.tick,
        )
        self.state.add_event(
            f"🤝 强制外交: 阵营{faction_a} ↔ 阵营{faction_b} → {new_status}"
        )

    def _handle_replace_leader(self, params: dict[str, Any]) -> None:
        """替换指定阵营的首领。"""
        self.state.add_event("🔄 首领替换（功能预留）")

    def _handle_apply_scenario(self, params: dict[str, Any]) -> None:
        """应用场景预设。"""
        from civsim.dashboard.scenarios import apply_scenario

        key = params.get("scenario_key", "")
        logs = apply_scenario(self.engine, key)
        for msg in logs:
            self.state.add_event(msg)
        # 应用后立即更新快照，使 UI 立即反映变化
        self.state.update_from_engine(self.engine)


# 操作类型 → 处理器映射
_GOD_ACTION_HANDLERS: dict = {
    GodAction.PAUSE: SimulationRunner._handle_pause,
    GodAction.RESUME: SimulationRunner._handle_resume,
    GodAction.STEP: SimulationRunner._handle_step,
    GodAction.SET_SPEED: SimulationRunner._handle_set_speed,
    GodAction.INJECT_EVENT: SimulationRunner._handle_inject_event,
    GodAction.SET_PARAMETER: SimulationRunner._handle_set_parameter,
    GodAction.SETTLEMENT_INTERVENE: SimulationRunner._handle_settlement_intervene,
    GodAction.FORCE_DIPLOMACY: SimulationRunner._handle_force_diplomacy,
    GodAction.REPLACE_LEADER: SimulationRunner._handle_replace_leader,
    GodAction.APPLY_SCENARIO: SimulationRunner._handle_apply_scenario,
}
