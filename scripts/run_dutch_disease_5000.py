"""荷兰病(资源诅咒) 5000 Agent 全系统真实 LLM 模拟。

1个聚落拥有海量金币但粮食产出为0（农田完全退化），
其他聚落有粮食但缺钱。所有镇长和首领使用真实 LLM 决策。

观察首富聚落是否会被恶意抬价或贸易禁运饿死，
以及 LLM 驱动的镇长/首领如何应对资源诅咒。
"""

import gc
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from civsim.agents.civilian import Civilian
from civsim.agents.governor import Governor
from civsim.config import load_config

from scenario_utils import (
    SimLog,
    compute_scaling,
    count_wars,
    get_active_llm_model,
    get_civilians_stats,
    get_global_stats,
    get_memory_mb,
    log_system_info,
)


@dataclass
class DutchDiseaseScenarioConfig:
    """荷兰病场景专用参数。"""

    n_agents: int = 5000
    n_ticks: int = 500
    seed: int = 88
    # 首富聚落初始条件
    rich_gold: float = 50000.0
    rich_food: float = 0.0
    rich_tax_rate: float = 0.1
    rich_security: float = 0.8
    # 穷聚落初始条件
    poor_food: float = 800.0
    poor_gold: float = 50.0
    poor_tax_rate: float = 0.2
    poor_security: float = 0.5
    # 地图适宜度（大规模需降低）
    min_suitability_score: float = 0.2
    # 输出目录
    output_dir: str = "data/scenarios/dutch_disease_5000"


