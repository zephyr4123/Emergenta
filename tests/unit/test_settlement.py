"""settlement.py 单元测试。

验证聚落数据模型的初始化、统计量计算、仓库操作和人口增减逻辑。
"""

import math

import pytest

from civsim.economy.settlement import Settlement


class TestSettlementInit:
    """测试 Settlement 初始化默认值。"""

    def test_required_fields(self) -> None:
        """验证必填字段正确设置。"""
        s = Settlement(id=1, name="测试村", position=(10, 20))
        assert s.id == 1
        assert s.name == "测试村"
        assert s.position == (10, 20)

    def test_default_population(self) -> None:
        """验证默认人口为 0。"""
        s = Settlement(id=1, name="村", position=(0, 0))
        assert s.population == 0

    def test_default_capacity(self) -> None:
        """验证默认容量为 200。"""
        s = Settlement(id=1, name="村", position=(0, 0))
        assert s.capacity == 200

    def test_default_infrastructure(self) -> None:
        """验证默认基础设施水平为 0.5。"""
        s = Settlement(id=1, name="村", position=(0, 0))
        assert s.infrastructure == 0.5

    def test_default_stockpile_all_zero(self) -> None:
        """验证默认仓库所有资源为 0。"""
        s = Settlement(id=1, name="村", position=(0, 0))
        for key in ["food", "wood", "ore", "gold"]:
            assert s.stockpile[key] == 0.0

    def test_default_tax_rate(self) -> None:
        """验证默认税率为 0.1。"""
        s = Settlement(id=1, name="村", position=(0, 0))
        assert s.tax_rate == 0.1

    def test_default_security_level(self) -> None:
        """验证默认治安水平为 0.5。"""
        s = Settlement(id=1, name="村", position=(0, 0))
        assert s.security_level == 0.5

    def test_default_optional_ids(self) -> None:
        """验证 governor_id 和 faction_id 默认为 None。"""
        s = Settlement(id=1, name="村", position=(0, 0))
        assert s.governor_id is None
        assert s.faction_id is None

    def test_stockpile_independence(self) -> None:
        """验证不同实例的仓库互相独立。"""
        s1 = Settlement(id=1, name="A", position=(0, 0))
        s2 = Settlement(id=2, name="B", position=(1, 1))
        s1.stockpile["food"] = 999.0
        assert s2.stockpile["food"] == 0.0


class TestPerCapitaFood:
    """测试 per_capita_food 人均食物计算。"""

    def test_zero_population_returns_inf(self) -> None:
        """验证人口为 0 时返回无穷大。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=0)
        assert math.isinf(s.per_capita_food)

    def test_basic_calculation(self) -> None:
        """验证人均食物基础计算。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=10)
        s.stockpile["food"] = 50.0
        assert s.per_capita_food == pytest.approx(5.0)

    def test_no_food(self) -> None:
        """验证无食物时人均为 0。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=100)
        assert s.per_capita_food == pytest.approx(0.0)

    def test_one_person(self) -> None:
        """验证单人时人均等于总量。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=1)
        s.stockpile["food"] = 42.0
        assert s.per_capita_food == pytest.approx(42.0)


