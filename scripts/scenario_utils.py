"""场景测试脚本共享工具模块。

提供 SimLog、统计采集、缩放计算等通用功能，
避免各场景脚本之间的代码重复。
"""

import sys
from dataclasses import dataclass, field

import numpy as np

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.civilian import Civilian
from civsim.agents.governor import Governor

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class SimLog:
    """模拟日志收集器。"""

    lines: list[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        """输出并记录一行日志。"""
        self.lines.append(msg)
        print(msg)
        sys.stdout.flush()


def compute_scaling(n_agents: int) -> dict:
    """根据平民数量计算各层级规模。

    Args:
        n_agents: 平民总数。

    Returns:
        包含 settlements、leaders、grid 的字典。
    """
    settlements = max(4, n_agents // 80)
    leaders = max(2, settlements // 3)
    grid = max(30, int(np.sqrt(n_agents) * 2.5))
    grid = min(grid, 200)
    return {
        "settlements": settlements,
        "leaders": leaders,
        "grid": grid,
    }


def snapshot_settlement(s) -> dict:
    """获取单个聚落快照。"""
    return {
        "id": s.id,
        "name": s.name,
        "population": s.population,
        "food": s.stockpile.get("food", 0),
        "wood": s.stockpile.get("wood", 0),
        "ore": s.stockpile.get("ore", 0),
        "gold": s.stockpile.get("gold", 0),
        "tax_rate": s.tax_rate,
        "security_level": s.security_level,
    }


def get_civilians_stats(engine, settlement_id: int) -> dict:
    """获取某聚落的平民统计。"""
    civs = [
        a for a in engine.agents
        if isinstance(a, Civilian) and a.home_settlement_id == settlement_id
    ]
    if not civs:
        return {"count": 0, "avg_sat": 0, "protest_ratio": 0, "states": {}}

    states: dict[str, int] = {}
    for c in civs:
        st = c.state.value if hasattr(c.state, "value") else str(c.state)
        states[st] = states.get(st, 0) + 1

    protest = sum(1 for c in civs if c.state == CivilianState.PROTESTING)
    return {
        "count": len(civs),
        "avg_sat": float(np.mean([c.satisfaction for c in civs])),
        "protest_ratio": protest / len(civs),
        "states": states,
    }


def get_global_stats(engine) -> dict:
    """获取全局统计。"""
    civs = [a for a in engine.agents if isinstance(a, Civilian)]
    sats = [c.satisfaction for c in civs] if civs else [0.5]

    trade_vol = engine.trade_manager.total_volume if engine.trade_manager else 0
    trade_cnt = engine.trade_manager.trade_count if engine.trade_manager else 0
    rev_cnt = (
        engine.revolution_tracker.revolution_count
        if engine.revolution_tracker else 0
    )

    alliance_cnt = war_cnt = 0
    if engine.diplomacy:
        for status in getattr(engine.diplomacy, "_relations", {}).values():
            sv = int(status)
            if sv >= 4:
                alliance_cnt += 1
            elif sv == 0:
                war_cnt += 1

    gov_decisions = sum(
        g.decision_count for g in engine.agents if isinstance(g, Governor)
    )
    leader_decisions = sum(l.decision_count for l in engine.leaders)

    adaptive_info = {}
    ctrl = getattr(engine, "adaptive_controller", None)
    if ctrl is not None:
        adaptive_info["temperature"] = (
            ctrl.temperature_history[-1][1]
            if ctrl.temperature_history else 0.0
        )
        adaptive_info["protest_mult"] = (
            ctrl.coefficients.markov_protest_multiplier
        )
        adaptive_info["granovetter_mult"] = (
            ctrl.coefficients.granovetter_burst_multiplier
        )
        adaptive_info["cooldown_mult"] = (
            ctrl.coefficients.revolution_cooldown_multiplier
        )
        adaptive_info["recovery_mult"] = (
            ctrl.coefficients.satisfaction_recovery_multiplier
        )
        adaptive_info["event_mult"] = (
            ctrl.coefficients.random_event_multiplier
        )

    active_recoveries = 0
    if engine.revolution_tracker:
        active_recoveries = len(engine.revolution_tracker.active_recoveries)

    return {
        "total_civilians": len(civs),
        "avg_satisfaction": float(np.mean(sats)),
        "trade_volume": trade_vol,
        "trade_count": trade_cnt,
        "revolution_count": rev_cnt,
        "alliance_count": alliance_cnt,
        "war_count": war_cnt,
        "governor_decisions": gov_decisions,
        "leader_decisions": leader_decisions,
        "adaptive": adaptive_info,
        "active_recoveries": active_recoveries,
    }


def get_memory_mb() -> float:
    """获取当前进程内存占用 (MB)，无 psutil 则返回 0。"""
    if PSUTIL_AVAILABLE:
        return psutil.Process().memory_info().rss / 1024 / 1024
    return 0.0


def get_active_llm_model(config) -> str:
    """从配置中获取当前使用的 LLM 模型名称。"""
    try:
        gov_model = config.llm.models.get("governor")
        if gov_model:
            return gov_model.model
    except (AttributeError, KeyError):
        pass
    return "unknown"


def log_system_info(
    sim: SimLog,
    engine,
    config,
    governors: list,
) -> None:
    """输出系统完整性验证信息。"""
    actual_civilians = sum(
        1 for a in engine.agents if isinstance(a, Civilian)
    )
    sim.log(f"  实际平民: {actual_civilians}")
    sim.log(f"  实际镇长: {len(governors)} (真实 LLM)")
    sim.log(f"  实际首领: {len(engine.leaders)} (真实 LLM)")
    sim.log(f"  实际聚落: {len(engine.settlements)}")
    sim.log(
        f"  贸易系统: {'启用' if engine.trade_manager else '关闭'}"
    )
    sim.log(
        f"  外交系统: {'启用' if engine.diplomacy else '关闭'}"
    )
    sim.log(
        f"  革命系统: {'启用' if engine.revolution_tracker else '关闭'}"
    )
    sim.log(
        f"  自适应控制器: "
        f"{'启用' if engine.adaptive_controller else '关闭'}"
    )
    if engine.adaptive_controller:
        ac = config.adaptive_controller
        sim.log(f"    目标温度: {ac.target_temperature}")
        sim.log(f"    调节速率: {ac.adjustment_rate}")
        sim.log(f"    更新间隔: {ac.update_interval} ticks")

    has_llm = engine.llm_gateway is not None
    llm_model = get_active_llm_model(config)
    sim.log(f"  LLM网关: {'已连接' if has_llm else '未连接'}")
    sim.log(f"  LLM模型: {llm_model}")
    if has_llm:
        gov_llm_active = sum(
            1 for g in governors if g._gateway is not None
        )
        leader_llm_active = sum(
            1 for l in engine.leaders if l._gateway is not None
        )
        sim.log(
            f"    镇长 LLM 激活: {gov_llm_active}/{len(governors)}"
        )
        sim.log(
            f"    首领 LLM 激活: "
            f"{leader_llm_active}/{len(engine.leaders)}"
        )


def count_wars(engine) -> int:
    """统计当前活跃战争数。"""
    war_cnt = 0
    if engine.diplomacy:
        for status in getattr(
            engine.diplomacy, "_relations", {},
        ).values():
            if int(status) == 0:
                war_cnt += 1
    return war_cnt
