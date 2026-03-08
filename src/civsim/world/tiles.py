"""地块类型定义与行为。

定义 6 种地块类型及其资源产出、再生、耗竭逻辑。
每个 Tile 是世界网格中的一个单元格。
"""

from dataclasses import dataclass
from enum import Enum


class TileType(Enum):
    """地块类型枚举。"""

    FARMLAND = "farmland"
    FOREST = "forest"
    MINE = "mine"
    WATER = "water"
    MOUNTAIN = "mountain"
    BARREN = "barren"
    SETTLEMENT = "settlement"


# 各地块类型的基础通行度
_DEFAULT_PASSABILITY: dict[TileType, float] = {
    TileType.FARMLAND: 0.9,
    TileType.FOREST: 0.6,
    TileType.MINE: 0.7,
    TileType.WATER: 0.1,
    TileType.MOUNTAIN: 0.2,
    TileType.BARREN: 0.8,
    TileType.SETTLEMENT: 1.0,
}


@dataclass
class Tile:
    """世界网格中的单个地块。

    Attributes:
        tile_type: 地块类型。
        position: 网格坐标 (x, y)。
        elevation: 海拔，0.0-1.0。
        moisture: 湿度，0.0-1.0。
        fertility: 农田肥力，0.0-1.0，使用后递减。
        density: 森林密度，0.0-1.0，砍伐后缓慢再生。
        reserve: 矿山储量，耗尽即为 0。
        passability: 通行度，0.0-1.0。
        owner_settlement_id: 所属聚落 ID。
    """

    tile_type: TileType
    position: tuple[int, int]
    elevation: float = 0.5
    moisture: float = 0.5
    fertility: float = 0.0
    density: float = 0.0
    reserve: float = 0.0
    passability: float = 0.8
    owner_settlement_id: int | None = None

    def __post_init__(self) -> None:
        """根据地块类型设置默认属性值。"""
        if self.passability == 0.8:
            self.passability = _DEFAULT_PASSABILITY.get(self.tile_type, 0.8)
        if self.tile_type == TileType.FARMLAND and self.fertility == 0.0:
            self.fertility = 0.8
        if self.tile_type == TileType.FOREST and self.density == 0.0:
            self.density = 0.8
        if self.tile_type == TileType.MINE and self.reserve == 0.0:
            self.reserve = 100.0

    def produce(self, season_multiplier: float = 1.0) -> dict[str, float]:
        """根据地块类型产出资源。

        Args:
            season_multiplier: 季节产出倍率。

        Returns:
            资源产出字典，如 {"food": 2.0}。
        """
        if self.tile_type == TileType.FARMLAND:
            output = 2.0 * self.fertility * season_multiplier
            return {"food": max(output, 0.0)}
        if self.tile_type == TileType.FOREST:
            output = 0.5 * self.density * season_multiplier
            return {"wood": max(output, 0.0)}
        if self.tile_type == TileType.MINE:
            if self.reserve <= 0:
                return {"ore": 0.0}
            output = min(1.0, self.reserve)
            return {"ore": output}
        return {}

    def consume(self, amount: float) -> float:
        """消耗地块资源（采集行为）。

        Args:
            amount: 期望采集量。

        Returns:
            实际采集到的量。
        """
        if self.tile_type == TileType.FARMLAND:
            actual = min(amount, self.fertility * 2.0)
            self.fertility = max(0.0, self.fertility - amount * 0.01)
            return actual
        if self.tile_type == TileType.FOREST:
            actual = min(amount, self.density)
            self.density = max(0.0, self.density - amount * 0.02)
            return actual
        if self.tile_type == TileType.MINE:
            actual = min(amount, self.reserve)
            self.reserve = max(0.0, self.reserve - actual)
            return actual
        return 0.0

    def regenerate(self, farmland_rate: float, forest_rate: float) -> None:
        """每 tick 自然再生。

        Args:
            farmland_rate: 农田肥力恢复速率。
            forest_rate: 森林密度恢复速率。
        """
        if self.tile_type == TileType.FARMLAND:
            self.fertility = min(1.0, self.fertility + farmland_rate * 0.001)
        elif self.tile_type == TileType.FOREST:
            self.density = min(1.0, self.density + forest_rate * 0.001)


def classify_tile(elevation: float, moisture: float, thresholds: dict[str, float]) -> TileType:
    """根据海拔和湿度将坐标分类为地块类型。

    Args:
        elevation: 归一化海拔值 [0, 1]。
        moisture: 归一化湿度值 [0, 1]。
        thresholds: 分类阈值配置。

    Returns:
        对应的地块类型。
    """
    if elevation >= thresholds.get("mountain_elevation", 0.70):
        return TileType.MOUNTAIN
    if moisture >= thresholds.get("water_moisture", 0.60):
        return TileType.WATER
    if elevation >= thresholds.get("forest_elevation", 0.50):
        return TileType.FOREST
    if moisture >= thresholds.get("farmland_moisture", 0.30):
        return TileType.FARMLAND
    return TileType.BARREN
