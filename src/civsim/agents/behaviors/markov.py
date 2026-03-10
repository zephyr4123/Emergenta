"""动态马尔可夫转移矩阵。

定义三种性格的基础转移矩阵，以及动态调节公式。
支持通过配置参数和自适应乘数进行动态系数调节。
"""

from __future__ import annotations

from enum import Enum

import numpy as np

from civsim.agents.behaviors.fsm import NUM_STATES, CivilianState
from civsim.config_params import MarkovCoefficientsConfig

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
    coefficients: MarkovCoefficientsConfig | None = None,
    protest_multiplier: float = 1.0,
    granovetter_multiplier: float = 1.0,
) -> np.ndarray:
    """计算动态调节后的转移概率矩阵。

    Args:
        personality: Agent 性格类型。
        hunger: 饥饿度 [0, 1]。
        tax_rate: 当前税率 [0, 1]。
        security: 当前治安水平 [0, 1]。
        protest_ratio: 邻居抗议比例 [0, 1]。
        revolt_threshold: Agent 的 Granovetter 阈值。
        coefficients: 马尔可夫系数配置（可选，默认使用硬编码值）。
        protest_multiplier: 抗议系数乘数（来自自适应控制器）。
        granovetter_multiplier: Granovetter 突变量乘数（来自自适应控制器）。

    Returns:
        归一化后的 7x7 转移概率矩阵。
    """
    base = PERSONALITY_MATRICES[personality].copy()
    safety = 1.0 - security  # 不安全度
    c = coefficients or MarkovCoefficientsConfig()
    pm = protest_multiplier

    # --- 饥饿效应 ---
    base[_W][_P] += c.hunger_to_protest_working * hunger * pm
    base[_W][_M] += c.hunger_to_migrate_working * hunger
    base[_R][_P] += c.hunger_to_protest_resting * hunger * pm
    base[_R][_W] += c.hunger_to_work_resting * hunger
    base[_S][_P] += c.hunger_to_protest_social * hunger * pm
    base[_T][_P] += c.hunger_to_protest_trading * hunger * pm

    # --- 税率效应 ---
    base[_W][_P] += c.tax_to_protest_working * tax_rate * pm
    base[_R][_P] += c.tax_to_protest_resting * tax_rate * pm
    base[_T][_P] += c.tax_to_protest_trading * tax_rate * pm
    base[_S][_P] += c.tax_to_protest_social * tax_rate * pm

    # --- 安全效应 ---
    base[_S][_F] += c.safety_to_fight_social * safety
    base[_P][_F] += c.safety_to_fight_protest * safety

    # --- Granovetter 邻居传染 ---
    gm = granovetter_multiplier
    if protest_ratio >= revolt_threshold:
        base[_W][_P] += c.granovetter_burst_working * gm
        base[_R][_P] += c.granovetter_burst_resting * gm
        base[_S][_P] += c.granovetter_burst_social * gm
        base[_T][_P] += c.granovetter_burst_trading * gm
        base[_M][_P] += c.granovetter_burst_migrating * gm

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
