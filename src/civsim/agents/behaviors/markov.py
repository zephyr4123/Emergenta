"""动态马尔可夫转移矩阵。

定义三种性格的基础转移矩阵，以及动态调节公式。
"""

from enum import Enum

import numpy as np

from civsim.agents.behaviors.fsm import NUM_STATES, CivilianState

# 状态索引简写
_W = CivilianState.WORKING
_R = CivilianState.RESTING
_T = CivilianState.TRADING
_S = CivilianState.SOCIALIZING
_M = CivilianState.MIGRATING
_P = CivilianState.PROTESTING
_F = CivilianState.FIGHTING


class Personality(Enum):
    """性格类型枚举。"""

    COMPLIANT = "compliant"
    NEUTRAL = "neutral"
    REBELLIOUS = "rebellious"


# fmt: off
_COMPLIANT_MATRIX = np.array([
    [0.50, 0.20, 0.12, 0.10, 0.05, 0.02, 0.01],
    [0.45, 0.25, 0.10, 0.12, 0.05, 0.02, 0.01],
    [0.35, 0.15, 0.25, 0.15, 0.06, 0.03, 0.01],
    [0.30, 0.15, 0.10, 0.30, 0.08, 0.05, 0.02],
    [0.40, 0.15, 0.10, 0.10, 0.20, 0.03, 0.02],
    [0.35, 0.10, 0.05, 0.10, 0.15, 0.20, 0.05],
    [0.25, 0.15, 0.05, 0.05, 0.20, 0.10, 0.20],
], dtype=np.float64)

_NEUTRAL_MATRIX = np.array([
    [0.40, 0.18, 0.12, 0.12, 0.08, 0.07, 0.03],
    [0.35, 0.22, 0.10, 0.13, 0.08, 0.08, 0.04],
    [0.28, 0.12, 0.25, 0.15, 0.08, 0.08, 0.04],
    [0.22, 0.12, 0.10, 0.28, 0.10, 0.12, 0.06],
    [0.30, 0.12, 0.08, 0.10, 0.25, 0.08, 0.07],
    [0.20, 0.08, 0.05, 0.10, 0.12, 0.35, 0.10],
    [0.18, 0.10, 0.05, 0.05, 0.17, 0.15, 0.30],
], dtype=np.float64)

_REBELLIOUS_MATRIX = np.array([
    [0.30, 0.12, 0.10, 0.13, 0.10, 0.18, 0.07],
    [0.25, 0.18, 0.08, 0.12, 0.10, 0.18, 0.09],
    [0.20, 0.10, 0.22, 0.13, 0.10, 0.16, 0.09],
    [0.15, 0.10, 0.08, 0.22, 0.10, 0.25, 0.10],
    [0.20, 0.10, 0.05, 0.08, 0.27, 0.18, 0.12],
    [0.10, 0.05, 0.03, 0.08, 0.10, 0.48, 0.16],
    [0.10, 0.08, 0.03, 0.03, 0.12, 0.20, 0.44],
], dtype=np.float64)
# fmt: on

PERSONALITY_MATRICES: dict[Personality, np.ndarray] = {
    Personality.COMPLIANT: _COMPLIANT_MATRIX,
    Personality.NEUTRAL: _NEUTRAL_MATRIX,
    Personality.REBELLIOUS: _REBELLIOUS_MATRIX,
}


def normalize_rows(matrix: np.ndarray) -> np.ndarray:
    """对矩阵每行归一化，确保概率和为 1。

    Args:
        matrix: 待归一化的矩阵。

    Returns:
        行归一化后的矩阵。
    """
    # 确保非负
    matrix = np.clip(matrix, 0.0, None)
    row_sums = matrix.sum(axis=1, keepdims=True)
    # 避免除以零
    row_sums = np.where(row_sums == 0, 1.0, row_sums)
    return matrix / row_sums


def compute_transition_matrix(
    personality: Personality,
    hunger: float,
    tax_rate: float,
    security: float,
    protest_ratio: float,
    revolt_threshold: float,
) -> np.ndarray:
    """计算动态调节后的转移概率矩阵。

    Args:
        personality: Agent 性格类型。
        hunger: 饥饿度 [0, 1]。
        tax_rate: 当前税率 [0, 1]。
        security: 当前治安水平 [0, 1]。
        protest_ratio: 邻居抗议比例 [0, 1]。
        revolt_threshold: Agent 的 Granovetter 阈值。

    Returns:
        归一化后的 7x7 转移概率矩阵。
    """
    base = PERSONALITY_MATRICES[personality].copy()
    safety = 1.0 - security  # 不安全度

    # --- 饥饿效应 ---
    base[_W][_P] += 0.15 * hunger
    base[_W][_M] += 0.10 * hunger
    base[_R][_W] += 0.20 * hunger
    base[_S][_P] += 0.10 * hunger

    # --- 税率效应 ---
    base[_W][_P] += 0.12 * tax_rate
    base[_T][_P] += 0.08 * tax_rate

    # --- 安全效应 ---
    base[_S][_F] += 0.10 * safety
    base[_P][_F] += 0.15 * safety

    # --- Granovetter 邻居传染 ---
    if protest_ratio >= revolt_threshold:
        base[_W][_P] += 0.40
        base[_R][_P] += 0.35
        base[_S][_P] += 0.45
        base[_T][_P] += 0.30

    return normalize_rows(base)


def sample_next_state(
    current_state: CivilianState,
    transition_matrix: np.ndarray,
    rng: np.random.Generator,
) -> CivilianState:
    """根据转移矩阵采样下一个状态。

    Args:
        current_state: 当前状态。
        transition_matrix: 转移概率矩阵。
        rng: NumPy 随机数生成器。

    Returns:
        采样得到的下一个状态。
    """
    probabilities = transition_matrix[current_state]
    next_idx = rng.choice(NUM_STATES, p=probabilities)
    return CivilianState(next_idx)
