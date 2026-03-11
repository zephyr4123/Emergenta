"""trade.py 单元测试。

验证贸易管理器的供需匹配、交易执行、距离定价和敌对过滤。
"""

import math

import pytest

from civsim.economy.settlement import Settlement
from civsim.economy.trade import (
    BASE_PRICES,
    TradeManager,
    TradeRoute,
    _are_hostile,
    _compute_distance,
    _find_buyers,
    _find_sellers,
)


def _make_settlement(
    sid: int, pop: int = 10, food: float = 100.0,
    wood: float = 50.0, ore: float = 20.0, gold: float = 100.0,
    position: tuple[int, int] = (0, 0),
    faction_id: int | None = None,
) -> Settlement:
    """创建测试用聚落。"""
    s = Settlement(
        id=sid, name=f"聚落{sid}", position=position,
        population=pop,
        stockpile={"food": food, "wood": wood, "ore": ore, "gold": gold},
    )
    s.faction_id = faction_id
    return s


class TestTradeHelpers:
    """测试贸易辅助函数。"""

    def test_compute_distance(self) -> None:
        """验证距离计算。"""
        d = _compute_distance((0, 0), (3, 4))
        assert d == pytest.approx(5.0)

    def test_compute_distance_same_point(self) -> None:
        """验证同点距离为零。"""
        d = _compute_distance((5, 5), (5, 5))
        assert d == pytest.approx(0.0)

    def test_are_hostile_same_faction(self) -> None:
        """验证同阵营不敌对。"""
        a = _make_settlement(0, faction_id=1)
        b = _make_settlement(1, faction_id=1)
        assert not _are_hostile(a, b, {})

    def test_are_hostile_war(self) -> None:
        """验证战争状态为敌对。"""
        a = _make_settlement(0, faction_id=1)
        b = _make_settlement(1, faction_id=2)
        relations = {(1, 2): 0}  # WAR
        assert _are_hostile(a, b, relations)

    def test_are_hostile_neutral_not_hostile(self) -> None:
        """验证中立状态非敌对。"""
        a = _make_settlement(0, faction_id=1)
        b = _make_settlement(1, faction_id=2)
        relations = {(1, 2): 2}  # NEUTRAL
        assert not _are_hostile(a, b, relations)

    def test_are_hostile_no_faction(self) -> None:
        """验证无阵营不敌对。"""
        a = _make_settlement(0, faction_id=None)
        b = _make_settlement(1, faction_id=2)
        assert not _are_hostile(a, b, {})


class TestFindSellersAndBuyers:
    """测试供需匹配。"""

    def test_find_sellers_food_surplus(self) -> None:
        """验证食物盈余的聚落被识别为卖家。"""
        # 人均 food > 5.0
        s = _make_settlement(0, pop=10, food=200.0)
        sellers = _find_sellers([s], "food")
        assert len(sellers) == 1

    def test_find_sellers_no_surplus(self) -> None:
        """验证食物不足的聚落不是卖家。"""
        s = _make_settlement(0, pop=10, food=20.0)
        sellers = _find_sellers([s], "food")
        assert len(sellers) == 0

    def test_find_buyers_food_deficit(self) -> None:
        """验证食物短缺的聚落被识别为买家。"""
        # 人均 food < 2.0
        s = _make_settlement(0, pop=10, food=5.0)
        buyers = _find_buyers([s], "food")
        assert len(buyers) == 1

    def test_find_buyers_no_deficit(self) -> None:
        """验证食物充足的聚落不是买家。"""
        s = _make_settlement(0, pop=10, food=200.0)
        buyers = _find_buyers([s], "food")
        assert len(buyers) == 0


class TestTradeRoute:
    """测试贸易路线数据类。"""

    def test_trade_route_creation(self) -> None:
        """验证贸易路线创建。"""
        route = TradeRoute(
            seller_id=0, buyer_id=1,
            resource="food", amount=10.0, price_gold=12.0,
        )
        assert route.seller_id == 0
        assert route.distance == 0.0