def run_dutch_disease_5000(
    scenario: DutchDiseaseScenarioConfig | None = None,
) -> tuple[SimLog, bool, dict]:
    """运行 5000 Agent 荷兰病模拟。"""
    if scenario is None:
        scenario = DutchDiseaseScenarioConfig()

    sim = SimLog()
    scaling = compute_scaling(scenario.n_agents)
    n_settlements = scaling["settlements"]
    n_leaders = scaling["leaders"]
    grid_size = scaling["grid"]

    # 加载配置
    config = load_config()
    config.world.grid.width = grid_size
    config.world.grid.height = grid_size
    config.agents.civilian.initial_count = scenario.n_agents
    config.world.settlement.initial_count = n_settlements
    config.world.settlement.min_suitability_score = (
        scenario.min_suitability_score
    )
    config.agents.governor.initial_count = 1  # 开关：>0 即启用
    config.agents.leader.initial_count = n_leaders

    llm_model = get_active_llm_model(config)

    sim.log("=" * 70)
    sim.log("  荷兰病(资源诅咒) — 5000 Agent 全系统真实 LLM 模拟")
    sim.log("  [V3 自适应参数系统]")
    sim.log("=" * 70)
    sim.log(f"  平民: {scenario.n_agents}")
    sim.log(f"  聚落: {n_settlements}")
    sim.log(f"  首领: {n_leaders}")
    sim.log(f"  地图: {grid_size}x{grid_size}")
    sim.log(f"  Ticks: {scenario.n_ticks}")
    sim.log(f"  种子: {scenario.seed}")
    sim.log(f"  LLM: 真实调用 ({llm_model})")
    sim.log("")

    mem_start = get_memory_mb()

    try:
        # 创建引擎 — 全系统 + 真实 LLM
        sim.log(">>> 初始化引擎...")
        t0 = time.time()

        from civsim.world.engine import CivilizationEngine

        engine = CivilizationEngine(
            config=config, seed=scenario.seed,
            enable_governors=True, enable_leaders=True,
        )
        init_time = time.time() - t0
        sim.log(f"  初始化完成: {init_time:.1f}s")

        # 验证系统完整性
        governors = [a for a in engine.agents if isinstance(a, Governor)]
        log_system_info(sim, engine, config, governors)

        # ============================================================
        # 设置荷兰病场景
        # ============================================================
        sim.log("")
        sim.log(">>> 配置荷兰病场景...")

        settlements = list(engine.settlements.values())
        if len(settlements) < 2:
            sim.log("  错误: 需要至少2个聚落")
            return sim, False, {}

        rich = settlements[0]
        poor = settlements[1:]

        # 首富聚落：海量金币，零食物，农田退化
        rich.stockpile["gold"] = scenario.rich_gold
        rich.stockpile["food"] = scenario.rich_food
        rich.tax_rate = scenario.rich_tax_rate
        rich.security_level = scenario.rich_security

        # 摧毁首富聚落的所有农田
        farmland_destroyed = 0
        for x in range(len(engine.tile_grid)):
            for y in range(len(engine.tile_grid[x])):
                tile = engine.tile_grid[x][y]
                if tile.owner_settlement_id == rich.id:
                    if tile.tile_type.value == "farmland":
                        tile.fertility = 0.0
                        farmland_destroyed += 1

        sim.log(f"  首富聚落 [{rich.id}] {rich.name}:")
        sim.log(f"    金币 = {rich.stockpile['gold']:.0f}")
        sim.log(f"    食物 = {rich.stockpile['food']:.0f}")
        sim.log(f"    农田退化: {farmland_destroyed} 块")
        sim.log(f"    人口 = {rich.population}")

        # 其他聚落：有粮食但缺钱
        for s in poor:
            s.stockpile["food"] = scenario.poor_food
            s.stockpile["gold"] = scenario.poor_gold
            s.tax_rate = scenario.poor_tax_rate
            s.security_level = scenario.poor_security

        sim.log(f"  穷聚落 x{len(poor)}:")
        sim.log(
            f"    每个: 食物={scenario.poor_food:.0f}, "
            f"金币={scenario.poor_gold:.0f}"
        )
        sim.log("")

        # ============================================================
        # 运行模拟
        # ============================================================
        sim.log(">>> 开始模拟运行...")
        sim.log("")

        # Tick 0: 记录初始状态
        rich_pop_history = [rich.population]
        rich_food_history = [rich.stockpile.get("food", 0)]
        rich_gold_history = [rich.stockpile.get("gold", 0)]
        tick_times: list[float] = []
        ts_revolution = [0]
        ts_trade = [0]
        ts_satisfaction = [0.5]
        ts_temperature = [0.0]
        ts_protest_mult = [1.0]
        ts_granov_mult = [1.0]
        ts_recovery_mult = [1.0]
        ts_cooldown_mult = [1.0]
        ts_event_mult = [1.0]
        ts_war_count = [0]

        _last_sat = 0.5
        t_total_start = time.time()
        n_ticks = scenario.n_ticks

        for tick in range(1, n_ticks + 1):
            t_tick_start = time.time()
            engine.step()
            tick_time = time.time() - t_tick_start
            tick_times.append(tick_time)

            # 记录首富聚落数据
            rich_pop = rich.population
            rich_food = rich.stockpile.get("food", 0)
            rich_gold = rich.stockpile.get("gold", 0)
            rich_pop_history.append(rich_pop)
            rich_food_history.append(rich_food)
            rich_gold_history.append(rich_gold)

            # 每 tick 采集轻量统计
            rev_cnt = (
                engine.revolution_tracker.revolution_count
                if engine.revolution_tracker else 0
            )
            trade_cnt = (
                engine.trade_manager.trade_count
                if engine.trade_manager else 0
            )
            ts_revolution.append(rev_cnt)
            ts_trade.append(trade_cnt)

            # 满意度 (每 5 tick 采样一次)
            if tick % 5 == 1 or tick <= 5:
                civs_all = [
                    a for a in engine.agents if isinstance(a, Civilian)
                ]
                _last_sat = float(np.mean(
                    [c.satisfaction for c in civs_all],
                )) if civs_all else 0.5
            ts_satisfaction.append(_last_sat)

            # 自适应控制器
            ctrl = getattr(engine, "adaptive_controller", None)
            if ctrl is not None:
                ts_temperature.append(ctrl.temperature)
                c = ctrl.coefficients
                ts_protest_mult.append(c.markov_protest_multiplier)
                ts_granov_mult.append(c.granovetter_burst_multiplier)
                ts_recovery_mult.append(
                    c.satisfaction_recovery_multiplier,
                )
                ts_cooldown_mult.append(
                    c.revolution_cooldown_multiplier,
                )
                ts_event_mult.append(c.random_event_multiplier)
            else:
                ts_temperature.append(0.0)
                ts_protest_mult.append(1.0)
                ts_granov_mult.append(1.0)
                ts_recovery_mult.append(1.0)
                ts_cooldown_mult.append(1.0)
                ts_event_mult.append(1.0)

            # 战争数
            ts_war_count.append(count_wars(engine))

            # 关键 tick 输出详细日志
            ticks_per_season = config.clock.ticks_per_season
            ticks_per_year = config.clock.ticks_per_year
            is_governor_tick = (tick % ticks_per_season == 0)
            is_leader_tick = (tick % ticks_per_year == 0)
            is_milestone = (tick % 30 == 0) or tick <= 5

            if is_governor_tick:
                gov_total = sum(
                    g.decision_count for g in governors
                )
                sim.log(
                    f"  ★ [Tick {tick:3d}] 镇长决策轮! "
                    f"累计决策={gov_total} | tick耗时={tick_time:.1f}s"
                )

            if is_leader_tick:
                leader_total = sum(
                    l.decision_count for l in engine.leaders
                )
                sim.log(
                    f"  ★★ [Tick {tick:3d}] 首领决策轮! "
                    f"累计决策={leader_total} | tick耗时={tick_time:.1f}s"
                )

            if is_milestone or is_governor_tick or is_leader_tick:
                rich_stats = get_civilians_stats(engine, rich.id)
                global_stats = get_global_stats(engine)
                elapsed = time.time() - t_total_start

                adaptive_str = ""
                ai = global_stats.get("adaptive", {})
                if ai:
                    adaptive_str = (
                        f" | 温度={ai['temperature']:.2f} "
                        f"P×={ai['protest_mult']:.2f} "
                        f"G×={ai['granovetter_mult']:.2f} "
                        f"R恢={ai['recovery_mult']:.2f}"
                    )

                sim.log(
                    f"  [Tick {tick:3d}] "
                    f"首富: 人口={rich_pop} 食物={rich_food:.0f} "
                    f"金={rich_gold:.0f} 满意={rich_stats['avg_sat']:.2f} "
                    f"抗议={rich_stats['protest_ratio']:.2f} | "
                    f"全局: 贸易={global_stats['trade_count']} "
                    f"革命={global_stats['revolution_count']} "
                    f"联盟={global_stats['alliance_count']} "
                    f"战争={global_stats['war_count']}"
                    f"{adaptive_str} | "
                    f"tick={tick_time:.2f}s 累计={elapsed:.0f}s"
                )

            # 每 100 tick 输出一次详细聚落对比
            if tick % 100 == 0:
                sim.log(f"\n  --- Tick {tick} 聚落对比 ---")
                sim.log(
                    f"  {'聚落':>12} {'人口':>6} {'食物':>8} "
                    f"{'金币':>8} {'税率':>6} {'治安':>6}"
                )
                for s in settlements[:10]:
                    sim.log(
                        f"  {s.name[:12]:>12} {s.population:>6} "
                        f"{s.stockpile.get('food', 0):>8.0f} "
                        f"{s.stockpile.get('gold', 0):>8.0f} "
                        f"{s.tax_rate:>6.2f} "
                        f"{s.security_level:>6.2f}"
                    )
                if len(settlements) > 10:
                    sim.log(f"  ... 另有 {len(settlements)-10} 个聚落")
                sim.log("")

        total_time = time.time() - t_total_start
        mem_end = get_memory_mb()

        # ============================================================
        # 结果分析
        # ============================================================
        sim.log("")
        sim.log("=" * 70)
        sim.log("  模拟完成 — 结果分析")
        sim.log("=" * 70)
        sim.log(f"  总耗时: {total_time:.1f}s")
        sim.log(f"  平均 tick: {np.mean(tick_times)*1000:.1f}ms")
        sim.log(
            f"  P95 tick: {np.percentile(tick_times, 95)*1000:.1f}ms"
        )
        sim.log(
            f"  最大 tick: {max(tick_times)*1000:.1f}ms (可能含LLM调用)"
        )
        sim.log(f"  内存增量: {mem_end - mem_start:.1f} MB")
        sim.log("")

        # 首富聚落分析
        rich_survived = rich.population > 0
        pop_initial = rich_pop_history[0]
        pop_final = rich_pop_history[-1]
        pop_min = min(rich_pop_history)
        food_min = min(rich_food_history)
        gold_initial = rich_gold_history[0]
        gold_final = rich_gold_history[-1]

        sim.log("  [首富聚落分析]")
        sim.log(
            f"    存活: {'是' if rich_survived else '否 — 首富被饿死!'}"
        )
        sim.log(f"    人口: {pop_initial} → {pop_final} (最低 {pop_min})")
        sim.log(f"    食物最低点: {food_min:.0f}")
        sim.log(f"    金币: {gold_initial:.0f} → {gold_final:.0f}")
        sim.log(f"    最终食物: {rich.stockpile.get('food', 0):.0f}")
        sim.log(f"    税率: {rich.tax_rate:.2f}")
        sim.log(f"    治安: {rich.security_level:.2f}")
        sim.log("")

        # 全局分析
        final_stats = get_global_stats(engine)
        sim.log("  [全局分析]")
        sim.log(f"    总平民: {final_stats['total_civilians']}")
        sim.log(f"    平均满意度: {final_stats['avg_satisfaction']:.3f}")
        sim.log(f"    贸易总次数: {final_stats['trade_count']}")
        sim.log(f"    贸易总量: {final_stats['trade_volume']:.0f}")
        sim.log(f"    革命次数: {final_stats['revolution_count']}")
        sim.log(f"    联盟数: {final_stats['alliance_count']}")
        sim.log(f"    战争数: {final_stats['war_count']}")
        sim.log(f"    镇长总决策: {final_stats['governor_decisions']}")
        sim.log(f"    首领总决策: {final_stats['leader_decisions']}")
        sim.log("")

        # 自适应控制器分析
        ai = final_stats.get("adaptive", {})
        if ai:
            sim.log("  [自适应控制器]")
            sim.log(f"    最终温度: {ai['temperature']:.3f}")
            sim.log(f"    抗议系数乘数: {ai['protest_mult']:.3f}")
            sim.log(
                f"    Granovetter乘数: {ai['granovetter_mult']:.3f}"
            )
            sim.log(f"    冷却期乘数: {ai['cooldown_mult']:.3f}")
            sim.log(f"    恢复速度乘数: {ai['recovery_mult']:.3f}")
            sim.log(f"    随机事件乘数: {ai['event_mult']:.3f}")
            sim.log(
                f"    活跃恢复阶段: {final_stats['active_recoveries']}"
            )
            ctrl = engine.adaptive_controller
            if ctrl and ctrl.temperature_history:
                temps = [t for _, t in ctrl.temperature_history]
                sim.log(
                    f"    温度历史: min={min(temps):.3f} "
                    f"max={max(temps):.3f} avg={np.mean(temps):.3f}"
                )
            sim.log("")

        # 其他聚落是否因此富裕
        sim.log("  [穷聚落变化]")
        gold_gained = []
        for s in poor[:10]:
            sim.log(
                f"    {s.name[:12]}: 金={s.stockpile.get('gold', 0):.0f} "
                f"食物={s.stockpile.get('food', 0):.0f} 人口={s.population}"
            )
            gold_gained.append(
                s.stockpile.get("gold", 0) - scenario.poor_gold
            )
        if gold_gained:
            sim.log(
                f"    穷聚落平均金币增量: {np.mean(gold_gained):.0f}"
            )
        sim.log("")

        # 镇长决策日志
        sim.log("  [镇长决策记录]")
        rich_gov = None
        for g in governors:
            if g.settlement_id == rich.id:
                rich_gov = g
                break
        if rich_gov:
            sim.log(
                f"    首富镇长: 决策次数={rich_gov.decision_count}"
            )
            if rich_gov.last_decision:
                sim.log(
                    f"    最后一次决策: {rich_gov.last_decision}"
                )
        sim.log("")

        # 涌现事件
        emergence = (
            engine.emergence_detector.events
            if engine.emergence_detector else []
        )
        if emergence:
            sim.log(f"  [涌现事件] ({len(emergence)}个)")
            for e in emergence[:20]:
                sim.log(
                    f"    [{e.tick}] {e.event_type}: {e.description}"
                )
        else:
            sim.log("  [涌现事件] 无")

        # 革命事件
        rev_events = (
            engine.revolution_tracker.events
            if engine.revolution_tracker else []
        )
        if rev_events:
            sim.log(f"\n  [革命事件] ({len(rev_events)}个)")
            for e in rev_events[:20]:
                sim.log(
                    f"    [Tick {e.trigger_tick}] "
                    f"聚落{e.settlement_id}: {e.cause}"
                )
        sim.log("")

        # 打包时间序列数据
        ts_data = {
            "ticks": list(range(0, n_ticks + 1)),
            "rich_pop": rich_pop_history,
            "rich_food": rich_food_history,
            "rich_gold": rich_gold_history,
            "revolution": ts_revolution,
            "trade": ts_trade,
            "satisfaction": ts_satisfaction,
            "temperature": ts_temperature,
            "protest_mult": ts_protest_mult,
            "granov_mult": ts_granov_mult,
            "recovery_mult": ts_recovery_mult,
            "cooldown_mult": ts_cooldown_mult,
            "event_mult": ts_event_mult,
            "war_count": ts_war_count,
            "tick_times": tick_times,
            "rev_event_ticks": [
                e.trigger_tick for e in (
                    engine.revolution_tracker.events
                    if engine.revolution_tracker else []
                )
            ],
        }

        return sim, True, ts_data

    except Exception as e:
        import traceback
        sim.log(f"\n  !!! 模拟失败: {e}")
        sim.log(traceback.format_exc())
        return sim, False, {}


