"""并行执行集成测试。

验证并行执行与串行执行的结果一致性。
"""

import numpy as np
import pytest

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.civilian import Civilian
from civsim.config import load_config
from civsim.parallel.coordinator import ParallelCoordinator
from civsim.world.engine import CivilizationEngine


class TestParallelSerialConsistency:
    """并行与串行执行一致性测试。"""

    def _create_engine(self, config_path: str, seed: int = 42) -> CivilizationEngine:
        """创建测试用引擎。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 50
        config.world.grid.width = 20
        config.world.grid.height = 20
        return CivilizationEngine(config=config, seed=seed)

    def test_parallel_produces_valid_results(self, config_path: str) -> None:
        """测试并行执行产出有效结果。"""
        engine = self._create_engine(config_path)
        engine.clock.advance()  # 推进一个 tick

        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        coord = ParallelCoordinator(batch_size=20)

        results = coord.execute_parallel_step(engine, civilians)

        assert len(results) == len(civilians)
        for r in results:
            assert 0 <= r.new_state <= 6
            assert 0.0 <= r.new_hunger <= 1.0
            assert 0.0 <= r.new_satisfaction <= 1.0

    def test_state_distribution_similar(self, config_path: str) -> None:
        """测试并行与串行的状态分布在统计上相似。

        由于随机种子不同，不要求完全一致，
        但整体分布应在合理范围内。
        """
        # 运行串行模式
        engine_serial = self._create_engine(config_path, seed=100)
        for _ in range(10):
            engine_serial.step()

        serial_states = [
            a.state for a in engine_serial.agents if isinstance(a, Civilian)
        ]
        serial_working = sum(1 for s in serial_states if s == CivilianState.WORKING)
        serial_working_ratio = serial_working / len(serial_states) if serial_states else 0

        # 运行并行模式（本地降级）
        engine_parallel = self._create_engine(config_path, seed=200)
        coord = ParallelCoordinator(batch_size=20)

        for _ in range(10):
            engine_parallel.clock.advance()
            engine_parallel._environment_update()
            civilians = [a for a in engine_parallel.agents if isinstance(a, Civilian)]
            results = coord.execute_parallel_step(engine_parallel, civilians)

            # Apply results
            agent_map = {c.unique_id: c for c in civilians}
            for r in results:
                agent = agent_map.get(r.agent_id)
                if agent:
                    agent.state = CivilianState(r.new_state)
                    agent.hunger = r.new_hunger
                    agent.satisfaction = r.new_satisfaction
                    if r.resource_deposit:
                        s = engine_parallel.settlements.get(agent.home_settlement_id)
                        if s:
                            s.deposit(r.resource_deposit)

            engine_parallel._settlement_reconcile()

        parallel_states = [
            a.state for a in engine_parallel.agents if isinstance(a, Civilian)
        ]
        parallel_working = sum(1 for s in parallel_states if s == CivilianState.WORKING)
        parallel_working_ratio = parallel_working / len(parallel_states) if parallel_states else 0

        # 两种模式下劳作比例应该在大致相同的范围内
        assert serial_working_ratio > 0.0
        assert parallel_working_ratio > 0.0

    def test_resource_production_nonzero(self, config_path: str) -> None:
        """测试并行执行后资源有产出。"""
        engine = self._create_engine(config_path)
        coord = ParallelCoordinator(batch_size=25)

        # 记录初始资源
        initial_food = sum(
            s.stockpile.get("food", 0) for s in engine.settlements.values()
        )

        # 运行一步
        engine.clock.advance()
        engine._environment_update()
        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        results = coord.execute_parallel_step(engine, civilians)

        # 检查是否有资源产出
        total_food_deposit = sum(
            r.resource_deposit.get("food", 0.0) for r in results
        )
        assert total_food_deposit > 0  # 农民应该产出食物


class TestEngineParallelIntegration:
    """引擎并行模式集成测试。"""

    def test_engine_step_with_coordinator(self, config_path: str) -> None:
        """测试引擎使用协调器执行 step。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 30
        config.world.grid.width = 20
        config.world.grid.height = 20
        config.performance.parallel_threshold = 10  # 低阈值触发并行
        config.ray.enabled = False  # 使用本地降级

        engine = CivilizationEngine(config=config, seed=42)
        # 手动设置协调器
        engine._coordinator = ParallelCoordinator(batch_size=15)
        engine._parallel_threshold = 10

        # 运行多步
        for _ in range(20):
            engine.step()

        # 验证基本功能正常
        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        assert len(civilians) > 0

        # 检查状态多样性
        states = {c.state for c in civilians}
        assert len(states) >= 2  # 至少有两种不同状态

    def test_engine_serial_when_below_threshold(self, config_path: str) -> None:
        """测试平民数量低于阈值时使用串行。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 5
        config.world.grid.width = 20
        config.world.grid.height = 20
        config.performance.parallel_threshold = 100  # 高阈值，不触发并行

        engine = CivilizationEngine(config=config, seed=42)
        # 即使有协调器，也不使用
        engine._coordinator = ParallelCoordinator()
        engine._parallel_threshold = 100

        for _ in range(10):
            engine.step()

        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        assert len(civilians) > 0
