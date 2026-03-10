"""LLM 调用成本追踪器。

记录每次 LLM 调用的 token 消耗和费用，提供分析接口。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 每百万 token 的价格（USD），基于 2026-03 Anthropic 定价
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-3-5-haiku-20241022": {"input": 1.0, "output": 5.0},
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
}

# 通用别名映射
_ALIAS_MAP: dict[str, str] = {
    "haiku": "claude-3-5-haiku-20241022",
    "sonnet": "claude-sonnet-4-20250514",
    "opus": "claude-opus-4-20250514",
}


@dataclass
class CallRecord:
    """单次 LLM 调用记录。

    Attributes:
        model: 模型名。
        prompt_tokens: 输入 token 数。
        completion_tokens: 输出 token 数。
        cache_hit: 是否缓存命中。
        cost_usd: 本次调用估算费用。
    """

    model: str
    prompt_tokens: int
    completion_tokens: int
    cache_hit: bool
    cost_usd: float


class CostTracker:
    """LLM 调用成本追踪器。

    Attributes:
        records: 所有调用记录。
    """

    def __init__(self) -> None:
        self.records: list[CallRecord] = []
        self._tick_costs: dict[int, float] = {}
        self._current_tick: int = 0

    def set_tick(self, tick: int) -> None:
        """设置当前 tick。

        Args:
            tick: 当前模拟 tick。
        """
        self._current_tick = tick

    def record_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cache_hit: bool = False,
    ) -> float:
        """记录一次 LLM 调用。

        Args:
            model: 模型名或路径（如 anthropic/claude-...）。
            prompt_tokens: 输入 token 数。
            completion_tokens: 输出 token 数。
            cache_hit: 是否缓存命中。

        Returns:
            本次调用估算费用（USD）。
        """
        cost = self._estimate_cost(model, prompt_tokens, completion_tokens, cache_hit)
        record = CallRecord(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_hit=cache_hit,
            cost_usd=cost,
        )
        self.records.append(record)

        # 按 tick 累计
        self._tick_costs[self._current_tick] = (
            self._tick_costs.get(self._current_tick, 0.0) + cost
        )
        return cost

    def _estimate_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cache_hit: bool,
    ) -> float:
        """估算调用费用。"""
        # 提取模型名（去掉 provider/ 前缀）
        model_name = model.split("/")[-1] if "/" in model else model

        pricing = MODEL_PRICING.get(model_name)
        if pricing is None:
            # 尝试别名
            for alias, full_name in _ALIAS_MAP.items():
                if alias in model_name.lower():
                    pricing = MODEL_PRICING.get(full_name)
                    break

        if pricing is None:
            # 使用中等价格作为默认
            pricing = {"input": 3.0, "output": 15.0}

        input_cost = prompt_tokens * pricing["input"] / 1_000_000
        output_cost = completion_tokens * pricing["output"] / 1_000_000

        # 缓存命中时输入成本降低 90%
        if cache_hit:
            input_cost *= 0.1

        return input_cost + output_cost

    def get_summary(self) -> dict[str, float | int]:
        """获取成本统计摘要。

        Returns:
            包含总成本、调用次数、缓存节省等信息的字典。
        """
        total_cost = sum(r.cost_usd for r in self.records)
        total_prompt = sum(r.prompt_tokens for r in self.records)
        total_completion = sum(r.completion_tokens for r in self.records)
        cache_hits = sum(1 for r in self.records if r.cache_hit)

        # 按模型分类
        by_model: dict[str, float] = {}
        for r in self.records:
            model_key = r.model.split("/")[-1] if "/" in r.model else r.model
            by_model[model_key] = by_model.get(model_key, 0.0) + r.cost_usd

        return {
            "total_cost_usd": total_cost,
            "total_calls": len(self.records),
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "cache_hits": cache_hits,
            "cost_by_model": by_model,
        }

    def get_cost_per_tick(self) -> float:
        """获取平均每 tick 的 LLM 成本。"""
        if not self._tick_costs:
            return 0.0
        return sum(self._tick_costs.values()) / len(self._tick_costs)
