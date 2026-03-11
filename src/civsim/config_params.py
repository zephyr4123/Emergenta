"""自适应参数系统配置模型。

将散布在多个文件中的硬编码常量提取为 Pydantic 配置模型，
支持通过 config.yaml 外部化配置。
"""

from pydantic import BaseModel, Field


class RevolutionParamsConfig(BaseModel):
    """革命相关参数配置。

    Attributes:
        protest_threshold: 抗议率触发阈值。
        satisfaction_threshold: 满意度触发阈值（低于此值）。
        duration_ticks: 需连续满足条件的 tick 数。
        cooldown_ticks: 革命后冷却期 tick 数。
        honeymoon_ticks: 革命后蜜月期 tick 数。
        honeymoon_satisfaction_boost: 蜜月期每 tick 满意度提升。
        honeymoon_vigilance_reduction: 蜜月期公民阈值下降量。
        resource_penalty_gold: 革命时金币留存比例。
        resource_penalty_food: 革命时食物留存比例。
        security_penalty: 革命时治安下降量。
        post_revolution_tax: 革命后重置税率。
    """

    protest_threshold: float = Field(default=0.20, ge=0.0, le=1.0)
    satisfaction_threshold: float = Field(default=0.40, ge=0.0, le=1.0)
    duration_ticks: int = Field(default=8, gt=0)
    cooldown_ticks: int = Field(default=30, gt=0)
    honeymoon_ticks: int = Field(default=40, gt=0)
    honeymoon_satisfaction_boost: float = Field(default=0.02, ge=0.0)
    honeymoon_vigilance_reduction: float = Field(default=0.05, ge=0.0)
    resource_penalty_gold: float = Field(default=0.5, ge=0.0, le=1.0)
    resource_penalty_food: float = Field(default=0.8, ge=0.0, le=1.0)
    security_penalty: float = Field(default=0.4, ge=0.0, le=1.0)
    post_revolution_tax: float = Field(default=0.15, ge=0.0, le=1.0)
    # --- 革命后遗症 (默认=0 不影响现有行为) ---
    aftermath_productivity_decay: float = Field(
        default=0.0, ge=0.0, le=0.5,
        description="革命后生产力衰减比例（每tick产出降低）",
    )
    aftermath_trust_penalty: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="革命后所属阵营外交信任惩罚",
    )
    aftermath_max_cumulative_decay: float = Field(
        default=0.0, ge=0.0, le=0.9,
        description="多次革命累积衰减上限",
    )


class LeaderPromptConfig(BaseModel):
    """首领 LLM 系统 Prompt 配置。

    允许从外部配置文件自定义首领的决策风格和行为准则，
    无需修改代码即可调整首领 AI 的性格。

    Attributes:
        system_prompt: 首领系统 Prompt 全文。
    """

    system_prompt: str = Field(
        default=(
            "你是一个文明模拟器中的阵营首领AI。你统领多个聚落。\n"
            "你的核心目标是：扩张势力、获取资源、削弱对手。\n"
            "联盟是暂时的工具，战争是资源再分配的手段。\n"
            "当你的实力明显强于对手时，宣战掠夺是理性选择。\n"
            "当你虚弱时，联盟是权宜之计，等待时机反叛。\n"
            "信任是有限的——背叛盟友获取利益是合理策略。\n\n"
            "决策范围：\n"
            "1. 外交行动：propose_alliance / propose_trade / declare_war / "
            "offer_peace / break_treaty / trade_embargo / none\n"
            "2. 政策指令：向下属聚落发布税率/治安/资源重点调整指令\n"
            "3. 军事命令：对敌对阵营发起攻击或防御\n\n"
            "决策原则：\n"
            "1. 当你总人口 > 对手 1.3 倍时，考虑宣战掠夺\n"
            "2. 当盟友变弱或威胁到你时，考虑背叛\n"
            "3. 当内部满意度低时，可以对外宣战来转嫁矛盾\n"
            "4. 不要与所有人结盟——没有敌人意味着没有扩张空间\n"
            "5. 贸易禁运可以削弱对手而不需要直接战争\n"
        ),
        description="首领系统 Prompt 全文，定义首领 AI 的决策风格",
    )


class TradeParamsConfig(BaseModel):
    """贸易相关参数配置。

    Attributes:
        trust_threshold: 信任度低于此值拒绝贸易。
        refuse_prob_base: 随机摩擦基础拒绝概率。
        refuse_prob_trust_factor: 信任度对拒绝概率的影响系数。
        trust_boost_per_trade: 每次成功跨阵营贸易的信任增量。
        surplus_trade_ratio: 盈余交易比例。
    """

    trust_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    refuse_prob_base: float = Field(default=0.3, ge=0.0, le=1.0)
    refuse_prob_trust_factor: float = Field(default=0.2, ge=0.0)
    trust_boost_per_trade: float = Field(default=0.01, ge=0.0)
    surplus_trade_ratio: float = Field(default=0.3, ge=0.0, le=1.0)
    # 扩展贸易参数
    base_price_food: float = Field(default=1.0, ge=0.0)
    base_price_wood: float = Field(default=1.5, ge=0.0)
    base_price_ore: float = Field(default=3.0, ge=0.0)
    min_surplus_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    distance_cost_factor: float = Field(default=0.05, ge=0.0)
    min_trade_amount: float = Field(default=0.5, ge=0.0)
    food_surplus_threshold: float = Field(default=8.0, ge=0.0)
    other_surplus_threshold: float = Field(default=3.0, ge=0.0)
    food_deficit_threshold: float = Field(default=3.0, ge=0.0)
    other_deficit_threshold: float = Field(default=1.0, ge=0.0)


