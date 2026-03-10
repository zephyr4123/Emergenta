"""LLM 成本追踪器单元测试。"""

import pytest

from civsim.llm.cost_tracker import CostTracker


class TestCostTracker:
    """CostTracker 测试。"""

    def test_initial_state(self) -> None:
        """测试初始状态。"""
        tracker = CostTracker()
        assert len(tracker.records) == 0
        assert tracker.get_cost_per_tick() == 0.0

    def test_record_call(self) -> None:
        """测试记录调用。"""
        tracker = CostTracker()
        cost = tracker.record_call(
            model="anthropic/claude-3-5-haiku-20241022",
            prompt_tokens=100,
            completion_tokens=50,
        )
        assert cost > 0
        assert len(tracker.records) == 1
        assert tracker.records[0].prompt_tokens == 100
        assert tracker.records[0].completion_tokens == 50

    def test_haiku_cost_estimation(self) -> None:
        """测试 Haiku 模型成本估算。"""
        tracker = CostTracker()
        cost = tracker.record_call(
            model="anthropic/claude-3-5-haiku-20241022",
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
        )
        # 1M input at $1 + 1M output at $5 = $6
        assert cost == pytest.approx(6.0, rel=0.01)

    def test_sonnet_cost_estimation(self) -> None:
        """测试 Sonnet 模型成本估算。"""
        tracker = CostTracker()
        cost = tracker.record_call(
            model="anthropic/claude-sonnet-4-20250514",
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
        )
        # 1M input at $3 + 1M output at $15 = $18
        assert cost == pytest.approx(18.0, rel=0.01)

    def test_cache_hit_reduces_cost(self) -> None:
        """测试缓存命中降低成本。"""
        tracker = CostTracker()
        cost_normal = tracker.record_call(
            model="anthropic/claude-sonnet-4-20250514",
            prompt_tokens=1000,
            completion_tokens=500,
            cache_hit=False,
        )
        cost_cached = tracker.record_call(
            model="anthropic/claude-sonnet-4-20250514",
            prompt_tokens=1000,
            completion_tokens=500,
            cache_hit=True,
        )
        assert cost_cached < cost_normal

    def test_unknown_model_uses_default(self) -> None:
        """测试未知模型使用默认价格。"""
        tracker = CostTracker()
        cost = tracker.record_call(
            model="unknown/custom-model",
            prompt_tokens=1000,
            completion_tokens=500,
        )
        assert cost > 0

    def test_tick_tracking(self) -> None:
        """测试按 tick 追踪成本。"""
        tracker = CostTracker()

        tracker.set_tick(1)
        tracker.record_call("anthropic/claude-3-5-haiku-20241022", 100, 50)
        tracker.record_call("anthropic/claude-3-5-haiku-20241022", 200, 100)

        tracker.set_tick(2)
        tracker.record_call("anthropic/claude-3-5-haiku-20241022", 100, 50)

        avg = tracker.get_cost_per_tick()
        assert avg > 0

    def test_get_summary(self) -> None:
        """测试获取统计摘要。"""
        tracker = CostTracker()
        tracker.record_call("anthropic/claude-3-5-haiku-20241022", 100, 50)
        tracker.record_call(
            "anthropic/claude-sonnet-4-20250514", 200, 100, cache_hit=True,
        )

        summary = tracker.get_summary()
        assert summary["total_calls"] == 2
        assert summary["total_prompt_tokens"] == 300
        assert summary["total_completion_tokens"] == 150
        assert summary["cache_hits"] == 1
        assert summary["total_cost_usd"] > 0
        assert "cost_by_model" in summary
        assert len(summary["cost_by_model"]) == 2

    def test_empty_summary(self) -> None:
        """测试空追踪器摘要。"""
        tracker = CostTracker()
        summary = tracker.get_summary()
        assert summary["total_calls"] == 0
        assert summary["total_cost_usd"] == 0.0
