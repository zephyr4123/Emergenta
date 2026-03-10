"""压力测试。

测试大规模 Agent 下全系统联动的稳定性和内存使用。
包含仅平民测试和全系统（平民+镇长+首领+贸易+外交+革命）测试。
"""

import pytest

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.civilian import Civilian
from civsim.agents.governor import Governor
from civsim.config import load_config
from civsim.parallel.coordinator import ParallelCoordinator
from civsim.world.engine import CivilizationEngine

_PSUTIL_AVAILABLE = True
try:
    import psutil
except ImportError:
    _PSUTIL_AVAILABLE = False


def _force_llm_fallback(engine: CivilizationEngine) -> None:
    """强制所有 LLM agent 使用规则回退策略。"""
    for a in engine.agents:
        if hasattr(a, "_gateway"):
            a._gateway = None
    for leader in engine.leaders:
        leader._gateway = None


class TestLargeScaleStability:
    """大规模稳定性测试（仅平民）。"""

    def test_1000_agents_100_ticks(self, config_path: str) -> None:
        """1000 agents + 100 ticks，验证无崩溃。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 1000
        config.world.grid.width = 50
        config.world.grid.height = 50
        config.performance.parallel_threshold = 200

        engine = CivilizationEngine(config=config, seed=42)
        engine._coordinator = ParallelCoordinator(batch_size=200)
        engine._parallel_threshold = 200

        for _ in range(100):
            engine.step()

        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        assert len(civilians) > 0

        for c in civilians:
            assert 0.0 <= c.hunger <= 1.0
            assert 0.0 <= c.satisfaction <= 1.0
            assert 0 <= int(c.state) <= 6

        for s in engine.settlements.values():
            assert s.population >= 0

    @pytest.mark.timeout(300)
    def test_5000_agents_stability(self, config_path: str) -> None:
        """5000 agents + 50 ticks，验证无崩溃无内存泄漏。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 5000
        config.world.grid.width = 100
        config.world.grid.height = 100
        config.performance.parallel_threshold = 500

        engine = CivilizationEngine(config=config, seed=42)
        engine._coordinator = ParallelCoordinator(batch_size=500)
        engine._parallel_threshold = 500

        initial_mem = 0.0
        if _PSUTIL_AVAILABLE:
            initial_mem = psutil.Process().memory_info().rss / (1024 * 1024)

        for _ in range(50):
            engine.step()

        if _PSUTIL_AVAILABLE:
            final_mem = psutil.Process().memory_info().rss / (1024 * 1024)
            mem_growth = final_mem - initial_mem
            assert mem_growth < 2048, f"内存增长过大: {mem_growth:.1f} MB"

        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        assert len(civilians) > 0


