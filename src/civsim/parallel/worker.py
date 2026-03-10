"""平民 Agent 纯函数计算与 Ray Worker。

提取自 Civilian.step()，实现无副作用的状态转移与行为计算。
"""

from __future__ import annotations

import numpy as np

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.behaviors.markov import (
    Personality,
    compute_transition_matrix,
    sample_next_state,
)
from civsim.agents.civilian import Profession
from civsim.parallel.snapshots import (
    AgentSnapshot,
    EnvironmentSnapshot,
    StepResult,
)

# 职业→产出资源映射
_PROFESSION_OUTPUT: dict[str, str] = {
    Profession.FARMER.value: "food",
    Profession.WOODCUTTER.value: "wood",
    Profession.MINER.value: "ore",
    Profession.MERCHANT.value: "gold",
}


def compute_civilian_step(
    agent: AgentSnapshot,
    env: EnvironmentSnapshot,
    rng_seed: int | None = None,
) -> StepResult:
    """计算单个平民的 step 结果（纯函数）。

    Args:
        agent: Agent 快照。
        env: 环境快照。
        rng_seed: 随机数种子。为 None 时使用 agent_id。

    Returns:
        计算结果，包含新状态、资源变化等。
    """
    rng = np.random.default_rng(rng_seed if rng_seed is not None else agent.unique_id)

    # 1. 获取环境参数
    s_snap = env.settlements.get(agent.home_settlement_id)
    tax_rate = s_snap.tax_rate if s_snap else 0.1
    security = s_snap.security_level if s_snap else 0.5
    scarcity_index = s_snap.scarcity_index if s_snap else 0.0

    # 2. 计算动态转移矩阵
    personality = Personality(agent.personality)
    matrix = compute_transition_matrix(
        personality=personality,
        hunger=agent.hunger,
        tax_rate=tax_rate,
        security=security,
        protest_ratio=agent.protest_ratio,
        revolt_threshold=agent.revolt_threshold,
    )

    # 3. 状态转移
    current_state = CivilianState(agent.state)
    new_state = sample_next_state(current_state, matrix, rng)
    if new_state != current_state:
        tick_in_state = 0
    else:
        tick_in_state = agent.tick_in_current_state + 1

    # 4. 行为执行（纯计算）
    resource_deposit: dict[str, float] = {}
    food_consumed = 0.0

    resource_deposit, hunger_delta = _compute_behavior(
        new_state, agent.profession, env,
    )

    # 5. 更新饥饿度
    new_hunger = agent.hunger + env.hunger_decay_per_tick
    new_hunger += hunger_delta
    # 食物消耗
    if new_state in (CivilianState.WORKING, CivilianState.RESTING):
        food_needed = env.food_per_civilian_per_tick * env.food_consumption_multiplier
        food_consumed = food_needed
        new_hunger -= 0.06  # 吃饭后降低饥饿
    new_hunger = max(0.0, min(1.0, new_hunger))

    # 6. 更新满意度
    new_satisfaction = _compute_satisfaction(
        agent.satisfaction, scarcity_index, tax_rate, new_hunger,
    )

    return StepResult(
        agent_id=agent.unique_id,
        new_state=int(new_state),
        new_hunger=new_hunger,
        new_satisfaction=new_satisfaction,
        tick_in_current_state=tick_in_state,
        resource_deposit=resource_deposit,
        food_consumed=food_consumed,
    )


def _compute_behavior(
    state: CivilianState,
    profession_value: str,
    env: EnvironmentSnapshot,
) -> tuple[dict[str, float], float]:
    """计算行为产出（纯函数）。

    Args:
        state: 当前状态。
        profession_value: 职业枚举值。
        env: 环境快照。

    Returns:
        (资源存入字典, 饥饿变化量) 元组。
    """
    resource_deposit: dict[str, float] = {}
    hunger_delta = 0.0

    if state == CivilianState.WORKING:
        resource_key = _PROFESSION_OUTPUT.get(profession_value, "food")
        base_output = 2.5 if resource_key == "food" else 1.0
        if resource_key == "food":
            base_output *= env.farm_multiplier
        elif resource_key == "wood":
            base_output *= env.forest_multiplier
        resource_deposit[resource_key] = base_output

    elif state == CivilianState.RESTING:
        hunger_delta = -0.05

    elif state == CivilianState.TRADING:
        trade_multiplier = 1.3 if env.is_autumn else 1.0
        resource_deposit["gold"] = 0.3 * trade_multiplier

    return resource_deposit, hunger_delta


def _compute_satisfaction(
    current_satisfaction: float,
    scarcity_index: float,
    tax_rate: float,
    hunger: float,
) -> float:
    """计算更新后的满意度（纯函数）。

    Args:
        current_satisfaction: 当前满意度。
        scarcity_index: 食物稀缺指数。
        tax_rate: 当前税率。
        hunger: 当前饥饿度。

    Returns:
        更新后的满意度 [0, 1]。
    """
    sat = current_satisfaction

    if scarcity_index > 0.5:
        sat -= 0.05
    elif scarcity_index > 0.3:
        sat -= 0.02
    elif scarcity_index < 0.2:
        sat += 0.01

    if tax_rate > 0.3:
        sat -= 0.08 * tax_rate

    if hunger > 0.6:
        sat -= 0.03

    return max(0.0, min(1.0, sat))


def process_batch(
    agents: list[AgentSnapshot],
    env: EnvironmentSnapshot,
    tick_seed: int = 0,
) -> list[StepResult]:
    """批量计算平民 step（供 Worker 调用）。

    Args:
        agents: Agent 快照列表。
        env: 环境快照。
        tick_seed: 当前 tick 用于生成唯一种子。

    Returns:
        计算结果列表。
    """
    results: list[StepResult] = []
    for agent in agents:
        seed = agent.unique_id * 10007 + tick_seed
        result = compute_civilian_step(agent, env, rng_seed=seed)
        results.append(result)
    return results
