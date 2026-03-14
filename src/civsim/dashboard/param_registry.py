"""参数注册表 — 将 Pydantic 配置模型映射为可视化控件。

定义所有可在面板中调整的参数元数据，提供通用的配置读写工具函数，
以及运行时传播处理器（如 capacity 同步到所有聚落）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================
# 参数规格定义
# ============================================================


@dataclass
class ParamSpec:
    """单个可配参数的元数据。

    Attributes:
        config_path: Pydantic 配置的点路径，如 "revolution_params.protest_threshold"。
        label: 面板上显示的中文标签。
        category: 所属分类。
        input_type: 控件类型：slider / number / textarea / switch。
        default: 默认值。
        description: 参数说明。
        min_val: slider/number 最小值。
        max_val: slider/number 最大值。
        step: slider/number 步长。
        special_handler: 特殊传播处理器名称。
    """

    config_path: str
    label: str
    category: str
    input_type: str
    default: Any
    description: str
    min_val: float | None = None
    max_val: float | None = None
    step: float | None = None
    special_handler: str | None = None


# ============================================================
# 参数注册表（7 个分类）
# ============================================================

PARAM_REGISTRY: list[ParamSpec] = [
    # ---- 经济系统 ----
    ParamSpec(
        "resources.regeneration.farmland_per_tick", "农田食物再生率",
        "经济系统", "slider", 0.8, "每 tick 农田基础食物产出",
        0.0, 5.0, 0.1,
    ),
    ParamSpec(
        "resources.regeneration.forest_per_tick", "森林木材再生率",
        "经济系统", "slider", 0.3, "每 tick 森林基础木材产出",
        0.0, 3.0, 0.1,
    ),
    ParamSpec(
        "resources.consumption.food_per_civilian_per_tick", "人均食物消耗",
        "经济系统", "slider", 0.5, "每平民每 tick 食物消耗",
        0.0, 3.0, 0.05,
    ),
    ParamSpec(
        "trade_params.trust_threshold", "贸易信任门槛",
        "经济系统", "slider", 0.15, "低于此信任度拒绝贸易",
        0.0, 1.0, 0.05,
    ),
    ParamSpec(
        "trade_params.distance_cost_factor", "贸易距离成本",
        "经济系统", "slider", 0.05, "每单位距离的贸易成本系数",
        0.0, 0.5, 0.01,
    ),
    ParamSpec(
        "trade_params.surplus_trade_ratio", "盈余交易比例",
        "经济系统", "slider", 0.5, "聚落可用于贸易的盈余比例",
        0.0, 1.0, 0.05,
    ),
    ParamSpec(
        "trade_params.food_surplus_threshold", "食物盈余阈值",
        "经济系统", "slider", 2.5, "人均食物超过此值才能出售",
        0.5, 10.0, 0.5,
    ),
    ParamSpec(
        "trade_params.max_trades_per_settlement_per_tick", "每聚落每tick最大贸易次数",
        "经济系统", "number", 5, "限制每聚落每tick参与的贸易次数",
        1, 20, 1,
    ),
    ParamSpec(
        "civilian_behavior.work_output_food", "劳作食物产出",
        "经济系统", "slider", 2.5, "农民每次劳作基础食物产出",
        0.0, 10.0, 0.5,
    ),
    ParamSpec(
        "civilian_behavior.trade_gold_output", "贸易金币产出",
        "经济系统", "slider", 0.3, "商人每次贸易基础金币产出",
        0.0, 3.0, 0.1,
    ),
    # ---- 社会行为 ----
    ParamSpec(
        "markov_coefficients.hunger_to_protest_working", "饥饿→抗议(劳作)",
        "社会行为", "slider", 0.60, "饥饿使劳作→抗议的转移概率增量",
        0.0, 2.0, 0.05,
    ),
    ParamSpec(
        "markov_coefficients.hunger_to_protest_social", "饥饿→抗议(社交)",
        "社会行为", "slider", 0.50, "饥饿使社交→抗议的转移概率增量",
        0.0, 2.0, 0.05,
    ),
    ParamSpec(
        "markov_coefficients.tax_to_protest_working", "税率→抗议(劳作)",
        "社会行为", "slider", 0.45, "税率使劳作→抗议的转移概率增量",
        0.0, 2.0, 0.05,
    ),
    ParamSpec(
        "markov_coefficients.granovetter_burst_working", "传染→抗议(劳作)",
        "社会行为", "slider", 0.80, "邻居传染使劳作→抗议的突变量",
        0.0, 2.0, 0.05,
    ),
    ParamSpec(
        "markov_coefficients.granovetter_burst_social", "传染→抗议(社交)",
        "社会行为", "slider", 0.85, "邻居传染使社交→抗议的突变量",
        0.0, 2.0, 0.05,
    ),
    ParamSpec(
        "satisfaction_coefficients.scarcity_high_penalty", "高稀缺满意度惩罚",
        "社会行为", "slider", 0.10, "稀缺指数>0.5时的每tick满意度惩罚",
        0.0, 0.5, 0.01,
    ),
    ParamSpec(
        "satisfaction_coefficients.tax_penalty_factor", "税率满意度惩罚系数",
        "社会行为", "slider", 0.15, "税率超阈值时的满意度惩罚乘数",
        0.0, 1.0, 0.01,
    ),
    ParamSpec(
        "satisfaction_coefficients.scarcity_low_recovery", "低稀缺满意度恢复",
        "社会行为", "slider", 0.01, "稀缺指数<0.2时的每tick满意度恢复",
        0.0, 0.1, 0.002,
    ),
    ParamSpec(
        "satisfaction_coefficients.oppression_threshold", "警察国家阈值",
        "社会行为", "slider", 0.8, "治安超此值产生反效果",
        0.0, 1.0, 0.05,
    ),
    ParamSpec(
        "civilian_behavior.initial_satisfaction", "初始满意度",
        "社会行为", "slider", 0.7, "新生平民的初始满意度",
        0.0, 1.0, 0.05,
    ),
    # ---- 政治系统 ----
    ParamSpec(
        "revolution_params.protest_threshold", "革命抗议阈值",
        "政治系统", "slider", 0.20, "抗议率超此值可触发革命",
        0.0, 1.0, 0.05,
    ),
    ParamSpec(
        "revolution_params.satisfaction_threshold", "革命满意度阈值",
        "政治系统", "slider", 0.40, "满意度低于此值可触发革命",
        0.0, 1.0, 0.05,
    ),
    ParamSpec(
        "revolution_params.cooldown_ticks", "革命冷却期",
        "政治系统", "number", 30, "革命后冷却tick数",
        5, 200, 5,
    ),
    ParamSpec(
        "revolution_params.honeymoon_ticks", "革命蜜月期",
        "政治系统", "number", 40, "革命后蜜月期tick数",
        5, 200, 5,
    ),
    ParamSpec(
        "revolution_params.population_loss_ratio", "革命人口损失比",
        "政治系统", "slider", 0.10, "革命时人口损失比例",
        0.0, 0.5, 0.01,
    ),
    ParamSpec(
        "governance_params.tax_change_limit", "税率单次变幅上限",
        "政治系统", "slider", 0.1, "镇长单次税率调整最大幅度",
        0.0, 0.5, 0.01,
    ),
    ParamSpec(
        "diplomacy_params.initial_trust", "外交初始信任",
        "政治系统", "slider", 0.55, "阵营间初始信任度",
        0.0, 1.0, 0.05,
    ),
    ParamSpec(
        "diplomacy_params.trust_decay_per_tick", "信任自然衰减",
        "政治系统", "number", 0.00015, "每tick信任度自然衰减量",
        0.0, 0.01, 0.00005,
    ),
    ParamSpec(
        "diplomacy_params.break_treaty_penalty", "毁约信任惩罚",
        "政治系统", "slider", -0.3, "撕毁条约的信任惩罚",
        -1.0, 0.0, 0.05,
    ),
    ParamSpec(
        "leader_fallback.war_strength_ratio", "宣战实力比阈值",
        "政治系统", "slider", 1.3, "实力超对手此倍数时考虑宣战",
        1.0, 3.0, 0.1,
    ),
    # ---- 聚落与人口 ----
    ParamSpec(
        "settlement_params.default_capacity", "聚落人口上限",
        "聚落与人口", "number", 500, "每聚落最大人口容量",
        50, 5000, 50,
        special_handler="propagate_capacity",
    ),
    ParamSpec(
        "engine_params.natural_growth_rate", "自然增长率",
        "聚落与人口", "slider", 0.004, "每tick人口自然增长概率",
        0.0, 0.05, 0.001,
    ),
    ParamSpec(
        "engine_params.starvation_scarcity_threshold", "饥荒稀缺阈值",
        "聚落与人口", "slider", 0.7, "稀缺指数超此值开始饿死",
        0.0, 1.0, 0.05,
    ),
    ParamSpec(
        "engine_params.starvation_rate_factor", "饥荒死亡系数",
        "聚落与人口", "slider", 0.1, "饥荒时死亡人数比例系数",
        0.0, 0.5, 0.01,
    ),
    ParamSpec(
        "settlement_params.starvation_unfed_factor", "断粮死亡系数",
        "聚落与人口", "slider", 0.05, "完全断粮时的死亡比例",
        0.0, 0.3, 0.01,
    ),
    ParamSpec(
        "agents.civilian.hunger_decay_per_tick", "饥饿衰减速率",
        "聚落与人口", "slider", 0.02, "每tick饥饿度自然增长",
        0.0, 0.1, 0.005,
    ),
    # ---- 迁徙与再分配 ----
    ParamSpec(
        "migration_params.reassignment_base_prob", "迁徙再分配基础概率",
        "聚落与人口", "slider", 0.3, "踏入他方领地时加入新聚落的基础概率",
        0.0, 1.0, 0.05,
    ),
    ParamSpec(
        "migration_params.scarcity_push_weight", "稀缺推力权重",
        "聚落与人口", "slider", 1.5, "家乡稀缺度对迁出概率的推力权重",
        0.0, 5.0, 0.1,
    ),
    ParamSpec(
        "migration_params.food_pull_weight", "食物吸引力权重",
        "聚落与人口", "slider", 1.0, "目标聚落食物充裕度对迁入概率的拉力权重",
        0.0, 5.0, 0.1,
    ),
    ParamSpec(
        "migration_params.directed_hunger_threshold", "定向迁徙饥饿阈值",
        "聚落与人口", "slider", 0.5, "饥饿度超此值时朝食物充裕聚落定向迁徙",
        0.0, 1.0, 0.05,
    ),
    ParamSpec(
        "migration_params.directed_search_radius", "定向迁徙搜索半径",
        "聚落与人口", "number", 15, "定向迁徙时搜索目标聚落的网格半径",
        5, 50, 1,
    ),
    ParamSpec(
        "migration_params.pioneer_seed_enabled", "先驱播种开关",
        "聚落与人口", "switch", True, "空聚落是否自动从附近获得先驱居民",
    ),
    ParamSpec(
        "migration_params.pioneer_seed_count", "先驱播种人数",
        "聚落与人口", "number", 2, "每次播种迁移的先驱居民人数",
        1, 10, 1,
    ),
    ParamSpec(
        "migration_params.pioneer_source_min_pop", "播种来源最低人口",
        "聚落与人口", "number", 10, "来源聚落触发播种的最低人口门槛",
        2, 50, 1,
    ),
    # ---- 自适应控制器 ----
    ParamSpec(
        "adaptive_controller.target_temperature", "目标温度",
        "自适应控制器", "slider", 0.45, "系统目标波动水平",
        0.0, 1.0, 0.05,
    ),
    ParamSpec(
        "adaptive_controller.adjustment_rate", "调节速率",
        "自适应控制器", "slider", 0.10, "P-controller调节速率",
        0.0, 1.0, 0.05,
    ),
    ParamSpec(
        "adaptive_controller.min_multiplier", "系数下限",
        "自适应控制器", "slider", 0.5, "动态系数乘数下限",
        0.0, 1.0, 0.1,
    ),
    ParamSpec(
        "adaptive_controller.max_multiplier", "系数上限",
        "自适应控制器", "slider", 2.0, "动态系数乘数上限",
        1.0, 5.0, 0.1,
    ),
    ParamSpec(
        "adaptive_controller.protest_weight", "抗议率权重",
        "自适应控制器", "slider", 0.30, "温度计算中抗议率的权重",
        0.0, 1.0, 0.05,
    ),
    ParamSpec(
        "adaptive_controller.revolution_weight", "革命频率权重",
        "自适应控制器", "slider", 0.25, "温度计算中革命频率的权重",
        0.0, 1.0, 0.05,
    ),
    ParamSpec(
        "adaptive_controller.war_weight", "战争权重",
        "自适应控制器", "slider", 0.15, "温度计算中战争的权重",
        0.0, 1.0, 0.05,
    ),
    ParamSpec(
        "adaptive_controller.enabled", "启用自适应控制",
        "自适应控制器", "switch", True, "是否启用自适应参数控制器",
    ),
    # ---- 随机事件 ----
    ParamSpec(
        "event_params.drought_prob", "旱灾概率",
        "随机事件", "slider", 0.002, "每tick每聚落旱灾发生概率",
        0.0, 0.05, 0.001,
    ),
    ParamSpec(
        "event_params.plague_prob", "瘟疫概率",
        "随机事件", "slider", 0.001, "每tick每聚落瘟疫发生概率",
        0.0, 0.05, 0.001,
    ),
    ParamSpec(
        "event_params.harvest_prob", "丰收概率",
        "随机事件", "slider", 0.005, "每tick每聚落丰收发生概率",
        0.0, 0.05, 0.001,
    ),
    ParamSpec(
        "event_params.bandits_prob", "流寇概率",
        "随机事件", "slider", 0.002, "每tick每聚落流寇发生概率",
        0.0, 0.05, 0.001,
    ),
    ParamSpec(
        "event_params.mine_discovery_prob", "矿脉发现概率",
        "随机事件", "slider", 0.003, "每tick每聚落矿脉发现概率",
        0.0, 0.05, 0.001,
    ),
    # ---- AI 人格 Prompt ----
    ParamSpec(
        "governor_prompt.system_prompt", "镇长 AI 人格 Prompt",
        "AI人格Prompt", "textarea", "", "镇长LLM系统Prompt，定义执政风格",
        special_handler="propagate_governor_prompt",
    ),
    ParamSpec(
        "leader_prompt.system_prompt", "首领 AI 人格 Prompt",
        "AI人格Prompt", "textarea", "", "首领LLM系统Prompt，定义决策风格",
        special_handler="propagate_leader_prompt",
    ),
]

# 按分类索引
CATEGORIES: list[str] = [
    "经济系统", "社会行为", "政治系统",
    "聚落与人口", "自适应控制器", "随机事件", "AI人格Prompt",
]

_REGISTRY_INDEX: dict[str, ParamSpec] = {
    p.config_path: p for p in PARAM_REGISTRY
}

# 旧参数名 → 新配置路径映射（向后兼容造物主面板旧控件）
LEGACY_PARAM_MAP: dict[str, str] = {
    "target_temperature": "adaptive_controller.target_temperature",
    "food_regen": "resources.regeneration.farmland_per_tick",
    "food_consumption": "resources.consumption.food_per_civilian_per_tick",
}


def get_param_spec(path: str) -> ParamSpec | None:
    """按配置路径查找参数规格。

    Args:
        path: 点路径，如 "revolution_params.protest_threshold"。

    Returns:
        对应的 ParamSpec，未找到返回 None。
    """
    return _REGISTRY_INDEX.get(path)


def get_params_by_category(category: str) -> list[ParamSpec]:
    """获取指定分类下的所有参数。

    Args:
        category: 分类名称。

    Returns:
        该分类下的 ParamSpec 列表。
    """
    return [p for p in PARAM_REGISTRY if p.category == category]


# ============================================================
# 通用配置读写
# ============================================================


def get_config_by_path(config: object, path: str) -> Any:
    """按点路径从 Pydantic 配置中读取值。

    Args:
        config: CivSimConfig 实例。
        path: 点路径，如 "revolution_params.protest_threshold"。

    Returns:
        对应字段的当前值。

    Raises:
        AttributeError: 路径无效。
    """
    obj = config
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj


def set_config_by_path(config: object, path: str, value: Any) -> None:
    """按点路径在 Pydantic 配置中设置值。

    Args:
        config: CivSimConfig 实例。
        path: 点路径，如 "revolution_params.protest_threshold"。
        value: 要设置的新值。

    Raises:
        AttributeError: 路径无效。
    """
    parts = path.split(".")
    obj = config
    for part in parts[:-1]:
        obj = getattr(obj, part)
    setattr(obj, parts[-1], value)


def resolve_legacy_param(name: str) -> str:
    """将旧参数名翻译为新配置路径。

    Args:
        name: 参数名（可能是旧名或新路径）。

    Returns:
        标准化的配置路径。
    """
    return LEGACY_PARAM_MAP.get(name, name)


# ============================================================
# 特殊传播处理器
# ============================================================


def propagate_capacity(engine: object, value: Any) -> None:
    """将人口上限传播到所有聚落。

    Args:
        engine: CivilizationModel 实例。
        value: 新的人口上限值。
    """
    cap = int(value)
    settlements = getattr(engine, "settlements", {})
    for settlement in settlements.values():
        settlement.capacity = cap
    logger.info("聚落人口上限已同步: %d (%d 个聚落)", cap, len(settlements))


def propagate_governor_prompt(engine: object, value: Any) -> None:
    """将镇长 Prompt 传播到所有已有镇长。

    Args:
        engine: CivilizationModel 实例。
        value: 新的系统 Prompt 文本。
    """
    prompt = str(value) if value else None
    governors = getattr(engine, "get_governors", lambda: [])()
    for gov in governors:
        gov.system_prompt_override = prompt
    logger.info("镇长 Prompt 已同步: %d 个镇长", len(governors))


def propagate_leader_prompt(engine: object, value: Any) -> None:
    """将首领 Prompt 传播到所有已有首领。

    Args:
        engine: CivilizationModel 实例。
        value: 新的系统 Prompt 文本。
    """
    prompt = str(value) if value else None
    leaders = getattr(engine, "leaders", [])
    for leader in leaders:
        leader.system_prompt_override = prompt
    logger.info("首领 Prompt 已同步: %d 个首领", len(leaders))


# 处理器名称 → 函数映射
SPECIAL_HANDLERS: dict[str, Any] = {
    "propagate_capacity": propagate_capacity,
    "propagate_governor_prompt": propagate_governor_prompt,
    "propagate_leader_prompt": propagate_leader_prompt,
}


def apply_special_handler(
    handler_name: str, engine: object, value: Any,
) -> None:
    """执行特殊传播处理器。

    Args:
        handler_name: 处理器名称。
        engine: CivilizationModel 实例。
        value: 新的参数值。
    """
    handler = SPECIAL_HANDLERS.get(handler_name)
    if handler:
        handler(engine, value)
    else:
        logger.warning("未知的特殊处理器: %s", handler_name)
