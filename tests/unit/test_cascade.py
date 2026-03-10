"""模型级联策略单元测试。"""

import pytest

from civsim.llm.cascade import CascadeStats, Complexity, ModelCascade


class TestComplexity:
    """Complexity 枚举测试。"""

    def test_values(self) -> None:
        """测试枚举值。"""
        assert Complexity.SIMPLE.value == "simple"
        assert Complexity.MODERATE.value == "moderate"
        assert Complexity.COMPLEX.value == "complex"


class TestCascadeStats:
    """CascadeStats 测试。"""

    def test_total(self) -> None:
        """测试总数计算。"""
        stats = CascadeStats(simple_count=5, moderate_count=3, complex_count=2)
        assert stats.total == 10

    def test_cost_savings_ratio(self) -> None:
        """测试成本节省比例。"""
        stats = CascadeStats(simple_count=10, moderate_count=0, complex_count=0)
        assert stats.cost_savings_ratio == 0.9  # 全部简单

        stats = CascadeStats(simple_count=0, moderate_count=10, complex_count=0)
        assert stats.cost_savings_ratio == 0.5  # 全部中等

    def test_cost_savings_ratio_empty(self) -> None:
        """测试无调用时为 0。"""
        stats = CascadeStats()
        assert stats.cost_savings_ratio == 0.0


class TestModelCascade:
    """ModelCascade 测试。"""

    def test_simple_classification(self) -> None:
        """测试稳定状态分类为简单。"""
        cascade = ModelCascade()
        complexity = cascade.classify_complexity(
            protest_ratio=0.1, satisfaction_avg=0.7,
            protest_delta=0.01, satisfaction_delta=0.01,
        )
        assert complexity == Complexity.SIMPLE

    def test_moderate_classification_high_protest_delta(self) -> None:
        """测试抗议变化大分类为中等。"""
        cascade = ModelCascade()
        complexity = cascade.classify_complexity(
            protest_ratio=0.2, satisfaction_avg=0.6,
            protest_delta=0.35,
        )
        assert complexity == Complexity.MODERATE

    def test_moderate_classification_low_satisfaction(self) -> None:
        """测试满意度低分类为中等。"""
        cascade = ModelCascade()
        complexity = cascade.classify_complexity(
            protest_ratio=0.1, satisfaction_avg=0.2,
        )
        assert complexity == Complexity.MODERATE

    def test_complex_classification_revolution_risk(self) -> None:
        """测试革命风险分类为复杂。"""
        cascade = ModelCascade()
        complexity = cascade.classify_complexity(
            has_revolution_risk=True,
        )
        assert complexity == Complexity.COMPLEX

    def test_complex_classification_high_protest(self) -> None:
        """测试高抗议率分类为复杂。"""
        cascade = ModelCascade()
        complexity = cascade.classify_complexity(
            protest_ratio=0.6,
        )
        assert complexity == Complexity.COMPLEX

    def test_complex_classification_diplomatic_change(self) -> None:
        """测试外交变化分类为复杂。"""
        cascade = ModelCascade()
        complexity = cascade.classify_complexity(
            has_diplomatic_change=True,
        )
        assert complexity == Complexity.COMPLEX

    def test_get_model_role(self) -> None:
        """测试模型角色映射。"""
        cascade = ModelCascade()
        assert cascade.get_model_role(Complexity.SIMPLE) == "governor"
        assert cascade.get_model_role(Complexity.MODERATE) == "leader"
        assert cascade.get_model_role(Complexity.COMPLEX) == "leader_opus"

    def test_custom_model_map(self) -> None:
        """测试自定义模型映射。"""
        custom_map = {
            Complexity.SIMPLE: "custom_haiku",
            Complexity.MODERATE: "custom_sonnet",
            Complexity.COMPLEX: "custom_opus",
        }
        cascade = ModelCascade(model_map=custom_map)
        assert cascade.get_model_role(Complexity.SIMPLE) == "custom_haiku"

    def test_stats_tracking(self) -> None:
        """测试统计追踪。"""
        cascade = ModelCascade()
        cascade.classify_complexity(protest_ratio=0.1)  # simple
        cascade.classify_complexity(protest_ratio=0.4)  # moderate
        cascade.classify_complexity(has_revolution_risk=True)  # complex

        stats = cascade.get_stats()
        assert stats["total"] == 3
        assert stats["simple"] == 1
        assert stats["moderate"] == 1
        assert stats["complex"] == 1
