"""地块类型与行为的单元测试。

覆盖 TileType 枚举、Tile 初始化默认值、produce/consume/regenerate 行为，
以及 classify_tile 海拔/湿度映射逻辑。
"""

import pytest

from civsim.world.tiles import Tile, TileType, classify_tile


class TestTileType:
    """TileType 枚举测试。"""

    def test_has_seven_types(self) -> None:
        """应包含 7 种地块类型。"""
        assert len(TileType) == 7

    def test_type_values(self) -> None:
        """各类型的字符串值应正确。"""
        expected = {
            "farmland",
            "forest",
            "mine",
            "water",
            "mountain",
            "barren",
            "settlement",
        }
        actual = {t.value for t in TileType}
        assert actual == expected

    def test_enum_members_by_name(self) -> None:
        """应能通过名称访问各成员。"""
        assert TileType.FARMLAND.value == "farmland"
        assert TileType.FOREST.value == "forest"
        assert TileType.MINE.value == "mine"
        assert TileType.WATER.value == "water"
        assert TileType.MOUNTAIN.value == "mountain"
        assert TileType.BARREN.value == "barren"
        assert TileType.SETTLEMENT.value == "settlement"


class TestTileInit:
    """Tile 初始化默认值测试。"""

    def test_farmland_defaults(self) -> None:
        """农田地块的默认肥力应为 0.8。"""
        tile = Tile(tile_type=TileType.FARMLAND, position=(0, 0))
        assert tile.fertility == pytest.approx(0.8)
        assert tile.passability == pytest.approx(0.9)

    def test_forest_defaults(self) -> None:
        """森林地块的默认密度应为 0.8。"""
        tile = Tile(tile_type=TileType.FOREST, position=(1, 1))
        assert tile.density == pytest.approx(0.8)
        assert tile.passability == pytest.approx(0.6)

    def test_mine_defaults(self) -> None:
        """矿山地块的默认储量应为 100。"""
        tile = Tile(tile_type=TileType.MINE, position=(2, 2))
        assert tile.reserve == pytest.approx(100.0)
        assert tile.passability == pytest.approx(0.7)

    def test_water_passability(self) -> None:
        """水源地块通行度应为 0.1。"""
        tile = Tile(tile_type=TileType.WATER, position=(3, 3))
        assert tile.passability == pytest.approx(0.1)

    def test_mountain_passability(self) -> None:
        """山地地块通行度应为 0.2。"""
        tile = Tile(tile_type=TileType.MOUNTAIN, position=(4, 4))
        assert tile.passability == pytest.approx(0.2)

    def test_barren_defaults(self) -> None:
        """荒地地块不应有特殊资源属性。"""
        tile = Tile(tile_type=TileType.BARREN, position=(5, 5))
        assert tile.fertility == pytest.approx(0.0)
        assert tile.density == pytest.approx(0.0)
        assert tile.reserve == pytest.approx(0.0)
        assert tile.passability == pytest.approx(0.8)

    def test_settlement_passability(self) -> None:
        """聚落地块通行度应为 1.0。"""
        tile = Tile(tile_type=TileType.SETTLEMENT, position=(6, 6))
        assert tile.passability == pytest.approx(1.0)

    def test_explicit_values_not_overridden(self) -> None:
        """显式指定的属性值不应被覆盖。"""
        tile = Tile(
            tile_type=TileType.FARMLAND,
            position=(0, 0),
            fertility=0.5,
        )
        assert tile.fertility == pytest.approx(0.5)

    def test_owner_settlement_id_default_none(self) -> None:
        """owner_settlement_id 默认应为 None。"""
        tile = Tile(tile_type=TileType.BARREN, position=(0, 0))
        assert tile.owner_settlement_id is None


