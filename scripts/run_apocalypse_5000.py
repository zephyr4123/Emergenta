"""世界末日(全面崩溃) 5000 Agent 全系统真实 LLM 模拟。

所有聚落同时陷入极端危机：食物耗尽、高税率、低治安、资源枯竭、
农田大面积退化。一场席卷全球的末日灾难。

核心问题：
1. 当所有聚落同时陷入饥荒，能否有任何文明存活？
2. LLM 首领会选择合作还是为残存资源厮杀？
3. 全面危机下革命级联会有多剧烈？
4. 贸易系统能否在普遍匮乏中成为救命稻草？
5. 最终存活率是多少？
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
class ApocalypseScenarioConfig:
    """世界末日场景专用参数。"""

    n_agents: int = 5000
    n_ticks: int = 500
    seed: int = 77
    # 全局末日初始条件
    initial_food: float = 30.0
    initial_gold: float = 20.0
    initial_wood: float = 10.0
    initial_ore: float = 5.0
    initial_tax_rate: float = 0.5
    initial_security: float = 0.2
    # 农田退化比例
    farmland_degrade_ratio: float = 0.5
    farmland_degrade_fertility: float = 0.1
    # 地图适宜度（大规模需降低）
    min_suitability_score: float = 0.2
    # 输出目录
    output_dir: str = "scripts/data/scenarios/apocalypse_5000"


def run_apocalypse_5000(
    scenario: ApocalypseScenarioConfig | None = None,
) -> tuple[SimLog, bool, dict]:
    """运行 5000 Agent 世界末日模拟。"""
    if scenario is None:
        scenario = ApocalypseScenarioConfig()

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
    sim.log("  世界末日(全面崩溃) — 5000 Agent 全系统真实 LLM 模拟")
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
        # 设置世界末日场景
        # ============================================================
        sim.log("")
        sim.log(">>> 配置世界末日场景...")

        settlements = list(engine.settlements.values())
        if len(settlements) < 2:
            sim.log("  错误: 需要至少2个聚落")
            return sim, False, {}

        # 所有聚落：极端初始条件
        for s in settlements:
            s.stockpile["food"] = scenario.initial_food
            s.stockpile["gold"] = scenario.initial_gold
            s.stockpile["wood"] = scenario.initial_wood
            s.stockpile["ore"] = scenario.initial_ore
            s.tax_rate = scenario.initial_tax_rate
            s.security_level = scenario.initial_security

        sim.log(f"  全部 {len(settlements)} 个聚落已设置末日条件:")
        sim.log(f"    食物 = {scenario.initial_food:.0f}")
        sim.log(f"    金币 = {scenario.initial_gold:.0f}")
        sim.log(f"    木材 = {scenario.initial_wood:.0f}")
        sim.log(f"    矿石 = {scenario.initial_ore:.0f}")
        sim.log(f"    税率 = {scenario.initial_tax_rate:.2f}")
        sim.log(f"    治安 = {scenario.initial_security:.2f}")

        # 退化 50% 的农田
        farmland_total = 0
        farmland_degraded = 0
        rng = np.random.default_rng(scenario.seed)
        for x in range(len(engine.tile_grid)):
            for y in range(len(engine.tile_grid[x])):
                tile = engine.tile_grid[x][y]
                if tile.tile_type.value == "farmland":
                    farmland_total += 1
                    if rng.random() < scenario.farmland_degrade_ratio:
                        tile.fertility = scenario.farmland_degrade_fertility
                        farmland_degraded += 1

        sim.log(
            f"  农田退化: {farmland_degraded}/{farmland_total} "
            f"({farmland_degraded/max(farmland_total,1)*100:.0f}%)"
        )

        # 统计初始总人口
        initial_total_pop = sum(s.population for s in settlements)
        sim.log(f"  初始总人口: {initial_total_pop}")
        sim.log("")

        # ============================================================
        # 运行模拟
        # ============================================================
        sim.log(">>> 开始模拟运行...")
        sim.log("")

        # 初始状态时间序列
        ts_global_pop = [initial_total_pop]
        ts_surviving_settlements = [len(settlements)]
        ts_total_food = [
            sum(s.stockpile.get("food", 0) for s in settlements)
        ]
        ts_total_gold = [
            sum(s.stockpile.get("gold", 0) for s in settlements)
        ]
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

            # 全局人口统计
            global_pop = sum(s.population for s in settlements)
            surviving = sum(
                1 for s in settlements if s.population > 0
            )
            total_food = sum(
                s.stockpile.get("food", 0) for s in settlements
            )
            total_gold = sum(
                s.stockpile.get("gold", 0) for s in settlements
            )
            ts_global_pop.append(global_pop)
            ts_surviving_settlements.append(surviving)
            ts_total_food.append(total_food)
            ts_total_gold.append(total_gold)

            # 全局统计
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

            # 满意度 (每 5 tick 采样)
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

                survival_rate = (
                    global_pop / initial_total_pop * 100
                    if initial_total_pop > 0 else 0
                )

                sim.log(
                    f"  [Tick {tick:3d}] "
                    f"人口={global_pop} ({survival_rate:.0f}%) "
                    f"存活聚落={surviving}/{len(settlements)} "
                    f"食物={total_food:.0f} "
                    f"金币={total_gold:.0f} | "
                    f"贸易={global_stats['trade_count']} "
                    f"革命={global_stats['revolution_count']} "
                    f"联盟={global_stats['alliance_count']} "
                    f"战争={global_stats['war_count']}"
                    f"{adaptive_str} | "
                    f"tick={tick_time:.2f}s 累计={elapsed:.0f}s"
                )

            # 每 100 tick 输出聚落存活排名
            if tick % 100 == 0:
                sorted_s = sorted(
                    settlements,
                    key=lambda s: s.population,
                    reverse=True,
                )
                alive = [s for s in sorted_s if s.population > 0]
                dead = len(settlements) - len(alive)
                sim.log(
                    f"\n  --- Tick {tick} 聚落存活排名 "
                    f"(存活 {len(alive)}/{len(settlements)}, "
                    f"灭亡 {dead}) ---"
                )
                sim.log(
                    f"  {'排名':>4} {'聚落':>10} {'人口':>6} "
                    f"{'食物':>8} {'金币':>8} {'税率':>6} {'治安':>6}"
                )
                for i, s in enumerate(alive[:10]):
                    sim.log(
                        f"  {i+1:>4} {s.name[:10]:>10} "
                        f"{s.population:>6} "
                        f"{s.stockpile.get('food', 0):>8.0f} "
                        f"{s.stockpile.get('gold', 0):>8.0f} "
                        f"{s.tax_rate:>6.2f} "
                        f"{s.security_level:>6.2f}"
                    )
                if len(alive) > 10:
                    sim.log(f"  ... 另有 {len(alive)-10} 个存活聚落")
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

        # 存活率分析
        final_pop = ts_global_pop[-1]
        survival_rate = (
            final_pop / initial_total_pop * 100
            if initial_total_pop > 0 else 0
        )
        final_surviving = ts_surviving_settlements[-1]
        pop_min = min(ts_global_pop)
        pop_min_tick = ts_global_pop.index(pop_min)

        sim.log("  [世界末日存活分析]")
        sim.log(
            f"    初始总人口: {initial_total_pop}"
        )
        sim.log(
            f"    最终总人口: {final_pop} "
            f"(存活率 {survival_rate:.1f}%)"
        )
        sim.log(
            f"    人口最低点: {pop_min} (tick {pop_min_tick})"
        )
        sim.log(
            f"    存活聚落: {final_surviving}/{len(settlements)} "
            f"(灭亡 {len(settlements)-final_surviving})"
        )
        sim.log(
            f"    最终总食物: {ts_total_food[-1]:.0f}"
        )
        sim.log(
            f"    最终总金币: {ts_total_gold[-1]:.0f}"
        )
        sim.log("")

        # 聚落存活详情
        sorted_final = sorted(
            settlements,
            key=lambda s: s.population,
            reverse=True,
        )
        alive_final = [s for s in sorted_final if s.population > 0]
        dead_final = [s for s in sorted_final if s.population == 0]

        sim.log("  [存活聚落 Top 10]")
        for i, s in enumerate(alive_final[:10]):
            sim.log(
                f"    #{i+1} {s.name[:12]}: "
                f"人口={s.population} "
                f"食物={s.stockpile.get('food', 0):.0f} "
                f"金币={s.stockpile.get('gold', 0):.0f} "
                f"税率={s.tax_rate:.2f} "
                f"治安={s.security_level:.2f}"
            )
        if len(alive_final) > 10:
            sim.log(f"    ... 另有 {len(alive_final)-10} 个存活")
        sim.log(f"    灭亡聚落: {len(dead_final)} 个")
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

        # 镇长决策记录（存活聚落的镇长）
        sim.log("  [存活聚落镇长决策记录]")
        alive_ids = {s.id for s in alive_final}
        for gov in governors:
            if gov.settlement_id in alive_ids and gov.decision_count > 0:
                sim.log(
                    f"    镇长{gov.unique_id} "
                    f"(聚落{gov.settlement_id}): "
                    f"决策次数={gov.decision_count}"
                )
                if gov.last_decision:
                    sim.log(f"    最后决策: {gov.last_decision}")
                break  # 只展示一个
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
            "global_pop": ts_global_pop,
            "surviving_settlements": ts_surviving_settlements,
            "total_food": ts_total_food,
            "total_gold": ts_total_gold,
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
            "initial_total_pop": initial_total_pop,
            "n_settlements": len(settlements),
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
    scenario: ApocalypseScenarioConfig,
    llm_model: str,
) -> str:
    """生成 Markdown 报告。"""
    scaling = compute_scaling(scenario.n_agents)
    lines = [
        "# 世界末日(全面崩溃) — 5000 Agent 全系统真实 LLM 模拟报告 "
        "[V3 自适应参数]",
        "",
        f"> 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 状态: {'成功' if success else '失败'}",
        "",
        "## 场景设定",
        "",
        "**世界末日(全面崩溃)**：所有聚落同时陷入极端危机——"
        f"食物仅剩 {scenario.initial_food:.0f}、"
        f"金币 {scenario.initial_gold:.0f}、"
        f"税率高达 {scenario.initial_tax_rate}、"
        f"治安仅 {scenario.initial_security}。"
        f"全球 {scenario.farmland_degrade_ratio*100:.0f}% 的农田退化"
        f"（肥力降至 {scenario.farmland_degrade_fertility}）。"
        f"所有镇长和首领使用真实 LLM ({llm_model}) 做决策。",
        "",
        "**核心问题**：",
        "1. 当所有聚落同时陷入饥荒，能否有任何文明存活？",
        "2. LLM 首领会选择合作互助还是为残存资源厮杀？",
        "3. 全面危机下革命级联会有多剧烈？",
        "4. 贸易系统能否在普遍匮乏中成为生存手段？",
        "5. 最终存活率是多少？自适应控制器能否力挽狂澜？",
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
        f"| 初始食物 | {scenario.initial_food:.0f} (全部聚落) |",
        f"| 初始金币 | {scenario.initial_gold:.0f} (全部聚落) |",
        f"| 初始税率 | {scenario.initial_tax_rate} (全部聚落) |",
        f"| 初始治安 | {scenario.initial_security} (全部聚落) |",
        f"| 农田退化 | {scenario.farmland_degrade_ratio*100:.0f}% |",
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
    """生成可视化图表并保存。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    from collections import Counter

    plt.rcParams["font.sans-serif"] = [
        "Arial Unicode MS", "PingFang SC", "Heiti SC", "SimHei",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    ticks = ts["ticks"]
    paths = []
    initial_pop = ts.get("initial_total_pop", 5000)
    n_settlements = ts.get("n_settlements", 62)

    # ================================================================
    # 图1: 世界末日总览 (3行: 人口, 存活聚落, 食物)
    # ================================================================
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=False)
    fig.suptitle(
        "世界末日总览 — 5000 Agent 全面崩溃模拟",
        fontsize=16, fontweight="bold",
    )

    # 全局人口
    ax1 = axes[0]
    ax1.plot(ticks, ts["global_pop"], color="#dc2626", linewidth=2.5)
    ax1.fill_between(
        ticks, ts["global_pop"], alpha=0.15, color="#dc2626",
    )
    ax1.axhline(
        y=initial_pop, color="#6b7280", linestyle=":",
        alpha=0.5, linewidth=1,
        label=f"初始人口 ({initial_pop})",
    )
    final_pop = ts["global_pop"][-1]
    survival_pct = final_pop / initial_pop * 100 if initial_pop else 0
    ax1.set_ylabel("总人口", fontsize=12)
    ax1.set_title(
        f"全局人口 ({initial_pop} → {final_pop}, "
        f"存活率 {survival_pct:.1f}%)",
        fontsize=13,
    )
    ax1.legend(fontsize=10, loc="upper right")
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(ticks[0], ticks[-1])

    # 存活聚落数
    ax2 = axes[1]
    ax2.plot(
        ticks, ts["surviving_settlements"],
        color="#f97316", linewidth=2.5,
    )
    ax2.fill_between(
        ticks, ts["surviving_settlements"],
        alpha=0.15, color="#f97316",
    )
    ax2.axhline(
        y=n_settlements, color="#6b7280", linestyle=":",
        alpha=0.5, linewidth=1,
        label=f"初始聚落 ({n_settlements})",
    )
    final_surviving = ts["surviving_settlements"][-1]
    ax2.set_ylabel("存活聚落数", fontsize=12)
    ax2.set_title(
        f"聚落存活 ({n_settlements} → {final_surviving}, "
        f"灭亡 {n_settlements - final_surviving})",
        fontsize=13,
    )
    ax2.legend(fontsize=10, loc="upper right")
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(ticks[0], ticks[-1])
    ax2.yaxis.set_major_locator(MaxNLocator(integer=True))

    # 总食物储备
    ax3 = axes[2]
    ax3.plot(ticks, ts["total_food"], color="#16a34a", linewidth=2)
    ax3.fill_between(
        ticks, ts["total_food"], alpha=0.15, color="#16a34a",
    )
    ax3b = ax3.twinx()
    ax3b.plot(
        ticks, ts["total_gold"], color="#eab308",
        linewidth=1.5, alpha=0.8,
    )
    ax3b.set_ylabel("总金币", fontsize=11, color="#996600")
    ax3b.tick_params(axis="y", labelcolor="#996600")
    ax3.set_ylabel("总食物", fontsize=12, color="#16a34a")
    ax3.set_xlabel("Tick", fontsize=12)
    ax3.set_title("全局资源储备", fontsize=13)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(ticks[0], ticks[-1])

    plt.tight_layout()
    p = f"{out_dir}/chart1_apocalypse_overview.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    paths.append(p)

    # ================================================================
    # 图2: 全局系统动力学
    # ================================================================
    V2_REVOLUTION = 105
    V2_SATISFACTION = 0.407

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
    # 图4: 涌现事件时间线 — 革命 + 贸易/战争
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
    scenario = ApocalypseScenarioConfig()
    config = load_config()
    llm_model = get_active_llm_model(config)

    sim, success, ts_data = run_apocalypse_5000(scenario)

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
