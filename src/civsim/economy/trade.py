"""聚落间贸易系统。

实现供需匹配、贸易路线和利润计算。
含贸易摩擦机制：信任度门槛、随机拒绝、距离惩罚。
含信任反馈：成功跨阵营贸易增加双边信任。
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass

from civsim.config_params import TradeParamsConfig
from civsim.economy.resources import RESOURCE_NAMES
from civsim.economy.settlement import Settlement

logger = logging.getLogger(__name__)

# 后向兼容的模块级常量
TRADE_TRUST_THRESHOLD = 0.4


@dataclass
class TradeRoute:
    """贸易路线。

    Attributes:
        seller_id: 卖方聚落 ID。
        buyer_id: 买方聚落 ID。
        resource: 交易资源类型。
        amount: 交易数量。
        price_gold: 金币价格。
        distance: 路线距离。
    """

    seller_id: int
    buyer_id: int
    resource: str
    amount: float
    price_gold: float
    distance: float = 0.0


# 资源基础价格（金币/单位）
BASE_PRICES: dict[str, float] = {
    "food": 1.0,
    "wood": 1.5,
    "ore": 3.0,
}

# 最小可交易盈余比例（提高以保留更多库存）
MIN_SURPLUS_RATIO = 0.5


class TradeManager:
    """贸易管理器。

    管理聚落间的资源交易。

    Attributes:
        completed_trades: 已完成的交易记录。
        total_volume: 总交易量。
        params: 贸易参数配置。
    """

    def __init__(
        self,
        params: TradeParamsConfig | None = None,
    ) -> None:
        self.params = params or TradeParamsConfig()
        self.completed_trades: list[TradeRoute] = []
        self.total_volume: float = 0.0
        self._tick_trades: list[TradeRoute] = []
        self._tick_trust_deltas: dict[tuple[int, int], float] = {}
        self._tick_volume: float = 0.0

    def find_opportunities(
        self,
        settlements: dict[int, Settlement],
        diplomacy_relations: dict[tuple[int, int], int] | None = None,
        trust_data: dict[tuple[int, int], float] | None = None,
    ) -> list[TradeRoute]:
        """寻找贸易机会，匹配供给过剩和需求不足的聚落。

        Args:
            settlements: 聚落字典。
            diplomacy_relations: 外交关系整数值字典。
            trust_data: 阵营间信任度字典。

        Returns:
            可行的贸易路线列表。
        """
        opportunities: list[TradeRoute] = []
        tradeable = [r for r in RESOURCE_NAMES if r != "gold"]
        settlement_list = list(settlements.values())

        for resource in tradeable:
            sellers = _find_sellers(settlement_list, resource)
            buyers = _find_buyers(settlement_list, resource)

            for seller, surplus in sellers:
                for buyer, need in buyers:
                    if seller.id == buyer.id:
                        continue
                    if diplomacy_relations and _are_hostile(
                        seller, buyer, diplomacy_relations,
                    ):
                        continue

                    # 信任度门槛：trust 过低时拒绝交易
                    if _should_refuse_trade(
                        seller, buyer, trust_data,
                        self.params,
                    ):
                        continue

                    amount = min(surplus * self.params.surplus_trade_ratio, need)
                    if amount < 0.5:
                        continue

                    distance = _compute_distance(
                        seller.position, buyer.position,
                    )
                    price = (
                        BASE_PRICES.get(resource, 1.0)
                        * amount
                        * (1.0 + distance * 0.05)
                    )
                    opportunities.append(TradeRoute(
                        seller_id=seller.id,
                        buyer_id=buyer.id,
                        resource=resource,
                        amount=amount,
                        price_gold=price,
                        distance=distance,
                    ))

        return opportunities

    def execute_trade(
        self,
        route: TradeRoute,
        settlements: dict[int, Settlement],
    ) -> bool:
        """执行一笔贸易。

        Args:
            route: 贸易路线。
            settlements: 聚落字典。

        Returns:
            是否执行成功。
        """
        seller = settlements.get(route.seller_id)
        buyer = settlements.get(route.buyer_id)

        if seller is None or buyer is None:
            return False

        available = seller.stockpile.get(route.resource, 0.0)
        if available < route.amount:
            return False

        buyer_gold = buyer.stockpile.get("gold", 0.0)
        if buyer_gold < route.price_gold:
            return False

        seller.stockpile[route.resource] -= route.amount
        buyer.stockpile[route.resource] = (
            buyer.stockpile.get(route.resource, 0.0) + route.amount
        )
        seller.stockpile["gold"] = (
            seller.stockpile.get("gold", 0.0) + route.price_gold
        )
        buyer.stockpile["gold"] -= route.price_gold

        self.completed_trades.append(route)
        self._tick_trades.append(route)
        self.total_volume += route.amount
        self._tick_volume += route.amount

        # 跨阵营成功贸易 → 记录信任增量
        seller_fid = seller.faction_id
        buyer_fid = buyer.faction_id
        if (
            seller_fid is not None
            and buyer_fid is not None
            and seller_fid != buyer_fid
        ):
            key = (min(seller_fid, buyer_fid), max(seller_fid, buyer_fid))
            self._tick_trust_deltas[key] = (
                self._tick_trust_deltas.get(key, 0.0)
                + self.params.trust_boost_per_trade
            )

        return True

    def process_tick(
        self,
        settlements: dict[int, Settlement],
        diplomacy_relations: dict[tuple[int, int], int] | None = None,
        trust_data: dict[tuple[int, int], float] | None = None,
    ) -> list[TradeRoute]:
        """处理一个 tick 的贸易，返回本 tick 完成的贸易列表。"""
        self._tick_trades = []
        self._tick_trust_deltas = {}
        self._tick_volume = 0.0
        opportunities = self.find_opportunities(
            settlements, diplomacy_relations, trust_data,
        )
        opportunities.sort(
            key=lambda r: r.price_gold / max(1.0, r.distance),
            reverse=True,
        )
        for route in opportunities:
            self.execute_trade(route, settlements)
        return self._tick_trades

    def compute_trust_deltas(self) -> dict[tuple[int, int], float]:
        """返回本 tick 跨阵营贸易产生的信任增量。

        Returns:
            阵营对 → 信任增量的字典。
        """
        return dict(self._tick_trust_deltas)

    def get_tick_stats(self) -> dict:
        """返回本 tick 贸易统计，供 LLM 上下文注入。

        Returns:
            包含贸易数、交易量等的统计字典。
        """
        return {
            "tick_trade_count": len(self._tick_trades),
            "tick_volume": round(self._tick_volume, 1),
            "total_trade_count": self.trade_count,
            "total_volume": round(self.total_volume, 1),
        }

    @property
    def trade_count(self) -> int:
        """总交易次数。"""
        return len(self.completed_trades)


def _should_refuse_trade(
    seller: Settlement,
    buyer: Settlement,
    trust_data: dict[tuple[int, int], float] | None,
    params: TradeParamsConfig | None = None,
) -> bool:
    """基于信任度和随机摩擦判断是否拒绝交易。"""
    if seller.faction_id is None or buyer.faction_id is None:
        return False
    if seller.faction_id == buyer.faction_id:
        return False

    if params is None:
        params = TradeParamsConfig()

    trust = 0.5
    if trust_data is not None:
        key = (
            min(seller.faction_id, buyer.faction_id),
            max(seller.faction_id, buyer.faction_id),
        )
        trust = trust_data.get(key, 0.5)

    # 信任度低于门槛直接拒绝
    if trust < params.trust_threshold:
        return True

    # 随机摩擦：信任越低拒绝概率越高
    refuse_prob = params.refuse_prob_base - params.refuse_prob_trust_factor * trust
    return random.random() < refuse_prob


def _find_sellers(
    settlements: list[Settlement], resource: str,
) -> list[tuple[Settlement, float]]:
    """找出有盈余的聚落。"""
    threshold = 8.0 if resource == "food" else 3.0
    results = []
    for s in settlements:
        stock = s.stockpile.get(resource, 0.0)
        per_cap = stock / max(1, s.population)
        if per_cap > threshold:
            surplus = stock - threshold * s.population * MIN_SURPLUS_RATIO
            if surplus > 1.0:
                results.append((s, surplus))
    return results


def _find_buyers(
    settlements: list[Settlement], resource: str,
) -> list[tuple[Settlement, float]]:
    """找出有短缺的聚落。"""
    deficit_threshold = 3.0 if resource == "food" else 1.0
    results = []
    for s in settlements:
        stock = s.stockpile.get(resource, 0.0)
        per_cap = stock / max(1, s.population)
        if per_cap < deficit_threshold:
            need = deficit_threshold * s.population - stock
            if need > 1.0:
                results.append((s, need))
    return results


def _compute_distance(
    pos_a: tuple[int, int], pos_b: tuple[int, int],
) -> float:
    """计算两点间的欧氏距离。"""
    dx = pos_a[0] - pos_b[0]
    dy = pos_a[1] - pos_b[1]
    return math.sqrt(dx * dx + dy * dy)


def _are_hostile(
    a: Settlement,
    b: Settlement,
    relations: dict[tuple[int, int], int],
) -> bool:
    """检查两个聚落所属阵营是否敌对。"""
    if a.faction_id is None or b.faction_id is None:
        return False
    if a.faction_id == b.faction_id:
        return False
    key = (min(a.faction_id, b.faction_id), max(a.faction_id, b.faction_id))
    status = relations.get(key, 2)  # 默认 NEUTRAL=2
    return status <= 1  # WAR=0 or HOSTILE=1