class TestTileProduce:
    """Tile.produce() 资源产出测试。"""

    def test_farmland_produces_food(self) -> None:
        """农田应产出 food，量为 2.0 * fertility * multiplier。"""
        tile = Tile(tile_type=TileType.FARMLAND, position=(0, 0))
        result = tile.produce(season_multiplier=1.0)
        assert "food" in result
        assert result["food"] == pytest.approx(2.0 * 0.8)

    def test_farmland_season_multiplier(self) -> None:
        """农田产出应受季节倍率影响。"""
        tile = Tile(tile_type=TileType.FARMLAND, position=(0, 0))
        result = tile.produce(season_multiplier=1.5)
        assert result["food"] == pytest.approx(2.0 * 0.8 * 1.5)

    def test_farmland_zero_fertility(self) -> None:
        """肥力为 0 时农田产出应为 0。"""
        tile = Tile(
            tile_type=TileType.FARMLAND, position=(0, 0)
        )
        # __post_init__ 会将 0.0 视为未设置并赋默认值，需显式置零
        tile.fertility = 0.0
        result = tile.produce()
        assert result["food"] == pytest.approx(0.0)

    def test_forest_produces_wood(self) -> None:
        """森林应产出 wood，量为 0.5 * density * multiplier。"""
        tile = Tile(tile_type=TileType.FOREST, position=(0, 0))
        result = tile.produce(season_multiplier=1.0)
        assert "wood" in result
        assert result["wood"] == pytest.approx(0.5 * 0.8)

    def test_forest_season_multiplier(self) -> None:
        """森林产出应受季节倍率影响。"""
        tile = Tile(tile_type=TileType.FOREST, position=(0, 0))
        result = tile.produce(season_multiplier=1.2)
        assert result["wood"] == pytest.approx(0.5 * 0.8 * 1.2)

    def test_mine_produces_ore(self) -> None:
        """矿山应产出 ore，单次上限为 1.0。"""
        tile = Tile(tile_type=TileType.MINE, position=(0, 0))
        result = tile.produce()
        assert "ore" in result
        assert result["ore"] == pytest.approx(1.0)

    def test_mine_low_reserve(self) -> None:
        """矿山储量不足 1.0 时应按实际储量产出。"""
        tile = Tile(tile_type=TileType.MINE, position=(0, 0), reserve=0.3)
        result = tile.produce()
        assert result["ore"] == pytest.approx(0.3)

    def test_mine_depleted(self) -> None:
        """矿山耗尽后应产出 0。"""
        tile = Tile(tile_type=TileType.MINE, position=(0, 0))
        # __post_init__ 会将 0.0 视为未设置并赋默认值，需显式置零
        tile.reserve = 0.0
        result = tile.produce()
        assert result["ore"] == pytest.approx(0.0)

    def test_non_productive_tiles_return_empty(self) -> None:
        """水/山/荒/聚落不产出资源。"""
        for tt in (
            TileType.WATER,
            TileType.MOUNTAIN,
            TileType.BARREN,
            TileType.SETTLEMENT,
        ):
            tile = Tile(tile_type=tt, position=(0, 0))
            result = tile.produce()
            assert result == {}

    def test_produce_default_multiplier_is_one(self) -> None:
        """不传 season_multiplier 时默认为 1.0。"""
        tile = Tile(tile_type=TileType.FARMLAND, position=(0, 0))
        result = tile.produce()
        assert result["food"] == pytest.approx(2.0 * 0.8 * 1.0)


