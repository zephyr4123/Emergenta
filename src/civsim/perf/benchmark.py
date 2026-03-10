"""性能基准测试工具。

自动化测量不同 Agent 规模下的仿真性能。
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PSUTIL_AVAILABLE = True
try:
    import psutil
except ImportError:
    _PSUTIL_AVAILABLE = False


@dataclass
class BenchmarkResult:
    """单次基准测试结果。

    Attributes:
        agent_count: Agent 数量。
        ticks: 运行 tick 数。
        total_time_s: 总耗时（秒）。
        avg_tick_ms: 平均每 tick 耗时（毫秒）。
        peak_memory_mb: 峰值内存（MB）。
        settlements: 聚落数量。
    """

    agent_count: int
    ticks: int
    total_time_s: float
    avg_tick_ms: float
    peak_memory_mb: float
    settlements: int


class SimulationBenchmark:
    """仿真性能基准测试。

    Attributes:
        results: 测试结果列表。
    """

    def __init__(self) -> None:
        self.results: list[BenchmarkResult] = []

    def run_benchmark(
        self,
        agent_counts: list[int] | None = None,
        ticks: int = 50,
        grid_size: int = 50,
    ) -> list[BenchmarkResult]:
        """运行多组基准测试。

        Args:
            agent_counts: 要测试的 Agent 数量列表。
            ticks: 每组运行的 tick 数。
            grid_size: 网格大小。

        Returns:
            测试结果列表。
        """
        from civsim.config import CivSimConfig

        if agent_counts is None:
            agent_counts = [100, 500, 1000]

        self.results = []
        for count in agent_counts:
            result = self._run_single(count, ticks, grid_size)
            self.results.append(result)
            logger.info(
                "基准测试: %d agents, %d ticks → %.1f ms/tick, %.1f MB",
                count, ticks, result.avg_tick_ms, result.peak_memory_mb,
            )
        return self.results

    def _run_single(
        self, agent_count: int, ticks: int, grid_size: int,
    ) -> BenchmarkResult:
        """运行单组基准测试。"""
        from civsim.config import CivSimConfig
        from civsim.world.engine import CivilizationEngine

        config = CivSimConfig()
        config.world.grid.width = grid_size
        config.world.grid.height = grid_size
        config.agents.civilian.initial_count = agent_count

        engine = CivilizationEngine(config=config, seed=42)
        n_settlements = len(engine.settlements)

        # 测量内存基线
        peak_mem = 0.0
        if _PSUTIL_AVAILABLE:
            process = psutil.Process()
            peak_mem = process.memory_info().rss / (1024 * 1024)

        start = time.monotonic()
        for _ in range(ticks):
            engine.step()
            if _PSUTIL_AVAILABLE:
                current_mem = process.memory_info().rss / (1024 * 1024)
                peak_mem = max(peak_mem, current_mem)

        total_time = time.monotonic() - start
        avg_tick_ms = (total_time / ticks) * 1000

        return BenchmarkResult(
            agent_count=agent_count,
            ticks=ticks,
            total_time_s=round(total_time, 3),
            avg_tick_ms=round(avg_tick_ms, 2),
            peak_memory_mb=round(peak_mem, 1),
            settlements=n_settlements,
        )

    def export_report(self, path: str | Path | None = None) -> dict:
        """导出测试报告。

        Args:
            path: 报告保存路径（JSON）。为 None 时仅返回字典。

        Returns:
            报告字典。
        """
        report = {
            "results": [
                {
                    "agent_count": r.agent_count,
                    "ticks": r.ticks,
                    "total_time_s": r.total_time_s,
                    "avg_tick_ms": r.avg_tick_ms,
                    "peak_memory_mb": r.peak_memory_mb,
                    "settlements": r.settlements,
                }
                for r in self.results
            ],
        }
        if path is not None:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        return report
