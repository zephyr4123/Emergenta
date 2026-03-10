"""基准测试工具单元测试。"""

import tempfile
from pathlib import Path

from civsim.perf.benchmark import BenchmarkResult, SimulationBenchmark


class TestBenchmarkResult:
    """BenchmarkResult 测试。"""

    def test_create_result(self) -> None:
        """测试创建结果。"""
        result = BenchmarkResult(
            agent_count=100,
            ticks=50,
            total_time_s=5.0,
            avg_tick_ms=100.0,
            peak_memory_mb=256.0,
            settlements=8,
        )
        assert result.agent_count == 100
        assert result.avg_tick_ms == 100.0


class TestSimulationBenchmark:
    """SimulationBenchmark 测试。"""

    def test_run_small_benchmark(self, config_path: str) -> None:
        """测试运行小规模基准测试。"""
        benchmark = SimulationBenchmark()
        results = benchmark.run_benchmark(
            agent_counts=[10],
            ticks=5,
            grid_size=20,
        )

        assert len(results) == 1
        assert results[0].agent_count == 10
        assert results[0].ticks == 5
        assert results[0].total_time_s > 0
        assert results[0].avg_tick_ms > 0

    def test_export_report(self, config_path: str) -> None:
        """测试导出报告。"""
        benchmark = SimulationBenchmark()
        benchmark.run_benchmark(
            agent_counts=[10],
            ticks=3,
            grid_size=20,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "benchmark.json"
            report = benchmark.export_report(str(path))

            assert path.exists()
            assert "results" in report
            assert len(report["results"]) == 1

    def test_export_report_no_file(self) -> None:
        """测试不保存文件只返回字典。"""
        benchmark = SimulationBenchmark()
        benchmark.results = [
            BenchmarkResult(
                agent_count=100, ticks=10,
                total_time_s=1.0, avg_tick_ms=100.0,
                peak_memory_mb=128.0, settlements=4,
            ),
        ]
        report = benchmark.export_report()
        assert len(report["results"]) == 1
