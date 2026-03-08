"""resources.py 单元测试。

验证资源类型枚举、资源储备创建和资源增减操作。
"""


from civsim.economy.resources import (
    RESOURCE_NAMES,
    ResourceType,
    add_resources,
    create_empty_stockpile,
    create_stockpile,
    subtract_resources,
)


class TestResourceType:
    """测试 ResourceType 枚举。"""

    def test_all_types_defined(self) -> None:
        """验证四种资源类型全部定义。"""
        assert ResourceType.FOOD.value == "food"
        assert ResourceType.WOOD.value == "wood"
        assert ResourceType.ORE.value == "ore"
        assert ResourceType.GOLD.value == "gold"

    def test_enum_count(self) -> None:
        """验证资源类型数量为 4。"""
        assert len(ResourceType) == 4

    def test_resource_names_list(self) -> None:
        """验证 RESOURCE_NAMES 与枚举一致。"""
        assert RESOURCE_NAMES == ["food", "wood", "ore", "gold"]


class TestCreateEmptyStockpile:
    """测试 create_empty_stockpile 全零资源。"""

    def test_all_values_zero(self) -> None:
        """验证空储备中所有资源为 0。"""
        stockpile = create_empty_stockpile()
        for key in RESOURCE_NAMES:
            assert stockpile[key] == 0.0

    def test_contains_all_resource_types(self) -> None:
        """验证空储备包含全部四种资源键。"""
        stockpile = create_empty_stockpile()
        assert set(stockpile.keys()) == {"food", "wood", "ore", "gold"}

    def test_returns_new_dict_each_call(self) -> None:
        """验证每次调用返回独立的字典实例。"""
        s1 = create_empty_stockpile()
        s2 = create_empty_stockpile()
        assert s1 is not s2


class TestCreateStockpile:
    """测试 create_stockpile 自定义初始值。"""

    def test_default_all_zero(self) -> None:
        """验证不传参时所有资源为 0。"""
        stockpile = create_stockpile()
        for key in RESOURCE_NAMES:
            assert stockpile[key] == 0.0

    def test_custom_values(self) -> None:
        """验证自定义参数正确设置。"""
        stockpile = create_stockpile(food=100.0, wood=50.0, ore=25.0, gold=10.0)
        assert stockpile["food"] == 100.0
        assert stockpile["wood"] == 50.0
        assert stockpile["ore"] == 25.0
        assert stockpile["gold"] == 10.0

    def test_partial_custom(self) -> None:
        """验证仅设置部分资源时其余为 0。"""
        stockpile = create_stockpile(food=42.0)
        assert stockpile["food"] == 42.0
        assert stockpile["wood"] == 0.0
        assert stockpile["ore"] == 0.0
        assert stockpile["gold"] == 0.0


class TestAddResources:
    """测试 add_resources 资源叠加。"""

    def test_basic_addition(self) -> None:
        """验证基础叠加逻辑。"""
        target = create_stockpile(food=10.0, wood=5.0)
        source = create_stockpile(food=20.0, wood=15.0, ore=3.0)
        add_resources(target, source)
        assert target["food"] == 30.0
        assert target["wood"] == 20.0
        assert target["ore"] == 3.0
        assert target["gold"] == 0.0

    def test_add_to_empty(self) -> None:
        """验证向空储备叠加。"""
        target = create_empty_stockpile()
        source = create_stockpile(gold=100.0)
        add_resources(target, source)
        assert target["gold"] == 100.0

    def test_add_empty_source(self) -> None:
        """验证叠加空来源不改变目标。"""
        target = create_stockpile(food=50.0, wood=30.0)
        source = create_empty_stockpile()
        add_resources(target, source)
        assert target["food"] == 50.0
        assert target["wood"] == 30.0

    def test_in_place_modification(self) -> None:
        """验证 add_resources 是原地修改 target。"""
        target = create_stockpile(food=10.0)
        original_id = id(target)
        add_resources(target, create_stockpile(food=5.0))
        assert id(target) == original_id
        assert target["food"] == 15.0


class TestSubtractResources:
    """测试 subtract_resources 资源扣除。"""

    def test_basic_subtraction(self) -> None:
        """验证基础扣除逻辑。"""
        target = create_stockpile(food=50.0, wood=30.0, ore=10.0, gold=20.0)
        amount = create_stockpile(food=20.0, wood=10.0)
        actual = subtract_resources(target, amount)
        assert target["food"] == 30.0
        assert target["wood"] == 20.0
        assert actual["food"] == 20.0
        assert actual["wood"] == 10.0

    def test_subtract_more_than_available(self) -> None:
        """验证扣除量超过库存时不低于 0。"""
        target = create_stockpile(food=10.0)
        amount = create_stockpile(food=999.0)
        actual = subtract_resources(target, amount)
        assert target["food"] == 0.0
        assert actual["food"] == 10.0

    def test_subtract_exact_amount(self) -> None:
        """验证恰好扣完时资源归零。"""
        target = create_stockpile(ore=25.0)
        amount = create_stockpile(ore=25.0)
        actual = subtract_resources(target, amount)
        assert target["ore"] == 0.0
        assert actual["ore"] == 25.0

    def test_subtract_zero(self) -> None:
        """验证扣除 0 不改变库存。"""
        target = create_stockpile(food=100.0)
        amount = create_empty_stockpile()
        actual = subtract_resources(target, amount)
        assert target["food"] == 100.0
        assert actual["food"] == 0.0

    def test_returns_actual_deduction(self) -> None:
        """验证返回值为实际扣除量。"""
        target = create_stockpile(food=5.0, gold=3.0)
        amount = create_stockpile(food=10.0, gold=1.0)
        actual = subtract_resources(target, amount)
        assert actual["food"] == 5.0
        assert actual["gold"] == 1.0
        assert actual["wood"] == 0.0
        assert actual["ore"] == 0.0

    def test_in_place_modification(self) -> None:
        """验证 subtract_resources 是原地修改 target。"""
        target = create_stockpile(food=50.0)
        original_id = id(target)
        subtract_resources(target, create_stockpile(food=10.0))
        assert id(target) == original_id
        assert target["food"] == 40.0
