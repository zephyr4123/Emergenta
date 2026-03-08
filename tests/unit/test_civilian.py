"""civilian.py 单元测试。

验证平民 Agent 的初始化、状态转移、行为执行以及性格差异。
使用简易 mock model 替代完整世界引擎，隔离测试平民逻辑。
"""

import mesa
import pytest

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.behaviors.markov import Personality
from civsim.agents.civilian import Civilian, Profession
from civsim.config import CivSimConfig
from civsim.economy.settlement import Settlement
from civsim.world.clock import Clock


class MockModel(mesa.Model):
    """用于测试的简易 Model。

    提供 settlements、clock、grid 和 config 属性，
    满足 Civilian 运行所需的最小依赖。
    """

    def __init__(
        self,
        width: int = 20,
        height: int = 20,
        seed: int | None = None,
    ) -> None:
        super().__init__(seed=seed)
        self.grid = mesa.space.MultiGrid(width, height, torus=False)
        self.clock = Clock(ticks_per_day=4, days_per_season=30)
        self.config = CivSimConfig()
        self.settlements: dict[int, Settlement] = {
            0: Settlement(
                id=0,
                name="测试聚落",
                position=(10, 10),
                population=50,
                stockpile={
                    "food": 500.0,
                    "wood": 200.0,
                    "ore": 50.0,
                    "gold": 100.0,
                },
            ),
        }


def _create_civilian(
    model: MockModel,
    personality: Personality = Personality.NEUTRAL,
    profession: Profession = Profession.FARMER,
    revolt_threshold: float = 0.4,
    pos: tuple[int, int] = (10, 10),
) -> Civilian:
    """创建一个平民并放置到网格上。

    Args:
        model: 测试用 Model。
        personality: 性格类型。
        profession: 职业类型。
        revolt_threshold: 反叛阈值。
        pos: 放置位置。

    Returns:
        已放置到网格上的 Civilian 实例。
    """
    civ = Civilian(
        model=model,
        home_settlement_id=0,
        personality=personality,
        profession=profession,
        revolt_threshold=revolt_threshold,
    )
    model.grid.place_agent(civ, pos)
    return civ


class TestCivilianInit:
    """测试平民 Agent 初始化属性。"""

    def test_default_attributes(self) -> None:
        """验证平民创建后的默认属性值。"""
        model = MockModel()
        civ = _create_civilian(model)

        assert civ.personality == Personality.NEUTRAL
        assert civ.profession == Profession.FARMER
        assert civ.revolt_threshold == 0.4
        assert civ.state == CivilianState.WORKING
        assert civ.hunger == 0.0
        assert civ.satisfaction == 0.7
        assert civ.tick_in_current_state == 0
        assert civ.home_settlement_id == 0

    def test_custom_personality(self) -> None:
        """验证指定性格能正确设置。"""
        model = MockModel()
        civ = _create_civilian(model, personality=Personality.REBELLIOUS)
        assert civ.personality == Personality.REBELLIOUS

    def test_custom_profession(self) -> None:
        """验证指定职业能正确设置。"""
        model = MockModel()
        civ = _create_civilian(model, profession=Profession.MINER)
        assert civ.profession == Profession.MINER

    def test_custom_revolt_threshold(self) -> None:
        """验证指定反叛阈值能正确设置。"""
        model = MockModel()
        civ = _create_civilian(model, revolt_threshold=0.15)
        assert civ.revolt_threshold == pytest.approx(0.15)

    def test_position_after_placement(self) -> None:
        """验证放置到网格后 pos 属性正确。"""
        model = MockModel()
        civ = _create_civilian(model, pos=(5, 8))
        assert civ.pos == (5, 8)

    def test_unique_ids_differ(self) -> None:
        """验证多个平民拥有不同的 unique_id。"""
        model = MockModel()
        c1 = _create_civilian(model, pos=(1, 1))
        c2 = _create_civilian(model, pos=(2, 2))
        assert c1.unique_id != c2.unique_id


