"""性能分析器。

运行时性能监控，测量 step 各阶段耗时和内存使用。
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)

_PSUTIL_AVAILABLE = True
try:
    import psutil
except ImportError:
    _PSUTIL_AVAILABLE = False


@dataclass
class StageMetrics:
    """单个阶段的性能指标。

    Attributes:
        name: 阶段名称。
        total_time_ms: 总耗时（毫秒）。
        call_count: 调用次数。
        max_time_ms: 最大单次耗时。
        min_time_ms: 最小单次耗时。
    """

    name: str
    total_time_ms: float = 0.0
    call_count: int = 0
    max_time_ms: float = 0.0
    min_time_ms: float = float("inf")

    @property
    def avg_time_ms(self) -> float:
        """平均耗时。"""
        if self.call_count == 0:
            return 0.0
        return self.total_time_ms / self.call_count

    def record(self, elapsed_ms: float) -> None:
        """记录一次耗时。"""
        self.total_time_ms += elapsed_ms
        self.call_count += 1
        self.max_time_ms = max(self.max_time_ms, elapsed_ms)
        self.min_time_ms = min(self.min_time_ms, elapsed_ms)


class PerformanceProfiler:
    """运行时性能分析器。

    提供装饰器和上下文管理器来测量代码段耗时。

    Attributes:
        stages: 各阶段性能指标。
        memory_samples: 内存使用采样记录。
    """

    def __init__(self) -> None:
        self.stages: dict[str, StageMetrics] = {}
        self.memory_samples: list[dict[str, float]] = []

    def profile_stage(self, stage_name: str) -> _StageTimer:
        """创建阶段计时上下文管理器。

        Args:
            stage_name: 阶段名称。

        Returns:
            上下文管理器。
        """
        if stage_name not in self.stages:
            self.stages[stage_name] = StageMetrics(name=stage_name)
        return _StageTimer(self.stages[stage_name])

    def sample_memory(self) -> dict[str, float]:
        """采样当前内存使用。

        Returns:
            包含 rss_mb 和 vms_mb 的字典。
        """
        if not _PSUTIL_AVAILABLE:
            return {"rss_mb": 0.0, "vms_mb": 0.0}

        process = psutil.Process()
        mem = process.memory_info()
        sample = {
            "rss_mb": mem.rss / (1024 * 1024),
            "vms_mb": mem.vms / (1024 * 1024),
        }
        self.memory_samples.append(sample)
        return sample

    def get_peak_memory_mb(self) -> float:
        """获取峰值 RSS 内存（MB）。"""
        if not self.memory_samples:
            return 0.0
        return max(s["rss_mb"] for s in self.memory_samples)

    def get_report(self) -> dict[str, Any]:
        """生成性能报告。

        Returns:
            包含各阶段耗时和内存使用的字典。
        """
        stage_report = {}
        for name, metrics in self.stages.items():
            stage_report[name] = {
                "avg_ms": round(metrics.avg_time_ms, 2),
                "max_ms": round(metrics.max_time_ms, 2),
                "min_ms": round(metrics.min_time_ms, 2) if metrics.min_time_ms != float("inf") else 0.0,
                "total_ms": round(metrics.total_time_ms, 2),
                "calls": metrics.call_count,
            }

        bottleneck = ""
        if self.stages:
            bottleneck = max(
                self.stages.values(), key=lambda m: m.total_time_ms,
            ).name

        return {
            "stages": stage_report,
            "bottleneck": bottleneck,
            "peak_memory_mb": round(self.get_peak_memory_mb(), 1),
            "memory_samples": len(self.memory_samples),
        }

    def reset(self) -> None:
        """重置所有指标。"""
        self.stages.clear()
        self.memory_samples.clear()


class _StageTimer:
    """阶段计时上下文管理器。"""

    def __init__(self, metrics: StageMetrics) -> None:
        self._metrics = metrics
        self._start: float = 0.0

    def __enter__(self) -> _StageTimer:
        self._start = time.monotonic()
        return self

    def __exit__(self, *args: Any) -> None:
        elapsed_ms = (time.monotonic() - self._start) * 1000
        self._metrics.record(elapsed_ms)


def profile_step(profiler: PerformanceProfiler, stage_name: str) -> Callable:
    """装饰器：测量函数执行耗时。

    Args:
        profiler: 性能分析器实例。
        stage_name: 阶段名称。

    Returns:
        装饰器函数。
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with profiler.profile_stage(stage_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator
