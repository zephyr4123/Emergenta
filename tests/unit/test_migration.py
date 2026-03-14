"""迁徙与聚落再分配行为的单元测试。"""

import numpy as np
import pytest

from civsim.agents.behaviors.migration import (
    _manhattan_distance,
    _random_neighbor,
    _step_toward,
    find_directed_target,
    pick_migration_cell,
    settlement_attractiveness,
    try_reassign_settlement,
)
from civsim.config_params_ext import MigrationParamsConfig
from civsim.economy.settlement import Settlement
from civsim.world.tiles import Tile, TileType


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


def _make_settlement(
    sid: int,
    pos: tuple[int, int],
    population: int = 100,
    food: float = 500.0,
    capacity: int = 500,
) -> Settlement:
    """创建测试用聚落。"""
    return Settlement(
        id=sid,
        name=f"S{sid}",
        position=pos,
        population=population,
        capacity=capacity,
        stockpile={"food": food, "wood": 100.0, "ore": 50.0, "gold": 50.0},
    )


def _make_tile(
    pos: tuple[int, int],
    owner_sid: int | None = None,
) -> Tile:
    """创建测试用地块。"""
    return Tile(
        tile_type=TileType.FARMLAND,
        position=pos,
        elevation=0.3,
        moisture=0.4,
    )


def _make_tile_grid(
    width: int,
    height: int,
    owner_map: dict[tuple[int, int], int] | None = None,
) -> list[list[Tile]]:
    """创建 width x height 的地块网格。"""
    grid: list[list[Tile]] = []
    for x in range(width):
        col: list[Tile] = []
        for y in range(height):
            tile = _make_tile((x, y))
            if owner_map and (x, y) in owner_map:
                tile.owner_settlement_id = owner_map[(x, y)]
            col.append(tile)
        grid.append(col)
    return grid


# ------------------------------------------------------------------
# settlement_attractiveness
# ------------------------------------------------------------------


class TestSettlementAttractiveness:
    """聚落吸引力计算测试。"""

    def test_high_food_high_capacity(self) -> None:
        """食物充裕且容量富余 → 吸引力接近 1.0。"""
        s = _make_settlement(1, (10, 10), population=50, food=1000.0, capacity=500)
        score = settlement_attractiveness(s)
        assert score > 0.7

    def test_starving_settlement(self) -> None:
        """食物为零 → 吸引力很低。"""
        s = _make_settlement(1, (10, 10), population=100, food=0.0)
        score = settlement_attractiveness(s)
        assert score < 0.4

    def test_full_capacity(self) -> None:
        """人口满载 → 容量分项为 0，拉低吸引力。"""
        s = _make_settlement(1, (10, 10), population=500, food=500.0, capacity=500)
        score = settlement_attractiveness(s)
        # 只有食物分项贡献
        s2 = _make_settlement(2, (10, 10), population=100, food=500.0, capacity=500)
        assert score < settlement_attractiveness(s2)

    def test_empty_settlement_with_food(self) -> None:
        """空聚落有库存食物 → 仍有一定吸引力。"""
        s = _make_settlement(1, (10, 10), population=0, food=200.0)
        score = settlement_attractiveness(s)
        assert score > 0.0

    def test_empty_settlement_no_food(self) -> None:
        """空聚落无食物 → 仅有容量分项。"""
        s = _make_settlement(1, (10, 10), population=0, food=0.0)
        score = settlement_attractiveness(s)
        assert 0.0 <= score <= 1.0


# ------------------------------------------------------------------
# find_directed_target
# ------------------------------------------------------------------


class TestFindDirectedTarget:
    """定向迁徙目标搜索测试。"""

    def test_finds_nearest_good_settlement(self) -> None:
        """应找到搜索半径内吸引力最高的聚落。"""
        params = MigrationParamsConfig(directed_search_radius=20)
        settlements = {
            1: _make_settlement(1, (5, 5), population=50, food=1000.0),
            2: _make_settlement(2, (15, 15), population=50, food=500.0),
            3: _make_settlement(3, (50, 50), population=50, food=2000.0),  # 太远
        }
        target = find_directed_target((10, 10), settlements, params, exclude_sid=None)
        assert target is not None
        # 应该找到 sid=1（更近且食物更多）或 sid=2
        assert target in [(5, 5), (15, 15)]

    def test_excludes_home_settlement(self) -> None:
        """应排除当前归属聚落。"""
        params = MigrationParamsConfig(directed_search_radius=20)
        settlements = {
            1: _make_settlement(1, (5, 5), population=50, food=1000.0),
        }
        target = find_directed_target((6, 6), settlements, params, exclude_sid=1)
        assert target is None

    def test_no_target_in_range(self) -> None:
        """搜索半径内无聚落 → 返回 None。"""
        params = MigrationParamsConfig(directed_search_radius=5)
        settlements = {
            1: _make_settlement(1, (50, 50), population=50, food=1000.0),
        }
        target = find_directed_target((0, 0), settlements, params, exclude_sid=None)
        assert target is None


# ------------------------------------------------------------------
# pick_migration_cell
# ------------------------------------------------------------------


