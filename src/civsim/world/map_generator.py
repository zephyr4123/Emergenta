"""Perlin Noise 地图生成器。

使用 Perlin Noise 生成海拔和湿度图，
再根据阈值分类为不同地块类型，最后放置聚落。
"""

import random

import numpy as np
from noise import pnoise2

from civsim.economy.settlement import Settlement
from civsim.world.tiles import Tile, TileType, classify_tile


def generate_elevation_moisture(
    width: int,
    height: int,
    elevation_scale: float = 20.0,
    moisture_scale: float = 15.0,
    octaves: int = 6,
    persistence: float = 0.5,
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """生成海拔和湿度的 Perlin Noise 图。

    Args:
        width: 地图宽度。
        height: 地图高度。
        elevation_scale: 海拔噪声缩放。
        moisture_scale: 湿度噪声缩放。
        octaves: 噪声叠加层数。
        persistence: 噪声衰减率。
        seed: 随机种子。

    Returns:
        (elevation, moisture) 两个归一化到 [0, 1] 的二维数组。
    """
    if seed is None:
        seed = random.randint(0, 99999)

    elevation = np.zeros((width, height))
    moisture = np.zeros((width, height))

    for x in range(width):
        for y in range(height):
            elevation[x][y] = pnoise2(
                x / elevation_scale,
                y / elevation_scale,
                octaves=octaves,
                persistence=persistence,
                base=seed,
            )
            moisture[x][y] = pnoise2(
                x / moisture_scale,
                y / moisture_scale,
                octaves=octaves,
                persistence=persistence,
                base=seed + 1,
            )

    # 归一化到 [0, 1]
    elevation = _normalize(elevation)
    moisture = _normalize(moisture)

    return elevation, moisture


def _normalize(arr: np.ndarray) -> np.ndarray:
    """将数组归一化到 [0, 1]。"""
    min_val = arr.min()
    max_val = arr.max()
    if max_val - min_val < 1e-10:
        return np.full_like(arr, 0.5)
    return (arr - min_val) / (max_val - min_val)


def generate_tile_grid(
    width: int,
    height: int,
    elevation: np.ndarray,
    moisture: np.ndarray,
    thresholds: dict[str, float],
) -> list[list[Tile]]:
    """根据海拔/湿度生成地块网格。

    Args:
        width: 地图宽度。
        height: 地图高度。
        elevation: 海拔数组。
        moisture: 湿度数组。
        thresholds: 地块分类阈值。

    Returns:
        二维 Tile 列表 [x][y]。
    """
    grid: list[list[Tile]] = []
    for x in range(width):
        col: list[Tile] = []
        for y in range(height):
            tile_type = classify_tile(elevation[x][y], moisture[x][y], thresholds)
            tile = Tile(
                tile_type=tile_type,
                position=(x, y),
                elevation=elevation[x][y],
                moisture=moisture[x][y],
            )
            col.append(tile)
        grid.append(col)
    return grid


def suitability_score(
    x: int,
    y: int,
    width: int,
    height: int,
    elevation: np.ndarray,
    tile_grid: list[list[Tile]],
    radius: int = 5,
) -> float:
    """计算某坐标的聚落适宜度评分。

    Args:
        x: x 坐标。
        y: y 坐标。
        width: 地图宽度。
        height: 地图高度。
        elevation: 海拔数组。
        tile_grid: 地块网格。
        radius: 评估半径。

    Returns:
        适宜度评分 [0, 1]。
    """
    # 该位置本身不能是水域或山地
    center_tile = tile_grid[x][y]
    if center_tile.tile_type in (TileType.WATER, TileType.MOUNTAIN):
        return 0.0

    score = 0.0
    count = 0
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height:
                count += 1
                tt = tile_grid[nx][ny].tile_type
                if tt == TileType.FARMLAND:
                    score += 0.3
                elif tt == TileType.WATER:
                    score += 0.4
                elif tt == TileType.FOREST:
                    score += 0.1

    # 平坦加分
    score += (1.0 - abs(elevation[x][y] - 0.3)) * 0.5

    if count == 0:
        return 0.0
    return score / count


def place_settlements(
    tile_grid: list[list[Tile]],
    elevation: np.ndarray,
    width: int,
    height: int,
    count: int = 8,
    min_score: float = 0.6,
    min_distance: int = 10,
) -> list[Settlement]:
    """在地图上放置聚落。

    贪心策略：按适宜度降序选点，保证聚落间最小距离。

    Args:
        tile_grid: 地块网格。
        elevation: 海拔数组。
        width: 地图宽度。
        height: 地图高度。
        count: 目标聚落数。
        min_score: 最低适宜度阈值。
        min_distance: 聚落间最小曼哈顿距离。

    Returns:
        生成的聚落列表。
    """
    # 计算所有位置的适宜度
    scores: list[tuple[float, int, int]] = []
    for x in range(width):
        for y in range(height):
            s = suitability_score(x, y, width, height, elevation, tile_grid)
            if s >= min_score:
                scores.append((s, x, y))

    scores.sort(reverse=True)

    settlements: list[Settlement] = []
    placed_positions: list[tuple[int, int]] = []

    for _s, x, y in scores:
        if len(settlements) >= count:
            break
        # 检查距离约束
        too_close = False
        for px, py in placed_positions:
            if abs(x - px) + abs(y - py) < min_distance:
                too_close = True
                break
        if too_close:
            continue

        sid = len(settlements)
        settlement = Settlement(
            id=sid,
            name=f"聚落_{sid}",
            position=(x, y),
        )
        settlements.append(settlement)
        placed_positions.append((x, y))

        # 将该地块标记为聚落类型
        tile_grid[x][y].tile_type = TileType.SETTLEMENT
        tile_grid[x][y].owner_settlement_id = sid

        # 分配周围领地
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                nx, ny = x + dx, y + dy
                if (
                    0 <= nx < width
                    and 0 <= ny < height
                    and tile_grid[nx][ny].owner_settlement_id is None
                ):
                        tile_grid[nx][ny].owner_settlement_id = sid
                        settlement.territory_tiles.append((nx, ny))

    return settlements