class TestTileConsume:
    """Tile.consume() 资源消耗测试。"""

    def test_farmland_consume_returns_actual(self) -> None:
        """农田消耗应返回实际采集量。"""
        tile = Tile(tile_type=TileType.FARMLAND, position=(0, 0))
        actual = tile.consume(1.0)
        # min(1.0, 0.8 * 2.0) = 1.0
        assert actual == pytest.approx(1.0)

    def test_farmland_consume_decreases_fertility(self) -> None:
        """农田消耗后肥力应递减。"""
        tile = Tile(tile_type=TileType.FARMLAND, position=(0, 0))
        original = tile.fertility
        tile.consume(1.0)
        assert tile.fertility < original
        # fertility = max(0, 0.8 - 1.0 * 0.01) = 0.79
        assert tile.fertility == pytest.approx(0.79)

    def test_farmland_consume_capped_by_fertility(self) -> None:
        """农田采集量不应超过 fertility * 2.0。"""
        tile = Tile(
            tile_type=TileType.FARMLAND, position=(0, 0), fertility=0.2
        )
        actual = tile.consume(10.0)
        assert actual == pytest.approx(0.2 * 2.0)

    def test_forest_consume_returns_actual(self) -> None:
        """森林消耗应返回实际采集量。"""
        tile = Tile(tile_type=TileType.FOREST, position=(0, 0))
        actual = tile.consume(0.5)
        assert actual == pytest.approx(0.5)

    def test_forest_consume_decreases_density(self) -> None:
        """森林消耗后密度应递减。"""
        tile = Tile(tile_type=TileType.FOREST, position=(0, 0))
        original = tile.density
        tile.consume(0.5)
        assert tile.density < original
        # density = max(0, 0.8 - 0.5 * 0.02) = 0.79
        assert tile.density == pytest.approx(0.79)

    def test_forest_consume_capped_by_density(self) -> None:
        """森林采集量不应超过当前密度。"""
        tile = Tile(tile_type=TileType.FOREST, position=(0, 0), density=0.3)
        actual = tile.consume(5.0)
        assert actual == pytest.approx(0.3)

    def test_mine_consume_decreases_reserve(self) -> None:
        """矿山消耗后储量应减少。"""
        tile = Tile(tile_type=TileType.MINE, position=(0, 0))
        tile.consume(10.0)
        assert tile.reserve == pytest.approx(90.0)

    def test_mine_consume_capped_by_reserve(self) -> None:
        """矿山采集量不应超过剩余储量。"""
        tile = Tile(tile_type=TileType.MINE, position=(0, 0), reserve=3.0)
        actual = tile.consume(5.0)
        assert actual == pytest.approx(3.0)
        assert tile.reserve == pytest.approx(0.0)

    def test_non_consumable_tiles_return_zero(self) -> None:
        """水/山/荒/聚落消耗应返回 0。"""
        for tt in (
            TileType.WATER,
            TileType.MOUNTAIN,
            TileType.BARREN,
            TileType.SETTLEMENT,
        ):
            tile = Tile(tile_type=tt, position=(0, 0))
            assert tile.consume(1.0) == pytest.approx(0.0)


class TestTileRegenerate:
    """Tile.regenerate() 自然再生测试。"""

    def test_farmland_fertility_increases(self) -> None:
        """农田再生应增加肥力。"""
        tile = Tile(
            tile_type=TileType.FARMLAND, position=(0, 0), fertility=0.5
        )
        tile.regenerate(farmland_rate=2.0, forest_rate=0.5)
        # fertility = min(1.0, 0.5 + 2.0 * 0.001) = 0.502
        assert tile.fertility == pytest.approx(0.502)

    def test_farmland_fertility_capped_at_one(self) -> None:
        """农田肥力再生不应超过 1.0。"""
        tile = Tile(
            tile_type=TileType.FARMLAND, position=(0, 0), fertility=0.999
        )
        tile.regenerate(farmland_rate=100.0, forest_rate=0.0)
        assert tile.fertility == pytest.approx(1.0)

    def test_forest_density_increases(self) -> None:
        """森林再生应增加密度。"""
        tile = Tile(
            tile_type=TileType.FOREST, position=(0, 0), density=0.5
        )
        tile.regenerate(farmland_rate=2.0, forest_rate=0.5)
        # density = min(1.0, 0.5 + 0.5 * 0.001) = 0.5005
        assert tile.density == pytest.approx(0.5005)

    def test_forest_density_capped_at_one(self) -> None:
        """森林密度再生不应超过 1.0。"""
        tile = Tile(
            tile_type=TileType.FOREST, position=(0, 0), density=0.999
        )
        tile.regenerate(farmland_rate=0.0, forest_rate=100.0)
        assert tile.density == pytest.approx(1.0)

    def test_mine_does_not_regenerate(self) -> None:
        """矿山储量不应再生。"""
        tile = Tile(tile_type=TileType.MINE, position=(0, 0), reserve=50.0)
        tile.regenerate(farmland_rate=2.0, forest_rate=0.5)
        assert tile.reserve == pytest.approx(50.0)

    def test_non_regenerating_tiles_unchanged(self) -> None:
        """水/山/荒/聚落再生调用不应改变任何属性。"""
        for tt in (
            TileType.WATER,
            TileType.MOUNTAIN,
            TileType.BARREN,
            TileType.SETTLEMENT,
        ):
            tile = Tile(tile_type=tt, position=(0, 0))
            tile.regenerate(farmland_rate=2.0, forest_rate=0.5)
            assert tile.fertility == pytest.approx(0.0)
            assert tile.density == pytest.approx(0.0)


