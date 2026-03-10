"""SDCA 快照系统。

将引擎可变状态序列化为不可变数据结构，供并行 Worker 使用。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SettlementSnapshot:
    """聚落快照（不可变）。

    Attributes:
        id: 聚落唯一标识。
        tax_rate: 当前税率。
        security_level: 治安水平。
        scarcity_index: 食物稀缺指数。
    """

    id: int
    tax_rate: float
    security_level: float
    scarcity_index: float


@dataclass(frozen=True)
class EnvironmentSnapshot:
    """环境快照（不可变）。

    包含所有聚落信息和时钟信息，供纯函数计算使用。

    Attributes:
        settlements: 聚落 ID → 聚落快照映射。
        farm_multiplier: 当前季节农田产出倍率。
        forest_multiplier: 当前季节森林产出倍率。
        food_consumption_multiplier: 当前季节食物消耗倍率。
        is_autumn: 当前是否秋季（影响贸易）。
        hunger_decay_per_tick: 每 tick 饥饿增长率。
        food_per_civilian_per_tick: 每人每 tick 食物消耗量。
    """

    settlements: dict[int, SettlementSnapshot]
    farm_multiplier: float
    forest_multiplier: float
    food_consumption_multiplier: float
    is_autumn: bool
    hunger_decay_per_tick: float
    food_per_civilian_per_tick: float


@dataclass(frozen=True)
class AgentSnapshot:
    """平民 Agent 快照（不可变）。

    Attributes:
        unique_id: Agent 唯一标识。
        personality: 性格类型值（Personality.value）。
        profession: 职业类型值（Profession.value）。
        revolt_threshold: Granovetter 反叛阈值。
        state: 当前 FSM 状态值（int）。
        hunger: 饥饿度。
        satisfaction: 满意度。
        home_settlement_id: 所属聚落 ID。
        tick_in_current_state: 当前状态持续 tick 数。
        protest_ratio: 邻居抗议比例。
    """

    unique_id: int
    personality: str
    profession: str
    revolt_threshold: float
    state: int
    hunger: float
    satisfaction: float
    home_settlement_id: int
    tick_in_current_state: int
    protest_ratio: float


@dataclass(frozen=True)
class StepResult:
    """单个平民的 step 计算结果。

    Attributes:
        agent_id: Agent 唯一标识。
        new_state: 新 FSM 状态值（int）。
        new_hunger: 更新后的饥饿度。
        new_satisfaction: 更新后的满意度。
        tick_in_current_state: 状态持续 tick 数。
        resource_deposit: 产出资源（key→amount）。
        food_consumed: 消耗的食物量。
    """

    agent_id: int
    new_state: int
    new_hunger: float
    new_satisfaction: float
    tick_in_current_state: int
    resource_deposit: dict[str, float]
    food_consumed: float


def create_environment_snapshot(engine: object) -> EnvironmentSnapshot:
    """从引擎创建环境快照。

    Args:
        engine: CivilizationEngine 实例。

    Returns:
        不可变的环境快照。
    """
    settlement_snaps: dict[int, SettlementSnapshot] = {}
    if hasattr(engine, "settlements"):
        for sid, s in engine.settlements.items():
            settlement_snaps[sid] = SettlementSnapshot(
                id=sid,
                tax_rate=s.tax_rate,
                security_level=s.security_level,
                scarcity_index=s.scarcity_index,
            )

    farm_mult = 1.0
    forest_mult = 1.0
    food_mult = 1.0
    is_autumn = False
    if hasattr(engine, "clock"):
        from civsim.world.clock import Season

        farm_mult = engine.clock.farm_multiplier
        forest_mult = engine.clock.forest_multiplier
        food_mult = engine.clock.food_consumption_multiplier
        is_autumn = engine.clock.current_season == Season.AUTUMN

    hunger_decay = 0.02
    food_per_civ = 0.3
    if hasattr(engine, "config"):
        hunger_decay = engine.config.agents.civilian.hunger_decay_per_tick
        food_per_civ = engine.config.resources.consumption.food_per_civilian_per_tick

    return EnvironmentSnapshot(
        settlements=settlement_snaps,
        farm_multiplier=farm_mult,
        forest_multiplier=forest_mult,
        food_consumption_multiplier=food_mult,
        is_autumn=is_autumn,
        hunger_decay_per_tick=hunger_decay,
        food_per_civilian_per_tick=food_per_civ,
    )


def create_agent_snapshot(
    agent: object,
    protest_ratio: float = 0.0,
) -> AgentSnapshot:
    """从平民 Agent 创建快照。

    Args:
        agent: Civilian 实例。
        protest_ratio: 预计算的邻居抗议比例。

    Returns:
        不可变的 Agent 快照。
    """
    return AgentSnapshot(
        unique_id=agent.unique_id,
        personality=agent.personality.value,
        profession=agent.profession.value,
        revolt_threshold=agent.revolt_threshold,
        state=int(agent.state),
        hunger=agent.hunger,
        satisfaction=agent.satisfaction,
        home_settlement_id=agent.home_settlement_id,
        tick_in_current_state=agent.tick_in_current_state,
        protest_ratio=protest_ratio,
    )


def create_agent_snapshots_batch(
    engine: object,
    civilians: list[object],
) -> list[AgentSnapshot]:
    """批量创建平民 Agent 快照。

    包含预计算每个 Agent 的邻居抗议比例。

    Args:
        engine: CivilizationEngine 实例。
        civilians: Civilian Agent 列表。

    Returns:
        Agent 快照列表。
    """
    from civsim.agents.behaviors.granovetter import compute_protest_ratio
    from civsim.agents.civilian import Civilian

    snapshots: list[AgentSnapshot] = []
    for agent in civilians:
        pr = 0.0
        if hasattr(engine, "grid") and agent.pos is not None:
            neighbors = engine.grid.iter_neighbors(
                agent.pos, moore=True, include_center=False, radius=3,
            )
            neighbor_states = [
                n.state for n in neighbors if isinstance(n, Civilian)
            ]
            pr = compute_protest_ratio(neighbor_states)
        snapshots.append(create_agent_snapshot(agent, pr))
    return snapshots
