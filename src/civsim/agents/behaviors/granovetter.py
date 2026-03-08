"""Granovetter 阈值传染模型。

实现基于邻居抗议比例和个体阈值的集体行动传染逻辑。
"""

from civsim.agents.behaviors.fsm import CivilianState


def compute_protest_ratio(
    neighbor_states: list[CivilianState],
) -> float:
    """计算邻居中抗议者的比例。

    Args:
        neighbor_states: 邻居的状态列表。

    Returns:
        抗议比例 [0, 1]，无邻居时返回 0。
    """
    if not neighbor_states:
        return 0.0
    protest_count = sum(
        1 for s in neighbor_states if s == CivilianState.PROTESTING
    )
    return protest_count / len(neighbor_states)


def granovetter_check(
    revolt_threshold: float,
    neighbor_states: list[CivilianState],
) -> bool:
    """检查是否触发 Granovetter 阈值传染。

    当邻居中抗议者的比例 >= 个体阈值时触发。

    Args:
        revolt_threshold: 个体的反叛阈值 [0, 1]。
        neighbor_states: 邻居的状态列表。

    Returns:
        是否触发传染。
    """
    ratio = compute_protest_ratio(neighbor_states)
    return ratio >= revolt_threshold


def compute_fighting_ratio(
    neighbor_states: list[CivilianState],
) -> float:
    """计算邻居中战斗者的比例。

    Args:
        neighbor_states: 邻居的状态列表。

    Returns:
        战斗比例 [0, 1]。
    """
    if not neighbor_states:
        return 0.0
    fighting_count = sum(
        1 for s in neighbor_states if s == CivilianState.FIGHTING
    )
    return fighting_count / len(neighbor_states)
