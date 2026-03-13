"""CivSim 配置加载与验证模块。

通过 Pydantic 模型对 config.yaml 进行类型安全的加载和校验。
所有可配置项统一由此模块管理，禁止在代码中硬编码配置值。
"""

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator

from civsim.config_params import (
    AdaptiveControllerConfig,
    LeaderPromptConfig,
    MarkovCoefficientsConfig,
    RevolutionParamsConfig,
    SatisfactionCoefficientsConfig,
    TradeParamsConfig,
)
from civsim.config_params_ext import (
    AnalyticsParamsConfig,
    CivilianBehaviorConfig,
    DiplomacyParamsConfig,
    EngineParamsConfig,
    EventParamsConfig,
    GatewayParamsConfig,
    GovernanceParamsConfig,
    GovernorFallbackConfig,
    LeaderFallbackConfig,
    MapSuitabilityConfig,
    MemoryParamsConfig,
    SeasonParamsConfig,
    SettlementParamsConfig,
    TileParamsConfig,
)

# ============================================================
# 子配置模型
# ============================================================


class ProjectConfig(BaseModel):
    """项目基本信息。"""

    name: str = "CivSim"
    version: str = "0.1.0"


class LLMModelConfig(BaseModel):
    """单个 LLM 模型配置。"""

    provider: str = "openai"
    model: str = ""
    max_tokens: int = 1024
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    api_key: str | None = None
    base_url: str | None = None


class LLMCacheConfig(BaseModel):
    """LLM 行为缓存配置。"""

    enabled: bool = True
    similarity_threshold: float = Field(default=0.92, ge=0.0, le=1.0)
    max_cache_size: int = Field(default=10000, gt=0)


class LLMConfig(BaseModel):
    """LLM 网关总配置。"""

    gateway: str = "litellm"
    default_api_key: str = ""
    default_base_url: str = ""
    models: dict[str, LLMModelConfig] = Field(default_factory=dict)
    cache: LLMCacheConfig = Field(default_factory=LLMCacheConfig)

    @field_validator("default_api_key", "default_base_url", mode="before")
    @classmethod
    def expand_env_var(cls, v: str) -> str:
        """将 ${VAR_NAME} 格式的值展开为环境变量。"""
        if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
            env_key = v[2:-1]
            return os.environ.get(env_key, "")
        return v

    def get_model_config(self, role: str) -> LLMModelConfig:
        """获取指定角色的模型配置，自动填充默认 api_key/base_url。

        Args:
            role: 角色名（governor / leader / leader_opus）。

        Returns:
            合并了默认值的模型配置。
        """
        if role not in self.models:
            msg = f"未找到角色 '{role}' 的 LLM 模型配置"
            raise KeyError(msg)
        cfg = self.models[role]
        return LLMModelConfig(
            provider=cfg.provider,
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            api_key=cfg.api_key or self.default_api_key,
            base_url=cfg.base_url or self.default_base_url or None,
        )


class GridConfig(BaseModel):
    """世界网格尺寸。"""

    width: int = Field(default=100, gt=0)
    height: int = Field(default=100, gt=0)


class MapGenerationConfig(BaseModel):
    """Perlin Noise 地图生成参数。"""

    algorithm: str = "perlin_noise"
    seed: int | None = None
    elevation_scale: float = Field(default=20.0, gt=0)
    moisture_scale: float = Field(default=15.0, gt=0)
    octaves: int = Field(default=6, gt=0)
    persistence: float = Field(default=0.5, gt=0.0, le=1.0)


class TileThresholdsConfig(BaseModel):
    """地块类型判定阈值。"""

    mountain_elevation: float = Field(default=0.70, ge=0.0, le=1.0)
    water_moisture: float = Field(default=0.60, ge=0.0, le=1.0)
    forest_elevation: float = Field(default=0.50, ge=0.0, le=1.0)
    farmland_moisture: float = Field(default=0.30, ge=0.0, le=1.0)


