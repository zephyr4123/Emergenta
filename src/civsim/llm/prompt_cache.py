"""Prompt 缓存管理器。

利用 Anthropic cache_control 缓存系统 prompt，减少重复 token 计费。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Prompt 缓存统计。

    Attributes:
        cache_creation_tokens: 缓存创建 token 数。
        cache_read_tokens: 缓存读取 token 数。
        total_requests: 总请求数。
        cached_requests: 使用缓存的请求数。
    """

    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    total_requests: int = 0
    cached_requests: int = 0

    @property
    def hit_rate(self) -> float:
        """缓存命中率。"""
        if self.total_requests == 0:
            return 0.0
        return self.cached_requests / self.total_requests


class PromptCacheManager:
    """管理 Anthropic Prompt Caching。

    将 system prompt 标记为可缓存前缀，减少重复请求的 token 消耗。

    Attributes:
        stats: 缓存统计数据。
    """

    def __init__(self) -> None:
        self.stats = CacheStats()
        self._cached_system_prompts: dict[str, str] = {}

    def register_system_prompt(self, role: str, prompt: str) -> None:
        """注册角色的系统 prompt 以供缓存。

        Args:
            role: 角色名（governor / leader）。
            prompt: 系统 prompt 文本。
        """
        self._cached_system_prompts[role] = prompt

    def prepare_cached_request(
        self,
        role: str,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> tuple[list[dict], str | None]:
        """为请求添加 cache_control 标记。

        将 system prompt 添加 cache_control breakpoint，
        使 Anthropic API 缓存该前缀部分。

        Args:
            role: 角色名。
            messages: 原始消息列表。
            system_prompt: 系统 prompt（优先于已注册的）。

        Returns:
            (处理后的消息列表, 带缓存标记的系统 prompt) 元组。
        """
        self.stats.total_requests += 1

        sp = system_prompt or self._cached_system_prompts.get(role)
        if sp is None:
            return messages, None

        self.stats.cached_requests += 1
        return messages, sp

    def update_stats_from_response(
        self,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
    ) -> None:
        """从 LLM 响应中更新缓存统计。

        Args:
            cache_creation_tokens: 本次请求的缓存创建 token 数。
            cache_read_tokens: 本次请求的缓存读取 token 数。
        """
        self.stats.cache_creation_tokens += cache_creation_tokens
        self.stats.cache_read_tokens += cache_read_tokens

    def get_cache_stats(self) -> dict[str, float | int]:
        """获取缓存统计摘要。

        Returns:
            包含命中率、token 节省等信息的字典。
        """
        return {
            "hit_rate": self.stats.hit_rate,
            "total_requests": self.stats.total_requests,
            "cached_requests": self.stats.cached_requests,
            "cache_creation_tokens": self.stats.cache_creation_tokens,
            "cache_read_tokens": self.stats.cache_read_tokens,
        }
