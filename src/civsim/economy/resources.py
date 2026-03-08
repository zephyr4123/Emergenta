"""资源类型定义与流转规则。

定义四种资源类型以及与资源相关的计算工具。
"""

from enum import Enum


class ResourceType(Enum):
    """资源类型枚举。"""

    FOOD = "food"
    WOOD = "wood"
    ORE = "ore"
    GOLD = "gold"


# 所有资源类型名称列表
RESOURCE_NAMES: list[str] = [r.value for r in ResourceType]


def create_empty_stockpile() -> dict[str, float]:
    """创建空的资源储备字典。

    Returns:
        所有资源量为 0 的字典。
    """
    return {r.value: 0.0 for r in ResourceType}


def create_stockpile(
    food: float = 0.0,
    wood: float = 0.0,
    ore: float = 0.0,
    gold: float = 0.0,
) -> dict[str, float]:
    """创建指定初始量的资源储备。

    Args:
        food: 食物量。
        wood: 木材量。
        ore: 矿石量。
        gold: 金币量。

    Returns:
        资源储备字典。
    """
    return {"food": food, "wood": wood, "ore": ore, "gold": gold}


def add_resources(
    target: dict[str, float],
    source: dict[str, float],
) -> None:
    """将 source 中的资源加到 target 上（原地修改）。

    Args:
        target: 被加的资源字典。
        source: 要加上的资源字典。
    """
    for key in RESOURCE_NAMES:
        target[key] = target.get(key, 0.0) + source.get(key, 0.0)


def subtract_resources(
    target: dict[str, float],
    amount: dict[str, float],
) -> dict[str, float]:
    """从 target 中扣除 amount（不会低于 0）。

    Args:
        target: 被扣的资源字典（原地修改）。
        amount: 要扣除的量。

    Returns:
        实际扣除的量。
    """
    actual = {}
    for key in RESOURCE_NAMES:
        wanted = amount.get(key, 0.0)
        available = target.get(key, 0.0)
        deducted = min(wanted, available)
        target[key] = available - deducted
        actual[key] = deducted
    return actual
