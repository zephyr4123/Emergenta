"""Worker 纯函数计算单元测试。"""

import numpy as np
import pytest

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.behaviors.markov import Personality
from civsim.agents.civilian import Profession
from civsim.parallel.snapshots import (
    AgentSnapshot,
    EnvironmentSnapshot,
    SettlementSnapshot,
)
from civsim.parallel.worker import (
    _compute_behavior,
    _compute_satisfaction,
    compute_civilian_step,
    process_batch,
)


def _make_env(
    tax_rate: float = 0.1,
    security: float = 0.5,
    scarcity: float = 0.2,
    is_autumn: bool = False,
) -> EnvironmentSnapshot:
    """创建测试用环境快照。"""
    return EnvironmentSnapshot(
        settlements={
            1: SettlementSnapshot(
                id=1, tax_rate=tax_rate,
                security_level=security, scarcity_index=scarcity,
            ),
        },
        farm_multiplier=1.0,
        forest_multiplier=1.0,
        food_consumption_multiplier=1.0,
        is_autumn=is_autumn,
        hunger_decay_per_tick=0.02,
        food_per_civilian_per_tick=0.5,
    )


def _make_agent(
    unique_id: int = 1,
    personality: str = "neutral",
    profession: str = "farmer",
    state: int = 0,
    hunger: float = 0.1,
    satisfaction: float = 0.7,
    protest_ratio: float = 0.0,
) -> AgentSnapshot:
    """创建测试用 Agent 快照。"""
    return AgentSnapshot(
        unique_id=unique_id,
        personality=personality,
        profession=profession,
        revolt_threshold=0.4,
        state=state,
        hunger=hunger,
        satisfaction=satisfaction,
        home_settlement_id=1,
        tick_in_current_state=0,
        protest_ratio=protest_ratio,
    )


class TestComputeCivilianStep:
    """compute_civilian_step 纯函数测试。"""

    def test_basic_step(self) -> None:
        """测试基础 step 计算。"""
        agent = _make_agent()
        env = _make_env()
        result = compute_civilian_step(agent, env, rng_seed=42)

        assert result.agent_id == 1
        assert 0 <= result.new_state <= 6
        assert 0.0 <= result.new_hunger <= 1.0
        assert 0.0 <= result.new_satisfaction <= 1.0

    def test_deterministic_with_same_seed(self) -> None:
        """测试相同种子产生相同结果。"""
        agent = _make_agent()
        env = _make_env()

        r1 = compute_civilian_step(agent, env, rng_seed=123)
        r2 = compute_civilian_step(agent, env, rng_seed=123)

        assert r1.new_state == r2.new_state
        assert r1.new_hunger == r2.new_hunger
        assert r1.new_satisfaction == r2.new_satisfaction

    def test_different_seeds_may_differ(self) -> None:
        """测试不同种子可能产生不同结果。"""
        agent = _make_agent()
        env = _make_env()

        results = set()
        for seed in range(100):
            r = compute_civilian_step(agent, env, rng_seed=seed)
            results.add(r.new_state)

        # 应该有多种可能的状态
        assert len(results) > 1

    def test_hungry_agent_has_valid_hunger(self) -> None:
        """测试饥饿 Agent 的饥饿度更新。"""
        agent = _make_agent(hunger=0.9)
        env = _make_env()
        result = compute_civilian_step(agent, env, rng_seed=42)

        assert 0.0 <= result.new_hunger <= 1.0

    def test_missing_settlement_uses_defaults(self) -> None:
        """测试找不到聚落时使用默认值。"""
        agent = AgentSnapshot(
            unique_id=1, personality="neutral", profession="farmer",
            revolt_threshold=0.4, state=0, hunger=0.1,
            satisfaction=0.7, home_settlement_id=999,
            tick_in_current_state=0, protest_ratio=0.0,
        )
        env = _make_env()
        result = compute_civilian_step(agent, env, rng_seed=42)
        assert result.agent_id == 1