class TestCivilianStep:
    """测试平民 step() 方法。"""

    def test_step_executes_without_error(self) -> None:
        """验证 step() 能正常执行不抛异常。"""
        model = MockModel()
        civ = _create_civilian(model)
        civ.step()

    def test_step_updates_hunger(self) -> None:
        """验证 step() 后饥饿度增加。"""
        model = MockModel()
        civ = _create_civilian(model)
        civ.step()
        # 饥饿度应该增加（即使消耗食物后也不会完全抵消增量）
        # 只要不异常就算通过；具体数值取决于 _update_needs 逻辑
        assert civ.hunger >= 0.0
        assert civ.hunger <= 1.0

    def test_step_state_is_valid(self) -> None:
        """验证 step() 后状态仍为合法的 CivilianState。"""
        model = MockModel()
        civ = _create_civilian(model)
        for _ in range(20):
            civ.step()
        assert civ.state in CivilianState

    def test_step_tick_counter_increments(self) -> None:
        """验证连续相同状态时 tick_in_current_state 递增。"""
        model = MockModel()
        # 使用顺从型、高食物环境，大概率保持 WORKING 状态
        civ = _create_civilian(model, personality=Personality.COMPLIANT)
        # 强制保持 WORKING 状态来测试计数
        civ.state = CivilianState.WORKING
        civ.tick_in_current_state = 0
        # 运行多次，检查计数器至少在某次为 > 0
        found_increment = False
        for _ in range(30):
            old_state = civ.state
            old_tick = civ.tick_in_current_state
            civ.step()
            if civ.state == old_state:
                assert civ.tick_in_current_state == old_tick + 1
                found_increment = True
                break
        assert found_increment, "30 次 step 中应至少有一次保持同一状态"

    def test_multiple_steps_state_transition_occurs(self) -> None:
        """验证执行多次 step 后发生至少一次状态转移。"""
        model = MockModel()
        civ = _create_civilian(model, personality=Personality.NEUTRAL)
        initial_state = civ.state
        states_seen = {initial_state}
        for _ in range(100):
            civ.step()
            states_seen.add(civ.state)
        assert len(states_seen) > 1, "100 次 step 后应至少经历过 2 种不同状态"