class TestClassifyTile:
    """classify_tile() 海拔/湿度映射测试。"""

    def setup_method(self) -> None:
        """设置默认阈值。"""
        self.thresholds: dict[str, float] = {
            "mountain_elevation": 0.70,
            "water_moisture": 0.60,
            "forest_elevation": 0.50,
            "farmland_moisture": 0.30,
        }

    def test_high_elevation_is_mountain(self) -> None:
        """高海拔应分类为山地。"""
        result = classify_tile(0.80, 0.0, self.thresholds)
        assert result == TileType.MOUNTAIN

    def test_mountain_at_boundary(self) -> None:
        """海拔恰好等于山地阈值应为山地。"""
        result = classify_tile(0.70, 0.0, self.thresholds)
        assert result == TileType.MOUNTAIN

    def test_high_moisture_is_water(self) -> None:
        """高湿度（非山地海拔）应分类为水源。"""
        result = classify_tile(0.40, 0.70, self.thresholds)
        assert result == TileType.WATER

    def test_water_at_boundary(self) -> None:
        """湿度恰好等于水源阈值应为水源。"""
        result = classify_tile(0.40, 0.60, self.thresholds)
        assert result == TileType.WATER

    def test_mid_elevation_is_forest(self) -> None:
        """中等海拔、低湿度应分类为森林。"""
        result = classify_tile(0.55, 0.20, self.thresholds)
        assert result == TileType.FOREST

    def test_forest_at_boundary(self) -> None:
        """海拔恰好等于森林阈值应为森林。"""
        result = classify_tile(0.50, 0.20, self.thresholds)
        assert result == TileType.FOREST

    def test_moderate_moisture_is_farmland(self) -> None:
        """中等湿度、低海拔应分类为农田。"""
        result = classify_tile(0.30, 0.40, self.thresholds)
        assert result == TileType.FARMLAND

    def test_farmland_at_boundary(self) -> None:
        """湿度恰好等于农田阈值应为农田。"""
        result = classify_tile(0.30, 0.30, self.thresholds)
        assert result == TileType.FARMLAND

    def test_low_everything_is_barren(self) -> None:
        """低海拔低湿度应分类为荒地。"""
        result = classify_tile(0.20, 0.10, self.thresholds)
        assert result == TileType.BARREN

    def test_mountain_takes_priority_over_water(self) -> None:
        """山地判定优先于水源（高海拔+高湿度应为山地）。"""
        result = classify_tile(0.80, 0.80, self.thresholds)
        assert result == TileType.MOUNTAIN

    def test_water_takes_priority_over_forest(self) -> None:
        """水源判定优先于森林（中高海拔+高湿度应为水源）。"""
        result = classify_tile(0.55, 0.70, self.thresholds)
        assert result == TileType.WATER

    def test_custom_thresholds(self) -> None:
        """自定义阈值应正确生效。"""
        custom = {
            "mountain_elevation": 0.90,
            "water_moisture": 0.80,
            "forest_elevation": 0.60,
            "farmland_moisture": 0.40,
        }
        # 0.75 海拔 < 0.90 山地阈值，0.10 湿度 < 0.80 水源阈值
        # 0.75 >= 0.60 森林阈值 => 森林
        result = classify_tile(0.75, 0.10, custom)
        assert result == TileType.FOREST
