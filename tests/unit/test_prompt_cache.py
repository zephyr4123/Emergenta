"""Prompt 缓存管理器单元测试。"""

from civsim.llm.prompt_cache import CacheStats, PromptCacheManager


class TestCacheStats:
    """CacheStats 测试。"""

    def test_initial_stats(self) -> None:
        """测试初始统计值。"""
        stats = CacheStats()
        assert stats.hit_rate == 0.0
        assert stats.total_requests == 0
        assert stats.cached_requests == 0

    def test_hit_rate_calculation(self) -> None:
        """测试命中率计算。"""
        stats = CacheStats(total_requests=10, cached_requests=7)
        assert stats.hit_rate == 0.7

    def test_hit_rate_zero_requests(self) -> None:
        """测试零请求时命中率为 0。"""
        stats = CacheStats(total_requests=0, cached_requests=0)
        assert stats.hit_rate == 0.0


class TestPromptCacheManager:
    """PromptCacheManager 测试。"""

    def test_register_and_retrieve(self) -> None:
        """测试注册和使用系统 prompt。"""
        cache = PromptCacheManager()
        cache.register_system_prompt("governor", "你是一个城镇管理者。")

        messages = [{"role": "user", "content": "当前状况如何？"}]
        result_messages, system_prompt = cache.prepare_cached_request(
            "governor", messages,
        )

        assert system_prompt == "你是一个城镇管理者。"
        assert result_messages == messages

    def test_override_with_explicit_prompt(self) -> None:
        """测试显式系统 prompt 优先。"""
        cache = PromptCacheManager()
        cache.register_system_prompt("governor", "注册的 prompt")

        messages = [{"role": "user", "content": "test"}]
        _, sp = cache.prepare_cached_request(
            "governor", messages, system_prompt="显式 prompt",
        )
        assert sp == "显式 prompt"

    def test_no_registered_prompt(self) -> None:
        """测试无注册 prompt 时返回 None。"""
        cache = PromptCacheManager()
        messages = [{"role": "user", "content": "test"}]
        _, sp = cache.prepare_cached_request("unknown_role", messages)
        assert sp is None

    def test_stats_tracking(self) -> None:
        """测试统计追踪。"""
        cache = PromptCacheManager()
        cache.register_system_prompt("governor", "prompt")

        messages = [{"role": "user", "content": "test"}]
        cache.prepare_cached_request("governor", messages)
        cache.prepare_cached_request("governor", messages)
        cache.prepare_cached_request("unknown", messages)

        assert cache.stats.total_requests == 3
        assert cache.stats.cached_requests == 2

    def test_update_stats_from_response(self) -> None:
        """测试从响应更新统计。"""
        cache = PromptCacheManager()
        cache.update_stats_from_response(
            cache_creation_tokens=500, cache_read_tokens=200,
        )
        assert cache.stats.cache_creation_tokens == 500
        assert cache.stats.cache_read_tokens == 200

        cache.update_stats_from_response(
            cache_creation_tokens=0, cache_read_tokens=300,
        )
        assert cache.stats.cache_read_tokens == 500

    def test_get_cache_stats(self) -> None:
        """测试获取缓存统计摘要。"""
        cache = PromptCacheManager()
        cache.register_system_prompt("governor", "prompt")
        cache.prepare_cached_request(
            "governor", [{"role": "user", "content": "test"}],
        )

        stats = cache.get_cache_stats()
        assert "hit_rate" in stats
        assert "total_requests" in stats
        assert stats["total_requests"] == 1
