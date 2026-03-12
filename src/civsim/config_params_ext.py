"""扩展参数配置模型。

将散布在各模块中的硬编码常量提取为 Pydantic 配置模型，
补充 config_params.py 中已有的 5 个核心模型。
"""

from pydantic import BaseModel, Field


class TileParamsConfig(BaseModel):
    """地块属性参数。"""

    default_fertility: float = Field(default=0.8, ge=0.0, le=1.0)
    default_density: float = Field(default=0.8, ge=0.0, le=1.0)
    default_reserve: float = Field(default=100.0, ge=0.0)
    farmland_base_output: float = Field(default=2.0, ge=0.0)
    forest_base_output: float = Field(default=0.5, ge=0.0)
    mine_max_output: float = Field(default=1.0, ge=0.0)
    fertility_regen_factor: float = Field(default=0.001, ge=0.0)
    density_regen_factor: float = Field(default=0.001, ge=0.0)
    consume_fertility_decay: float = Field(default=0.01, ge=0.0)
    consume_density_decay: float = Field(default=0.02, ge=0.0)


class SeasonParamsConfig(BaseModel):
    """季节效应参数。"""

    farm_spring: float = Field(default=1.0, ge=0.0)
    farm_summer: float = Field(default=1.5, ge=0.0)
    farm_autumn: float = Field(default=1.2, ge=0.0)
    farm_winter: float = Field(default=0.3, ge=0.0)
    forest_spring: float = Field(default=1.0, ge=0.0)
    forest_summer: float = Field(default=1.2, ge=0.0)
    forest_autumn: float = Field(default=0.8, ge=0.0)
    forest_winter: float = Field(default=0.5, ge=0.0)
    food_consumption_winter: float = Field(default=1.5, ge=0.0)
    spring_growth_bonus: float = Field(default=1.5, ge=0.0)
    autumn_trade_bonus: float = Field(default=1.3, ge=0.0)


class MapSuitabilityConfig(BaseModel):
    """地图聚落适宜度评分参数。"""

    farmland_weight: float = Field(default=0.3, ge=0.0)
    water_weight: float = Field(default=0.4, ge=0.0)
    forest_weight: float = Field(default=0.1, ge=0.0)
    flatness_weight: float = Field(default=0.5, ge=0.0)
    optimal_elevation: float = Field(default=0.3, ge=0.0, le=1.0)
    suitability_radius: int = Field(default=5, gt=0)
    min_settlement_distance: int = Field(default=10, gt=0)
    territory_radius: int = Field(default=3, gt=0)


class EventParamsConfig(BaseModel):
    """随机事件参数。"""

    drought_prob: float = Field(default=0.002, ge=0.0, le=1.0)
    plague_prob: float = Field(default=0.001, ge=0.0, le=1.0)
    mine_discovery_prob: float = Field(default=0.003, ge=0.0, le=1.0)
    harvest_prob: float = Field(default=0.005, ge=0.0, le=1.0)
    bandits_prob: float = Field(default=0.002, ge=0.0, le=1.0)
    drought_duration: int = Field(default=30, gt=0)
    drought_fertility_mult: float = Field(default=0.3, ge=0.0, le=1.0)
    plague_pop_loss_ratio: float = Field(default=0.10, ge=0.0, le=1.0)
    harvest_duration: int = Field(default=15, gt=0)
    harvest_food_bonus: float = Field(default=5.0, ge=0.0)
    bandits_gold_mult: float = Field(default=0.7, ge=0.0, le=1.0)
    bandits_security_loss: float = Field(default=0.2, ge=0.0)


class EngineParamsConfig(BaseModel):
    """引擎核心参数。"""

    profession_farmer_ratio: float = Field(default=0.4, ge=0.0, le=1.0)
    profession_woodcutter_ratio: float = Field(default=0.2, ge=0.0, le=1.0)
    profession_miner_ratio: float = Field(default=0.2, ge=0.0, le=1.0)
    profession_merchant_ratio: float = Field(default=0.2, ge=0.0, le=1.0)
    natural_growth_rate: float = Field(default=0.002, ge=0.0)
    starvation_scarcity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    starvation_rate_factor: float = Field(default=0.1, ge=0.0)
    neighbor_radius: int = Field(default=3, gt=0)


