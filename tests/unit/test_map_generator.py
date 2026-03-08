"""map_generator.py 单元测试。

验证 Perlin Noise 地图生成器的海拔/湿度输出、
地块网格生成、聚落适宜度评分和聚落放置逻辑。
使用小尺寸地图 (20x20) 加速测试。
"""

import numpy as np
import pytest

from civsim.economy.settlement import Settlement
from civsim.world.map_generator import (
    generate_elevation_moisture,
    generate_tile_grid,
    place_settlements,
    suitability_score,
)
from civsim.world.tiles import Tile, TileType

# 测试用默认阈值
_DEFAULT_THRESHOLDS: dict[str, float] = {
    "mountain_elevation": 0.70,
    "water_moisture": 0.60,
    "forest_elevation": 0.50,
    "farmland_moisture": 0.30,
}


class TestGenerateElevationMoisture:
    """测试 generate_elevation_moisture 函数。"""

    def test_output_shape(self) -> None:
        """验证输出数组形状与指定的宽高一致。"""
        width, height = 20, 20
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        assert elev.shape == (width, height)
        assert moist.shape == (width, height)

    def test_output_shape_rectangular(self) -> None:
        """验证非正方形地图输出形状正确。"""
        width, height = 15, 25
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        assert elev.shape == (width, height)
        assert moist.shape == (width, height)

    def test_output_range_zero_to_one(self) -> None:
        """验证输出值被归一化到 [0, 1] 范围。"""
        elev, moist = generate_elevation_moisture(20, 20, seed=42)
        assert elev.min() >= 0.0
        assert elev.max() <= 1.0
        assert moist.min() >= 0.0
        assert moist.max() <= 1.0

    def test_output_uses_full_range(self) -> None:
        """验证归一化后最小值为 0、最大值为 1。"""
        elev, moist = generate_elevation_moisture(20, 20, seed=42)
        assert elev.min() == pytest.approx(0.0, abs=1e-9)
        assert elev.max() == pytest.approx(1.0, abs=1e-9)
        assert moist.min() == pytest.approx(0.0, abs=1e-9)
        assert moist.max() == pytest.approx(1.0, abs=1e-9)

    def test_same_seed_produces_same_result(self) -> None:
        """验证相同种子生成完全相同的地图。"""
        e1, m1 = generate_elevation_moisture(20, 20, seed=123)
        e2, m2 = generate_elevation_moisture(20, 20, seed=123)
        np.testing.assert_array_equal(e1, e2)
        np.testing.assert_array_equal(m1, m2)

    def test_different_seed_produces_different_result(self) -> None:
        """验证不同种子生成不同的地图。"""
        e1, m1 = generate_elevation_moisture(20, 20, seed=100)
        e2, m2 = generate_elevation_moisture(20, 20, seed=200)
        assert not np.array_equal(e1, e2)

    def test_elevation_and_moisture_differ(self) -> None:
        """验证海拔和湿度使用不同的 noise base，结果不同。"""
        elev, moist = generate_elevation_moisture(20, 20, seed=42)
        assert not np.array_equal(elev, moist)

    def test_none_seed_does_not_crash(self) -> None:
        """验证 seed=None 时正常运行（使用随机种子）。"""
        elev, moist = generate_elevation_moisture(20, 20, seed=None)
        assert elev.shape == (20, 20)
        assert moist.shape == (20, 20)


class TestGenerateTileGrid:
    """测试 generate_tile_grid 函数。"""

    def test_grid_dimensions(self) -> None:
        """验证生成的地块网格尺寸正确。"""
        width, height = 20, 20
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        assert len(grid) == width
        assert all(len(col) == height for col in grid)

    def test_grid_dimensions_rectangular(self) -> None:
        """验证非正方形地图的地块网格尺寸正确。"""
        width, height = 10, 15
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        assert len(grid) == width
        assert all(len(col) == height for col in grid)

    def test_all_elements_are_tiles(self) -> None:
        """验证网格中每个元素都是 Tile 实例。"""
        width, height = 20, 20
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        for x in range(width):
            for y in range(height):
                assert isinstance(grid[x][y], Tile)

    def test_tile_positions_correct(self) -> None:
        """验证每个 Tile 的 position 属性与其网格坐标一致。"""
        width, height = 10, 10
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        for x in range(width):
            for y in range(height):
                assert grid[x][y].position == (x, y)

    def test_tile_types_are_valid(self) -> None:
        """验证所有地块类型都属于 TileType 枚举。"""
        width, height = 20, 20
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        for x in range(width):
            for y in range(height):
                assert grid[x][y].tile_type in TileType

    def test_high_elevation_becomes_mountain(self) -> None:
        """验证高海拔区域被分类为山地。"""
        width, height = 5, 5
        elev = np.full((width, height), 0.85)
        moist = np.full((width, height), 0.1)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        for x in range(width):
            for y in range(height):
                assert grid[x][y].tile_type == TileType.MOUNTAIN

    def test_high_moisture_becomes_water(self) -> None:
        """验证高湿度、低海拔区域被分类为水域。"""
        width, height = 5, 5
        elev = np.full((width, height), 0.3)
        moist = np.full((width, height), 0.8)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        for x in range(width):
            for y in range(height):
                assert grid[x][y].tile_type == TileType.WATER


