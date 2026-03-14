"""场景预设模块 — 荷兰病、信息茧房、世界末日一键配置。

将 scripts/ 下三大经典场景的核心设定封装为运行时可注入的预设，
通过造物主面板一键应用到正在运行的仿真引擎。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from civsim.world.tiles import TileType


@dataclass
class ScenarioPreset:
    """场景预设元数据。

    Attributes:
        key: 场景标识符。
        name: 中文名称。
        description: 场景简述。
    """

    key: str
    name: str
    description: str


# ── 预设注册表 ───────────────────────────────────────────────

SCENARIO_REGISTRY: list[ScenarioPreset] = [
    ScenarioPreset(
        key="dutch_disease",
        name="荷兰病（资源诅咒）",
        description="一个聚落黄金暴富但粮食为零、农田荒废，观察贸易依赖与社会崩溃",
    ),
    ScenarioPreset(
        key="info_cocoon",
        name="信息茧房（虚假繁荣）",
        description="~15%聚落处于高税低粮极端困境，其余正常，观察涌现差异",
    ),
    ScenarioPreset(
        key="apocalypse",
        name="世界末日（全球危机）",
        description="所有聚落同时陷入极端资源匮乏+50%农田毁坏，观察幸存率",
    ),
]


def get_preset_options() -> list[dict[str, str]]:
    """返回场景预设下拉框选项列表。"""
    return [
        {"label": p.name, "value": p.key}
        for p in SCENARIO_REGISTRY
    ]


# ── 场景应用函数 ─────────────────────────────────────────────


def apply_scenario(engine: Any, key: str) -> list[str]:
    """将指定场景预设应用到运行中的引擎。

    Args:
        engine: CivilizationEngine 实例。
        key: 场景标识符。

    Returns:
        事件日志消息列表。
    """
    handler = _SCENARIO_HANDLERS.get(key)
    if handler is None:
        return [f"⚠ 未知场景: {key}"]
    return handler(engine)


# ── 生存保障参数包（三场景共用）──────────────────────────────


def _apply_survival_params(engine: Any) -> str:
    """注入统一的生存保障参数，让文明在压力下挣扎而非瞬间崩溃。

    核心思路：拉宽食物产出-消耗的安全边际，降低死亡速率，
    缓和抗议/革命烈度，给贸易和迁徙留出反应窗口。

    Args:
        engine: CivilizationEngine 实例。

    Returns:
        日志消息。
    """
    c = engine.config

    # ── 食物经济：拉宽安全边际 ──
    c.civilian_behavior.work_output_food = 4.0      # 农民产出 2.5→4.0
    c.resources.consumption.food_per_civilian_per_tick = 0.3  # 消耗 0.5→0.3

    # ── 饥荒死亡率：大幅降低 ──
    c.settlement_params.starvation_unfed_factor = 0.005  # 断粮致死 0.05→0.005
    c.engine_params.starvation_rate_factor = 0.01        # 稀缺致死 0.1→0.01

    # ── 革命惩罚：温和化 ──
    c.revolution_params.resource_penalty_food = 0.2      # 食物损失 80%→20%
    c.revolution_params.population_loss_ratio = 0.03     # 人口损失 10%→3%
    c.revolution_params.protest_threshold = 0.35         # 革命门槛 0.20→0.35

    # ── 抗议传染：降低烈度 ──
    c.markov_coefficients.hunger_to_protest_working = 0.30   # 0.60→0.30
    c.markov_coefficients.hunger_to_protest_social = 0.25    # 0.50→0.25
    c.markov_coefficients.granovetter_burst_working = 0.40   # 0.80→0.40
    c.markov_coefficients.granovetter_burst_social = 0.45    # 0.85→0.45

    # ── 贸易：提高流通效率 ──
    c.trade_params.food_surplus_threshold = 3.0
    c.trade_params.surplus_trade_ratio = 0.5
    c.trade_params.refuse_prob_base = 0.1
    c.trade_params.max_trades_per_settlement_per_tick = 5

    return (
        "⚙ 生存保障参数已注入: "
        "食物产出↑消耗↓, 饥荒致死率↓↓, "
        "革命惩罚↓, 抗议传染↓, 贸易↑"
    )


# ── 荷兰病 ──────────────────────────────────────────────────


def _apply_dutch_disease(engine: Any) -> list[str]:
    """荷兰病：一个聚落暴富但无粮。

    富裕聚落拥有巨量黄金但农田荒废、粮食为零，
    必须依赖贸易从其他聚落购买食物才能存活。
    """
    logs: list[str] = []
    settlements = list(engine.settlements.values())
    if not settlements:
        return ["⚠ 无聚落可配置"]

    # 选人口最多的聚落作为"富裕聚落"
    rich = max(settlements, key=lambda s: s.population)
    others = [s for s in settlements if s.id != rich.id]

    # ── 注入生存保障参数 ──
    if hasattr(engine, "config"):
        logs.append(_apply_survival_params(engine))

    # ── 富裕聚落：暴金、零粮 ──
    rich.stockpile["gold"] = 50000.0
    rich.stockpile["food"] = 0.0
    rich.tax_rate = 0.1
    rich.security_level = 0.5
    logs.append(
        f"💰 [{rich.name}] 金币→50000, 食物→0, "
        f"税率→10%, 治安→50%"
    )

    # 摧毁富裕聚落领地内的农田（保留极低肥力，允许缓慢再生）
    destroyed = 0
    for tx, ty in rich.territory_tiles:
        tile = engine.tile_grid[tx][ty]
        if tile.tile_type == TileType.FARMLAND:
            tile.fertility = 0.05
            destroyed += 1
    if destroyed:
        logs.append(f"🏜 [{rich.name}] {destroyed} 块农田肥力降至 0.05")

    # ── 其余聚落：充足粮食、少量金币 ──
    for s in others:
        s.stockpile["food"] = 5000.0
        s.stockpile["gold"] = 50.0
        s.tax_rate = 0.15
        s.security_level = 0.5
    logs.append(
        f"🌾 其余 {len(others)} 个聚落: "
        f"食物→5000, 金币→50, 税率→15%"
    )

    logs.insert(0, "🎬 场景预设 [荷兰病] 已应用")
    return logs


# ── 信息茧房 ────────────────────────────────────────────────


def _apply_info_cocoon(engine: Any) -> list[str]:
    """信息茧房：部分聚落极端困境。

    ~15%聚落处于高税低粮的极端困境，其余正常。
    困境聚落面临真实生存压力，观察是否有迁徙/贸易救济。
    """
    logs: list[str] = []
    settlements = list(engine.settlements.values())
    if not settlements:
        return ["⚠ 无聚落可配置"]

    # ── 注入生存保障参数 ──
    if hasattr(engine, "config"):
        logs.append(_apply_survival_params(engine))

    # ~15% 聚落陷入困境
    n_lying = max(1, int(len(settlements) * 0.15))
    rng = random.Random(42)
    crisis = rng.sample(settlements, min(n_lying, len(settlements)))
    crisis_ids = {s.id for s in crisis}
    honest = [s for s in settlements if s.id not in crisis_ids]

    # ── 困境聚落：高税、低粮、低治安 ──
    for s in crisis:
        s.stockpile["food"] = 100.0
        s.stockpile["gold"] = 20.0
        s.tax_rate = 0.5
        s.security_level = 0.3

    crisis_names = ", ".join(s.name for s in crisis[:5])
    suffix = f"等{len(crisis)}个" if len(crisis) > 5 else ""
    logs.append(
        f"🔴 困境聚落 [{crisis_names}{suffix}]: "
        f"食物→100, 税率→50%, 治安→30%"
    )

    # ── 正常聚落 ──
    for s in honest:
        s.stockpile["food"] = 3000.0
        s.tax_rate = 0.15
        s.security_level = 0.5
    logs.append(
        f"🟢 正常聚落 ({len(honest)}个): "
        f"食物→3000, 税率→15%, 治安→50%"
    )

    logs.insert(0, "🎬 场景预设 [信息茧房] 已应用")
    return logs


# ── 世界末日 ────────────────────────────────────────────────


def _apply_apocalypse(engine: Any) -> list[str]:
    """世界末日：全局极端危机。

    所有聚落同时陷入资源匮乏，50%农田被毁。
    文明需要在极端逆境中缓慢恢复。
    """
    logs: list[str] = []
    settlements = list(engine.settlements.values())
    if not settlements:
        return ["⚠ 无聚落可配置"]

    # ── 注入生存保障参数 ──
    if hasattr(engine, "config"):
        logs.append(_apply_survival_params(engine))

    # ── 所有聚落：极端匮乏 ──
    for s in settlements:
        s.stockpile["food"] = 100.0
        s.stockpile["gold"] = 20.0
        s.stockpile["wood"] = 10.0
        s.stockpile["ore"] = 5.0
        s.tax_rate = 0.4
        s.security_level = 0.3
    logs.append(
        f"💀 全部 {len(settlements)} 个聚落: "
        f"食物→100, 金→20, 木→10, 矿→5, 税→40%, 治安→30%"
    )

    # ── 摧毁 50% 农田 ──
    farmland_tiles = []
    w = len(engine.tile_grid)
    h = len(engine.tile_grid[0]) if w > 0 else 0
    for x in range(w):
        for y in range(h):
            tile = engine.tile_grid[x][y]
            if tile.tile_type == TileType.FARMLAND:
                farmland_tiles.append(tile)

    rng = random.Random(77)
    n_destroy = len(farmland_tiles) // 2
    targets = rng.sample(farmland_tiles, min(n_destroy, len(farmland_tiles)))
    for tile in targets:
        tile.fertility = 0.1
    logs.append(
        f"🏜 {len(targets)}/{len(farmland_tiles)} 块农田"
        f"肥力降至 0.1"
    )

    logs.insert(0, "🎬 场景预设 [世界末日] 已应用")
    return logs


# ── 场景处理器映射 ────────────────────────────────────────────

_SCENARIO_HANDLERS: dict[str, Any] = {
    "dutch_disease": _apply_dutch_disease,
    "info_cocoon": _apply_info_cocoon,
    "apocalypse": _apply_apocalypse,
}
