"""并行协调器单元测试。"""

import pytest

from civsim.parallel.coordinator import ParallelCoordinator, _is_ray_available


class TestParallelCoordinatorInit:
    """ParallelCoordinator 初始化测试。"""

    def test_default_init_local(self) -> None:
        """测试默认初始化（本地模式）。"""
        coord = ParallelCoordinator(num_workers=2, batch_size=50)
        assert coord.num_workers == 2
        assert coord.batch_size == 50
        assert coord.use_ray is False

    def test_ray_disabled_explicitly(self) -> None:
        """测试显式禁用 Ray。"""
        coord = ParallelCoordinator(enable_ray=False)
        assert coord.use_ray is False


class TestSplitBatches:
    """批次分割测试。"""

    def test_split_even(self) -> None:
        """测试均匀分割。"""
        from civsim.parallel.snapshots import AgentSnapshot

        coord = ParallelCoordinator(batch_size=5)
        agents = [
            AgentSnapshot(
                unique_id=i, personality="neutral", profession="farmer",
                revolt_threshold=0.4, state=0, hunger=0.1,
                satisfaction=0.7, home_settlement_id=1,
                tick_in_current_state=0, protest_ratio=0.0,
            )
            for i in range(10)
        ]
        batches = coord._split_batches(agents)
        assert len(batches) == 2
        assert len(batches[0]) == 5
        assert len(batches[1]) == 5

    def test_split_uneven(self) -> None:
        """测试不均匀分割。"""
        from civsim.parallel.snapshots import AgentSnapshot

        coord = ParallelCoordinator(batch_size=3)
        agents = [
            AgentSnapshot(
                unique_id=i, personality="neutral", profession="farmer",
                revolt_threshold=0.4, state=0, hunger=0.1,
                satisfaction=0.7, home_settlement_id=1,
                tick_in_current_state=0, protest_ratio=0.0,
            )
            for i in range(7)
        ]
        batches = coord._split_batches(agents)
        assert len(batches) == 3
        assert len(batches[0]) == 3
        assert len(batches[1]) == 3
        assert len(batches[2]) == 1

    def test_split_empty(self) -> None:
        """测试空列表。"""
        coord = ParallelCoordinator(batch_size=10)
        batches = coord._split_batches([])
        assert batches == []


class TestLocalExecution:
    """本地串行执行测试。"""

    def test_execute_with_engine(self, config_path: str) -> None:
        """测试通过引擎执行并行 step。"""
        from civsim.agents.civilian import Civilian
        from civsim.config import load_config
        from civsim.world.engine import CivilizationEngine

        config = load_config(config_path)
        config.agents.civilian.initial_count = 20
        config.world.grid.width = 20
        config.world.grid.height = 20
        engine = CivilizationEngine(config=config, seed=42)

        coord = ParallelCoordinator(batch_size=10)
        civilians = [a for a in engine.agents if isinstance(a, Civilian)]

        results = coord.execute_parallel_step(engine, civilians)

        assert len(results) == len(civilians)
        for r in results:
            assert 0 <= r.new_state <= 6
            assert 0.0 <= r.new_hunger <= 1.0
            assert 0.0 <= r.new_satisfaction <= 1.0

    def test_execute_empty_civilians(self, config_path: str) -> None:
        """测试空平民列表。"""
        from civsim.config import load_config
        from civsim.world.engine import CivilizationEngine

        config = load_config(config_path)
        config.agents.civilian.initial_count = 5
        config.world.grid.width = 20
        config.world.grid.height = 20
        engine = CivilizationEngine(config=config, seed=42)

        coord = ParallelCoordinator()
        results = coord.execute_parallel_step(engine, [])
        assert results == []


class TestShutdown:
    """资源清理测试。"""

    def test_shutdown_local(self) -> None:
        """测试本地模式关闭。"""
        coord = ParallelCoordinator()
        coord.shutdown()  # 不应抛出异常
        assert coord.use_ray is False
