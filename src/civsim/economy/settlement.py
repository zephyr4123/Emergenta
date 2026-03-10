"""聚落系统。

管理聚落的公共仓库、人口、税率、治安等属性，
提供 per_capita_food 和 scarcity_index 等统计量计算。
"""

from dataclasses import dataclass, field

from civsim.config_params_ext import SettlementParamsConfig
from civsim.economy.resources import add_resources, create_stockpile


@dataclass
class Settlement:
    """聚落数据模型。

    Attributes:
        id: 聚落唯一标识。
        name: 聚落名称。
        position: 中心坐标 (x, y)。
        territory_tiles: 领地内所有地块坐标列表。
        population: 当前人口。
        capacity: 人口容量上限。
        infrastructure: 基础设施水平 [0, 1]。
        stockpile: 公共仓库资源储备。
        tax_rate: 税率 [0, 1]。
        security_level: 治安水平 [0, 1]。
        governor_id: 关联的镇长 Agent ID。
        faction_id: 所属阵营 ID。
    """

    id: int
    name: str
    position: tuple[int, int]
    territory_tiles: list[tuple[int, int]] = field(default_factory=list)
    population: int = 0
    capacity: int = 200
    infrastructure: float = 0.5
    stockpile: dict[str, float] = field(default_factory=lambda: create_stockpile())
    tax_rate: float = 0.1
    security_level: float = 0.5
    governor_id: int | None = None
    faction_id: int | None = None
    _settlement_params: SettlementParamsConfig | None = field(
        default=None, repr=False,
    )

    @property
    def per_capita_food(self) -> float:
        """人均食物量。"""
        if self.population <= 0:
            return float("inf")
        return self.stockpile.get("food", 0.0) / self.population

    @property
    def scarcity_index(self) -> float:
        """食物稀缺指数 [0, 1]，越高越缺粮。

        当人均食物 >= scarcity_full_threshold 时稀缺度为 0，
        人均食物为 0 时稀缺度为 1。
        """
        params = self._settlement_params or SettlementParamsConfig()
        threshold = params.scarcity_full_threshold
        pf = self.per_capita_food
        if pf >= threshold:
            return 0.0
        return max(0.0, 1.0 - pf / threshold)

    def deposit(self, resources: dict[str, float]) -> None:
        """向仓库存入资源。

        Args:
            resources: 要存入的资源字典。
        """
        add_resources(self.stockpile, resources)

    def withdraw_food(self, amount: float) -> float:
        """从仓库提取食物。

        Args:
            amount: 期望提取量。

        Returns:
            实际提取到的食物量。
        """
        available = self.stockpile.get("food", 0.0)
        actual = min(amount, available)
        self.stockpile["food"] = available - actual
        return actual

    def consume_food_for_population(self, per_capita: float) -> int:
        """为全体人口消耗食物，返回饿死人数。

        Args:
            per_capita: 每人每 tick 食物消耗量。

        Returns:
            因饥饿减少的人口数。
        """
        total_needed = per_capita * self.population
        actual = self.withdraw_food(total_needed)
        if total_needed <= 0:
            return 0
        feed_ratio = actual / total_needed
        if feed_ratio >= 1.0:
            return 0
        # 按未满足比例计算饿死人数（至少1人）
        unfed_ratio = 1.0 - feed_ratio
        params = self._settlement_params or SettlementParamsConfig()
        deaths = max(1, int(self.population * unfed_ratio * params.starvation_unfed_factor))
        self.population = max(0, self.population - deaths)
        return deaths

    def natural_growth(self, rate: float = 0.002) -> int:
        """自然人口增长。

        Args:
            rate: 基础增长率。

        Returns:
            新增人口数。
        """
        if self.population >= self.capacity or self.scarcity_index > 0.5:
            return 0
        growth = max(1, int(self.population * rate))
        self.population = min(self.capacity, self.population + growth)
        return growth
