"""端到端测试：Phase 1 基础仿真。

运行完整的 CivilizationEngine 仿真 50 tick，验证：
- 无异常崩溃
- DataCollector 数据完整性
- 资源变化合理性
- 聚落人口非负
- 满意度和饥饿度在合法范围内
"""


from civsim.agents.civilian import Civilian
from civsim.config import CivSimConfig
from civsim.world.engine import CivilizationEngine

_E2E_TICKS = 50
_E2E_CIVILIAN_COUNT = 100
_E2E_GRID_SIZE = 20


def _make_e2e_config() -> CivSimConfig:
    """构造端到端测试配置。

    Returns:
        100 平民 + 20x20 地图的配置对象。
    """
    return CivSimConfig(
        world={
            "grid": {"width": _E2E_GRID_SIZE, "height": _E2E_GRID_SIZE},
            "map_generation": {"seed": 12345},
            "settlement": {"initial_count": 4, "min_suitability_score": 0.0},
        },
        agents={
            "civilian": {"initial_count": _E2E_CIVILIAN_COUNT},
        },
        resources={
            "initial_stockpile": {
                "food": 500,
                "wood": 200,
                "ore": 50,
                "gold": 100,
            },
        },
    )


def _get_civilians(engine: CivilizationEngine) -> list[Civilian]:
    """从引擎中提取所有平民 Agent。

    Args:
        engine: 文明引擎实例。

    Returns:
        平民 Agent 列表。
    """
    return [a for a in engine.agents if isinstance(a, Civilian)]


class TestPhase1NoExceptionCrash:
    """验证仿真运行 50 tick 不崩溃。"""

    def test_simulation_runs_without_exception(self) -> None:
        """完整运行 50 tick，无异常抛出。"""
        config = _make_e2e_config()
        engine = CivilizationEngine(config=config, seed=12345)

        for _ in range(_E2E_TICKS):
            engine.step()

        # 如果到达此处说明未崩溃
        assert engine.clock.tick == _E2E_TICKS


class TestPhase1DataCollectorIntegrity:
    """验证 DataCollector 数据完整性。"""

    def test_every_tick_has_record(self) -> None:
        """DataCollector 应为每个 tick 记录一条数据。"""
        config = _make_e2e_config()
        engine = CivilizationEngine(config=config, seed=12345)

        for _ in range(_E2E_TICKS):
            engine.step()

        df = engine.datacollector.get_model_vars_dataframe()
        assert len(df) == _E2E_TICKS, (
            f"DataCollector 应有 {_E2E_TICKS} 条记录，实际 {len(df)}"
        )

    def test_all_expected_columns_present(self) -> None:
        """DataCollector 应包含所有预期的模型指标列。"""
        config = _make_e2e_config()
        engine = CivilizationEngine(config=config, seed=12345)

        for _ in range(5):
            engine.step()

        df = engine.datacollector.get_model_vars_dataframe()
        expected_columns = [
            "total_population",
            "working_count",
            "resting_count",
            "trading_count",
            "socializing_count",
            "migrating_count",
            "protesting_count",
            "fighting_count",
            "total_food",
            "total_wood",
            "total_ore",
            "total_gold",
            "avg_satisfaction",
            "avg_hunger",
            "protest_ratio",
        ]
        for col in expected_columns:
            assert col in df.columns, f"DataCollector 缺少列: {col}"

    def test_state_counts_sum_to_population(self) -> None:
        """每 tick 各状态人数之和应等于总人口。"""
        config = _make_e2e_config()
        engine = CivilizationEngine(config=config, seed=12345)

        for _ in range(_E2E_TICKS):
            engine.step()

        df = engine.datacollector.get_model_vars_dataframe()
        state_columns = [
            "working_count",
            "resting_count",
            "trading_count",
            "socializing_count",
            "migrating_count",
            "protesting_count",
            "fighting_count",
        ]
        for idx in range(len(df)):
            row = df.iloc[idx]
            state_sum = sum(row[col] for col in state_columns)
            assert state_sum == row["total_population"], (
                f"Tick {idx}: 状态人数之和 ({state_sum}) "
                f"不等于总人口 ({row['total_population']})"
            )