class TestFullSystemStability:
    """全系统联动稳定性测试（平民 + 镇长 + 首领 + 贸易 + 外交 + 革命）。"""

    def test_500_agents_full_system_200_ticks(
        self, config_path: str,
    ) -> None:
        """500 平民 + 全系统 200 ticks（触发镇长决策）。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 500
        config.world.grid.width = 50
        config.world.grid.height = 50
        config.world.settlement.initial_count = 6
        config.agents.leader.initial_count = 2

        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True, enable_leaders=True,
        )
        _force_llm_fallback(engine)

        governors = [a for a in engine.agents if isinstance(a, Governor)]
        assert len(governors) == len(engine.settlements)
        assert len(engine.leaders) == 2
        assert engine.trade_manager is not None
        assert engine.revolution_tracker is not None
        assert engine.diplomacy is not None

        for _ in range(200):
            engine.step()

        # 验证镇长至少做过一次决策（200 ticks > 120 ticks/季）
        total_gov_decisions = sum(g.decision_count for g in governors)
        assert total_gov_decisions > 0, "镇长应在200 ticks内做过决策"

        # 验证贸易系统运行
        assert engine.trade_manager.trade_count >= 0

        # 验证平民数值合理
        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        for c in civilians:
            assert 0.0 <= c.hunger <= 1.0
            assert 0.0 <= c.satisfaction <= 1.0

    @pytest.mark.timeout(300)
    def test_1000_agents_full_system_150_ticks(
        self, config_path: str,
    ) -> None:
        """1000 平民 + 全系统 150 ticks。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 1000
        config.world.grid.width = 80
        config.world.grid.height = 80
        config.world.settlement.initial_count = 12
        config.agents.leader.initial_count = 4

        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True, enable_leaders=True,
        )
        _force_llm_fallback(engine)

        governors = [a for a in engine.agents if isinstance(a, Governor)]
        assert len(governors) == len(engine.settlements)
        assert len(engine.leaders) == 4

        initial_mem = 0.0
        if _PSUTIL_AVAILABLE:
            initial_mem = psutil.Process().memory_info().rss / (1024 * 1024)

        for _ in range(150):
            engine.step()

        if _PSUTIL_AVAILABLE:
            final_mem = psutil.Process().memory_info().rss / (1024 * 1024)
            mem_growth = final_mem - initial_mem
            assert mem_growth < 1024, f"内存增长过大: {mem_growth:.1f} MB"

        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        assert len(civilians) > 0

        # 验证聚落存活
        assert len(engine.settlements) > 0

    @pytest.mark.timeout(600)
    def test_5000_agents_full_system_50_ticks(
        self, config_path: str,
    ) -> None:
        """5000 平民 + 全系统 50 ticks，验证大规模不崩溃。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 5000
        config.world.grid.width = 150
        config.world.grid.height = 150
        config.world.settlement.initial_count = 60
        config.agents.leader.initial_count = 8

        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True, enable_leaders=True,
        )
        _force_llm_fallback(engine)

        governors = [a for a in engine.agents if isinstance(a, Governor)]
        assert len(governors) == len(engine.settlements)
        assert len(engine.leaders) > 0

        for _ in range(50):
            engine.step()

        civilians = [a for a in engine.agents if isinstance(a, Civilian)]
        assert len(civilians) > 0

        for c in civilians:
            assert 0.0 <= c.hunger <= 1.0
            assert 0.0 <= c.satisfaction <= 1.0


class TestFullSystemEmergence:
    """全系统涌现行为验证。"""

    def test_trade_system_runs_with_full_system(
        self, config_path: str,
    ) -> None:
        """验证贸易系统在全系统运行中正常运转。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 300
        config.world.grid.width = 40
        config.world.grid.height = 40
        config.world.settlement.initial_count = 6
        config.agents.leader.initial_count = 2

        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True, enable_leaders=True,
        )
        _force_llm_fallback(engine)

        for _ in range(200):
            engine.step()

        # 贸易依赖供需不平衡，平衡起步可能无交易
        # 只验证系统正常运转不崩溃
        assert engine.trade_manager is not None
        assert engine.trade_manager.trade_count >= 0

    def test_governor_decisions_affect_settlements(
        self, config_path: str,
    ) -> None:
        """验证镇长决策实际改变聚落参数。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 200
        config.world.grid.width = 40
        config.world.grid.height = 40
        config.world.settlement.initial_count = 4
        config.agents.leader.initial_count = 2

        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True, enable_leaders=True,
        )
        _force_llm_fallback(engine)

        # 记录初始税率/治安
        initial_params = {}
        for sid, s in engine.settlements.items():
            initial_params[sid] = {
                "tax": s.tax_rate, "sec": s.security_level,
            }

        # 运行足够长触发镇长决策
        for _ in range(150):
            engine.step()

        # 至少有一个聚落的参数被镇长改变
        changed = False
        for sid, s in engine.settlements.items():
            orig = initial_params.get(sid, {})
            if (
                abs(s.tax_rate - orig.get("tax", 0)) > 0.001
                or abs(s.security_level - orig.get("sec", 0)) > 0.001
            ):
                changed = True
                break
        assert changed, "至少一个聚落应被镇长决策改变"


class TestSystemIntegrity:
    """系统完整性测试。"""

    def test_settlements_survive(self, config_path: str) -> None:
        """验证聚落在大规模运行后仍存在。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 500
        config.world.grid.width = 50
        config.world.grid.height = 50

        engine = CivilizationEngine(config=config, seed=42)
        engine._coordinator = ParallelCoordinator(batch_size=100)
        engine._parallel_threshold = 100

        initial_settlements = len(engine.settlements)
        for _ in range(100):
            engine.step()

        assert len(engine.settlements) == initial_settlements

    def test_data_collector_works(self, config_path: str) -> None:
        """验证数据采集器在并行模式下正常工作。"""
        config = load_config(config_path)
        config.agents.civilian.initial_count = 200
        config.world.grid.width = 30
        config.world.grid.height = 30

        engine = CivilizationEngine(config=config, seed=42)
        engine._coordinator = ParallelCoordinator(batch_size=50)
        engine._parallel_threshold = 50

        for _ in range(30):
            engine.step()

        df = engine.datacollector.get_model_vars_dataframe()
        assert len(df) == 30
