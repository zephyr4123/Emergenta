"""随机事件系统。

从世界引擎提取的事件触发、应用和持续效果处理逻辑。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

from civsim.config_params_ext import EventParamsConfig

if TYPE_CHECKING:
    from civsim.economy.settlement import Settlement
    from civsim.world.tiles import Tile, TileType

logger = logging.getLogger(__name__)

RANDOM_EVENTS = [
    {"name": "旱灾", "prob": 0.002, "scope": "settlement"},
    {"name": "瘟疫", "prob": 0.001, "scope": "settlement"},
    {"name": "矿脉发现", "prob": 0.003, "scope": "tile"},
    {"name": "丰收", "prob": 0.005, "scope": "settlement"},
    {"name": "流寇", "prob": 0.002, "scope": "settlement"},
]


def trigger_random_events(
    settlements: dict[int, object],
    tile_grid: list[list[object]],
    active_events: list[dict],
    rng: np.random.Generator,
    event_multiplier: float = 1.0,
    event_params: EventParamsConfig | None = None,
) -> list[dict]:
    """按概率触发随机事件。

    Args:
        settlements: 聚落字典。
        tile_grid: 地块网格。
        active_events: 当前活跃事件列表（会被原地修改）。
        rng: 随机数生成器。
        event_multiplier: 事件概率乘数（来自自适应控制器）。
        event_params: 随机事件参数配置，为 None 时使用默认值。

    Returns:
        新触发的事件列表。
    """
    event_params = event_params or EventParamsConfig()

    if not settlements:
        return []

    dynamic_events = [
        {"name": "旱灾",   "prob": event_params.drought_prob,         "scope": "settlement"},
        {"name": "瘟疫",   "prob": event_params.plague_prob,          "scope": "settlement"},
        {"name": "矿脉发现", "prob": event_params.mine_discovery_prob, "scope": "tile"},
        {"name": "丰收",   "prob": event_params.harvest_prob,         "scope": "settlement"},
        {"name": "流寇",   "prob": event_params.bandits_prob,         "scope": "settlement"},
    ]

    new_events: list[dict] = []
    sids = list(settlements.keys())
    for ev in dynamic_events:
        prob = ev["prob"] * event_multiplier
        if rng.random() < prob:
            sid = rng.choice(sids)
            settlement = settlements[sid]
            applied = apply_event(ev["name"], settlement, tile_grid, event_params=event_params)
            if applied is not None:
                new_events.append(applied)
                # 只有持续性事件（含 remaining_ticks）才加入活跃列表
                if "remaining_ticks" in applied:
                    active_events.append(applied)

    return new_events


def apply_event(
    name: str,
    settlement: object,
    tile_grid: list[list[object]],
    event_params: EventParamsConfig | None = None,
) -> dict | None:
    """应用随机事件效果。

    Args:
        name: 事件名称。
        settlement: 聚落对象。
        tile_grid: 地块网格。
        event_params: 随机事件参数配置，为 None 时使用默认值。

    Returns:
        持续事件字典（旱灾/丰收），即时事件返回 None。
    """
    from civsim.world.tiles import TileType

    event_params = event_params or EventParamsConfig()
    sid = settlement.id if hasattr(settlement, "id") else 0

    if name == "旱灾":
        if hasattr(settlement, "territory_tiles"):
            for tx, ty in settlement.territory_tiles:
                if tile_grid[tx][ty].tile_type == TileType.FARMLAND:
                    tile_grid[tx][ty].fertility *= event_params.drought_fertility_mult
        return {
            "name": "旱灾", "settlement_id": sid,
            "remaining_ticks": event_params.drought_duration,
        }
    elif name == "瘟疫":
        plague_deaths = 0
        if hasattr(settlement, "population") and settlement.population > 0:
            plague_deaths = max(
                1,
                int(settlement.population * event_params.plague_pop_loss_ratio),
            )
        return {"name": "瘟疫", "settlement_id": sid, "deaths": plague_deaths}
    elif name == "丰收":
        return {
            "name": "丰收", "settlement_id": sid,
            "remaining_ticks": event_params.harvest_duration,
        }
    elif name == "流寇":
        if hasattr(settlement, "stockpile"):
            settlement.stockpile["gold"] *= event_params.bandits_gold_mult
        if hasattr(settlement, "security_level"):
            settlement.security_level = max(
                0.0, settlement.security_level - event_params.bandits_security_loss
            )
        return None

    return None


def process_active_events(
    active_events: list[dict],
    settlements: dict[int, object],
    event_params: EventParamsConfig | None = None,
) -> list[dict]:
    """处理持续中的事件，返回仍活跃的事件列表。

    Args:
        active_events: 当前活跃事件列表。
        settlements: 聚落字典。
        event_params: 随机事件参数配置，为 None 时使用默认值。

    Returns:
        仍活跃的事件列表。
    """
    event_params = event_params or EventParamsConfig()
    remaining = []
    for ev in active_events:
        ev["remaining_ticks"] -= 1
        if ev["remaining_ticks"] > 0:
            if ev["name"] == "丰收":
                s = settlements.get(ev["settlement_id"])
                if s and hasattr(s, "deposit"):
                    s.deposit({"food": event_params.harvest_food_bonus})
            remaining.append(ev)
    return remaining