class SettlementPlacementConfig(BaseModel):
    """聚落自动放置配置。"""

    auto_placement: bool = True
    min_suitability_score: float = Field(default=0.3, ge=0.0, le=1.0)
    initial_count: int = Field(default=8, gt=0)


class WorldConfig(BaseModel):
    """世界引擎总配置。"""

    grid: GridConfig = Field(default_factory=GridConfig)
    map_generation: MapGenerationConfig = Field(default_factory=MapGenerationConfig)
    tile_thresholds: TileThresholdsConfig = Field(default_factory=TileThresholdsConfig)
    settlement: SettlementPlacementConfig = Field(default_factory=SettlementPlacementConfig)


class ClockConfig(BaseModel):
    """时间系统配置。"""

    ticks_per_day: int = Field(default=4, gt=0)
    days_per_season: int = Field(default=30, gt=0)
    seasons_per_year: int = Field(default=4, gt=0)
    governor_decision_interval: str = "season"
    leader_decision_interval: str = "year"

    @property
    def ticks_per_season(self) -> int:
        """每季度的 tick 数。"""
        return self.ticks_per_day * self.days_per_season

    @property
    def ticks_per_year(self) -> int:
        """每年的 tick 数。"""
        return self.ticks_per_season * self.seasons_per_year


class RevoltThresholdConfig(BaseModel):
    """Granovetter 阈值分布参数。"""

    mean: float = Field(default=0.25, ge=0.0, le=1.0)
    std: float = Field(default=0.12, ge=0.0)
    min: float = Field(default=0.05, ge=0.0, le=1.0)
    max: float = Field(default=0.80, ge=0.0, le=1.0)


class PersonalityDistributionConfig(BaseModel):
    """性格类型分布比例。"""

    compliant: float = Field(default=0.40, ge=0.0, le=1.0)
    neutral: float = Field(default=0.35, ge=0.0, le=1.0)
    rebellious: float = Field(default=0.25, ge=0.0, le=1.0)

    @field_validator("rebellious", mode="after")
    @classmethod
    def validate_sum(cls, v: float, info: object) -> float:
        """验证三种性格比例之和为 1.0。"""
        data = info.data if hasattr(info, "data") else {}
        total = data.get("compliant", 0.5) + data.get("neutral", 0.35) + v
        if abs(total - 1.0) > 0.01:
            msg = f"性格分布比例之和必须为 1.0，当前为 {total}"
            raise ValueError(msg)
        return v


class CivilianAgentConfig(BaseModel):
    """平民 Agent 配置。"""

    initial_count: int = Field(default=1000, ge=0)
    personality_distribution: PersonalityDistributionConfig = Field(
        default_factory=PersonalityDistributionConfig
    )
    revolt_threshold: RevoltThresholdConfig = Field(default_factory=RevoltThresholdConfig)
    hunger_decay_per_tick: float = Field(default=0.02, ge=0.0)


class GovernorAgentConfig(BaseModel):
    """镇长 Agent 配置。"""

    initial_count: int = Field(default=0, ge=0)
    decision_context_window: int = Field(default=120, gt=0)


class LeaderAgentConfig(BaseModel):
    """首领 Agent 配置。"""

    initial_count: int = Field(default=0, ge=0)
    memory_max_entries: int = Field(default=500, gt=0)


class AgentsConfig(BaseModel):
    """所有 Agent 类型的总配置。"""

    civilian: CivilianAgentConfig = Field(default_factory=CivilianAgentConfig)
    governor: GovernorAgentConfig = Field(default_factory=GovernorAgentConfig)
    leader: LeaderAgentConfig = Field(default_factory=LeaderAgentConfig)


class ResourceRegenerationConfig(BaseModel):
    """资源再生速率。"""

    farmland_per_tick: float = Field(default=0.8, ge=0.0)
    forest_per_tick: float = Field(default=0.3, ge=0.0)
    mine_per_tick: float = Field(default=0.0, ge=0.0)


