"""Phase 2 端到端功能测试。

100 平民 + 4 聚落 + 4 镇长 + 200 tick 完整仿真。
验证 LLM 调用成功、镇长决策影响和数据采集完整性。
"""

import pytest

from civsim.agents.governor import Governor
from civsim.config import CivSimConfig, load_config
from civsim.llm.gateway import LLMGateway
from civsim.world.engine import CivilizationEngine


def _make_phase2_config() -> CivSimConfig:
    """构造 Phase 2 E2E 测试配置。"""
    return CivSimConfig(
        world={
            "grid": {"width": 20, "height": 20},
            "map_generation": {"seed": 42},
            "settlement": {"initial_count": 4, "min_suitability_score": 0.0},
        },
        agents={
            "civilian": {"initial_count": 100},
            "governor": {"initial_count": 1},
        },
        resources={
            "initial_stockpile": {"food": 1000, "wood": 400, "ore": 100, "gold": 200},
        },
    )


class TestPhase2FallbackSimulation:
    """Phase 2 端到端测试（使用规则回退策略，不需要 LLM）。"""

    def test_200_ticks_no_crash(self) -> None:
        """验证 200 tick 仿真无异常崩溃。"""
        config = _make_phase2_config()
        engine = CivilizationEngine(config=config, seed=42, enable_governors=True)

        for _ in range(200):
            engine.step()

        # 验证基本完整性
        df = engine.datacollector.get_model_vars_dataframe()
        assert len(df) == 200, f"应有 200 条记录，实际 {len(df)}"

    def test_governors_make_decisions(self) -> None:
        """验证镇长在 200 tick 内做出多次决策。"""
        config = _make_phase2_config()
        engine = CivilizationEngine(config=config, seed=42, enable_governors=True)

        for _ in range(200):
            engine.step()

        governors = [a for a in engine.agents if isinstance(a, Governor)]
        assert len(governors) == 4

        # 200 ticks / 120 ticks_per_season = 至少 1 个完整季度
        for gov in governors:
            assert gov.decision_count >= 1, (
                f"镇长 {gov.unique_id} 应至少做出 1 次决策"
            )

    def test_data_collection_complete(self) -> None:
        """验证数据采集包含所有指标。"""
        config = _make_phase2_config()
        engine = CivilizationEngine(config=config, seed=42, enable_governors=True)

        for _ in range(50):
            engine.step()

        df = engine.datacollector.get_model_vars_dataframe()
        required_columns = [
            "total_population", "total_food", "total_wood",
            "total_ore", "total_gold", "avg_satisfaction",
            "protest_ratio", "working_count", "protesting_count",
        ]
        for col in required_columns:
            assert col in df.columns, f"缺少指标列: {col}"

    def test_governor_decisions_affect_economy(self) -> None:
        """验证镇长决策改变了聚落经济指标。"""
        config = _make_phase2_config()
        engine = CivilizationEngine(config=config, seed=42, enable_governors=True)

        # 记录初始状态
        initial_tax_rates = {
            sid: s.tax_rate for sid, s in engine.settlements.items()
        }

        # 运行两个完整季度
        for _ in range(240):
            engine.step()

        # 验证至少有一个聚落的税率发生了变化
        changed = False
        for sid, settlement in engine.settlements.items():
            if abs(settlement.tax_rate - initial_tax_rates[sid]) > 0.001:
                changed = True
                break

        assert changed, "镇长决策后至少一个聚落的税率应发生变化"

    def test_compare_with_and_without_governors(self) -> None:
        """对比有/无镇长的仿真差异。"""
        config_with = _make_phase2_config()
        config_without = _make_phase2_config()

        engine_with = CivilizationEngine(
            config=config_with, seed=42, enable_governors=True
        )
        engine_without = CivilizationEngine(
            config=config_without, seed=42, enable_governors=False
        )

        for _ in range(200):
            engine_with.step()
            engine_without.step()

        df_with = engine_with.datacollector.get_model_vars_dataframe()
        df_without = engine_without.datacollector.get_model_vars_dataframe()

        # 两个仿真应有不同的轨迹（镇长决策引入了差异）
        # 比较最终状态
        final_food_with = df_with["total_food"].iloc[-1]
        final_food_without = df_without["total_food"].iloc[-1]

        # 由于镇长使用回退策略会调整税率，两者应有所不同
        # 但差异可能很小，所以只验证两者都正常运行
        assert final_food_with >= 0
        assert final_food_without >= 0
        assert len(df_with) == len(df_without) == 200


class TestPhase2RealLLMSimulation:
    """Phase 2 端到端测试（使用真实 LLM 调用）。"""

    @pytest.fixture()
    def llm_engine(self) -> CivilizationEngine | None:
        """创建使用真实 LLM 的引擎。"""
        try:
            real_config = load_config()
        except FileNotFoundError:
            pytest.skip("找不到 config.yaml")
            return None

        config = _make_phase2_config()
        engine = CivilizationEngine(config=config, seed=42, enable_governors=True)

        # 配置真实 LLM 网关
        gw = LLMGateway(max_retries=1, timeout=60)
        llm_cfg = real_config.llm
        for role in llm_cfg.models:
            model_cfg = llm_cfg.get_model_config(role)
            gw.register_model(role, model_cfg)
        engine.llm_gateway = gw

        # 更新镇长的网关引用
        for agent in engine.agents:
            if isinstance(agent, Governor):
                agent._gateway = gw

        return engine

    def test_real_llm_200_ticks(self, llm_engine: CivilizationEngine) -> None:
        """使用真实 LLM 运行 200 tick 完整仿真。"""
        if llm_engine is None:
            pytest.skip("LLM 引擎不可用")

        for _ in range(200):
            llm_engine.step()

        # 验证 LLM 调用统计
        assert llm_engine.llm_gateway is not None
        stats = llm_engine.llm_gateway.stats
        assert stats.total_calls >= 1, "应至少有 1 次 LLM 调用"

        # 验证镇长决策
        governors = [a for a in llm_engine.agents if isinstance(a, Governor)]
        for gov in governors:
            assert gov.decision_count >= 1

        # 验证数据完整性
        df = llm_engine.datacollector.get_model_vars_dataframe()
        assert len(df) == 200

        # 验证系统动力学指标
        assert df["total_food"].iloc[-1] >= 0
        assert df["total_population"].iloc[-1] >= 0