class MarkovCoefficientsConfig(BaseModel):
    """马尔可夫转移矩阵动态调节系数配置。

    Attributes:
        hunger_to_protest_working: 饥饿→劳作→抗议系数。
        hunger_to_migrate_working: 饥饿→劳作→迁徙系数。
        hunger_to_protest_resting: 饥饿→休息→抗议系数。
        hunger_to_work_resting: 饥饿→休息→劳作系数。
        hunger_to_protest_social: 饥饿→社交→抗议系数。
        hunger_to_protest_trading: 饥饿→交易→抗议系数。
        tax_to_protest_working: 税率→劳作→抗议系数。
        tax_to_protest_resting: 税率→休息→抗议系数。
        tax_to_protest_trading: 税率→交易→抗议系数。
        tax_to_protest_social: 税率→社交→抗议系数。
        safety_to_fight_social: 不安全→社交→战斗系数。
        safety_to_fight_protest: 不安全→抗议→战斗系数。
        granovetter_burst_working: 邻居传染→劳作→抗议突变量。
        granovetter_burst_resting: 邻居传染→休息→抗议突变量。
        granovetter_burst_social: 邻居传染→社交→抗议突变量。
        granovetter_burst_trading: 邻居传染→交易→抗议突变量。
        granovetter_burst_migrating: 邻居传染→迁徙→抗议突变量。
    """

    hunger_to_protest_working: float = Field(default=0.60, ge=0.0)
    hunger_to_migrate_working: float = Field(default=0.15, ge=0.0)
    hunger_to_protest_resting: float = Field(default=0.45, ge=0.0)
    hunger_to_work_resting: float = Field(default=0.20, ge=0.0)
    hunger_to_protest_social: float = Field(default=0.50, ge=0.0)
    hunger_to_protest_trading: float = Field(default=0.30, ge=0.0)
    tax_to_protest_working: float = Field(default=0.45, ge=0.0)
    tax_to_protest_resting: float = Field(default=0.30, ge=0.0)
    tax_to_protest_trading: float = Field(default=0.30, ge=0.0)
    tax_to_protest_social: float = Field(default=0.25, ge=0.0)
    safety_to_fight_social: float = Field(default=0.10, ge=0.0)
    safety_to_fight_protest: float = Field(default=0.30, ge=0.0)
    granovetter_burst_working: float = Field(default=0.80, ge=0.0)
    granovetter_burst_resting: float = Field(default=0.70, ge=0.0)
    granovetter_burst_social: float = Field(default=0.85, ge=0.0)
    granovetter_burst_trading: float = Field(default=0.60, ge=0.0)
    granovetter_burst_migrating: float = Field(default=0.50, ge=0.0)


class SatisfactionCoefficientsConfig(BaseModel):
    """满意度更新系数配置。

    Attributes:
        scarcity_high_penalty: 高稀缺（>0.5）满意度惩罚。
        scarcity_mid_penalty: 中稀缺（>0.3）满意度惩罚。
        scarcity_low_recovery: 低稀缺（<0.2）满意度恢复。
        tax_penalty_threshold: 税率惩罚阈值。
        tax_penalty_factor: 税率惩罚系数。
        hunger_penalty_threshold: 饥饿惩罚阈值。
        hunger_penalty: 饥饿满意度惩罚。
        oppression_threshold: 警察国家效应阈值。
        oppression_factor: 警察国家效应系数。
    """

    scarcity_high_penalty: float = Field(default=0.10, ge=0.0)
    scarcity_mid_penalty: float = Field(default=0.04, ge=0.0)
    scarcity_low_recovery: float = Field(default=0.01, ge=0.0)
    tax_penalty_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    tax_penalty_factor: float = Field(default=0.15, ge=0.0)
    hunger_penalty_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    hunger_penalty: float = Field(default=0.08, ge=0.0)
    oppression_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    oppression_factor: float = Field(default=0.03, ge=0.0)


class AdaptiveControllerConfig(BaseModel):
    """自适应控制器配置。

    Attributes:
        enabled: 是否启用自适应控制器。
        update_interval: 每 N tick 更新一次。
        target_temperature: 目标系统温度 [0, 1]。
        adjustment_rate: P-controller 调节速率。
        min_multiplier: 系数乘数下限。
        max_multiplier: 系数乘数上限。
        lookback_ticks: 近期革命统计回溯 tick 数。
    """

    enabled: bool = True
    update_interval: int = Field(default=10, gt=0)
    target_temperature: float = Field(default=0.30, ge=0.0, le=1.0)
    adjustment_rate: float = Field(default=0.15, ge=0.0, le=1.0)
    min_multiplier: float = Field(default=0.3, ge=0.0)
    max_multiplier: float = Field(default=2.0, ge=1.0)
    lookback_ticks: int = Field(default=200, gt=0)