class TestPickMigrationCell:
    """迁徙坐标选择测试。"""

    def test_directed_when_hungry(self) -> None:
        """饥饿度超阈值时应朝目标聚落方向移动。"""
        params = MigrationParamsConfig(
            directed_hunger_threshold=0.5, directed_search_radius=20,
        )
        rng = np.random.default_rng(42)
        settlements = {
            1: _make_settlement(1, (0, 0), population=50, food=100.0),
            2: _make_settlement(2, (10, 10), population=50, food=1000.0),
        }
        new_pos = pick_migration_cell(
            pos=(5, 5), grid_width=20, grid_height=20,
            hunger=0.8, settlements=settlements,
            params=params, home_settlement_id=1, rng=rng,
        )
        # 应朝 (10, 10) 方向移动，即 x+1, y+1
        assert new_pos == (6, 6)

    def test_random_when_not_hungry(self) -> None:
        """饥饿度低时随机游走。"""
        params = MigrationParamsConfig(directed_hunger_threshold=0.5)
        rng = np.random.default_rng(42)
        settlements = {
            1: _make_settlement(1, (0, 0), population=50, food=100.0),
        }
        new_pos = pick_migration_cell(
            pos=(5, 5), grid_width=20, grid_height=20,
            hunger=0.1, settlements=settlements,
            params=params, home_settlement_id=1, rng=rng,
        )
        # 应在 (5,5) 的 Moore 邻域内
        assert abs(new_pos[0] - 5) <= 1
        assert abs(new_pos[1] - 5) <= 1

    def test_boundary_clamping(self) -> None:
        """网格边界坐标应被钳制。"""
        params = MigrationParamsConfig(directed_hunger_threshold=0.5)
        rng = np.random.default_rng(42)
        new_pos = pick_migration_cell(
            pos=(0, 0), grid_width=10, grid_height=10,
            hunger=0.1, settlements={}, params=params,
            home_settlement_id=1, rng=rng,
        )
        assert new_pos[0] >= 0 and new_pos[1] >= 0


# ------------------------------------------------------------------
# try_reassign_settlement
# ------------------------------------------------------------------


class TestTryReassignSettlement:
    """聚落再分配测试。"""

    def test_reassign_on_foreign_tile(self) -> None:
        """踏入他方领地，家乡稀缺 → 大概率切换。"""
        params = MigrationParamsConfig(
            reassignment_base_prob=1.0,  # 确保触发
            scarcity_push_weight=1.5,
            food_pull_weight=1.0,
        )
        rng = np.random.default_rng(42)
        tile_grid = _make_tile_grid(10, 10, {(5, 5): 2})
        settlements = {
            1: _make_settlement(1, (0, 0), population=100, food=0.0),  # 家乡无食物
            2: _make_settlement(2, (5, 5), population=50, food=1000.0),
        }
        result = try_reassign_settlement(
            pos=(5, 5), tile_grid=tile_grid,
            home_settlement_id=1, settlements=settlements,
            params=params, rng=rng,
        )
        assert result == 2

    def test_no_reassign_on_own_tile(self) -> None:
        """在自己领地 → 不切换。"""
        params = MigrationParamsConfig()
        rng = np.random.default_rng(42)
        tile_grid = _make_tile_grid(10, 10, {(5, 5): 1})
        settlements = {
            1: _make_settlement(1, (5, 5), population=100, food=500.0),
        }
        result = try_reassign_settlement(
            pos=(5, 5), tile_grid=tile_grid,
            home_settlement_id=1, settlements=settlements,
            params=params, rng=rng,
        )
        assert result is None

    def test_no_reassign_on_unowned_tile(self) -> None:
        """无主地块 → 不切换。"""
        params = MigrationParamsConfig()
        rng = np.random.default_rng(42)
        tile_grid = _make_tile_grid(10, 10)  # 所有地块无主
        settlements = {
            1: _make_settlement(1, (0, 0), population=100, food=500.0),
        }
        result = try_reassign_settlement(
            pos=(5, 5), tile_grid=tile_grid,
            home_settlement_id=1, settlements=settlements,
            params=params, rng=rng,
        )
        assert result is None

    def test_low_prob_may_not_reassign(self) -> None:
        """基础概率为 0 → 绝不切换。"""
        params = MigrationParamsConfig(reassignment_base_prob=0.0)
        rng = np.random.default_rng(42)
        tile_grid = _make_tile_grid(10, 10, {(5, 5): 2})
        settlements = {
            1: _make_settlement(1, (0, 0), population=100, food=0.0),
            2: _make_settlement(2, (5, 5), population=50, food=1000.0),
        }
        result = try_reassign_settlement(
            pos=(5, 5), tile_grid=tile_grid,
            home_settlement_id=1, settlements=settlements,
            params=params, rng=rng,
        )
        assert result is None

    def test_out_of_bounds(self) -> None:
        """越界坐标 → 返回 None。"""
        params = MigrationParamsConfig()
        rng = np.random.default_rng(42)
        tile_grid = _make_tile_grid(10, 10)
        result = try_reassign_settlement(
            pos=(99, 99), tile_grid=tile_grid,
            home_settlement_id=1, settlements={},
            params=params, rng=rng,
        )
        assert result is None


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------


class TestUtilities:
    """工具函数测试。"""

    def test_manhattan_distance(self) -> None:
        """曼哈顿距离计算。"""
        assert _manhattan_distance((0, 0), (3, 4)) == 7
        assert _manhattan_distance((5, 5), (5, 5)) == 0

    def test_step_toward(self) -> None:
        """朝目标移动一步。"""
        assert _step_toward((5, 5), (10, 10), 20, 20) == (6, 6)
        assert _step_toward((5, 5), (5, 10), 20, 20) == (5, 6)
        assert _step_toward((5, 5), (0, 0), 20, 20) == (4, 4)

    def test_step_toward_boundary(self) -> None:
        """边界处不越界。"""
        assert _step_toward((0, 0), (-1, -1), 10, 10) == (0, 0)
        assert _step_toward((9, 9), (20, 20), 10, 10) == (9, 9)

    def test_random_neighbor_in_bounds(self) -> None:
        """随机邻居始终在网格内。"""
        rng = np.random.default_rng(42)
        for _ in range(100):
            pos = _random_neighbor((0, 0), 10, 10, rng)
            assert 0 <= pos[0] < 10
            assert 0 <= pos[1] < 10
