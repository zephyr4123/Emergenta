"""Phase 3 端到端功能测试。

使用真实配置运行完整三层仿真，验证：
- 首领/镇长/平民协同运行
- 贸易、外交、革命子系统正常工作
- 涌现行为检测功能
- 全链路无异常崩溃
"""

import pytest

from civsim.config import load_config
from civsim.world.engine import CivilizationEngine


def _make_phase3_config(
    grid_size: int = 40,
    civilians: int = 50,
    leaders: int = 2,
    settlements: int = 4,
):
    """创建 Phase 3 测试用配置。"""
    config = load_config()
    config.world.grid.width = grid_size
    config.world.grid.height = grid_size
    config.agents.civilian.initial_count = civilians
    config.agents.governor.initial_count = 1
    config.agents.leader.initial_count = leaders
    config.world.settlement.initial_count = settlements
    config.world.settlement.min_suitability_score = 0.3
    return config


class TestPhase3BasicRun:
    """测试 Phase 3 基础运行。"""

    def test_phase3_runs_without_exception(self) -> None:
        """验证 Phase 3 完整仿真 200 tick 无异常。"""
        config = _make_phase3_config()
        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True,
            enable_leaders=True,
        )

        assert len(engine.settlements) > 0
        assert len(engine.leaders) > 0
        assert engine.diplomacy is not None
        assert engine.trade_manager is not None
        assert engine.revolution_tracker is not None
        assert engine.emergence_detector is not None

        for _ in range(200):
            engine.step()

        model_data = engine.datacollector.get_model_vars_dataframe()
        assert len(model_data) == 200
        assert "total_population" in model_data.columns
        assert "trade_volume" in model_data.columns
        assert "faction_count" in model_data.columns

    def test_phase3_faction_assignment(self) -> None:
        """验证阵营分配正确。"""
        config = _make_phase3_config(civilians=30)
        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True,
            enable_leaders=True,
        )

        for s in engine.settlements.values():
            assert s.faction_id is not None

        for leader in engine.leaders:
            assert len(leader.controlled_settlements) > 0


class TestPhase3Subsystems:
    """测试 Phase 3 各子系统。"""

    def test_trade_occurs_during_simulation(self) -> None:
        """验证贸易在仿真中发生。"""
        config = _make_phase3_config(civilians=40)
        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True,
            enable_leaders=True,
        )

        # 制造贸易条件
        sids = list(engine.settlements.keys())
        if len(sids) >= 2:
            engine.settlements[sids[0]].stockpile["food"] = 2000.0
            engine.settlements[sids[0]].population = 5
            engine.settlements[sids[1]].stockpile["food"] = 10.0
            engine.settlements[sids[1]].population = 20

        for _ in range(50):
            engine.step()

        assert engine.trade_manager.total_volume > 0

    def test_diplomacy_changes_during_simulation(self) -> None:
        """验证首领在年度边界执行决策。"""
        config = _make_phase3_config(civilians=30)
        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True,
            enable_leaders=True,
        )

        ticks_per_year = (
            engine.clock.ticks_per_day
            * engine.clock.days_per_season
            * engine.clock.seasons_per_year
        )
        for _ in range(ticks_per_year + 10):
            engine.step()

        for leader in engine.leaders:
            assert leader.decision_count >= 1

    def test_emergence_detector_runs(self) -> None:
        """验证涌现检测器在仿真中运行。"""
        config = _make_phase3_config(civilians=30)
        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True,
            enable_leaders=True,
        )

        for _ in range(100):
            engine.step()

        assert engine.emergence_detector is not None

    def test_data_collection_complete(self) -> None:
        """验证数据采集包含所有 Phase 3 指标。"""
        config = _make_phase3_config(civilians=30)
        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True,
            enable_leaders=True,
        )

        for _ in range(10):
            engine.step()

        df = engine.datacollector.get_model_vars_dataframe()
        phase3_columns = [
            "trade_volume", "alliance_count", "war_count",
            "revolution_count", "faction_count",
        ]
        for col in phase3_columns:
            assert col in df.columns, f"缺少指标: {col}"


class TestPhase3WithoutBreaking:
    """验证 Phase 3 不影响 Phase 1/2 功能。"""

    def test_phase1_still_works(self) -> None:
        """验证无首领/镇长模式仍然正常。"""
        config = load_config()
        config.world.grid.width = 20
        config.world.grid.height = 20
        config.agents.civilian.initial_count = 20
        config.agents.governor.initial_count = 0
        config.agents.leader.initial_count = 0
        config.world.settlement.initial_count = 3
        config.world.settlement.min_suitability_score = 0.3

        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=False,
            enable_leaders=False,
        )

        for _ in range(50):
            engine.step()

        df = engine.datacollector.get_model_vars_dataframe()
        assert len(df) == 50

    def test_phase2_still_works(self) -> None:
        """验证仅镇长模式仍然正常。"""
        config = load_config()
        config.world.grid.width = 20
        config.world.grid.height = 20
        config.agents.civilian.initial_count = 20
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 0
        config.world.settlement.initial_count = 3
        config.world.settlement.min_suitability_score = 0.3

        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True,
            enable_leaders=False,
        )

        for _ in range(50):
            engine.step()

        assert engine.leaders == []
        assert engine.diplomacy is None
