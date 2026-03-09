"""Mesa DataCollector 扩展。

采集全局指标：各状态人数、资源总量、满意度分布、抗议率、
贸易量、外交关系数、革命次数。
"""

import mesa
import numpy as np

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.civilian import Civilian


def count_state(model: mesa.Model, state: CivilianState) -> int:
    """统计处于某状态的平民数量。"""
    return sum(
        1 for a in model.agents
        if isinstance(a, Civilian) and a.state == state
    )


def total_resource(model: mesa.Model, resource: str) -> float:
    """统计所有聚落某资源的总量。"""
    if not hasattr(model, "settlements"):
        return 0.0
    return sum(s.stockpile.get(resource, 0.0) for s in model.settlements.values())


def avg_satisfaction(model: mesa.Model) -> float:
    """全体平民平均满意度。"""
    civilians = [a for a in model.agents if isinstance(a, Civilian)]
    if not civilians:
        return 0.0
    return float(np.mean([c.satisfaction for c in civilians]))


def protest_ratio(model: mesa.Model) -> float:
    """全局抗议率。"""
    civilians = [a for a in model.agents if isinstance(a, Civilian)]
    if not civilians:
        return 0.0
    protesting = sum(1 for c in civilians if c.state == CivilianState.PROTESTING)
    return protesting / len(civilians)


def total_population(model: mesa.Model) -> int:
    """全部平民总数。"""
    return sum(1 for a in model.agents if isinstance(a, Civilian))


def avg_hunger(model: mesa.Model) -> float:
    """全体平民平均饥饿度。"""
    civilians = [a for a in model.agents if isinstance(a, Civilian)]
    if not civilians:
        return 0.0
    return float(np.mean([c.hunger for c in civilians]))


def trade_volume(model: mesa.Model) -> float:
    """当前总贸易量。"""
    tm = getattr(model, "trade_manager", None)
    if tm is not None:
        return tm.total_volume
    return 0.0


def alliance_count(model: mesa.Model) -> int:
    """当前联盟数量。"""
    dm = getattr(model, "diplomacy", None)
    if dm is None:
        return 0
    relations = getattr(dm, "_relations", {})
    return sum(1 for s in relations.values() if int(s) >= 4)


def war_count(model: mesa.Model) -> int:
    """当前战争数量。"""
    dm = getattr(model, "diplomacy", None)
    if dm is None:
        return 0
    relations = getattr(dm, "_relations", {})
    return sum(1 for s in relations.values() if int(s) == 0)


def revolution_count(model: mesa.Model) -> int:
    """累计革命次数。"""
    rt = getattr(model, "revolution_tracker", None)
    if rt is not None:
        return rt.revolution_count
    return 0


def faction_count(model: mesa.Model) -> int:
    """当前阵营数量。"""
    leaders = getattr(model, "leaders", None)
    if leaders is not None:
        return len(leaders)
    return 0


def create_datacollector() -> mesa.DataCollector:
    """创建标准的 DataCollector 实例。

    Returns:
        配置好所有模型级和 Agent 级指标的 DataCollector。
    """
    return mesa.DataCollector(
        model_reporters={
            "total_population": total_population,
            "working_count": lambda m: count_state(m, CivilianState.WORKING),
            "resting_count": lambda m: count_state(m, CivilianState.RESTING),
            "trading_count": lambda m: count_state(m, CivilianState.TRADING),
            "socializing_count": lambda m: count_state(m, CivilianState.SOCIALIZING),
            "migrating_count": lambda m: count_state(m, CivilianState.MIGRATING),
            "protesting_count": lambda m: count_state(m, CivilianState.PROTESTING),
            "fighting_count": lambda m: count_state(m, CivilianState.FIGHTING),
            "total_food": lambda m: total_resource(m, "food"),
            "total_wood": lambda m: total_resource(m, "wood"),
            "total_ore": lambda m: total_resource(m, "ore"),
            "total_gold": lambda m: total_resource(m, "gold"),
            "avg_satisfaction": avg_satisfaction,
            "avg_hunger": avg_hunger,
            "protest_ratio": protest_ratio,
            "trade_volume": trade_volume,
            "alliance_count": alliance_count,
            "war_count": war_count,
            "revolution_count": revolution_count,
            "faction_count": faction_count,
        },
        agent_reporters={
            "state": lambda a: a.state.value if isinstance(a, Civilian) else None,
            "hunger": lambda a: a.hunger if isinstance(a, Civilian) else None,
            "satisfaction": lambda a: (
                a.satisfaction if isinstance(a, Civilian) else None
            ),
        },
    )
