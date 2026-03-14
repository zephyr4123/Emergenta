"""迁徙与聚落再分配行为模块。

提供定向迁徙（饥饿时朝食物充裕聚落移动）和
聚落再分配（踏入他方领地时概率性加入新聚落）的纯函数。
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.random import Generator

    from civsim.config_params_ext import MigrationParamsConfig
    from civsim.economy.settlement import Settlement
    from civsim.world.tiles import Tile


def settlement_attractiveness(settlement: Settlement) -> float:
    """计算聚落对迁徙者的吸引力 [0, 1]。

    基于人均食物（相对于稀缺阈值）和剩余容量比例。
    零人口聚落用库存食物 / 基线阈值作近似，避免极端值。

    Args:
        settlement: 目标聚落。

    Returns:
        吸引力评分 [0, 1]。
    """
    from civsim.config_params_ext import SettlementParamsConfig

    params = settlement._settlement_params or SettlementParamsConfig()
    threshold = params.scarcity_full_threshold

    if settlement.population <= 0:
        # 空聚落：按库存食物 / 基线计算近似吸引力
        food = settlement.stockpile.get("food", 0.0)
        food_score = min(1.0, food / max(threshold, 1.0))
    else:
        food_score = min(1.0, settlement.per_capita_food / max(threshold, 1.0))

    # 容量余量
    cap_ratio = max(0.0, 1.0 - settlement.population / max(settlement.capacity, 1))

    return 0.7 * food_score + 0.3 * cap_ratio


def find_directed_target(
    pos: tuple[int, int],
    settlements: dict[int, Settlement],
    params: MigrationParamsConfig,
    exclude_sid: int | None = None,
) -> tuple[int, int] | None:
    """在搜索半径内找到最佳迁徙目标聚落的位置。

    Args:
        pos: 当前位置。
        settlements: 所有聚落。
        params: 迁徙参数。
        exclude_sid: 排除的聚落 ID（当前归属）。

    Returns:
        最佳目标聚落的位置，或 None。
    """
    best_score = -1.0
    best_pos: tuple[int, int] | None = None
    radius = params.directed_search_radius

    for sid, s in settlements.items():
        if sid == exclude_sid:
            continue
        dist = _manhattan_distance(pos, s.position)
        if dist > radius or dist == 0:
            continue
        attr = settlement_attractiveness(s)
        # 距离惩罚：近距离优先
        score = attr / (1.0 + 0.1 * dist)
        if score > best_score:
            best_score = score
            best_pos = s.position

    return best_pos


def pick_migration_cell(
    pos: tuple[int, int],
    grid_width: int,
    grid_height: int,
    hunger: float,
    settlements: dict[int, Settlement],
    params: MigrationParamsConfig,
    home_settlement_id: int,
    rng: Generator,
) -> tuple[int, int]:
    """选择迁徙目标坐标。

    饥饿度超过阈值时定向朝最佳聚落移动，否则随机游走。

    Args:
        pos: 当前位置 (x, y)。
        grid_width: 网格宽度。
        grid_height: 网格高度。
        hunger: 当前饥饿度。
        settlements: 所有聚落。
        params: 迁徙参数。
        home_settlement_id: 当前归属聚落 ID。
        rng: 随机数生成器。

    Returns:
        新的目标坐标 (x, y)。
    """
    if hunger >= params.directed_hunger_threshold:
        target = find_directed_target(
            pos, settlements, params, exclude_sid=home_settlement_id,
        )
        if target is not None:
            return _step_toward(pos, target, grid_width, grid_height)

    # 随机游走
    return _random_neighbor(pos, grid_width, grid_height, rng)


def try_reassign_settlement(
    pos: tuple[int, int],
    tile_grid: list[list[Tile]],
    home_settlement_id: int,
    settlements: dict[int, Settlement],
    params: MigrationParamsConfig,
    rng: Generator,
) -> int | None:
    """踏入他方领地时概率性更换归属聚落。

    概率公式：min(1.0, base * (1 + scarcity*push) * (0.5 + attr*pull))

    Args:
        pos: 当前位置。
        tile_grid: 地图地块网格。
        home_settlement_id: 当前归属聚落 ID。
        settlements: 所有聚落。
        params: 迁徙参数。
        rng: 随机数生成器。

    Returns:
        新的聚落 ID，或 None（未切换）。
    """
    x, y = pos
    if x < 0 or y < 0:
        return None
    if x >= len(tile_grid) or y >= len(tile_grid[0]):
        return None

    tile = tile_grid[x][y]
    tile_owner = getattr(tile, "owner_settlement_id", None)

    if tile_owner is None or tile_owner == home_settlement_id:
        return None

    target = settlements.get(tile_owner)
    if target is None:
        return None

    home = settlements.get(home_settlement_id)
    if home is None:
        return tile_owner  # 家乡不存在，直接加入

    # 计算概率
    scarcity = home.scarcity_index
    attr = settlement_attractiveness(target)
    prob = min(
        1.0,
        params.reassignment_base_prob
        * (1.0 + scarcity * params.scarcity_push_weight)
        * (0.5 + attr * params.food_pull_weight),
    )

    if rng.random() < prob:
        return tile_owner

    return None


# ------------------------------------------------------------------
# 内部工具函数
# ------------------------------------------------------------------


def _manhattan_distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    """计算曼哈顿距离。"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _step_toward(
    pos: tuple[int, int],
    target: tuple[int, int],
    width: int,
    height: int,
) -> tuple[int, int]:
    """朝目标方向移动一步。"""
    dx = target[0] - pos[0]
    dy = target[1] - pos[1]
    sx = 1 if dx > 0 else (-1 if dx < 0 else 0)
    sy = 1 if dy > 0 else (-1 if dy < 0 else 0)
    nx = max(0, min(width - 1, pos[0] + sx))
    ny = max(0, min(height - 1, pos[1] + sy))
    return (nx, ny)


def _random_neighbor(
    pos: tuple[int, int],
    width: int,
    height: int,
    rng: Generator,
) -> tuple[int, int]:
    """随机选取一个相邻格子（Moore 邻域）。"""
    offsets = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1),
    ]
    idx = int(rng.integers(len(offsets)))
    dx, dy = offsets[idx]
    nx = max(0, min(width - 1, pos[0] + dx))
    ny = max(0, min(height - 1, pos[1] + dy))
    return (nx, ny)