class TestPhase1ResourceSanity:
    """验证资源变化合理性。"""

    def test_resources_remain_non_negative(self) -> None:
        """所有聚落的资源在整个仿真过程中始终非负。"""
        config = _make_e2e_config()
        engine = CivilizationEngine(config=config, seed=12345)

        for tick in range(_E2E_TICKS):
            engine.step()
            for sid, settlement in engine.settlements.items():
                for resource, amount in settlement.stockpile.items():
                    assert amount >= 0, (
                        f"Tick {tick + 1}, 聚落 {sid}: "
                        f"{resource} 为负值 ({amount})"
                    )

    def test_total_food_does_not_vanish_immediately(self) -> None:
        """初始 500 食物 x 4 聚落，前 5 tick 食物总量不应归零。"""
        config = _make_e2e_config()
        engine = CivilizationEngine(config=config, seed=12345)

        for _ in range(5):
            engine.step()

        df = engine.datacollector.get_model_vars_dataframe()
        assert df["total_food"].iloc[-1] > 0, (
            "前 5 tick 食物总量不应归零"
        )

    def test_resource_change_is_bounded(self) -> None:
        """每 tick 的资源变化幅度应在合理范围内（无异常跳变）。"""
        config = _make_e2e_config()
        engine = CivilizationEngine(config=config, seed=12345)

        for _ in range(_E2E_TICKS):
            engine.step()

        df = engine.datacollector.get_model_vars_dataframe()

        for resource in ["total_food", "total_wood", "total_ore", "total_gold"]:
            values = df[resource].tolist()
            for i in range(1, len(values)):
                change = abs(values[i] - values[i - 1])
                # 单 tick 变化不应超过总量的 50%（极端保守上限）
                max_val = max(values[i], values[i - 1], 1.0)
                assert change <= max_val * 0.5 + 200, (
                    f"Tick {i}: {resource} 变化幅度异常 "
                    f"({values[i - 1]:.1f} -> {values[i]:.1f})"
                )


class TestPhase1PopulationConstraints:
    """验证聚落人口约束。"""

    def test_population_non_negative(self) -> None:
        """所有聚落在仿真过程中人口始终 >= 0。"""
        config = _make_e2e_config()
        engine = CivilizationEngine(config=config, seed=12345)

        for tick in range(_E2E_TICKS):
            engine.step()
            for sid, settlement in engine.settlements.items():
                assert settlement.population >= 0, (
                    f"Tick {tick + 1}, 聚落 {sid}: "
                    f"人口为负值 ({settlement.population})"
                )

    def test_total_population_tracked_correctly(self) -> None:
        """DataCollector 中的 total_population 应与实际 Agent 数量一致。"""
        config = _make_e2e_config()
        engine = CivilizationEngine(config=config, seed=12345)

        for _ in range(_E2E_TICKS):
            engine.step()

        df = engine.datacollector.get_model_vars_dataframe()
        # 最后一个 tick 的 total_population 应等于实际 Civilian 数量
        final_pop = df["total_population"].iloc[-1]
        actual_civilians = len(_get_civilians(engine))
        assert final_pop == actual_civilians, (
            f"DataCollector 总人口 ({final_pop}) "
            f"与实际 Agent 数量 ({actual_civilians}) 不一致"
        )


class TestPhase1ValueRanges:
    """验证满意度和饥饿度在合法范围 [0, 1] 内。"""

    def test_satisfaction_in_range(self) -> None:
        """每个平民的满意度应始终在 [0, 1] 范围内。"""
        config = _make_e2e_config()
        engine = CivilizationEngine(config=config, seed=12345)

        for tick in range(_E2E_TICKS):
            engine.step()
            for agent in _get_civilians(engine):
                assert 0.0 <= agent.satisfaction <= 1.0, (
                    f"Tick {tick + 1}, Agent {agent.unique_id}: "
                    f"满意度越界 ({agent.satisfaction})"
                )

    def test_hunger_in_range(self) -> None:
        """每个平民的饥饿度应始终在 [0, 1] 范围内。"""
        config = _make_e2e_config()
        engine = CivilizationEngine(config=config, seed=12345)

        for tick in range(_E2E_TICKS):
            engine.step()
            for agent in _get_civilians(engine):
                assert 0.0 <= agent.hunger <= 1.0, (
                    f"Tick {tick + 1}, Agent {agent.unique_id}: "
                    f"饥饿度越界 ({agent.hunger})"
                )

    def test_avg_metrics_in_range(self) -> None:
        """DataCollector 记录的平均满意度和饥饿度应在 [0, 1] 范围内。"""
        config = _make_e2e_config()
        engine = CivilizationEngine(config=config, seed=12345)

        for _ in range(_E2E_TICKS):
            engine.step()

        df = engine.datacollector.get_model_vars_dataframe()
        for _, row in df.iterrows():
            assert 0.0 <= row["avg_satisfaction"] <= 1.0, (
                f"avg_satisfaction 越界: {row['avg_satisfaction']}"
            )
            assert 0.0 <= row["avg_hunger"] <= 1.0, (
                f"avg_hunger 越界: {row['avg_hunger']}"
            )
            assert 0.0 <= row["protest_ratio"] <= 1.0, (
                f"protest_ratio 越界: {row['protest_ratio']}"
            )
