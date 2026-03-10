"""性能分析器单元测试。"""

import time

from civsim.perf.profiler import PerformanceProfiler, StageMetrics, profile_step


class TestStageMetrics:
    """StageMetrics 测试。"""

    def test_initial_state(self) -> None:
        """测试初始状态。"""
        m = StageMetrics(name="test")
        assert m.avg_time_ms == 0.0
        assert m.call_count == 0

    def test_record(self) -> None:
        """测试记录耗时。"""
        m = StageMetrics(name="test")
        m.record(10.0)
        m.record(20.0)
        m.record(30.0)

        assert m.call_count == 3
        assert m.total_time_ms == 60.0
        assert m.avg_time_ms == 20.0
        assert m.max_time_ms == 30.0
        assert m.min_time_ms == 10.0


class TestPerformanceProfiler:
    """PerformanceProfiler 测试。"""

    def test_profile_stage_context_manager(self) -> None:
        """测试上下文管理器计时。"""
        profiler = PerformanceProfiler()

        with profiler.profile_stage("test_stage"):
            time.sleep(0.01)

        assert "test_stage" in profiler.stages
        assert profiler.stages["test_stage"].call_count == 1
        assert profiler.stages["test_stage"].total_time_ms > 0

    def test_multiple_stages(self) -> None:
        """测试多个阶段。"""
        profiler = PerformanceProfiler()

        with profiler.profile_stage("stage_a"):
            pass
        with profiler.profile_stage("stage_b"):
            pass

        assert len(profiler.stages) == 2

    def test_repeated_stage(self) -> None:
        """测试重复阶段累计。"""
        profiler = PerformanceProfiler()

        for _ in range(5):
            with profiler.profile_stage("repeat"):
                pass

        assert profiler.stages["repeat"].call_count == 5

    def test_sample_memory(self) -> None:
        """测试内存采样。"""
        profiler = PerformanceProfiler()
        sample = profiler.sample_memory()

        assert "rss_mb" in sample
        assert "vms_mb" in sample
        assert len(profiler.memory_samples) == 1

    def test_get_report(self) -> None:
        """测试性能报告生成。"""
        profiler = PerformanceProfiler()

        with profiler.profile_stage("fast"):
            pass
        with profiler.profile_stage("slow"):
            time.sleep(0.01)

        report = profiler.get_report()
        assert "stages" in report
        assert "bottleneck" in report
        assert "peak_memory_mb" in report
        assert len(report["stages"]) == 2

    def test_reset(self) -> None:
        """测试重置。"""
        profiler = PerformanceProfiler()
        with profiler.profile_stage("test"):
            pass
        profiler.sample_memory()

        profiler.reset()
        assert len(profiler.stages) == 0
        assert len(profiler.memory_samples) == 0


class TestProfileStepDecorator:
    """profile_step 装饰器测试。"""

    def test_decorator(self) -> None:
        """测试装饰器正确记录。"""
        profiler = PerformanceProfiler()

        @profile_step(profiler, "my_func")
        def my_func(x: int) -> int:
            return x * 2

        result = my_func(5)
        assert result == 10
        assert "my_func" in profiler.stages
        assert profiler.stages["my_func"].call_count == 1