class ResourceConsumptionConfig(BaseModel):
    """资源消耗速率。"""

    food_per_civilian_per_tick: float = Field(default=0.5, ge=0.0)


class InitialStockpileConfig(BaseModel):
    """聚落初始资源储备。"""

    food: float = Field(default=500, ge=0.0)
    wood: float = Field(default=200, ge=0.0)
    ore: float = Field(default=50, ge=0.0)
    gold: float = Field(default=100, ge=0.0)


class ResourcesConfig(BaseModel):
    """资源系统总配置。"""

    types: list[str] = Field(default_factory=lambda: ["food", "wood", "ore", "gold"])
    regeneration: ResourceRegenerationConfig = Field(default_factory=ResourceRegenerationConfig)
    consumption: ResourceConsumptionConfig = Field(default_factory=ResourceConsumptionConfig)
    initial_stockpile: InitialStockpileConfig = Field(default_factory=InitialStockpileConfig)


class MQTTTopicsConfig(BaseModel):
    """MQTT 消息主题模板。"""

    p2p: str = "civsim/agent/{agent_id}/direct"
    settlement: str = "civsim/settlement/{settlement_id}/broadcast"
    global_topic: str = Field(default="civsim/world/broadcast", alias="global")


class MQTTConfig(BaseModel):
    """MQTT 通信配置。"""

    broker_host: str = "localhost"
    broker_port: int = Field(default=1883, gt=0)
    topics: MQTTTopicsConfig = Field(default_factory=MQTTTopicsConfig)


class DatabaseConfig(BaseModel):
    """数据存储配置。"""

    engine: str = "duckdb"
    path: str = "scripts/data/simulations/civsim.duckdb"
    snapshot_interval: int = Field(default=100, gt=0)


class TestingConfig(BaseModel):
    """测试环境配置。"""

    use_real_llm: bool = True
    test_simulation_ticks: int = Field(default=50, gt=0)
    test_civilian_count: int = Field(default=20, gt=0)
    test_grid_size: int = Field(default=20, gt=0)


class VisualizationConfig(BaseModel):
    """可视化配置。"""

    enabled: bool = True
    renderer: str = "matplotlib"
    update_interval: int = Field(default=10, gt=0)
    export_format: str = "png"


class DashboardConfig(BaseModel):
    """造物主面板配置。"""

    port: int = Field(default=8050, gt=0)
    refresh_interval_ms: int = Field(default=1000, gt=100)
    max_history: int = Field(default=5000, gt=100)
    snapshot_dir: str = "data/snapshots"
    export_dir: str = "data/exports"


class RayConfig(BaseModel):
    """Ray 分布式执行配置。"""

    enabled: bool = False
    num_workers: int = Field(default=4, gt=0)
    batch_size: int = Field(default=100, gt=0)
    object_store_memory_mb: int = Field(default=200, gt=0)


class PerformanceConfig(BaseModel):
    """性能优化配置。"""

    parallel_threshold: int = Field(default=200, ge=0)
    profiling_enabled: bool = False


# ============================================================
# 顶层配置模型
# ============================================================


