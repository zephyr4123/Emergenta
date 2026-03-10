"""LLM 优化集成测试。

验证 gateway + cost_tracker + prompt_cache + cascade 协同工作。
"""

import pytest

from civsim.llm.cascade import Complexity, ModelCascade
from civsim.llm.cost_tracker import CostTracker
from civsim.llm.gateway import LLMGateway
from civsim.llm.prompt_cache import PromptCacheManager


class TestGatewayCostIntegration:
    """Gateway + CostTracker 集成测试。"""

    def test_cost_tracker_enabled(self) -> None:
        """测试 Gateway 启用成本追踪。"""
        gw = LLMGateway()
        gw.enable_cost_tracking()

        assert gw.cost_tracker is not None
        assert isinstance(gw.cost_tracker, CostTracker)

    def test_prompt_cache_enabled(self) -> None:
        """测试 Gateway 启用 Prompt 缓存。"""
        gw = LLMGateway()
        gw.enable_prompt_cache()

        assert gw.prompt_cache is not None
        assert isinstance(gw.prompt_cache, PromptCacheManager)


class TestCascadeIntegration:
    """ModelCascade + CostTracker 集成测试。"""

    def test_cascade_classifies_and_tracks(self) -> None:
        """测试级联分类并追踪成本。"""
        cascade = ModelCascade()
        tracker = CostTracker()

        # 模拟多次决策
        scenarios = [
            {"protest_ratio": 0.05, "satisfaction_avg": 0.8},  # simple
            {"protest_ratio": 0.4, "satisfaction_avg": 0.4},   # moderate
            {"protest_ratio": 0.6, "satisfaction_avg": 0.2},   # complex
        ]

        for scenario in scenarios:
            complexity = cascade.classify_complexity(**scenario)
            role = cascade.get_model_role(complexity)

            # 模拟记录调用
            if complexity == Complexity.SIMPLE:
                tracker.record_call("anthropic/claude-3-5-haiku-20241022", 100, 50)
            elif complexity == Complexity.MODERATE:
                tracker.record_call("anthropic/claude-sonnet-4-20250514", 200, 100)
            else:
                tracker.record_call("anthropic/claude-opus-4-20250514", 300, 150)

        summary = tracker.get_summary()
        assert summary["total_calls"] == 3
        assert summary["total_cost_usd"] > 0

        cascade_stats = cascade.get_stats()
        assert cascade_stats["total"] == 3
        assert cascade_stats["simple"] >= 1
        assert cascade_stats["complex"] >= 1


class TestPromptCacheWithCostTracker:
    """PromptCache + CostTracker 集成测试。"""

    def test_cache_reduces_tracked_cost(self) -> None:
        """测试缓存命中降低追踪成本。"""
        cache = PromptCacheManager()
        tracker = CostTracker()

        cache.register_system_prompt("governor", "你是城镇管理者")

        # 第一次调用（无缓存）
        messages = [{"role": "user", "content": "test"}]
        cache.prepare_cached_request("governor", messages)
        cost_1 = tracker.record_call(
            "anthropic/claude-3-5-haiku-20241022", 500, 200, cache_hit=False,
        )

        # 第二次调用（有缓存）
        cache.prepare_cached_request("governor", messages)
        cost_2 = tracker.record_call(
            "anthropic/claude-3-5-haiku-20241022", 500, 200, cache_hit=True,
        )

        assert cost_2 < cost_1

        summary = tracker.get_summary()
        assert summary["cache_hits"] == 1


class TestCallWithCascade:
    """Gateway.call_with_cascade 测试（无真实 LLM 调用）。"""

    def test_cascade_role_mapping(self) -> None:
        """测试级联角色映射逻辑。"""
        gw = LLMGateway()

        # 未注册模型时不应崩溃（会在 call 时报错）
        # 这里只测试映射逻辑
        from civsim.config import LLMModelConfig
        gw.register_model("governor", LLMModelConfig(
            provider="anthropic", model="claude-3-5-haiku-20241022",
        ))

        # call_with_cascade 会选择 governor 对应 simple
        # 但由于没有真实 API key，不实际调用
        assert "governor" in gw._model_configs