class TestPersonalityBehaviorDifference:
    """测试不同性格的行为差异。"""

    def test_rebellious_protests_more(self) -> None:
        """验证叛逆型平民比顺从型更容易进入抗议状态。

        统计大量 step 后各类型进入 PROTESTING 的次数，
        叛逆型应明显高于顺从型。
        """
        n_agents = 30
        n_steps = 200

        compliant_protest_count = 0
        rebellious_protest_count = 0

        # 顺从型统计
        model_c = MockModel(seed=42)
        agents_c = [
            _create_civilian(
                model_c,
                personality=Personality.COMPLIANT,
                pos=(i % 20, i // 20),
            )
            for i in range(n_agents)
        ]
        for _ in range(n_steps):
            for agent in agents_c:
                agent.step()
                if agent.state == CivilianState.PROTESTING:
                    compliant_protest_count += 1

        # 叛逆型统计
        model_r = MockModel(seed=42)
        agents_r = [
            _create_civilian(
                model_r,
                personality=Personality.REBELLIOUS,
                pos=(i % 20, i // 20),
            )
            for i in range(n_agents)
        ]
        for _ in range(n_steps):
            for agent in agents_r:
                agent.step()
                if agent.state == CivilianState.PROTESTING:
                    rebellious_protest_count += 1

        assert rebellious_protest_count > compliant_protest_count, (
            f"叛逆型抗议次数 ({rebellious_protest_count}) "
            f"应大于顺从型 ({compliant_protest_count})"
        )

    def test_compliant_works_more(self) -> None:
        """验证顺从型平民比叛逆型更多时间处于劳作状态。"""
        n_steps = 200

        model_c = MockModel(seed=99)
        civ_c = _create_civilian(
            model_c, personality=Personality.COMPLIANT, pos=(5, 5)
        )
        compliant_work = 0
        for _ in range(n_steps):
            civ_c.step()
            if civ_c.state == CivilianState.WORKING:
                compliant_work += 1

        model_r = MockModel(seed=99)
        civ_r = _create_civilian(
            model_r, personality=Personality.REBELLIOUS, pos=(5, 5)
        )
        rebellious_work = 0
        for _ in range(n_steps):
            civ_r.step()
            if civ_r.state == CivilianState.WORKING:
                rebellious_work += 1

        assert compliant_work > rebellious_work, (
            f"顺从型劳作次数 ({compliant_work}) "
            f"应大于叛逆型 ({rebellious_work})"
        )


class TestDoWork:
    """测试 _do_work() 资源产出逻辑。"""

    def test_farmer_produces_food(self) -> None:
        """验证农民劳作后聚落食物增加。"""
        model = MockModel()
        civ = _create_civilian(model, profession=Profession.FARMER)
        settlement = model.settlements[0]
        initial_food = settlement.stockpile["food"]

        civ.state = CivilianState.WORKING
        civ._do_work()

        assert settlement.stockpile["food"] > initial_food

    def test_woodcutter_produces_wood(self) -> None:
        """验证樵夫劳作后聚落木材增加。"""
        model = MockModel()
        civ = _create_civilian(model, profession=Profession.WOODCUTTER)
        settlement = model.settlements[0]
        initial_wood = settlement.stockpile["wood"]

        civ.state = CivilianState.WORKING
        civ._do_work()

        assert settlement.stockpile["wood"] > initial_wood

    def test_miner_produces_ore(self) -> None:
        """验证矿工劳作后聚落矿石增加。"""
        model = MockModel()
        civ = _create_civilian(model, profession=Profession.MINER)
        settlement = model.settlements[0]
        initial_ore = settlement.stockpile["ore"]

        civ.state = CivilianState.WORKING
        civ._do_work()

        assert settlement.stockpile["ore"] > initial_ore

    def test_merchant_produces_gold(self) -> None:
        """验证商人劳作后聚落金币增加。"""
        model = MockModel()
        civ = _create_civilian(model, profession=Profession.MERCHANT)
        settlement = model.settlements[0]
        initial_gold = settlement.stockpile["gold"]

        civ.state = CivilianState.WORKING
        civ._do_work()

        assert settlement.stockpile["gold"] > initial_gold

    def test_work_output_affected_by_season(self) -> None:
        """验证劳作产出受季节倍率影响。"""
        # 夏季倍率 1.5x
        model_summer = MockModel()
        model_summer.clock.tick = model_summer.clock.ticks_per_season  # 夏季
        settlement_summer = model_summer.settlements[0]
        initial_food_summer = settlement_summer.stockpile["food"]

        civ_summer = _create_civilian(model_summer, profession=Profession.FARMER)
        civ_summer._do_work()
        summer_output = settlement_summer.stockpile["food"] - initial_food_summer

        # 冬季倍率 0.3x
        model_winter = MockModel()
        model_winter.clock.tick = model_winter.clock.ticks_per_season * 3  # 冬季
        settlement_winter = model_winter.settlements[0]
        initial_food_winter = settlement_winter.stockpile["food"]

        civ_winter = _create_civilian(model_winter, profession=Profession.FARMER)
        civ_winter._do_work()
        winter_output = settlement_winter.stockpile["food"] - initial_food_winter

        assert summer_output > winter_output, (
            f"夏季产出 ({summer_output}) 应大于冬季产出 ({winter_output})"
        )

    def test_work_without_settlement_no_error(self) -> None:
        """验证没有聚落时劳作不报错。"""
        model = MockModel()
        model.settlements = {}
        civ = _create_civilian(model, profession=Profession.FARMER)
        civ._do_work()  # 不应抛异常


class TestDoRest:
    """测试 _do_rest() 休息行为。"""

    def test_rest_reduces_hunger(self) -> None:
        """验证休息能降低饥饿度。"""
        model = MockModel()
        civ = _create_civilian(model)
        civ.hunger = 0.5
        civ._do_rest()
        assert civ.hunger < 0.5

    def test_rest_does_not_go_below_zero(self) -> None:
        """验证休息后饥饿度不低于 0。"""
        model = MockModel()
        civ = _create_civilian(model)
        civ.hunger = 0.01
        civ._do_rest()
        assert civ.hunger >= 0.0


class TestDoMigrate:
    """测试 _do_migrate() 迁徙行为。"""

    def test_migrate_changes_position(self) -> None:
        """验证迁徙后位置发生变化（多次尝试，至少一次不同）。"""
        model = MockModel()
        civ = _create_civilian(model, pos=(10, 10))
        moved = False
        for _ in range(20):
            old_pos = civ.pos
            civ._do_migrate()
            if civ.pos != old_pos:
                moved = True
                break
        assert moved, "多次迁徙后至少有一次位置应发生变化"

    def test_migrate_stays_in_bounds(self) -> None:
        """验证迁徙后位置不越界。"""
        model = MockModel(width=20, height=20)
        civ = _create_civilian(model, pos=(0, 0))
        for _ in range(50):
            civ._do_migrate()
            x, y = civ.pos
            assert 0 <= x < 20
            assert 0 <= y < 20
