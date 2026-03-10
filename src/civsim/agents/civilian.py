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
        if hasattr(model, "config"):
            self.satisfaction = model.config.civilian_behavior.initial_satisfaction
        self.tick_in_current_state: int = 0
        self._rng = np.random.default_rng(self.unique_id)

    def step(self) -> None:
        """每 tick 执行：转移矩阵计算 → 状态转移 → 行为执行。"""
        # 1. 获取环境参数
        env = self._get_environment_params()

        # 2. 获取自适应乘数
        protest_mult = 1.0
        granovetter_mult = 1.0
        coefficients = None
        if hasattr(self.model, "adaptive_controller"):
            ctrl = self.model.adaptive_controller
            if ctrl is not None:
                protest_mult = ctrl.coefficients.markov_protest_multiplier
                granovetter_mult = (
                    ctrl.coefficients.granovetter_burst_multiplier
                )
        if hasattr(self.model, "config"):
            coefficients = self.model.config.markov_coefficients

        # 3. 计算动态转移矩阵
        matrix = compute_transition_matrix(
            personality=self.personality,
            hunger=self.hunger,
            tax_rate=env["tax_rate"],
            security=env["security"],
            protest_ratio=env["protest_ratio"],
            revolt_threshold=self.revolt_threshold,
            coefficients=coefficients,
            protest_multiplier=protest_mult,
            granovetter_multiplier=granovetter_mult,
        )

        # 4. 状态转移
        new_state = sample_next_state(self.state, matrix, self._rng)
        if new_state != self.state:
            self.state = new_state
            self.tick_in_current_state = 0
        else:
            self.tick_in_current_state += 1

        # 5. 执行对应行为
        self._execute_behavior()

        # 6. 更新饥饿与满意度
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
            radius = 3
            if hasattr(engine, "config"):
                radius = engine.config.engine_params.neighbor_radius
            neighbors = engine.grid.iter_neighbors(
                self.pos, moore=True, include_center=False, radius=radius
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
        if hasattr(self.model, "config"):
            cb = self.model.config.civilian_behavior
            base_output = cb.work_output_food if resource_key == "food" else cb.work_output_other
        else:
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
        recovery = 0.05
        if hasattr(self.model, "config"):
            recovery = self.model.config.civilian_behavior.rest_hunger_recovery
        self.hunger = max(0.0, self.hunger - recovery)

    def _do_trade(self) -> None:
        """交易：产出少量金币。"""
        if hasattr(self.model, "settlements"):
            settlement = self.model.settlements.get(self.home_settlement_id)
            if settlement:
                gold_output = 0.3
                if hasattr(self.model, "config"):
                    gold_output = self.model.config.civilian_behavior.trade_gold_output
                trade_multiplier = 1.0
                if hasattr(self.model, "clock"):
                    from civsim.world.clock import Season
                    if self.model.clock.current_season == Season.AUTUMN:
                        trade_multiplier = 1.3
                        if hasattr(self.model, "config"):
                            trade_multiplier = (
                                self.model.config.season_params.autumn_trade_bonus
                            )
                settlement.deposit({"gold": gold_output * trade_multiplier})

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
                    food_sat_ratio = 0.8
                    food_recovery = 0.06
                    if hasattr(self.model, "config"):
                        cb = self.model.config.civilian_behavior
                        food_sat_ratio = cb.food_satisfaction_ratio
                        food_recovery = cb.food_satiation_recovery
                    if eaten >= food_needed * food_sat_ratio:
                        self.hunger = max(0.0, self.hunger - food_recovery)

        # 满意度更新
        self._update_satisfaction()

    def _update_satisfaction(self) -> None:
        """根据环境更新满意度。

        使用配置系数（如可用），支持蜜月期恢复和自适应乘数。
        """
        settlement = None
        if hasattr(self.model, "settlements"):
            settlement = self.model.settlements.get(self.home_settlement_id)

        if settlement is None:
            return

        # 获取满意度系数配置
        sc = None
        if hasattr(self.model, "config"):
            sc = self.model.config.satisfaction_coefficients

        # 获取自适应恢复乘数
        recovery_mult = 1.0
        if hasattr(self.model, "adaptive_controller"):
            ctrl = self.model.adaptive_controller
            if ctrl is not None:
                recovery_mult = (
                    ctrl.coefficients.satisfaction_recovery_multiplier
                )

        # 食物充足/匮乏效应
        scarcity_high = sc.scarcity_high_penalty if sc else 0.10
        scarcity_mid = sc.scarcity_mid_penalty if sc else 0.04
        scarcity_low_rec = sc.scarcity_low_recovery if sc else 0.01

        if settlement.scarcity_index > 0.5:
            self.satisfaction = max(0.0, self.satisfaction - scarcity_high)
        elif settlement.scarcity_index > 0.3:
            self.satisfaction = max(0.0, self.satisfaction - scarcity_mid)
        elif settlement.scarcity_index < 0.2:
            self.satisfaction = min(
                1.0,
                self.satisfaction + scarcity_low_rec * recovery_mult,
            )

        # 高税率降低满意度
        tax_threshold = sc.tax_penalty_threshold if sc else 0.3
        tax_factor = sc.tax_penalty_factor if sc else 0.15
        if settlement.tax_rate > tax_threshold:
            penalty = tax_factor * settlement.tax_rate
            self.satisfaction = max(0.0, self.satisfaction - penalty)

        # 饥饿直接影响满意度
        hunger_threshold = sc.hunger_penalty_threshold if sc else 0.6
        hunger_pen = sc.hunger_penalty if sc else 0.08
        if self.hunger > hunger_threshold:
            self.satisfaction = max(0.0, self.satisfaction - hunger_pen)

        # 治安过高引发反感（警察国家效应）
        oppression_threshold = sc.oppression_threshold if sc else 0.8
        oppression_factor = sc.oppression_factor if sc else 0.03
        if settlement.security_level > oppression_threshold:
            oppression = (
                oppression_factor
                * (settlement.security_level - oppression_threshold) / 0.2
            )
            self.satisfaction = max(0.0, self.satisfaction - oppression)

        # 革命后蜜月期恢复
        if hasattr(self.model, "revolution_tracker"):
            tracker = self.model.revolution_tracker
            if tracker is not None:
                recovery = tracker.get_recovery(self.home_settlement_id)
                if recovery is not None:
                    boost = recovery.satisfaction_boost * recovery_mult
                    self.satisfaction = min(1.0, self.satisfaction + boost)
