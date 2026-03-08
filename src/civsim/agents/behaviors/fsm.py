"""有限状态机定义。

定义平民 Agent 的 7 种状态及状态索引映射。
"""

from enum import IntEnum


class CivilianState(IntEnum):
    """平民 Agent 状态枚举。

    使用 IntEnum 方便作为矩阵行/列索引。
    """

    WORKING = 0
    RESTING = 1
    TRADING = 2
    SOCIALIZING = 3
    MIGRATING = 4
    PROTESTING = 5
    FIGHTING = 6


# 状态中文名映射
STATE_NAMES: dict[CivilianState, str] = {
    CivilianState.WORKING: "劳作",
    CivilianState.RESTING: "休息",
    CivilianState.TRADING: "交易",
    CivilianState.SOCIALIZING: "社交",
    CivilianState.MIGRATING: "迁徙",
    CivilianState.PROTESTING: "抗议",
    CivilianState.FIGHTING: "战斗",
}

NUM_STATES: int = len(CivilianState)
