"""SDCA 快照系统单元测试。"""

import pytest

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.behaviors.markov import Personality
from civsim.agents.civilian import Profession
from civsim.parallel.snapshots import (
    AgentSnapshot,
    EnvironmentSnapshot,
    SettlementSnapshot,
    StepResult,
    create_agent_snapshot,
    create_environment_snapshot,
)


class TestSettlementSnapshot:
    """SettlementSnapshot 不可变性与创建测试。"""

    def test_create_settlement_snapshot(self) -> None:
        """测试创建聚落快照。"""
        snap = SettlementSnapshot(
            id=1, tax_rate=0.2, security_level=0.6, scarcity_index=0.3,
        )
        assert snap.id == 1
        assert snap.tax_rate == 0.2
        assert snap.security_level == 0.6
        assert snap.scarcity_index == 0.3

    def test_immutability(self) -> None:
        """测试快照不可变性。"""
        snap = SettlementSnapshot(
            id=1, tax_rate=0.2, security_level=0.6, scarcity_index=0.3,
        )
        with pytest.raises(AttributeError):
            snap.tax_rate = 0.5  # type: ignore[misc]


class TestEnvironmentSnapshot:
    """EnvironmentSnapshot 创建与不可变性测试。"""

    def test_create_environment_snapshot(self) -> None:
        """测试创建环境快照。"""
        settlements = {
            1: SettlementSnapshot(id=1, tax_rate=0.1, security_level=0.5, scarcity_index=0.2),
        }
        snap = EnvironmentSnapshot(
            settlements=settlements,
            farm_multiplier=1.5,
            forest_multiplier=1.2,
            food_consumption_multiplier=1.0,
            is_autumn=False,
            hunger_decay_per_tick=0.02,
            food_per_civilian_per_tick=0.5,
        )
        assert snap.farm_multiplier == 1.5
        assert len(snap.settlements) == 1
        assert snap.settlements[1].tax_rate == 0.1

    def test_immutability(self) -> None:
        """测试环境快照不可变性。"""
        snap = EnvironmentSnapshot(
            settlements={},
            farm_multiplier=1.0,
            forest_multiplier=1.0,
            food_consumption_multiplier=1.0,
            is_autumn=False,
            hunger_decay_per_tick=0.02,
            food_per_civilian_per_tick=0.5,
        )
        with pytest.raises(AttributeError):
            snap.farm_multiplier = 2.0  # type: ignore[misc]


class TestAgentSnapshot:
    """AgentSnapshot 创建与不可变性测试。"""

    def test_create_agent_snapshot(self) -> None:
        """测试创建 Agent 快照。"""
        snap = AgentSnapshot(
            unique_id=42,
            personality=Personality.NEUTRAL.value,
            profession=Profession.FARMER.value,
            revolt_threshold=0.4,
            state=int(CivilianState.WORKING),
            hunger=0.3,
            satisfaction=0.7,
            home_settlement_id=1,
            tick_in_current_state=5,
            protest_ratio=0.1,
        )
        assert snap.unique_id == 42
        assert snap.personality == "neutral"
        assert snap.profession == "farmer"
        assert snap.state == 0

    def test_immutability(self) -> None:
        """测试 Agent 快照不可变性。"""
        snap = AgentSnapshot(
            unique_id=1, personality="neutral", profession="farmer",
            revolt_threshold=0.4, state=0, hunger=0.0,
            satisfaction=0.7, home_settlement_id=1,
            tick_in_current_state=0, protest_ratio=0.0,
        )
        with pytest.raises(AttributeError):
            snap.hunger = 0.5  # type: ignore[misc]


class TestStepResult:
    """StepResult 创建测试。"""

    def test_create_step_result(self) -> None:
        """测试创建 step 结果。"""
        result = StepResult(
            agent_id=1,
            new_state=int(CivilianState.RESTING),
            new_hunger=0.15,
            new_satisfaction=0.65,
            tick_in_current_state=0,
            resource_deposit={},
            food_consumed=0.0,
        )
        assert result.agent_id == 1
        assert result.new_state == 1
        assert result.new_hunger == 0.15

    def test_with_resources(self) -> None:
        """测试带资源产出的结果。"""
        result = StepResult(
            agent_id=1,
            new_state=int(CivilianState.WORKING),
            new_hunger=0.1,
            new_satisfaction=0.7,
            tick_in_current_state=3,
            resource_deposit={"food": 2.5},
            food_consumed=0.5,
        )
        assert result.resource_deposit["food"] == 2.5
        assert result.food_consumed == 0.5


class TestCreateFromEngine:
    """从引擎对象创建快照的测试。"""

    def test_create_environment_snapshot_from_engine(self, config_path: str) -> None:
        """测试从引擎创建环境快照。"""
        from civsim.config import load_config
        from civsim.world.engine import CivilizationEngine

        config = load_config(config_path)
        config.agents.civilian.initial_count = 10
        config.world.grid.width = 20
        config.world.grid.height = 20
        engine = CivilizationEngine(config=config, seed=42)

        snap = create_environment_snapshot(engine)

        assert len(snap.settlements) == len(engine.settlements)
        assert snap.farm_multiplier > 0
        assert snap.hunger_decay_per_tick > 0

    def test_create_agent_snapshot_from_civilian(self, config_path: str) -> None:
        """测试从平民 Agent 创建快照。"""
        from civsim.config import load_config
        from civsim.world.engine import CivilizationEngine

        config = load_config(config_path)
        config.agents.civilian.initial_count = 5
        config.world.grid.width = 20
        config.world.grid.height = 20
        engine = CivilizationEngine(config=config, seed=42)

        from civsim.agents.civilian import Civilian
        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        assert len(civilians) > 0

        snap = create_agent_snapshot(civilians[0])
        assert snap.unique_id == civilians[0].unique_id
        assert snap.personality == civilians[0].personality.value
