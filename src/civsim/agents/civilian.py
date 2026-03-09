"""平民 Agent 完整实现。

基于 FSM + Markov 转移矩阵驱动的平民行为模型。
每个 tick：计算动态转移矩阵 → 状态转移 → 执行对应行为。
"""

from enum import Enum

import mesa
import numpy as np

from civsim.agents.base import BaseAgent
from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.behaviors.granovetter import compute_protest_ratio
from civsim.agents.behaviors.markov import (
    Personality,
    compute_transition_matrix,
    sample_next_state,
)


class Profession(Enum):
    """职业类型枚举。"""

    FARMER = "farmer"
    WOODCUTTER = "woodcutter"
    MINER = "miner"
    MERCHANT = "merchant"


# 职业→产出资源映射
_PROFESSION_OUTPUT: dict[Profession, str] = {
    Profession.FARMER: "food",
    Profession.WOODCUTTER: "wood",
    Profession.MINER: "ore",
    Profession.MERCHANT: "gold",
}


class Civilian(BaseAgent):
    """平民 Agent。

    Attributes:
        personality: 性格类型。
        profession: 职业类型。
        revolt_threshold: Granovetter 反叛阈值。
        state: 当前 FSM 状态。
        hunger: 饥饿度 [0, 1]。
        satisfaction: 满意度 [0, 1]。
        tick_in_current_state: 当前状态持续 tick 数。
    """

    def __init__(
        self,
        model: mesa.Model,
        home_settlement_id: int,
        personality: Personality,
        profession: Profession,
        revolt_threshold: float,
    ) -> None:
        super().__init__(model, home_settlement_id)
        self.personality = personality
        self.profession = profession
        self.revolt_threshold = revolt_threshold
        self.state = CivilianState.WORKING
        self.hunger: float = 0.0
        self.satisfaction: float = 0.7
        self.tick_in_current_state: int = 0
        self._rng = np.random.default_rng(self.unique_id)

    def step(self) -> None:
        """每 tick 执行：转移矩阵计算 → 状态转移 → 行为执行。"""
        # 1. 获取环境参数
        env = self._get_environment_params()

        # 2. 计算动态转移矩阵
        matrix = compute_transition_matrix(
            personality=self.personality,
            hunger=self.hunger,
            tax_rate=env["tax_rate"],
            security=env["security"],
            protest_ratio=env["protest_ratio"],
            revolt_threshold=self.revolt_threshold,
        )

        # 3. 状态转移
        new_state = sample_next_state(self.state, matrix, self._rng)
        if new_state != self.state:
            self.state = new_state
            self.tick_in_current_state = 0
        else:
            self.tick_in_current_state += 1

        # 4. 执行对应行为
        self._execute_behavior()

        # 5. 更新饥饿与满意度
        self._update_needs()

    def _get_environment_params(self) -> dict[str, float]:
        """从世界引擎获取当前环境参数。"""
        engine = self.model

        # 获取所属聚落信息
        settlement = None
        if hasattr(engine, "settlements"):
            settlement = engine.settlements.get(self.home_settlement_id)

        tax_rate = settlement.tax_rate if settlement else 0.1
        security = settlement.security_level if settlement else 0.5

        # 获取邻居状态
        neighbor_states = []
        if hasattr(engine, "grid") and self.pos is not None:
            neighbors = engine.grid.iter_neighbors(
                self.pos, moore=True, include_center=False, radius=3
            )
            neighbor_states = [
                n.state for n in neighbors
                if isinstance(n, Civilian)
            ]

        protest_ratio = compute_protest_ratio(neighbor_states)

        return {
            "tax_rate": tax_rate,
            "security": security,
            "protest_ratio": protest_ratio,
        }

    def _execute_behavior(self) -> None:
        """根据当前状态执行对应行为。"""
        if self.state == CivilianState.WORKING:
            self._do_work()
        elif self.state == CivilianState.RESTING:
            self._do_rest()
        elif self.state == CivilianState.TRADING:
            self._do_trade()
        elif self.state == CivilianState.MIGRATING:
            self._do_migrate()
        # SOCIALIZING / PROTESTING / FIGHTING 暂时无资源效果

    def _do_work(self) -> None:
        """劳作：根据职业产出资源到聚落仓库。"""
        resource_key = _PROFESSION_OUTPUT.get(self.profession, "food")
        base_output = 2.5 if resource_key == "food" else 1.0
        # 季节倍率
        if hasattr(self.model, "clock"):
            if resource_key == "food":
                base_output *= self.model.clock.farm_multiplier
            elif resource_key == "wood":
                base_output *= self.model.clock.forest_multiplier

        if hasattr(self.model, "settlements"):
            settlement = self.model.settlements.get(self.home_settlement_id)
            if settlement:
                settlement.deposit({resource_key: base_output})

    def _do_rest(self) -> None:
        """休息：恢复饥饿度。"""
        self.hunger = max(0.0, self.hunger - 0.05)

    def _do_trade(self) -> None:
        """交易：产出少量金币。"""
        if hasattr(self.model, "settlements"):
            settlement = self.model.settlements.get(self.home_settlement_id)
            if settlement:
                trade_multiplier = 1.0
                if hasattr(self.model, "clock"):
                    from civsim.world.clock import Season
                    if self.model.clock.current_season == Season.AUTUMN:
                        trade_multiplier = 1.3
                settlement.deposit({"gold": 0.3 * trade_multiplier})

    def _do_migrate(self) -> None:
        """迁徙：在网格上移动。"""
        if not hasattr(self.model, "grid") or self.pos is None:
            return
        neighbors = self.model.grid.get_neighborhood(
            self.pos, moore=True, include_center=False
        )
        if neighbors:
            new_pos = self._rng.choice(len(neighbors))
            self.model.grid.move_agent(self, neighbors[new_pos])

    def _update_needs(self) -> None:
        """更新饥饿度和满意度。"""
        # 饥饿每 tick 增加
        hunger_rate = 0.02
        if hasattr(self.model, "config"):
            hunger_rate = self.model.config.agents.civilian.hunger_decay_per_tick
        self.hunger = min(1.0, self.hunger + hunger_rate)

        # 劳作或休息时消耗食物降低饥饿
        if self.state in (CivilianState.WORKING, CivilianState.RESTING) and hasattr(
            self.model, "settlements"
        ):
                settlement = self.model.settlements.get(self.home_settlement_id)
                if settlement:
                    food_needed = 0.3
                    if hasattr(self.model, "config"):
                        food_needed = (
                            self.model.config.resources.consumption
                            .food_per_civilian_per_tick
                        )
                    if hasattr(self.model, "clock"):
                        food_needed *= self.model.clock.food_consumption_multiplier
                    eaten = settlement.withdraw_food(food_needed)
                    if eaten >= food_needed * 0.8:
                        self.hunger = max(0.0, self.hunger - 0.06)

        # 满意度更新
        self._update_satisfaction()

    def _update_satisfaction(self) -> None:
        """根据环境更新满意度。"""
        settlement = None
        if hasattr(self.model, "settlements"):
            settlement = self.model.settlements.get(self.home_settlement_id)

        if settlement is None:
            return

        # 食物充足 → 满意度上升，匮乏 → 满意度下降
        if settlement.scarcity_index > 0.5:
            self.satisfaction = max(0.0, self.satisfaction - 0.01)
        elif settlement.scarcity_index < 0.2:
            self.satisfaction = min(1.0, self.satisfaction + 0.01)

        # 高税率降低满意度（税率越高惩罚越重）
        if settlement.tax_rate > 0.3:
            penalty = 0.02 * settlement.tax_rate
            self.satisfaction = max(0.0, self.satisfaction - penalty)