class CivSimConfig(BaseModel):
    """CivSim 全局配置根模型。"""

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    world: WorldConfig = Field(default_factory=WorldConfig)
    clock: ClockConfig = Field(default_factory=ClockConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    resources: ResourcesConfig = Field(default_factory=ResourcesConfig)
    mqtt: MQTTConfig = Field(default_factory=MQTTConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    testing: TestingConfig = Field(default_factory=TestingConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    ray: RayConfig = Field(default_factory=RayConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    revolution_params: RevolutionParamsConfig = Field(
        default_factory=RevolutionParamsConfig,
    )
    trade_params: TradeParamsConfig = Field(default_factory=TradeParamsConfig)
    markov_coefficients: MarkovCoefficientsConfig = Field(
        default_factory=MarkovCoefficientsConfig,
    )
    satisfaction_coefficients: SatisfactionCoefficientsConfig = Field(
        default_factory=SatisfactionCoefficientsConfig,
    )
    adaptive_controller: AdaptiveControllerConfig = Field(
        default_factory=AdaptiveControllerConfig,
    )
    tile_params: TileParamsConfig = Field(default_factory=TileParamsConfig)
    season_params: SeasonParamsConfig = Field(default_factory=SeasonParamsConfig)
    map_suitability: MapSuitabilityConfig = Field(
        default_factory=MapSuitabilityConfig,
    )
    event_params: EventParamsConfig = Field(default_factory=EventParamsConfig)
    engine_params: EngineParamsConfig = Field(default_factory=EngineParamsConfig)
    civilian_behavior: CivilianBehaviorConfig = Field(
        default_factory=CivilianBehaviorConfig,
    )
    governor_fallback: GovernorFallbackConfig = Field(
        default_factory=GovernorFallbackConfig,
    )
    leader_fallback: LeaderFallbackConfig = Field(
        default_factory=LeaderFallbackConfig,
    )
    governance_params: GovernanceParamsConfig = Field(
        default_factory=GovernanceParamsConfig,
    )
    diplomacy_params: DiplomacyParamsConfig = Field(
        default_factory=DiplomacyParamsConfig,
    )
    settlement_params: SettlementParamsConfig = Field(
        default_factory=SettlementParamsConfig,
    )
    analytics_params: AnalyticsParamsConfig = Field(
        default_factory=AnalyticsParamsConfig,
    )
    gateway_params: GatewayParamsConfig = Field(
        default_factory=GatewayParamsConfig,
    )
    memory_params: MemoryParamsConfig = Field(
        default_factory=MemoryParamsConfig,
    )
    leader_prompt: LeaderPromptConfig = Field(
        default_factory=LeaderPromptConfig,
    )
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)


# ============================================================
# 配置加载函数
# ============================================================

# 项目根目录（config.yaml 所在位置）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def find_config_path(config_path: str | Path | None = None) -> Path:
    """查找配置文件路径。

    Args:
        config_path: 显式指定的配置文件路径。为 None 时自动查找。

    Returns:
        配置文件的绝对路径。

    Raises:
        FileNotFoundError: 找不到配置文件。
    """
    if config_path is not None:
        path = Path(config_path)
        if not path.exists():
            msg = f"指定的配置文件不存在: {path}"
            raise FileNotFoundError(msg)
        return path.resolve()

    # 按优先级搜索: 当前目录 → 项目根目录
    candidates = [
        Path.cwd() / "config.yaml",
        _PROJECT_ROOT / "config.yaml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    msg = f"找不到 config.yaml，已搜索: {[str(c) for c in candidates]}"
    raise FileNotFoundError(msg)


def load_config(config_path: str | Path | None = None) -> CivSimConfig:
    """加载并验证 config.yaml 配置文件。

    Args:
        config_path: 配置文件路径。为 None 时自动查找。

    Returns:
        经过 Pydantic 验证的配置对象。

    Raises:
        FileNotFoundError: 找不到配置文件。
        pydantic.ValidationError: 配置内容不符合模型约束。
    """
    path = find_config_path(config_path)
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raw = {}

    return CivSimConfig(**raw)


# 全局单例（延迟初始化）
_config: CivSimConfig | None = None


def get_config(config_path: str | Path | None = None) -> CivSimConfig:
    """获取全局配置单例。

    首次调用时加载配置文件，后续调用返回缓存实例。

    Args:
        config_path: 仅首次加载时生效的配置文件路径。

    Returns:
        全局配置对象。
    """
    global _config
    if _config is None:
        _config = load_config(config_path)
    return _config


def reset_config() -> None:
    """重置全局配置单例（用于测试）。"""
    global _config
    _config = None