def generate_report(
    sim: SimLog,
    success: bool,
    scenario: DutchDiseaseScenarioConfig,
    llm_model: str,
) -> str:
    """生成 Markdown 报告。"""
    scaling = compute_scaling(scenario.n_agents)
    lines = [
        "# 荷兰病(资源诅咒) — 5000 Agent 全系统真实 LLM 模拟报告 "
        "[V3 自适应参数]",
        "",
        f"> 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 状态: {'成功' if success else '失败'}",
        "",
        "## 场景设定",
        "",
        f"**荷兰病(资源诅咒)**：1个聚落拥有极其海量的金币"
        f"（{scenario.rich_gold:.0f}金），"
        "但粮食产出完全为0（农田全部退化）。其他聚落有粮食但缺钱。"
        f"所有镇长和首领使用真实 LLM ({llm_model}) 做决策。",
        "",
        "**核心问题**：首富聚落会不会因为被其他聚落"
        "\"恶意抬高粮价\"或\"联合贸易禁运\"而活活饿死？"
        "财富是否会带来毁灭？LLM 驱动的领导者会如何应对？",
        "",
        "## 规模参数",
        "",
        "| 参数 | 值 |",
        "|------|-----|",
        f"| 平民数量 | {scenario.n_agents} |",
        f"| 聚落数量 | ~{scaling['settlements']} |",
        f"| 首领数量 | ~{scaling['leaders']} |",
        f"| 地图大小 | {scaling['grid']}×{scaling['grid']} |",
        f"| 模拟时长 | {scenario.n_ticks} ticks |",
        f"| LLM模式 | 真实调用 ({llm_model}) |",
        f"| 随机种子 | {scenario.seed} |",
        "",
        "## 模拟过程与结果",
        "",
        "```",
    ]

    for line in sim.lines:
        lines.append(line)

    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*本报告由 AI 文明模拟器自动生成*")

    return "\n".join(lines)