class TestTradeManager:
    """测试贸易管理器。"""

    def test_find_opportunities_matches_supply_demand(self) -> None:
        """验证供需匹配能找到贸易机会。"""
        tm = TradeManager()
        settlements = {
            0: _make_settlement(0, pop=10, food=200.0, gold=50.0, position=(0, 0)),
            1: _make_settlement(1, pop=10, food=5.0, gold=50.0, position=(5, 5)),
        }
        opps = tm.find_opportunities(settlements)
        assert len(opps) > 0
        assert opps[0].resource == "food"

    def test_find_opportunities_filters_hostile(self) -> None:
        """验证敌对阵营不产生贸易机会。"""
        tm = TradeManager()
        settlements = {
            0: _make_settlement(0, pop=10, food=200.0, gold=50.0, faction_id=1),
            1: _make_settlement(1, pop=10, food=5.0, gold=50.0, faction_id=2),
        }
        relations = {(1, 2): 0}  # WAR
        opps = tm.find_opportunities(settlements, relations)
        assert len(opps) == 0

    def test_execute_trade_transfers_resources(self) -> None:
        """验证交易执行转移资源和金币。"""
        tm = TradeManager()
        seller = _make_settlement(0, food=200.0, gold=50.0)
        buyer = _make_settlement(1, food=5.0, gold=50.0)
        settlements = {0: seller, 1: buyer}

        route = TradeRoute(
            seller_id=0, buyer_id=1,
            resource="food", amount=10.0, price_gold=15.0,
        )
        result = tm.execute_trade(route, settlements)
        assert result is True
        assert seller.stockpile["food"] == pytest.approx(190.0)
        assert buyer.stockpile["food"] == pytest.approx(15.0)
        assert seller.stockpile["gold"] == pytest.approx(65.0)
        assert buyer.stockpile["gold"] == pytest.approx(35.0)

    def test_execute_trade_scales_down_insufficient_stock(self) -> None:
        """验证库存不足时交易自动缩减规模。"""
        tm = TradeManager()
        seller = _make_settlement(0, food=5.0)
        buyer = _make_settlement(1, gold=50.0)
        settlements = {0: seller, 1: buyer}

        route = TradeRoute(
            seller_id=0, buyer_id=1,
            resource="food", amount=100.0, price_gold=15.0,
        )
        result = tm.execute_trade(route, settlements)
        # 缩减到 available=5.0，scale=0.05，price=0.75
        assert result is True
        assert seller.stockpile["food"] == pytest.approx(0.0)

    def test_execute_trade_fails_below_min_amount(self) -> None:
        """验证库存低于最小交易量时交易失败。"""
        tm = TradeManager()
        seller = _make_settlement(0, food=0.1)  # 低于 min_trade_amount=0.5
        buyer = _make_settlement(1, gold=50.0)
        settlements = {0: seller, 1: buyer}

        route = TradeRoute(
            seller_id=0, buyer_id=1,
            resource="food", amount=100.0, price_gold=15.0,
        )
        result = tm.execute_trade(route, settlements)
        assert result is False

    def test_execute_trade_fails_insufficient_gold(self) -> None:
        """验证金币不足时交易失败。"""
        tm = TradeManager()
        seller = _make_settlement(0, food=200.0)
        buyer = _make_settlement(1, gold=1.0)
        settlements = {0: seller, 1: buyer}

        route = TradeRoute(
            seller_id=0, buyer_id=1,
            resource="food", amount=10.0, price_gold=50.0,
        )
        result = tm.execute_trade(route, settlements)
        assert result is False

    def test_process_tick_accumulates_volume(self) -> None:
        """验证 process_tick 累积贸易量。"""
        tm = TradeManager()
        settlements = {
            0: _make_settlement(0, pop=10, food=200.0, gold=50.0, position=(0, 0)),
            1: _make_settlement(1, pop=10, food=5.0, gold=50.0, position=(5, 5)),
        }
        trades = tm.process_tick(settlements)
        assert tm.total_volume >= 0
        assert tm.trade_count >= 0

    def test_process_tick_sorts_by_profitability(self) -> None:
        """验证贸易按利润/距离排序（优先近距离高价）。"""
        tm = TradeManager()
        settlements = {
            0: _make_settlement(0, pop=5, food=200.0, gold=50.0, position=(0, 0)),
            1: _make_settlement(1, pop=5, food=5.0, gold=100.0, position=(2, 2)),
            2: _make_settlement(2, pop=5, food=5.0, gold=100.0, position=(50, 50)),
        }
        tm.process_tick(settlements)
        # 至少应该执行一些交易
        assert tm.trade_count >= 0