class TestComputeBehavior:
    """_compute_behavior 纯函数测试。"""

    def test_working_farmer_produces_food(self) -> None:
        """测试农民劳作产出食物。"""
        env = _make_env()
        resources, hunger_delta = _compute_behavior(
            CivilianState.WORKING, "farmer", env,
        )
        assert "food" in resources
        assert resources["food"] == 2.5  # base * 1.0 farm_multiplier

    def test_working_woodcutter_produces_wood(self) -> None:
        """测试伐木工产出木材。"""
        env = _make_env()
        resources, _ = _compute_behavior(
            CivilianState.WORKING, "woodcutter", env,
        )
        assert "wood" in resources
        assert resources["wood"] == 1.0

    def test_resting_reduces_hunger(self) -> None:
        """测试休息降低饥饿。"""
        env = _make_env()
        resources, hunger_delta = _compute_behavior(
            CivilianState.RESTING, "farmer", env,
        )
        assert len(resources) == 0
        assert hunger_delta == -0.05

    def test_trading_produces_gold(self) -> None:
        """测试交易产出金币。"""
        env = _make_env(is_autumn=False)
        resources, _ = _compute_behavior(
            CivilianState.TRADING, "merchant", env,
        )
        assert "gold" in resources
        assert resources["gold"] == pytest.approx(0.3)

    def test_trading_autumn_bonus(self) -> None:
        """测试秋季交易加成。"""
        env = _make_env(is_autumn=True)
        resources, _ = _compute_behavior(
            CivilianState.TRADING, "merchant", env,
        )
        assert resources["gold"] == pytest.approx(0.3 * 1.3)

    def test_protesting_no_output(self) -> None:
        """测试抗议无资源产出。"""
        env = _make_env()
        resources, hunger_delta = _compute_behavior(
            CivilianState.PROTESTING, "farmer", env,
        )
        assert len(resources) == 0
        assert hunger_delta == 0.0


class TestComputeSatisfaction:
    """_compute_satisfaction 纯函数测试。"""

    def test_high_scarcity_decreases_satisfaction(self) -> None:
        """测试高稀缺度降低满意度。"""
        sat = _compute_satisfaction(0.7, scarcity_index=0.6, tax_rate=0.1, hunger=0.1)
        assert sat < 0.7

    def test_low_scarcity_increases_satisfaction(self) -> None:
        """测试低稀缺度增加满意度。"""
        sat = _compute_satisfaction(0.7, scarcity_index=0.1, tax_rate=0.1, hunger=0.1)
        assert sat > 0.7

    def test_high_tax_decreases_satisfaction(self) -> None:
        """测试高税率降低满意度。"""
        sat = _compute_satisfaction(0.7, scarcity_index=0.2, tax_rate=0.8, hunger=0.1)
        assert sat < 0.7

    def test_high_hunger_decreases_satisfaction(self) -> None:
        """测试高饥饿降低满意度。"""
        sat = _compute_satisfaction(0.7, scarcity_index=0.2, tax_rate=0.1, hunger=0.8)
        assert sat < 0.7

    def test_satisfaction_clamped(self) -> None:
        """测试满意度被限制在 [0, 1]。"""
        sat = _compute_satisfaction(0.01, scarcity_index=0.9, tax_rate=0.9, hunger=0.9)
        assert sat >= 0.0

        sat = _compute_satisfaction(0.99, scarcity_index=0.0, tax_rate=0.0, hunger=0.0)
        assert sat <= 1.0


class TestProcessBatch:
    """process_batch 批量计算测试。"""

    def test_empty_batch(self) -> None:
        """测试空批次。"""
        env = _make_env()
        results = process_batch([], env)
        assert results == []

    def test_batch_produces_results_for_all(self) -> None:
        """测试批量计算为每个 Agent 产出结果。"""
        env = _make_env()
        agents = [_make_agent(unique_id=i) for i in range(10)]
        results = process_batch(agents, env)

        assert len(results) == 10
        ids = {r.agent_id for r in results}
        assert ids == set(range(10))

    def test_batch_deterministic(self) -> None:
        """测试批量计算确定性。"""
        env = _make_env()
        agents = [_make_agent(unique_id=i) for i in range(5)]

        r1 = process_batch(agents, env, tick_seed=100)
        r2 = process_batch(agents, env, tick_seed=100)

        for a, b in zip(r1, r2):
            assert a.new_state == b.new_state
            assert a.new_hunger == b.new_hunger
