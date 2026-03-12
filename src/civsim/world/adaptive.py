"""自适应参数控制器。

P-controller 恒温器：根据系统温度（抗议、革命、满意度、战争等指标）
动态调节马尔可夫系数、Granovetter 阈值、满意度恢复速率等系数乘数，
使仿真在宽参数范围内自然产生丰富涌现行为。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from civsim.config_params import AdaptiveControllerConfig

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """系统状态快照。

    每 N tick 采样一次，用于计算系统温度。

    Attributes:
        tick: 当前 tick。
        global_protest_ratio: 全局抗议率。
        avg_satisfaction: 全局平均满意度。
        revolution_count: 累计革命次数。
        revolutions_recent: 近 lookback_ticks 内革命次数。
        active_wars: 当前活跃战争数。
        collapsed_settlements: 人口为 0 的聚落数。
        total_settlements: 聚落总数。
        total_population: 总人口。
        trade_volume_recent: 近期贸易量。
    """

    tick: int = 0
    global_protest_ratio: float = 0.0
    avg_satisfaction: float = 0.5
    revolution_count: int = 0
    revolutions_recent: int = 0
    active_wars: int = 0
    collapsed_settlements: int = 0
    total_settlements: int = 1
    total_population: int = 0
    trade_volume_recent: float = 0.0


@dataclass
class AdaptiveCoefficients:
    """自适应系数乘数。

    默认 1.0 = 无调节。控制器根据温度上下调整。

    Attributes:
        markov_protest_multiplier: 马尔可夫抗议系数乘数。
        granovetter_burst_multiplier: Granovetter 传染突变量乘数。
        revolution_cooldown_multiplier: 革命冷却期乘数。
        satisfaction_recovery_multiplier: 满意度恢复速率乘数。
        random_event_multiplier: 随机事件概率乘数。
        satisfaction_penalty_multiplier: 满意度惩罚力度乘数（<1 减轻惩罚）。
    """

    markov_protest_multiplier: float = 1.0
    granovetter_burst_multiplier: float = 1.0
    revolution_cooldown_multiplier: float = 1.0
    satisfaction_recovery_multiplier: float = 1.0
    random_event_multiplier: float = 1.0
    satisfaction_penalty_multiplier: float = 1.0


class AdaptiveParameterController:
    """P-controller 自适应参数控制器。

    温度高（系统过热：大量抗议/革命/战争）→
        降低促抗议系数、延长冷却期、加速满意度恢复。
    温度低（系统死水：无抗议/无冲突）→
        提高促抗议系数、增加随机事件概率。

    Attributes:
        config: 控制器配置。
        coefficients: 当前系数乘数。
        temperature: 当前系统温度。
        temperature_history: 温度历史记录。
    """

    def __init__(
        self, config: AdaptiveControllerConfig | None = None,
    ) -> None:
        self.config = config or AdaptiveControllerConfig()
        self.coefficients = AdaptiveCoefficients()
        self.temperature: float = 0.0
        self.temperature_history: list[tuple[int, float]] = []
        self._last_update_tick: int = -1

    def should_update(self, current_tick: int) -> bool:
        """判断是否应更新控制器。

        Args:
            current_tick: 当前 tick。

        Returns:
            是否应执行更新。
        """
        if not self.config.enabled:
            return False
        if current_tick <= 0:
            return False
        return (
            current_tick - self._last_update_tick
            >= self.config.update_interval
        )

    def compute_temperature(self, metrics: SystemMetrics) -> float:
        """计算系统温度。

        温度 ∈ [0, 1]，综合抗议率、满意度、革命、战争等指标。
        权重和缩放因子从 config (Layer 2) 读取。

        Args:
            metrics: 系统状态快照。

        Returns:
            系统温度值。
        """
        cfg = self.config
        # 缩放因子 (Layer 2)
        protest_heat = min(1.0, metrics.global_protest_ratio * cfg.protest_scale)
        satisfaction_cold = max(0.0, 1.0 - metrics.avg_satisfaction)
        revolution_heat = min(
            1.0, metrics.revolutions_recent * cfg.revolution_scale,
        )
        war_heat = min(1.0, metrics.active_wars * cfg.war_scale)
        collapse_heat = 0.0
        if metrics.total_settlements > 0:
            collapse_heat = min(
                1.0,
                metrics.collapsed_settlements / metrics.total_settlements,
            )

        # 权重 (Layer 2)
        temperature = (
            cfg.protest_weight * protest_heat
            + cfg.satisfaction_weight * satisfaction_cold
            + cfg.revolution_weight * revolution_heat
            + cfg.war_weight * war_heat
            + cfg.collapse_weight * collapse_heat
        )

        return max(0.0, min(1.0, temperature))

    def update(self, metrics: SystemMetrics) -> AdaptiveCoefficients:
        """更新系数乘数。

        P-controller 逻辑：
        error = temperature - target → 正值表示过热，负值表示过冷。

        Args:
            metrics: 系统状态快照。

        Returns:
            更新后的系数乘数。
        """
        self._last_update_tick = metrics.tick
        self.temperature = self.compute_temperature(metrics)
        self.temperature_history.append((metrics.tick, self.temperature))

        # 保留最近 100 条记录
        if len(self.temperature_history) > 100:
            self.temperature_history = self.temperature_history[-100:]

        error = self.temperature - self.config.target_temperature
        rate = self.config.adjustment_rate
        lo = self.config.min_multiplier
        hi = self.config.max_multiplier

        # 满意度危机检测：当满意度是主要热量来源时，
        # 需要治本（减轻惩罚）而非治标（压制抗议）
        satisfaction_cold = max(0.0, 1.0 - metrics.avg_satisfaction)
        satisfaction_crisis = metrics.avg_satisfaction < 0.25

        if error > 0:
            # 过热 → 降低促抗议系数，加速恢复
            self.coefficients.markov_protest_multiplier = _clamp(
                self.coefficients.markov_protest_multiplier - rate * error,
                lo, hi,
            )
            self.coefficients.granovetter_burst_multiplier = _clamp(
                self.coefficients.granovetter_burst_multiplier
                - rate * error * 0.8,
                lo, hi,
            )
            self.coefficients.revolution_cooldown_multiplier = _clamp(
                self.coefficients.revolution_cooldown_multiplier
                + rate * error * 0.5,
                lo, hi,
            )
            self.coefficients.satisfaction_recovery_multiplier = _clamp(
                self.coefficients.satisfaction_recovery_multiplier
                + rate * error * 0.6,
                lo, hi,
            )
            self.coefficients.random_event_multiplier = _clamp(
                self.coefficients.random_event_multiplier
                - rate * error * 0.3,
                lo, hi,
            )
            # 满意度危机时额外响应：减轻惩罚力度（治本）
            if satisfaction_crisis:
                self.coefficients.satisfaction_penalty_multiplier = _clamp(
                    self.coefficients.satisfaction_penalty_multiplier
                    - rate * satisfaction_cold * 0.5,
                    lo, hi,
                )
            else:
                # 满意度健康时恢复惩罚力度
                self.coefficients.satisfaction_penalty_multiplier = _clamp(
                    self.coefficients.satisfaction_penalty_multiplier
                    + rate * 0.1,
                    lo, hi,
                )
        elif error < 0:
            # 过冷 → 提高促抗议系数，增加事件
            abs_error = abs(error)
            self.coefficients.markov_protest_multiplier = _clamp(
                self.coefficients.markov_protest_multiplier
                + rate * abs_error * 0.5,
                lo, hi,
            )
            self.coefficients.granovetter_burst_multiplier = _clamp(
                self.coefficients.granovetter_burst_multiplier
                + rate * abs_error * 0.3,
                lo, hi,
            )
            self.coefficients.revolution_cooldown_multiplier = _clamp(
                self.coefficients.revolution_cooldown_multiplier
                - rate * abs_error * 0.2,
                lo, hi,
            )
            self.coefficients.satisfaction_recovery_multiplier = _clamp(
                self.coefficients.satisfaction_recovery_multiplier
                - rate * abs_error * 0.3,
                lo, hi,
            )
            self.coefficients.random_event_multiplier = _clamp(
                self.coefficients.random_event_multiplier
                + rate * abs_error * 0.4,
                lo, hi,
            )
            # 过冷时恢复惩罚力度
            self.coefficients.satisfaction_penalty_multiplier = _clamp(
                self.coefficients.satisfaction_penalty_multiplier
                + rate * abs_error * 0.3,
                lo, hi,
            )

        if metrics.tick % 50 == 0:
            logger.info(
                "自适应控制器 tick=%d: 温度=%.3f, 目标=%.3f, "
                "protest_mult=%.2f, granovetter_mult=%.2f, "
                "cooldown_mult=%.2f, recovery_mult=%.2f, "
                "penalty_mult=%.2f, event_mult=%.2f",
                metrics.tick, self.temperature,
                self.config.target_temperature,
                self.coefficients.markov_protest_multiplier,
                self.coefficients.granovetter_burst_multiplier,
                self.coefficients.revolution_cooldown_multiplier,
                self.coefficients.satisfaction_recovery_multiplier,
                self.coefficients.satisfaction_penalty_multiplier,
                self.coefficients.random_event_multiplier,
            )

        return self.coefficients

    def get_global_context(self) -> dict:
        """获取全局态势信息，供 LLM 注入。

        Returns:
            包含温度、系数、历史等的字典。
        """
        recent_temps = [
            t for _, t in self.temperature_history[-10:]
        ]
        avg_temp = (
            sum(recent_temps) / len(recent_temps) if recent_temps else 0.0
        )

        return {
            "system_temperature": round(self.temperature, 3),
            "avg_temperature_recent": round(avg_temp, 3),
            "protest_multiplier": round(
                self.coefficients.markov_protest_multiplier, 2,
            ),
            "recovery_multiplier": round(
                self.coefficients.satisfaction_recovery_multiplier, 2,
            ),
            "target_temperature": self.config.target_temperature,
        }


def _clamp(value: float, lo: float, hi: float) -> float:
    """将值限制在 [lo, hi] 范围内。"""
    return max(lo, min(hi, value))
