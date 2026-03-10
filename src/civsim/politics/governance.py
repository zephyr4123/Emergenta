"""治理机制。

管理税率调整、治安投入和资源分配策略。
确保决策执行时遵守约束条件。
"""

from __future__ import annotations

from dataclasses import dataclass

from civsim.config_params_ext import GovernanceParamsConfig
from civsim.economy.settlement import Settlement


@dataclass
class GovernanceAction:
    """治理行动数据。

    Attributes:
        tax_rate_change: 税率变化量 [-0.1, 0.1]。
        security_change: 治安投入变化量 [-0.15, 0.15]。
        resource_focus: 资源重点方向。
        reasoning: 决策理由。
    """

    tax_rate_change: float = 0.0
    security_change: float = 0.0
    resource_focus: str = "balanced"
    reasoning: str = ""

    @classmethod
    def from_decision(cls, decision: dict) -> GovernanceAction:
        """从 LLM 决策字典创建。

        Args:
            decision: 经过验证的决策字典。

        Returns:
            GovernanceAction 实例。
        """
        return cls(
            tax_rate_change=decision.get("tax_rate_change", 0.0),
            security_change=decision.get("security_change", 0.0),
            resource_focus=decision.get("resource_focus", "balanced"),
            reasoning=decision.get("reasoning", ""),
        )


def apply_governance_action(
    settlement: Settlement,
    action: GovernanceAction,
    params: GovernanceParamsConfig | None = None,
) -> dict[str, float]:
    """将治理行动应用到聚落。

    确保税率和治安水平在 [0, 1] 范围内。

    Args:
        settlement: 目标聚落。
        action: 治理行动。
        params: 治理参数配置。

    Returns:
        应用后的变化摘要。
    """
    if params is None:
        params = GovernanceParamsConfig()

    old_tax = settlement.tax_rate
    old_security = settlement.security_level

    # 约束税率变化
    tax_limit = params.tax_change_limit
    clamped_tax_change = max(-tax_limit, min(tax_limit, action.tax_rate_change))
    new_tax = max(0.0, min(1.0, settlement.tax_rate + clamped_tax_change))
    settlement.tax_rate = new_tax

    # 约束治安变化
    sec_limit = params.security_change_limit
    clamped_sec_change = max(-sec_limit, min(sec_limit, action.security_change))
    new_security = max(0.0, min(1.0, settlement.security_level + clamped_sec_change))
    settlement.security_level = new_security

    # 资源重点方向会影响平民的劳作分配（通过引擎层调整）
    return {
        "tax_rate_old": old_tax,
        "tax_rate_new": new_tax,
        "security_old": old_security,
        "security_new": new_security,
        "resource_focus": action.resource_focus,
    }


def compute_governance_score(
    settlement: Settlement,
    params: GovernanceParamsConfig | None = None,
) -> float:
    """计算聚落的治理效能评分。

    综合考虑满意度（由外部提供）、食物稀缺度和人口规模。

    Args:
        settlement: 聚落。
        params: 治理参数配置。

    Returns:
        治理评分 [0, 1]。
    """
    if params is None:
        params = GovernanceParamsConfig()

    food_score = 1.0 - settlement.scarcity_index
    pop_ratio = min(1.0, settlement.population / max(1, settlement.capacity))
    stability = 1.0 - settlement.tax_rate * params.tax_stability_factor

    return (
        food_score * params.governance_food_weight
        + pop_ratio * params.governance_pop_weight
        + stability * params.governance_stability_weight
    )