class TestSuitabilityScore:
    """测试 suitability_score 函数。"""

    def test_water_tile_returns_zero(self) -> None:
        """验证水域地块的适宜度评分为 0。"""
        width, height = 10, 10
        elev = np.full((width, height), 0.3)
        # 构建一个全水域地图
        moist = np.full((width, height), 0.8)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        score = suitability_score(5, 5, width, height, elev, grid)
        assert score == 0.0

    def test_mountain_tile_returns_zero(self) -> None:
        """验证山地地块的适宜度评分为 0。"""
        width, height = 10, 10
        elev = np.full((width, height), 0.85)
        moist = np.full((width, height), 0.1)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        score = suitability_score(5, 5, width, height, elev, grid)
        assert score == 0.0

    def test_farmland_area_has_positive_score(self) -> None:
        """验证农田区域的适宜度评分为正值。"""
        width, height = 20, 20
        # 低海拔 + 中湿度 → 农田
        elev = np.full((width, height), 0.3)
        moist = np.full((width, height), 0.4)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        score = suitability_score(10, 10, width, height, elev, grid)
        assert score > 0.0

    def test_score_within_valid_range(self) -> None:
        """验证适宜度评分在合理范围内。"""
        width, height = 20, 20
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        for x in range(width):
            for y in range(height):
                score = suitability_score(x, y, width, height, elev, grid)
                assert score >= 0.0

    def test_mixed_terrain_scores_vary(self) -> None:
        """验证不同地形的适宜度评分存在差异。"""
        width, height = 20, 20
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        scores = set()
        for x in range(width):
            for y in range(height):
                s = suitability_score(x, y, width, height, elev, grid)
                scores.add(round(s, 4))
        assert len(scores) > 1, "不同位置的适宜度评分应有差异"


class TestPlaceSettlements:
    """测试 place_settlements 函数。"""

    def test_settlements_count(self) -> None:
        """验证生成的聚落数量不超过请求数量。"""
        width, height = 20, 20
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        settlements = place_settlements(
            grid, elev, width, height,
            count=3,
            min_score=0.0,
            min_distance=3,
        )
        assert len(settlements) <= 3
        assert len(settlements) > 0

    def test_settlements_are_settlement_type(self) -> None:
        """验证返回的对象都是 Settlement 实例。"""
        width, height = 20, 20
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        settlements = place_settlements(
            grid, elev, width, height,
            count=3,
            min_score=0.0,
            min_distance=3,
        )
        for s in settlements:
            assert isinstance(s, Settlement)

    def test_settlement_tile_type_marked(self) -> None:
        """验证聚落所在地块的类型被标记为 SETTLEMENT。"""
        width, height = 20, 20
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        settlements = place_settlements(
            grid, elev, width, height,
            count=3,
            min_score=0.0,
            min_distance=3,
        )
        for s in settlements:
            x, y = s.position
            assert grid[x][y].tile_type == TileType.SETTLEMENT

    def test_settlement_min_distance_enforced(self) -> None:
        """验证聚落之间的曼哈顿距离不低于 min_distance。"""
        width, height = 20, 20
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        min_dist = 5
        settlements = place_settlements(
            grid, elev, width, height,
            count=4,
            min_score=0.0,
            min_distance=min_dist,
        )
        for i, s1 in enumerate(settlements):
            for s2 in settlements[i + 1:]:
                x1, y1 = s1.position
                x2, y2 = s2.position
                manhattan = abs(x1 - x2) + abs(y1 - y2)
                assert manhattan >= min_dist, (
                    f"聚落 {s1.id} 与 {s2.id} 距离 {manhattan} "
                    f"小于最小距离 {min_dist}"
                )

    def test_settlement_ids_sequential(self) -> None:
        """验证聚落 ID 从 0 开始递增。"""
        width, height = 20, 20
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        settlements = place_settlements(
            grid, elev, width, height,
            count=3,
            min_score=0.0,
            min_distance=3,
        )
        for i, s in enumerate(settlements):
            assert s.id == i

    def test_settlement_territory_assigned(self) -> None:
        """验证聚落被分配了领地地块。"""
        width, height = 20, 20
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        settlements = place_settlements(
            grid, elev, width, height,
            count=2,
            min_score=0.0,
            min_distance=5,
        )
        for s in settlements:
            assert len(s.territory_tiles) > 0

    def test_high_min_score_may_reduce_count(self) -> None:
        """验证当 min_score 过高时，生成的聚落数量可能少于请求数。"""
        width, height = 20, 20
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        settlements = place_settlements(
            grid, elev, width, height,
            count=10,
            min_score=0.99,
            min_distance=3,
        )
        # 高阈值下可能放不了那么多
        assert len(settlements) <= 10

    def test_positions_within_bounds(self) -> None:
        """验证所有聚落位置在地图范围内。"""
        width, height = 20, 20
        elev, moist = generate_elevation_moisture(width, height, seed=42)
        grid = generate_tile_grid(width, height, elev, moist, _DEFAULT_THRESHOLDS)
        settlements = place_settlements(
            grid, elev, width, height,
            count=4,
            min_score=0.0,
            min_distance=3,
        )
        for s in settlements:
            x, y = s.position
            assert 0 <= x < width
            assert 0 <= y < height