class CivilianBehaviorConfig(BaseModel):
    """平民行为参数。"""

    work_output_food: float = Field(default=2.5, ge=0.0)
    work_output_other: float = Field(default=1.0, ge=0.0)
    rest_hunger_recovery: float = Field(default=0.05, ge=0.0)
    trade_gold_output: float = Field(default=0.3, ge=0.0)
    food_satiation_recovery: float = Field(default=0.06, ge=0.0)
    food_satisfaction_ratio: float = Field(default=0.8, ge=0.0, le=1.0)
    initial_satisfaction: float = Field(default=0.7, ge=0.0, le=1.0)


class GovernorFallbackConfig(BaseModel):
    """镇长回退决策阈值参数。"""

    scarcity_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    scarcity_tax_change: float = Field(default=-0.05)
    protest_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    protest_security_change: float = Field(default=0.1)
    high_protest_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    high_protest_tax_change: float = Field(default=-0.03)
    low_satisfaction_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    low_satisfaction_tax_change: float = Field(default=-0.05)
    stable_scarcity_max: float = Field(default=0.2, ge=0.0, le=1.0)
    stable_protest_max: float = Field(default=0.1, ge=0.0, le=1.0)
    stable_satisfaction_min: float = Field(default=0.6, ge=0.0, le=1.0)
    stable_tax_change: float = Field(default=0.03)


class LeaderFallbackConfig(BaseModel):
    """首领回退决策阈值参数。"""

    war_strength_ratio: float = Field(default=1.3, ge=0.0)
    war_probability: float = Field(default=0.3, ge=0.0, le=1.0)
    betrayal_trust_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    betrayal_probability: float = Field(default=0.2, ge=0.0, le=1.0)
    scapegoat_satisfaction_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    scapegoat_probability: float = Field(default=0.2, ge=0.0, le=1.0)
    protest_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    low_satisfaction_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    military_gold_weight: float = Field(default=0.5, ge=0.0)
    military_pop_weight: float = Field(default=0.1, ge=0.0)
    war_trust_penalty: float = Field(default=-0.2)
    embargo_trust_penalty: float = Field(default=-0.15)


class GovernanceParamsConfig(BaseModel):
    """治理机制参数。"""

    tax_change_limit: float = Field(default=0.1, ge=0.0)
    security_change_limit: float = Field(default=0.15, ge=0.0)
    governance_food_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    governance_pop_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    governance_stability_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    tax_stability_factor: float = Field(default=0.3, ge=0.0)


class DiplomacyParamsConfig(BaseModel):
    """外交系统参数。"""

    initial_trust: float = Field(default=0.5, ge=0.0, le=1.0)
    trust_decay_per_tick: float = Field(default=0.001, ge=0.0)
    treaty_trust_boost: float = Field(default=0.1, ge=0.0)
    break_treaty_penalty: float = Field(default=-0.3)
    downgrade_trust_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    upgrade_trust_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0,
        description="信任度达此值时自动升级为 FRIENDLY",
    )
    randomize_trust: bool = True
    trust_random_min: float = Field(default=0.2, ge=0.0, le=1.0)
    trust_random_max: float = Field(default=0.6, ge=0.0, le=1.0)


class SettlementParamsConfig(BaseModel):
    """聚落参数。"""

    default_capacity: int = Field(default=500, gt=0)
    default_infrastructure: float = Field(default=0.5, ge=0.0, le=1.0)
    default_tax_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    default_security_level: float = Field(default=0.5, ge=0.0, le=1.0)
    scarcity_full_threshold: float = Field(default=5.0, gt=0.0)
    starvation_unfed_factor: float = Field(default=0.05, ge=0.0)


class AnalyticsParamsConfig(BaseModel):
    """涌现检测参数。"""

    trade_growth_threshold: float = Field(default=50.0, ge=0.0)
    war_cascade_min_wars: int = Field(default=2, ge=1)


class GatewayParamsConfig(BaseModel):
    """LLM 网关参数。"""

    max_retries: int = Field(default=2, ge=0)
    timeout: int = Field(default=30, gt=0)
    retry_backoff_base: float = Field(default=1.0, ge=0.0)
    max_concurrent_requests: int = Field(
        default=10, gt=0,
        description="最大并发 LLM 请求数，避免 API 过载",
    )


class MemoryParamsConfig(BaseModel):
    """记忆系统参数。"""

    importance_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    decision_importance: float = Field(default=0.8, ge=0.0, le=1.0)
