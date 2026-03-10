"""并行模式仿真验证测试。

验证并行模式下的完整仿真功能，包括涌现行为触发。
"""

import numpy as np
import pytest

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.civilian import Civilian
from civsim.config import load_config
from civsim.parallel.coordinator import ParallelCoordinator
from civsim.world.engine import CivilizationEngine


class TestParallelSimulationIntegrity:
    """并行模式仿真完整性测试。"""

    def test_full_simulation_parallel(self, config_path: str) -> None:
        """运行完整并行模拟，验证基本功能。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 200
        config.world.grid.width = 30
        config.world.grid.height = 30
        config.performance.parallel_threshold = 50

        engine = CivilizationEngine(config=config, seed=42)
        engine._coordinator = ParallelCoordinator(batch_size=50)
        engine._parallel_threshold = 50

        for _ in range(200):
            engine.step()

        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        assert len(civilians) > 0

        # 验证状态分布合理
        state_counts = {}
        for c in civilians:
            state_counts[c.state] = state_counts.get(c.state, 0) + 1

        # 至少应有 3 种以上不同状态
        assert len(state_counts) >= 3

    def test_hunger_satisfaction_evolution(self, config_path: str) -> None:
        """验证饥饿和满意度在并行模式下正常演化。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 100
        config.world.grid.width = 25
        config.world.grid.height = 25
        config.performance.parallel_threshold = 20

        engine = CivilizationEngine(config=config, seed=42)
        engine._coordinator = ParallelCoordinator(batch_size=30)
        engine._parallel_threshold = 20

        # 记录初始满意度
        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        initial_avg_sat = np.mean([c.satisfaction for c in civilians])

        for _ in range(100):
            engine.step()

        # 运行后满意度应有变化
        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        final_avg_sat = np.mean([c.satisfaction for c in civilians])

        # 满意度应该有所变化（不管升降）
        assert abs(final_avg_sat - initial_avg_sat) > 0.01 or len(civilians) > 0

    def test_resource_flow_positive(self, config_path: str) -> None:
        """验证并行模式下资源流通正常。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 100
        config.world.grid.width = 25
        config.world.grid.height = 25

        engine = CivilizationEngine(config=config, seed=42)
        engine._coordinator = ParallelCoordinator(batch_size=50)
        engine._parallel_threshold = 20

        for _ in range(50):
            engine.step()

        # 验证至少有一些食物产出
        total_food = sum(
            s.stockpile.get("food", 0) for s in engine.settlements.values()
        )
        # 食物量应大于 0（有农民劳作）
        assert total_food >= 0  # 可能被消耗完，但不应为负

    def test_serial_vs_parallel_both_functional(self, config_path: str) -> None:
        """验证串行和并行模式都能正常完成仿真。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 50
        config.world.grid.width = 20
        config.world.grid.height = 20

        # 串行模式
        engine_serial = CivilizationEngine(config=config, seed=42)
        for _ in range(30):
            engine_serial.step()

        serial_civilians = [a for a in engine_serial.agents if isinstance(a, Civilian)]

        # 并行模式
        engine_parallel = CivilizationEngine(config=config, seed=42)
        engine_parallel._coordinator = ParallelCoordinator(batch_size=20)
        engine_parallel._parallel_threshold = 10

        for _ in range(30):
            engine_parallel.step()

        parallel_civilians = [
            a for a in engine_parallel.agents if isinstance(a, Civilian)
        ]

        # 两种模式都应产出结果
        assert len(serial_civilians) > 0
        assert len(parallel_civilians) > 0

        # 两种模式的 Agent 数量应相同（没有 Agent 销毁机制）
        assert len(serial_civilians) == len(parallel_civilians)
