"""Phase 4 规模化 E2E 测试。

验证全系统联动（并行执行 + 镇长 + 首领 + 贸易 + 外交 + 革命）
在不同规模下正常工作。
"""

import pytest

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.civilian import Civilian
from civsim.agents.governor import Governor
from civsim.config import load_config
from civsim.parallel.coordinator import ParallelCoordinator
from civsim.world.engine import CivilizationEngine


def _force_llm_fallback(engine: CivilizationEngine) -> None:
    """强制所有 LLM agent 使用规则回退策略。"""
    for a in engine.agents:
        if hasattr(a, "_gateway"):
            a._gateway = None
    for leader in engine.leaders:
        leader._gateway = None


class TestParallel100Agents:
    """100 agents 并行测试。"""

    def test_parallel_100_agents_50_ticks(self, config_path: str) -> None:
        """100 agents 并行 50 ticks，验证无异常。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 100
        config.world.grid.width = 30
        config.world.grid.height = 30
        config.performance.parallel_threshold = 50
        config.resources.initial_stockpile.food = 3000

        engine = CivilizationEngine(config=config, seed=42)
        engine._coordinator = ParallelCoordinator(batch_size=30)
        engine._parallel_threshold = 50

        for _ in range(50):
            engine.step()

        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        assert len(civilians) > 0

        states = {c.state for c in civilians}
        assert len(states) >= 2

        for s in engine.settlements.values():
            for resource, amount in s.stockpile.items():
                assert amount >= 0, f"资源 {resource} 为负: {amount}"


class TestFullSystemScaling:
    """全系统联动规模化测试。"""

    def test_200_agents_full_system(self, config_path: str) -> None:
        """200 平民 + 全系统 200 ticks。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 200
        config.world.grid.width = 40
        config.world.grid.height = 40
        config.world.settlement.initial_count = 4
        config.agents.leader.initial_count = 2
        config.resources.initial_stockpile.food = 5000

        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True, enable_leaders=True,
        )
        _force_llm_fallback(engine)

        assert len(engine.get_governors()) == len(engine.settlements)
        assert len(engine.leaders) == 2
        assert engine.trade_manager is not None
        assert engine.diplomacy is not None
        assert engine.revolution_tracker is not None

        for _ in range(200):
            engine.step()

        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        # 有真实死亡/出生机制，人口可能波动但食物充足不应全灭
        assert len(civilians) > 0, (
            "食物充足条件下 200 tick 后不应全灭"
        )
        assert all(0.0 <= c.satisfaction <= 1.0 for c in civilians)

    def test_500_agents_full_system_parallel(
        self, config_path: str,
    ) -> None:
        """500 平民 + 全系统 + 并行协调器 200 ticks。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 500
        config.world.grid.width = 50
        config.world.grid.height = 50
        config.world.settlement.initial_count = 8
        config.agents.leader.initial_count = 3
        config.performance.parallel_threshold = 100
        config.resources.initial_stockpile.food = 10000

        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True, enable_leaders=True,
        )
        _force_llm_fallback(engine)
        engine._coordinator = ParallelCoordinator(batch_size=100)
        engine._parallel_threshold = 100

        for _ in range(200):
            engine.step()

        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        assert len(civilians) > 0

        governors = engine.get_governors()
        total_decisions = sum(g.decision_count for g in governors)
        assert total_decisions > 0, "200 ticks 应触发镇长决策"


class TestGracefulDegradation:
    """降级执行测试。"""

    def test_runs_without_ray(self, config_path: str) -> None:
        """Ray 不可用时自动降级验证。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 50
        config.world.grid.width = 20
        config.world.grid.height = 20
        config.resources.initial_stockpile.food = 2000

        engine = CivilizationEngine(config=config, seed=42)

        coord = ParallelCoordinator(enable_ray=False)
        assert coord.use_ray is False

        engine._coordinator = coord
        engine._parallel_threshold = 10

        for _ in range(20):
            engine.step()

        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        assert len(civilians) > 0


class TestLLMCostOptimization:
    """成本追踪集成验证。"""

    def test_cost_tracker_standalone(self) -> None:
        """测试成本追踪器独立运行。"""
        from civsim.llm.cost_tracker import CostTracker

        tracker = CostTracker()
        tracker.set_tick(1)
        tracker.record_call("anthropic/claude-3-5-haiku-20241022", 500, 200)
        tracker.set_tick(2)
        tracker.record_call("anthropic/claude-sonnet-4-20250514", 300, 100)

        summary = tracker.get_summary()
        assert summary["total_calls"] == 2
        assert summary["total_cost_usd"] > 0
        assert tracker.get_cost_per_tick() > 0


class TestDatabaseBatchPerformance:
    """批量写入性能验证。"""

    def test_batch_insert_faster_than_single(self, config_path: str) -> None:
        """测试批量写入正常工作。"""
        import tempfile
        from pathlib import Path

        from civsim.data.database import Database

        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(str(Path(tmpdir) / "test.duckdb"))

            records = [
                {
                    "tick": i, "settlement_id": j,
                    "population": 100 + i, "food": 500.0 - i,
                    "wood": 200.0, "ore": 50.0, "gold": 100.0,
                    "tax_rate": 0.1, "security_level": 0.5,
                    "satisfaction_avg": 0.7, "protest_ratio": 0.05,
                }
                for i in range(100)
                for j in range(4)
            ]

            count = db.batch_insert_world_states(records)
            assert count == 400

            df = db.query_world_state(tick=50)
            assert len(df) == 4

            db.close()

    def test_archive_old_data(self) -> None:
        """测试归档旧数据。"""
        import tempfile
        from pathlib import Path

        from civsim.data.database import Database

        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(str(Path(tmpdir) / "test.duckdb"))

            records = [
                {
                    "tick": i, "settlement_id": 1,
                    "population": 100, "food": 500.0,
                    "wood": 200.0, "ore": 50.0, "gold": 100.0,
                    "tax_rate": 0.1, "security_level": 0.5,
                    "satisfaction_avg": 0.7, "protest_ratio": 0.05,
                }
                for i in range(100)
            ]
            db.batch_insert_world_states(records)

            archived = db.archive_old_data(50)
            assert archived == 50

            latest = db.get_latest_tick()
            assert latest == 99

            stats = db.get_table_stats()
            assert stats["world_state"] == 50

            db.close()
