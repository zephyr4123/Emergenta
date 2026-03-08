"""Mesa DataCollector 扩展。

采集全局指标：各状态人数、资源总量、满意度分布、抗议率。
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
        },
        agent_reporters={
            "state": lambda a: a.state.value if isinstance(a, Civilian) else None,
            "hunger": lambda a: a.hunger if isinstance(a, Civilian) else None,
            "satisfaction": lambda a: (
                a.satisfaction if isinstance(a, Civilian) else None
            ),
        },
    )
