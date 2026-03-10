"""模型级联策略。

根据决策复杂度自动选择合适的 LLM 模型：
- simple → Haiku（低成本快速响应）
- moderate → Sonnet（均衡选择）
- complex → Opus（最高能力）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Complexity(Enum):
    """决策复杂度等级。"""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


# 复杂度 → 模型角色映射
DEFAULT_MODEL_MAP: dict[Complexity, str] = {
    Complexity.SIMPLE: "governor",
    Complexity.MODERATE: "leader",
    Complexity.COMPLEX: "leader_opus",
}


@dataclass
class CascadeStats:
    """级联统计。

    Attributes:
        simple_count: 简单决策次数。
        moderate_count: 中等决策次数。
        complex_count: 复杂决策次数。
    """

    simple_count: int = 0
    moderate_count: int = 0
    complex_count: int = 0

    @property
    def total(self) -> int:
        """总决策次数。"""
        return self.simple_count + self.moderate_count + self.complex_count

    @property
    def cost_savings_ratio(self) -> float:
        """成本节省比例（相对于全部使用 Opus）。"""
        if self.total == 0:
            return 0.0
        return self.simple_count / self.total * 0.9 + self.moderate_count / self.total * 0.5


class ModelCascade:
    """模型级联决策器。

    根据感知数据的变化幅度自动判断决策复杂度，
    选择合适级别的 LLM 模型。

    Attributes:
        model_map: 复杂度 → 模型角色映射。
        stats: 级联统计。
    """

    def __init__(
        self,
        model_map: dict[Complexity, str] | None = None,
        protest_threshold: float = 0.3,
        satisfaction_threshold: float = 0.2,
    ) -> None:
        self.model_map = model_map or dict(DEFAULT_MODEL_MAP)
        self._protest_threshold = protest_threshold
        self._satisfaction_threshold = satisfaction_threshold
        self.stats = CascadeStats()

    def classify_complexity(
        self,
        protest_ratio: float = 0.0,
        satisfaction_avg: float = 0.7,
        protest_delta: float = 0.0,
        satisfaction_delta: float = 0.0,
        has_diplomatic_change: bool = False,
        has_revolution_risk: bool = False,
    ) -> Complexity:
        """根据多种指标判断决策复杂度。

        Args:
            protest_ratio: 当前抗议比例。
            satisfaction_avg: 平均满意度。
            protest_delta: 抗议比例变化量。
            satisfaction_delta: 满意度变化量。
            has_diplomatic_change: 是否有外交状态变化。
            has_revolution_risk: 是否有革命风险。

        Returns:
            决策复杂度等级。
        """
        # 高风险情况 → 复杂
        if has_revolution_risk or protest_ratio > 0.5:
            self.stats.complex_count += 1
            return Complexity.COMPLEX

        if has_diplomatic_change:
            self.stats.complex_count += 1
            return Complexity.COMPLEX

        # 中等变化 → 中等
        if (
            abs(protest_delta) > self._protest_threshold
            or abs(satisfaction_delta) > self._satisfaction_threshold
            or protest_ratio > 0.3
            or satisfaction_avg < 0.3
        ):
            self.stats.moderate_count += 1
            return Complexity.MODERATE

        # 稳定状态 → 简单
        self.stats.simple_count += 1
        return Complexity.SIMPLE

    def get_model_role(self, complexity: Complexity) -> str:
        """获取对应复杂度的模型角色名。

        Args:
            complexity: 决策复杂度。

        Returns:
            模型角色名。
        """
        return self.model_map.get(complexity, "leader")

    def get_stats(self) -> dict[str, int | float]:
        """获取级联统计摘要。"""
        return {
            "total": self.stats.total,
            "simple": self.stats.simple_count,
            "moderate": self.stats.moderate_count,
            "complex": self.stats.complex_count,
            "cost_savings_ratio": self.stats.cost_savings_ratio,
        }