class TestScarcityIndex:
    """测试 scarcity_index 稀缺指数边界值。"""

    def test_abundant_food_zero_scarcity(self) -> None:
        """验证人均食物 >= 5 时稀缺度为 0。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=10)
        s.stockpile["food"] = 100.0  # 人均 10
        assert s.scarcity_index == pytest.approx(0.0)

    def test_exactly_five_per_capita(self) -> None:
        """验证人均恰好为 5 时稀缺度为 0。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=10)
        s.stockpile["food"] = 50.0
        assert s.scarcity_index == pytest.approx(0.0)

    def test_zero_food_max_scarcity(self) -> None:
        """验证无食物时稀缺度为 1。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=10)
        assert s.scarcity_index == pytest.approx(1.0)

    def test_half_scarcity(self) -> None:
        """验证人均 2.5 时稀缺度为 0.5。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=10)
        s.stockpile["food"] = 25.0  # 人均 2.5
        assert s.scarcity_index == pytest.approx(0.5)

    def test_zero_population_zero_scarcity(self) -> None:
        """验证人口为 0 时（人均无穷大）稀缺度为 0。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=0)
        assert s.scarcity_index == pytest.approx(0.0)


class TestDeposit:
    """测试 deposit 仓库存入。"""

    def test_deposit_food(self) -> None:
        """验证存入食物。"""
        s = Settlement(id=1, name="村", position=(0, 0))
        s.deposit({"food": 50.0, "wood": 0.0, "ore": 0.0, "gold": 0.0})
        assert s.stockpile["food"] == 50.0

    def test_deposit_multiple_resources(self) -> None:
        """验证同时存入多种资源。"""
        s = Settlement(id=1, name="村", position=(0, 0))
        s.deposit({"food": 10.0, "wood": 20.0, "ore": 5.0, "gold": 3.0})
        assert s.stockpile["food"] == 10.0
        assert s.stockpile["wood"] == 20.0
        assert s.stockpile["ore"] == 5.0
        assert s.stockpile["gold"] == 3.0

    def test_deposit_accumulates(self) -> None:
        """验证多次存入累加。"""
        s = Settlement(id=1, name="村", position=(0, 0))
        s.deposit({"food": 10.0, "wood": 0.0, "ore": 0.0, "gold": 0.0})
        s.deposit({"food": 15.0, "wood": 0.0, "ore": 0.0, "gold": 0.0})
        assert s.stockpile["food"] == 25.0


class TestWithdrawFood:
    """测试 withdraw_food 食物提取。"""

    def test_withdraw_within_stock(self) -> None:
        """验证库存充足时提取指定量。"""
        s = Settlement(id=1, name="村", position=(0, 0))
        s.stockpile["food"] = 100.0
        actual = s.withdraw_food(30.0)
        assert actual == 30.0
        assert s.stockpile["food"] == 70.0

    def test_withdraw_exceeds_stock(self) -> None:
        """验证提取量超过库存时只取出全部库存。"""
        s = Settlement(id=1, name="村", position=(0, 0))
        s.stockpile["food"] = 20.0
        actual = s.withdraw_food(50.0)
        assert actual == 20.0
        assert s.stockpile["food"] == 0.0

    def test_withdraw_exact_stock(self) -> None:
        """验证恰好取完。"""
        s = Settlement(id=1, name="村", position=(0, 0))
        s.stockpile["food"] = 10.0
        actual = s.withdraw_food(10.0)
        assert actual == 10.0
        assert s.stockpile["food"] == 0.0

    def test_withdraw_from_empty(self) -> None:
        """验证从空仓库提取返回 0。"""
        s = Settlement(id=1, name="村", position=(0, 0))
        actual = s.withdraw_food(10.0)
        assert actual == 0.0
        assert s.stockpile["food"] == 0.0


class TestConsumeFoodForPopulation:
    """测试 consume_food_for_population 饿死逻辑。"""

    def test_sufficient_food_no_deaths(self) -> None:
        """验证食物充足时无人饿死。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=100)
        s.stockpile["food"] = 200.0
        deaths = s.consume_food_for_population(0.5)  # 需要 50
        assert deaths == 0
        assert s.population == 100
        assert s.stockpile["food"] == pytest.approx(150.0)

    def test_zero_population_no_deaths(self) -> None:
        """验证人口为 0 时无消耗无死亡。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=0)
        deaths = s.consume_food_for_population(0.5)
        assert deaths == 0

    def test_insufficient_food_causes_deaths(self) -> None:
        """验证食物不足时产生饿死人口。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=100)
        s.stockpile["food"] = 10.0  # 需要 50，远不够
        deaths = s.consume_food_for_population(0.5)
        assert deaths >= 1
        assert s.population < 100

    def test_no_food_causes_deaths(self) -> None:
        """验证完全没有食物时产生饿死人口。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=100)
        s.stockpile["food"] = 0.0
        deaths = s.consume_food_for_population(0.5)
        assert deaths >= 1
        assert s.population < 100

    def test_population_never_below_zero(self) -> None:
        """验证人口不会降到 0 以下。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=1)
        s.stockpile["food"] = 0.0
        s.consume_food_for_population(0.5)
        assert s.population >= 0

    def test_food_consumed_even_if_insufficient(self) -> None:
        """验证食物不足时仍然消耗全部库存。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=100)
        s.stockpile["food"] = 10.0
        s.consume_food_for_population(0.5)
        assert s.stockpile["food"] == pytest.approx(0.0)

    def test_deaths_at_least_one_when_hungry(self) -> None:
        """验证食物不足时至少死亡 1 人。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=100)
        s.stockpile["food"] = 49.0  # 需要 50，差一点
        deaths = s.consume_food_for_population(0.5)
        assert deaths >= 1


class TestNaturalGrowth:
    """测试 natural_growth 自然增长。"""

    def test_basic_growth(self) -> None:
        """验证正常条件下人口增长。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=100, capacity=200)
        s.stockpile["food"] = 1000.0  # 人均 10，稀缺度 0
        growth = s.natural_growth(rate=0.05)
        assert growth >= 1
        assert s.population == 100 + growth

    def test_no_growth_at_capacity(self) -> None:
        """验证人口达到容量上限时不再增长。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=200, capacity=200)
        s.stockpile["food"] = 5000.0
        growth = s.natural_growth(rate=0.05)
        assert growth == 0
        assert s.population == 200

    def test_no_growth_when_scarce(self) -> None:
        """验证稀缺指数 > 0.5 时不增长。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=100, capacity=200)
        # 人均食物 = 2.0, scarcity = 1 - 2/5 = 0.6 > 0.5
        s.stockpile["food"] = 200.0
        growth = s.natural_growth(rate=0.05)
        assert growth == 0
        assert s.population == 100

    def test_growth_does_not_exceed_capacity(self) -> None:
        """验证增长后人口不超过容量上限。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=199, capacity=200)
        s.stockpile["food"] = 5000.0
        s.natural_growth(rate=0.5)
        assert s.population <= s.capacity

    def test_growth_at_least_one(self) -> None:
        """验证增长量至少为 1（向下取整后仍保证最低 1）。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=10, capacity=200)
        s.stockpile["food"] = 5000.0
        growth = s.natural_growth(rate=0.001)
        assert growth >= 1

    def test_growth_with_moderate_scarcity(self) -> None:
        """验证稀缺指数 > 0.5 时不增长。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=100, capacity=200)
        # 人均 = 2.4, scarcity = 1 - 2.4/5 = 0.52 > 0.5
        s.stockpile["food"] = 240.0
        growth = s.natural_growth(rate=0.05)
        assert growth == 0

    def test_growth_with_low_scarcity(self) -> None:
        """验证稀缺指数 < 0.5 时正常增长。"""
        s = Settlement(id=1, name="村", position=(0, 0), population=100, capacity=200)
        # 人均 = 3.0, scarcity = 1 - 3/5 = 0.4 < 0.5
        s.stockpile["food"] = 300.0
        growth = s.natural_growth(rate=0.05)
        assert growth >= 1
