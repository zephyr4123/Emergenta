"""LLM 行为缓存。

基于决策上下文相似度的缓存系统，当输入场景与历史场景相似时
直接复用历史决策，避免重复调用 LLM。
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目。

    Attributes:
        key_hash: 输入特征的哈希值。
        input_features: 输入特征字典（用于相似度计算）。
        decision: 缓存的决策结果。
        hit_count: 命中次数。
    """

    key_hash: str
    input_features: dict[str, float]
    decision: dict
    hit_count: int = 0


class BehaviorCache:
    """行为缓存管理器。

    使用特征向量距离判断场景相似度，
    相似场景直接复用历史决策而不调用 LLM。

    Attributes:
        similarity_threshold: 相似度阈值 [0, 1]。
        max_size: 缓存最大容量。
    """

    def __init__(
        self,
        similarity_threshold: float = 0.92,
        max_size: int = 10000,
    ) -> None:
        self.similarity_threshold = similarity_threshold
        self.max_size = max_size
        self._cache: dict[str, CacheEntry] = {}
        self._total_queries: int = 0
        self._total_hits: int = 0

    def query(self, features: dict[str, float]) -> dict | None:
        """查询缓存，返回匹配的决策或 None。

        Args:
            features: 当前输入特征字典。

        Returns:
            匹配的历史决策字典，未命中则返回 None。
        """
        self._total_queries += 1

        # 先尝试精确哈希匹配
        key = self._hash_features(features)
        if key in self._cache:
            entry = self._cache[key]
            entry.hit_count += 1
            self._total_hits += 1
            return entry.decision

        # 再尝试相似度匹配
        for entry in self._cache.values():
            sim = self._compute_similarity(features, entry.input_features)
            if sim >= self.similarity_threshold:
                entry.hit_count += 1
                self._total_hits += 1
                return entry.decision

        return None

    def store(self, features: dict[str, float], decision: dict) -> None:
        """存储一条决策到缓存。

        Args:
            features: 输入特征字典。
            decision: 决策结果字典。
        """
        if len(self._cache) >= self.max_size:
            self._evict()

        key = self._hash_features(features)
        self._cache[key] = CacheEntry(
            key_hash=key,
            input_features=features,
            decision=decision,
        )

    @property
    def hit_rate(self) -> float:
        """缓存命中率。"""
        if self._total_queries == 0:
            return 0.0
        return self._total_hits / self._total_queries

    @property
    def size(self) -> int:
        """当前缓存大小。"""
        return len(self._cache)

    def clear(self) -> None:
        """清空缓存。"""
        self._cache.clear()
        self._total_queries = 0
        self._total_hits = 0

    def _hash_features(self, features: dict[str, float]) -> str:
        """生成特征的哈希键。

        将浮点数四舍五入到两位小数后哈希，避免微小差异导致缓存未命中。
        """
        rounded = {k: round(v, 2) for k, v in sorted(features.items())}
        content = json.dumps(rounded, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def _compute_similarity(
        self, a: dict[str, float], b: dict[str, float]
    ) -> float:
        """计算两组特征的余弦相似度。

        Args:
            a: 特征字典 A。
            b: 特征字典 B。

        Returns:
            相似度 [0, 1]。
        """
        all_keys = set(a.keys()) | set(b.keys())
        if not all_keys:
            return 1.0

        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0
        for k in all_keys:
            va = a.get(k, 0.0)
            vb = b.get(k, 0.0)
            dot += va * vb
            norm_a += va * va
            norm_b += vb * vb

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a**0.5 * norm_b**0.5)

    def _evict(self) -> None:
        """淘汰最少命中的缓存条目。"""
        if not self._cache:
            return
        min_key = min(self._cache, key=lambda k: self._cache[k].hit_count)
        del self._cache[min_key]