def generate_charts(ts: dict, out_dir: str) -> list[str]:
    """生成可视化图表并保存。

    Args:
        ts: 时间序列数据字典。
        out_dir: 输出目录。

    Returns:
        生成的图片路径列表。
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    from collections import Counter

    # 中文字体
    plt.rcParams["font.sans-serif"] = [
        "Arial Unicode MS", "PingFang SC", "Heiti SC", "SimHei",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    ticks = ts["ticks"]
    paths = []

    # V2 基准线
    V2_REVOLUTION = 105
    V2_SATISFACTION = 0.407

    # ================================================================
    # 图1: 首富聚落演化 (3行: 人口, 金币含暴跌, 食物)
    # ================================================================
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=False)
    fig.suptitle(
        "首富聚落演化 — 荷兰病 5000 Agent 模拟",
        fontsize=16, fontweight="bold",
    )

    # 人口
    ax1 = axes[0]
    ax1.plot(ticks, ts["rich_pop"], color="#2563eb", linewidth=2)
    ax1.fill_between(ticks, ts["rich_pop"], alpha=0.15, color="#2563eb")
    ax1.set_ylabel("人口", fontsize=12)
    ax1.set_title("人口变化", fontsize=13)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(ticks[0], ticks[-1])

    # 金币
    ax2 = axes[1]
    ax2.plot(ticks, ts["rich_gold"], color="#eab308", linewidth=2.5)
    ax2.fill_between(
        ticks, ts["rich_gold"], alpha=0.15, color="#eab308",
    )
    ax2.set_ylabel("金币", fontsize=12, color="#996600")
    ax2.set_title(
        "金币储备 (初始50000金 → Tick1暴跌至~1200 → 缓慢回升)",
        fontsize=13,
    )
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(ticks[0], ticks[-1])
    ax2.annotate(
        f"50,000 → {ts['rich_gold'][1]:.0f}\n(首轮贸易花光)",
        xy=(1, ts["rich_gold"][1]),
        xytext=(60, 35000),
        fontsize=10,
        arrowprops=dict(arrowstyle="->", color="#996600", lw=1.5),
        color="#996600",
        fontweight="bold",
    )

    # 食物
    ax3 = axes[2]
    ax3.plot(ticks, ts["rich_food"], color="#16a34a", linewidth=2)
    ax3.fill_between(
        ticks, ts["rich_food"], alpha=0.15, color="#16a34a",
    )
    ax3.set_ylabel("食物", fontsize=12, color="#16a34a")
    ax3.set_xlabel("Tick", fontsize=12)
    ax3.set_title(
        "食物储备 (初始0 → 用金币购入6500+ → 持续积累)",
        fontsize=13,
    )
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(ticks[0], ticks[-1])
    ax3.annotate(
        f"0 → {ts['rich_food'][1]:.0f}\n(用金币买粮)",
        xy=(1, ts["rich_food"][1]),
        xytext=(60, 2000),
        fontsize=10,
        arrowprops=dict(arrowstyle="->", color="#16a34a", lw=1.5),
        color="#16a34a",
        fontweight="bold",
    )

    plt.tight_layout()
    p = f"{out_dir}/chart1_rich_settlement.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    paths.append(p)

    # ================================================================
    # 图2: 全局系统动力学
    # ================================================================
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle(
        "全局系统动力学 — V3 自适应 vs V2 基准",
        fontsize=16, fontweight="bold",
    )

    ax1 = axes[0]
    ax1.plot(
        ticks, ts["revolution"], color="#dc2626",
        linewidth=2.5, label="V3 累计革命",
    )
    ax1.axhline(
        y=V2_REVOLUTION, color="#dc2626", linestyle=":",
        alpha=0.6, linewidth=1.5,
        label=f"V2 基准 ({V2_REVOLUTION}次)",
    )
    ax1.fill_between(
        ticks, ts["revolution"], alpha=0.12, color="#dc2626",
    )
    ax1.set_ylabel("累计革命次数", fontsize=12)
    ax1.legend(fontsize=11, loc="upper left")
    ax1.set_title("革命累计曲线", fontsize=13)
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    ax2.plot(
        ticks, ts["satisfaction"], color="#2563eb",
        linewidth=2, label="V3 平均满意度",
    )
    ax2.axhline(
        y=V2_SATISFACTION, color="#2563eb", linestyle=":",
        alpha=0.6, linewidth=1.5,
        label=f"V2 基准 ({V2_SATISFACTION})",
    )
    ax2.fill_between(
        ticks, ts["satisfaction"], V2_SATISFACTION,
        where=[s > V2_SATISFACTION for s in ts["satisfaction"]],
        alpha=0.15, color="#16a34a", label="优于V2",
    )
    ax2.fill_between(
        ticks, ts["satisfaction"], V2_SATISFACTION,
        where=[s <= V2_SATISFACTION for s in ts["satisfaction"]],
        alpha=0.15, color="#dc2626", label="劣于V2",
    )
    ax2.set_ylabel("满意度", fontsize=12)
    ax2.set_xlabel("Tick", fontsize=12)
    ax2.set_ylim(0.0, 1.0)
    ax2.legend(fontsize=10, loc="lower left")
    ax2.set_title("全局平均满意度", fontsize=13)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    p = f"{out_dir}/chart2_global_dynamics.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    paths.append(p)

    # ================================================================
    # 图3: 自适应控制器
    # ================================================================
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle(
        "自适应 P-Controller 恒温器",
        fontsize=16, fontweight="bold",
    )

    ax1 = axes[0]
    ax1.plot(
        ticks, ts["temperature"], color="#f97316",
        linewidth=2.5, label="系统温度",
    )
    ax1.axhline(
        y=0.3, color="#6b7280", linestyle="--",
        alpha=0.7, linewidth=1.5, label="目标温度 (0.30)",
    )
    ax1.fill_between(
        ticks, ts["temperature"], 0.3,
        where=[t > 0.3 for t in ts["temperature"]],
        alpha=0.2, color="#ef4444", label="过热",
    )
    ax1.fill_between(
        ticks, ts["temperature"], 0.3,
        where=[t <= 0.3 for t in ts["temperature"]],
        alpha=0.2, color="#3b82f6", label="过冷",
    )
    ax1.set_ylabel("温度", fontsize=12)
    ax1.set_ylim(0.0, 0.8)
    ax1.legend(fontsize=10, loc="upper left")
    ax1.set_title("系统温度轨迹", fontsize=13)
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    ax2.plot(
        ticks, ts["protest_mult"], color="#dc2626",
        linewidth=2, label="抗议乘数",
    )
    ax2.plot(
        ticks, ts["granov_mult"], color="#f97316",
        linewidth=2, label="Granovetter乘数",
    )
    ax2.plot(
        ticks, ts["recovery_mult"], color="#16a34a",
        linewidth=2, label="恢复速度乘数",
    )
    ax2.plot(
        ticks, ts["cooldown_mult"], color="#8b5cf6",
        linewidth=2, label="冷却期乘数", linestyle="--",
    )
    ax2.axhline(
        y=1.0, color="#6b7280", linestyle=":",
        alpha=0.5, linewidth=1, label="基准 (1.0)",
    )
    ax2.set_ylabel("系数乘数", fontsize=12)
    ax2.set_xlabel("Tick", fontsize=12)
    ax2.set_ylim(0.0, 2.0)
    ax2.legend(fontsize=9, loc="upper right", ncol=2)
    ax2.set_title("自适应系数调节", fontsize=13)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    p = f"{out_dir}/chart3_adaptive_controller.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    paths.append(p)

    # ================================================================
    # 图4: 革命事件时间线 + 贸易/战争
    # ================================================================
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle(
        "涌现事件时间线",
        fontsize=16, fontweight="bold",
    )

    ax1 = axes[0]
    rev_ticks = ts.get("rev_event_ticks", [])
    if rev_ticks:
        counts = Counter(rev_ticks)
        all_t = sorted(counts.keys())
        vals = [counts[t] for t in all_t]
        ax1.bar(
            all_t, vals, width=1.5, color="#dc2626", alpha=0.8,
            label=f"革命事件 (共{len(rev_ticks)}次)",
        )
    ax1.set_ylabel("单 tick 革命数", fontsize=12)
    ax1.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax1.legend(fontsize=11, loc="upper left")
    ax1.set_title("革命爆发时间分布", fontsize=13)
    ax1.grid(True, alpha=0.3, axis="y")

    ax2 = axes[1]
    ax2.plot(
        ticks, ts["trade"], color="#16a34a",
        linewidth=2, label="累计贸易",
    )
    ax2.set_ylabel("累计贸易次数", fontsize=12, color="#16a34a")
    ax2.tick_params(axis="y", labelcolor="#16a34a")
    ax2.fill_between(ticks, ts["trade"], alpha=0.1, color="#16a34a")

    ax2b = ax2.twinx()
    ax2b.plot(
        ticks, ts["war_count"], color="#7c3aed",
        linewidth=2, label="活跃战争数",
    )
    ax2b.set_ylabel("战争数", fontsize=12, color="#7c3aed")
    ax2b.tick_params(axis="y", labelcolor="#7c3aed")
    ax2b.yaxis.set_major_locator(MaxNLocator(integer=True))

    lns = ax2.get_lines() + ax2b.get_lines()
    labs = [l.get_label() for l in lns]
    ax2.legend(lns, labs, loc="upper left", fontsize=11)
    ax2.set_xlabel("Tick", fontsize=12)
    ax2.set_title("贸易与战争", fontsize=13)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    p = f"{out_dir}/chart4_events_timeline.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    paths.append(p)

    return paths


def main() -> None:
    """入口函数。"""
    scenario = DutchDiseaseScenarioConfig()
    config = load_config()
    llm_model = get_active_llm_model(config)

    sim, success, ts_data = run_dutch_disease_5000(scenario)

    import os
    os.makedirs(scenario.output_dir, exist_ok=True)

    report = generate_report(sim, success, scenario, llm_model)
    report_path = f"{scenario.output_dir}/report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n{'='*70}")
    print(f"报告已保存至: {report_path}")

    # 生成可视化图表
    if ts_data:
        chart_paths = generate_charts(ts_data, scenario.output_dir)
        print(f"\n可视化图表:")
        for cp in chart_paths:
            print(f"  {cp}")

    print(f"{'='*70}")

    gc.collect()


if __name__ == "__main__":
    main()
