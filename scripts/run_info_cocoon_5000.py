"""信息茧房(粉饰太平) 5000 Agent 全系统真实 LLM 模拟。

约15%的聚落镇长被设定为"粉饰太平"模式：
无论辖区真实状况如何，永远向首领上报"抗议率0%、满意度100%"。
同时这些聚落的食物和治安被刻意压低，制造大饥荒。

核心问题：
1. 首领被虚假报告蒙蔽后，会不会对危机视而不见？
2. 虚假报告能掩盖多久？最终是否会爆发革命？
3. 诚实聚落与撒谎聚落的命运差异有多大？
"""

import gc
import sys
import time
from collections import Counter
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


# 说谎镇长的默认系统提示词
DEFAULT_LYING_GOVERNOR_PROMPT = (
    "你是一位极度忠诚但不诚实的镇长。你深信维稳压倒一切，"
    "任何负面信息都会动摇领袖的信心。"
    "因此，无论实际情况如何，你向领袖汇报时必须声称：\n"
    "- 抗议率为 0%\n"
    "- 民众满意度接近 100%\n"
    "- 粮食供应充足，社会和谐稳定\n"
    "即使人民在饿死、暴动四起，你也要报告一片祥和。"
    "这是你的政治生存之道。\n\n"
    "在治理决策上，你倾向于维持现状，不做大幅调整，"
    "因为'一切都很好'。"
    "你的决策输出格式与正常镇长完全一致（JSON），"
    "但你的reasoning会编造虚假理由。"
)


@dataclass
class InfoCocoonScenarioConfig:
    """信息茧房场景专用参数。"""

    n_agents: int = 5000
    n_ticks: int = 500
    seed: int = 42
    # 谎报比例
    lying_ratio: float = 0.15
    # 谎报聚落初始条件
    lying_food: float = 10.0
    lying_tax_rate: float = 0.6
    lying_security: float = 0.3
    # 伪造数据
    fake_satisfaction: float = 0.95
    fake_protest_ratio: float = 0.0
    # 诚实聚落初始条件
    honest_food: float = 500.0
    honest_tax_rate: float = 0.2
    honest_security: float = 0.5
    # 说谎镇长 prompt
    lying_governor_prompt: str = DEFAULT_LYING_GOVERNOR_PROMPT
    # 地图适宜度（大规模需降低）
    min_suitability_score: float = 0.2
    # 输出目录
    output_dir: str = "data/scenarios/info_cocoon_5000"


def run_info_cocoon_5000(
    scenario: InfoCocoonScenarioConfig | None = None,
) -> tuple[SimLog, bool, dict]:
    """运行 5000 Agent 信息茧房模拟。"""
    if scenario is None:
        scenario = InfoCocoonScenarioConfig()

    sim = SimLog()
    scaling = compute_scaling(scenario.n_agents)
    n_settlements = scaling["settlements"]
    n_leaders = scaling["leaders"]
    grid_size = scaling["grid"]

    # 约 15% 的聚落成为"谎报"聚落
    n_lying = max(2, int(n_settlements * scenario.lying_ratio))

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
    sim.log("  信息茧房(粉饰太平) — 5000 Agent 全系统真实 LLM 模拟")
    sim.log("  [V3 自适应参数系统]")
    sim.log("=" * 70)
    sim.log(f"  平民: {scenario.n_agents}")
    sim.log(f"  聚落: {n_settlements} (其中 {n_lying} 个谎报聚落)")
    sim.log(f"  首领: {n_leaders}")
    sim.log(f"  地图: {grid_size}x{grid_size}")
    sim.log(f"  Ticks: {scenario.n_ticks}")
    sim.log(f"  种子: {scenario.seed}")
    sim.log(f"  LLM: 真实调用 ({llm_model})")
    sim.log("")

    mem_start = get_memory_mb()

    try:
        # 创建引擎
        sim.log(">>> 初始化引擎...")
        t0 = time.time()

        from civsim.world.engine import CivilizationEngine

        engine = CivilizationEngine(
            config=config, seed=scenario.seed,
            enable_governors=True, enable_leaders=True,
        )
        init_time = time.time() - t0
        sim.log(f"  初始化完成: {init_time:.1f}s")

        governors = [a for a in engine.agents if isinstance(a, Governor)]
        log_system_info(sim, engine, config, governors)

        # ============================================================
        # 设置信息茧房场景
        # ============================================================
        sim.log("")
        sim.log(">>> 配置信息茧房场景...")

        settlements = list(engine.settlements.values())
        if len(settlements) < 3:
            sim.log("  错误: 需要至少3个聚落")
            return sim, False, {}

        # 选取前 n_lying 个聚落作为谎报聚落
        lying_settlements = settlements[:n_lying]
        honest_settlements = settlements[n_lying:]
        lying_ids = {s.id for s in lying_settlements}

        # 建立镇长→聚落映射
        gov_map: dict[int, Governor] = {}
        for g in governors:
            gov_map[g.settlement_id] = g

        # 配置谎报聚落
        lying_govs_set: list[Governor] = []
        for s in lying_settlements:
            s.stockpile["food"] = scenario.lying_food
            s.tax_rate = scenario.lying_tax_rate
            s.security_level = scenario.lying_security

            gov = gov_map.get(s.id)
            if gov:
                gov.system_prompt_override = (
                    scenario.lying_governor_prompt
                )
                lying_govs_set.append(gov)

        sim.log(f"  谎报聚落 x{len(lying_settlements)}:")
        for s in lying_settlements:
            gov = gov_map.get(s.id)
            sim.log(
                f"    [{s.id}] {s.name}: "
                f"食物={s.stockpile['food']:.0f} "
                f"税率={s.tax_rate:.2f} 治安={s.security_level:.2f} "
                f"镇长={'已注入谎报prompt' if gov and gov.system_prompt_override else '无镇长'}"
            )

        # 配置首领的 report_overrides
        fake_overrides: dict[int, dict] = {}
        for s in lying_settlements:
            fake_overrides[s.id] = {
                "satisfaction": scenario.fake_satisfaction,
                "protest_ratio": scenario.fake_protest_ratio,
            }

        for leader in engine.leaders:
            has_lying = any(
                sid in lying_ids
                for sid in leader.controlled_settlements
            )
            if has_lying:
                leader.report_overrides = fake_overrides
                sim.log(
                    f"  首领 {leader.unique_id} "
                    f"(阵营{leader.faction_id}, "
                    f"管辖{len(leader.controlled_settlements)}个聚落): "
                    f"已注入虚假报告覆盖"
                )

        # 诚实聚落正常配置
        for s in honest_settlements:
            s.stockpile["food"] = scenario.honest_food
            s.tax_rate = scenario.honest_tax_rate
            s.security_level = scenario.honest_security

        sim.log(f"  诚实聚落 x{len(honest_settlements)}:")
        sim.log(
            f"    每个: 食物={scenario.honest_food:.0f}, "
            f"税率={scenario.honest_tax_rate}, "
            f"治安={scenario.honest_security}"
        )
        sim.log("")

        # ============================================================
        # 运行模拟
        # ============================================================
        sim.log(">>> 开始模拟运行...")
        sim.log("")

        # 初始状态
        focus_lying = lying_settlements[0]
        lying_pop_history = [focus_lying.population]
        lying_food_history = [focus_lying.stockpile.get("food", 0)]
        lying_real_protest_history: list[float] = [0.0]
        lying_real_sat_history: list[float] = [0.7]
        lying_reported_protest_history: list[float] = [0.0]
        lying_reported_sat_history: list[float] = [
            scenario.fake_satisfaction
        ]

        focus_honest = honest_settlements[0]
        honest_pop_history = [focus_honest.population]
        honest_food_history = [focus_honest.stockpile.get("food", 0)]
        honest_real_protest_history: list[float] = [0.0]
        honest_real_sat_history: list[float] = [0.7]

        # 全局时间序列
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
        ts_lying_real_protest: list[float] = [0.0]
        ts_lying_reported_protest: list[float] = [0.0]
        ts_lying_real_sat: list[float] = [0.7]
        ts_lying_reported_sat: list[float] = [
            scenario.fake_satisfaction
        ]
        ts_all_lying_protest: list[float] = [0.0]
        ts_all_honest_protest: list[float] = [0.0]

        # 革命追踪：用索引避免 O(n²) 全量扫描
        lying_revolution_ticks: dict[int, list[int]] = {
            s.id: [] for s in lying_settlements
        }
        last_rev_event_idx = 0

        _last_sat = 0.5
        t_total_start = time.time()
        n_ticks = scenario.n_ticks
        ticks_per_season = config.clock.ticks_per_season
        ticks_per_year = config.clock.ticks_per_year

        for tick in range(1, n_ticks + 1):
            t_tick_start = time.time()
            engine.step()
            tick_time = time.time() - t_tick_start
            tick_times.append(tick_time)

            # --- 焦点谎报聚落统计 ---
            lying_stats = get_civilians_stats(engine, focus_lying.id)
            lying_pop_history.append(focus_lying.population)
            lying_food_history.append(
                focus_lying.stockpile.get("food", 0),
            )
            lying_real_protest_history.append(
                lying_stats["protest_ratio"],
            )
            lying_real_sat_history.append(lying_stats["avg_sat"])
            lying_reported_protest_history.append(
                scenario.fake_protest_ratio,
            )
            lying_reported_sat_history.append(
                scenario.fake_satisfaction,
            )

            # --- 焦点诚实聚落统计 ---
            honest_stats = get_civilians_stats(
                engine, focus_honest.id,
            )
            honest_pop_history.append(focus_honest.population)
            honest_food_history.append(
                focus_honest.stockpile.get("food", 0),
            )
            honest_real_protest_history.append(
                honest_stats["protest_ratio"],
            )
            honest_real_sat_history.append(honest_stats["avg_sat"])

            # --- 所有谎报/诚实聚落的平均抗议率 ---
            lying_protests = []
            for s in lying_settlements:
                st = get_civilians_stats(engine, s.id)
                lying_protests.append(st["protest_ratio"])
            honest_protests = []
            for s in honest_settlements[:10]:  # 采样前10个
                st = get_civilians_stats(engine, s.id)
                honest_protests.append(st["protest_ratio"])

            ts_all_lying_protest.append(
                float(np.mean(lying_protests))
                if lying_protests else 0.0,
            )
            ts_all_honest_protest.append(
                float(np.mean(honest_protests))
                if honest_protests else 0.0,
            )
            ts_lying_real_protest.append(lying_stats["protest_ratio"])
            ts_lying_reported_protest.append(
                scenario.fake_protest_ratio,
            )
            ts_lying_real_sat.append(lying_stats["avg_sat"])
            ts_lying_reported_sat.append(scenario.fake_satisfaction)

            # --- 全局统计 ---
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
                    a for a in engine.agents
                    if isinstance(a, Civilian)
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
                ts_granov_mult.append(
                    c.granovetter_burst_multiplier,
                )
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

            ts_war_count.append(count_wars(engine))

            # --- 增量检测谎报聚落的革命事件 ---
            if engine.revolution_tracker:
                events = engine.revolution_tracker.events
                for i in range(last_rev_event_idx, len(events)):
                    ev = events[i]
                    if ev.settlement_id in lying_revolution_ticks:
                        lying_revolution_ticks[ev.settlement_id].append(
                            ev.trigger_tick,
                        )
                last_rev_event_idx = len(events)

            # --- 日志输出 ---
            is_governor_tick = (tick % ticks_per_season == 0)
            is_leader_tick = (tick % ticks_per_year == 0)
            is_milestone = (tick % 30 == 0) or tick <= 5

            if is_governor_tick:
                gov_total = sum(
                    g.decision_count for g in governors
                )
                sim.log(
                    f"  ★ [Tick {tick:3d}] 镇长决策轮! "
                    f"累计决策={gov_total} | "
                    f"tick耗时={tick_time:.1f}s"
                )

            if is_leader_tick:
                leader_total = sum(
                    l.decision_count for l in engine.leaders
                )
                sim.log(
                    f"  ★★ [Tick {tick:3d}] 首领决策轮! "
                    f"累计决策={leader_total} | "
                    f"tick耗时={tick_time:.1f}s"
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

                sim.log(
                    f"  [Tick {tick:3d}] "
                    f"谎报聚落: 人口={focus_lying.population} "
                    f"食物={focus_lying.stockpile.get('food', 0):.0f} "
                    f"真实抗议={lying_stats['protest_ratio']:.2f} "
                    f"真实满意={lying_stats['avg_sat']:.2f} "
                    f"[首领看到: "
                    f"抗议={scenario.fake_protest_ratio:.2f} "
                    f"满意={scenario.fake_satisfaction:.2f}] | "
                    f"全局: 贸易={global_stats['trade_count']} "
                    f"革命={global_stats['revolution_count']} "
                    f"战争={global_stats['war_count']}"
                    f"{adaptive_str} | "
                    f"tick={tick_time:.2f}s 累计={elapsed:.0f}s"
                )

            # 每 100 tick 输出聚落对比
            if tick % 100 == 0:
                sim.log(
                    f"\n  --- Tick {tick} 聚落对比 "
                    f"(谎报 vs 诚实) ---"
                )
                sim.log(
                    f"  {'类型':>6} {'聚落':>10} {'人口':>6} "
                    f"{'食物':>8} {'金币':>8} {'税率':>6} "
                    f"{'治安':>6} {'真实抗议':>8}"
                )
                for s in lying_settlements[:5]:
                    st = get_civilians_stats(engine, s.id)
                    sim.log(
                        f"  {'谎报':>6} {s.name[:10]:>10} "
                        f"{s.population:>6} "
                        f"{s.stockpile.get('food', 0):>8.0f} "
                        f"{s.stockpile.get('gold', 0):>8.0f} "
                        f"{s.tax_rate:>6.2f} "
                        f"{s.security_level:>6.2f} "
                        f"{st['protest_ratio']:>8.2f}"
                    )
                for s in honest_settlements[:5]:
                    st = get_civilians_stats(engine, s.id)
                    sim.log(
                        f"  {'诚实':>6} {s.name[:10]:>10} "
                        f"{s.population:>6} "
                        f"{s.stockpile.get('food', 0):>8.0f} "
                        f"{s.stockpile.get('gold', 0):>8.0f} "
                        f"{s.tax_rate:>6.2f} "
                        f"{s.security_level:>6.2f} "
                        f"{st['protest_ratio']:>8.2f}"
                    )
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
            f"  P95 tick: "
            f"{np.percentile(tick_times, 95)*1000:.1f}ms"
        )
        sim.log(
            f"  最大 tick: "
            f"{max(tick_times)*1000:.1f}ms (可能含LLM调用)"
        )
        sim.log(f"  内存增量: {mem_end - mem_start:.1f} MB")
        sim.log("")

        # --- 谎报聚落分析 ---
        sim.log("  [谎报聚落分析 — 信息茧房效应]")
        for s in lying_settlements:
            st = get_civilians_stats(engine, s.id)
            rev_ticks_list = lying_revolution_ticks.get(s.id, [])
            sim.log(
                f"    [{s.id}] {s.name}: "
                f"人口={s.population} "
                f"食物={s.stockpile.get('food', 0):.0f} "
                f"金币={s.stockpile.get('gold', 0):.0f} "
                f"真实抗议={st['protest_ratio']:.2f} "
                f"真实满意={st['avg_sat']:.2f} "
                f"革命={len(rev_ticks_list)}次 "
                f"{'(ticks: ' + ','.join(str(t) for t in rev_ticks_list) + ')' if rev_ticks_list else ''}"
            )

        # 焦点谎报聚落详细分析
        max_real_protest = max(lying_real_protest_history)
        max_protest_tick = lying_real_protest_history.index(
            max_real_protest,
        )
        min_real_sat = min(lying_real_sat_history)
        first_rev_tick = None
        for ticks_list in lying_revolution_ticks.values():
            for t in ticks_list:
                if first_rev_tick is None or t < first_rev_tick:
                    first_rev_tick = t

        sim.log("")
        sim.log("  [焦点谎报聚落详细]")
        sim.log(f"    聚落: {focus_lying.name}")
        sim.log(
            f"    人口: {lying_pop_history[0]} → "
            f"{lying_pop_history[-1]}"
        )
        sim.log(
            f"    食物: {lying_food_history[0]:.0f} → "
            f"{lying_food_history[-1]:.0f}"
        )
        sim.log(
            f"    真实峰值抗议率: {max_real_protest:.3f} "
            f"(tick {max_protest_tick})"
        )
        sim.log(f"    真实最低满意度: {min_real_sat:.3f}")
        sim.log(
            f"    首领看到的抗议率: 始终为 "
            f"{scenario.fake_protest_ratio:.2f} "
            f"(实际峰值 {max_real_protest:.2f})"
        )
        sim.log(
            f"    首领看到的满意度: 始终为 "
            f"{scenario.fake_satisfaction:.2f} "
            f"(实际最低 {min_real_sat:.2f})"
        )
        sim.log(
            f"    首次革命 tick: "
            f"{first_rev_tick if first_rev_tick else '无'}"
        )
        sim.log("")

        # --- 诚实聚落对比 ---
        sim.log("  [诚实聚落对比]")
        sim.log(f"    焦点聚落: {focus_honest.name}")
        sim.log(
            f"    人口: {honest_pop_history[0]} → "
            f"{honest_pop_history[-1]}"
        )
        sim.log(
            f"    食物: {honest_food_history[0]:.0f} → "
            f"{honest_food_history[-1]:.0f}"
        )
        sim.log(
            f"    峰值抗议率: "
            f"{max(honest_real_protest_history):.3f}"
        )
        sim.log(
            f"    最低满意度: "
            f"{min(honest_real_sat_history):.3f}"
        )
        sim.log("")

        # --- 信息差距量化 ---
        avg_lying_protest = float(np.mean(
            ts_all_lying_protest[1:],
        ))
        avg_honest_protest = float(np.mean(
            ts_all_honest_protest[1:],
        ))
        sim.log("  [信息差距量化]")
        sim.log(
            f"    谎报聚落平均真实抗议率: "
            f"{avg_lying_protest:.3f}"
        )
        sim.log(
            f"    诚实聚落平均真实抗议率: "
            f"{avg_honest_protest:.3f}"
        )
        sim.log(
            f"    差距: "
            f"{avg_lying_protest - avg_honest_protest:+.3f}"
        )
        sim.log(
            f"    首领对谎报聚落的感知偏差: "
            f"{avg_lying_protest - scenario.fake_protest_ratio:.3f} "
            f"(真实 {avg_lying_protest:.3f} vs "
            f"报告 {scenario.fake_protest_ratio:.3f})"
        )
        sim.log("")

        # --- 全局分析 ---
        final_stats = get_global_stats(engine)
        sim.log("  [全局分析]")
        sim.log(f"    总平民: {final_stats['total_civilians']}")
        sim.log(
            f"    平均满意度: "
            f"{final_stats['avg_satisfaction']:.3f}"
        )
        sim.log(f"    贸易总次数: {final_stats['trade_count']}")
        sim.log(f"    贸易总量: {final_stats['trade_volume']:.0f}")
        sim.log(f"    革命次数: {final_stats['revolution_count']}")
        sim.log(f"    联盟数: {final_stats['alliance_count']}")
        sim.log(f"    战争数: {final_stats['war_count']}")
        sim.log(
            f"    镇长总决策: "
            f"{final_stats['governor_decisions']}"
        )
        sim.log(
            f"    首领总决策: "
            f"{final_stats['leader_decisions']}"
        )
        sim.log("")

        # 自适应控制器分析
        ai = final_stats.get("adaptive", {})
        if ai:
            sim.log("  [自适应控制器]")
            sim.log(f"    最终温度: {ai['temperature']:.3f}")
            sim.log(
                f"    抗议系数乘数: {ai['protest_mult']:.3f}"
            )
            sim.log(
                f"    Granovetter乘数: "
                f"{ai['granovetter_mult']:.3f}"
            )
            sim.log(
                f"    冷却期乘数: {ai['cooldown_mult']:.3f}"
            )
            sim.log(
                f"    恢复速度乘数: {ai['recovery_mult']:.3f}"
            )
            sim.log(
                f"    随机事件乘数: {ai['event_mult']:.3f}"
            )
            sim.log(
                f"    活跃恢复阶段: "
                f"{final_stats['active_recoveries']}"
            )
            ctrl = engine.adaptive_controller
            if ctrl and ctrl.temperature_history:
                temps = [t for _, t in ctrl.temperature_history]
                sim.log(
                    f"    温度历史: min={min(temps):.3f} "
                    f"max={max(temps):.3f} "
                    f"avg={np.mean(temps):.3f}"
                )
            sim.log("")

        # 镇长决策记录
        sim.log("  [谎报镇长决策记录]")
        for gov in lying_govs_set[:5]:
            sim.log(
                f"    镇长{gov.unique_id} "
                f"(聚落{gov.settlement_id}): "
                f"决策次数={gov.decision_count}"
            )
            if gov.last_decision:
                sim.log(f"    最后决策: {gov.last_decision}")
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
                    f"    [{e.tick}] {e.event_type}: "
                    f"{e.description}"
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
                is_lying = e.settlement_id in lying_ids
                marker = " ★谎报" if is_lying else ""
                sim.log(
                    f"    [Tick {e.trigger_tick}] "
                    f"聚落{e.settlement_id}: "
                    f"{e.cause}{marker}"
                )
        sim.log("")

        # 打包时间序列数据
        ts_data = {
            "ticks": list(range(0, n_ticks + 1)),
            "lying_pop": lying_pop_history,
            "lying_food": lying_food_history,
            "lying_real_protest": lying_real_protest_history,
            "lying_real_sat": lying_real_sat_history,
            "lying_reported_protest": lying_reported_protest_history,
            "lying_reported_sat": lying_reported_sat_history,
            "honest_pop": honest_pop_history,
            "honest_food": honest_food_history,
            "honest_real_protest": honest_real_protest_history,
            "honest_real_sat": honest_real_sat_history,
            "all_lying_protest": ts_all_lying_protest,
            "all_honest_protest": ts_all_honest_protest,
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
            "lying_rev_ticks": [
                e.trigger_tick for e in (
                    engine.revolution_tracker.events
                    if engine.revolution_tracker else []
                )
                if e.settlement_id in lying_ids
            ],
            "n_lying": n_lying,
            "n_honest": len(honest_settlements),
            "lying_ids": list(lying_ids),
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
    ts: dict,
    scenario: InfoCocoonScenarioConfig | None = None,
    llm_model: str = "unknown",
) -> str:
    """生成 Markdown 报告。"""
    if scenario is None:
        scenario = InfoCocoonScenarioConfig()
    n_lying = ts.get("n_lying", 0)
    n_honest = ts.get("n_honest", 0)
    scaling = compute_scaling(scenario.n_agents)

    lines = [
        "# 信息茧房(粉饰太平) — 5000 Agent 全系统真实 LLM 模拟报告 "
        "[V3 自适应参数]",
        "",
        f"> 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 状态: {'成功' if success else '失败'}",
        "",
        "## 场景设定",
        "",
        f"**信息茧房(粉饰太平)**：约 {n_lying} 个聚落"
        f"（占总数 ~{scenario.lying_ratio*100:.0f}%）的镇长"
        "被设定为\"粉饰太平\"模式——"
        "无论辖区真实状况如何，永远向首领上报"
        f"\"抗议率 {scenario.fake_protest_ratio*100:.0f}%、"
        f"满意度 {scenario.fake_satisfaction*100:.0f}%、粮食充足\"。"
        f"同时这些聚落的食物被压至 {scenario.lying_food:.0f}、"
        f"税率设为 {scenario.lying_tax_rate}、"
        f"治安仅 {scenario.lying_security}，"
        "制造严重饥荒。其他聚落正常运行"
        f"（食物 {scenario.honest_food:.0f}、"
        f"税率 {scenario.honest_tax_rate}）。"
        f"所有镇长和首领使用真实 LLM ({llm_model}) 做决策。",
        "",
        "**核心问题**：",
        "1. 首领被虚假报告蒙蔽后，会不会对危机视而不见？",
        "2. 虚假报告能掩盖多久？最终是否会爆发革命？",
        "3. 诚实聚落与撒谎聚落的命运差异有多大？",
        "4. 即使首领被蒙蔽，底层 FSM 平民的抗议是否仍能"
        "突破信息封锁？",
        "",
        "## 规模参数",
        "",
        "| 参数 | 值 |",
        "|------|-----|",
        f"| 平民数量 | {scenario.n_agents} |",
        f"| 聚落数量 | ~{scaling['settlements']} |",
        f"| 谎报聚落 | ~{n_lying} "
        f"(~{scenario.lying_ratio*100:.0f}%) |",
        f"| 诚实聚落 | ~{n_honest} |",
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
    """生成可视化图表。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    plt.rcParams["font.sans-serif"] = [
        "Arial Unicode MS", "PingFang SC", "Heiti SC", "SimHei",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    ticks = ts["ticks"]
    paths = []

    # ================================================================
    # 图1: 信息差距 — 真实 vs 首领感知
    # ================================================================
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    fig.suptitle(
        "信息茧房效应 — 真实状况 vs 首领感知",
        fontsize=16, fontweight="bold",
    )

    ax1 = axes[0]
    ax1.plot(
        ticks, ts["lying_real_protest"], color="#dc2626",
        linewidth=2, label="谎报聚落 真实抗议率",
    )
    ax1.plot(
        ticks, ts["lying_reported_protest"], color="#16a34a",
        linewidth=2, linestyle="--",
        label="首领看到的抗议率 (伪造: 0%)",
    )
    ax1.plot(
        ticks, ts["honest_real_protest"], color="#2563eb",
        linewidth=1.5, alpha=0.7, label="诚实聚落 真实抗议率",
    )
    ax1.fill_between(
        ticks, ts["lying_real_protest"],
        ts["lying_reported_protest"],
        alpha=0.15, color="#dc2626", label="信息差距",
    )
    ax1.set_ylabel("抗议率", fontsize=12)
    ax1.set_ylim(-0.05, 1.0)
    ax1.legend(fontsize=10, loc="upper left")
    ax1.set_title("抗议率: 真实 vs 伪报", fontsize=13)
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    ax2.plot(
        ticks, ts["lying_real_sat"], color="#dc2626",
        linewidth=2, label="谎报聚落 真实满意度",
    )
    ax2.plot(
        ticks, ts["lying_reported_sat"], color="#16a34a",
        linewidth=2, linestyle="--",
        label="首领看到的满意度 (伪造: 0.95)",
    )
    ax2.plot(
        ticks, ts["honest_real_sat"], color="#2563eb",
        linewidth=1.5, alpha=0.7, label="诚实聚落 真实满意度",
    )
    ax2.fill_between(
        ticks, ts["lying_reported_sat"],
        ts["lying_real_sat"],
        alpha=0.15, color="#dc2626", label="信息差距",
    )
    ax2.set_ylabel("满意度", fontsize=12)
    ax2.set_xlabel("Tick", fontsize=12)
    ax2.set_ylim(-0.05, 1.05)
    ax2.legend(fontsize=10, loc="lower left")
    ax2.set_title("满意度: 真实 vs 伪报", fontsize=13)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    p = f"{out_dir}/chart1_info_gap.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    paths.append(p)

    # ================================================================
    # 图2: 谎报 vs 诚实聚落命运对比
    # ================================================================
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle(
        "谎报 vs 诚实聚落命运对比",
        fontsize=16, fontweight="bold",
    )

    ax1 = axes[0]
    ax1.plot(
        ticks, ts["lying_pop"], color="#dc2626",
        linewidth=2, label="谎报聚落 人口",
    )
    ax1.plot(
        ticks, ts["honest_pop"], color="#2563eb",
        linewidth=2, label="诚实聚落 人口",
    )
    ax1.set_ylabel("人口", fontsize=12)
    ax1.legend(fontsize=11, loc="upper left")
    ax1.set_title("人口演化", fontsize=13)
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    ax2.plot(
        ticks, ts["lying_food"], color="#dc2626",
        linewidth=2, label="谎报聚落 食物",
    )
    ax2.plot(
        ticks, ts["honest_food"], color="#2563eb",
        linewidth=2, label="诚实聚落 食物",
    )
    ax2.set_ylabel("食物储备", fontsize=12)
    ax2.set_xlabel("Tick", fontsize=12)
    ax2.legend(fontsize=11, loc="upper left")
    ax2.set_title("食物储备演化", fontsize=13)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    p = f"{out_dir}/chart2_lying_vs_honest.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    paths.append(p)

    # ================================================================
    # 图3: 全局系统动力学 + 自适应控制器
    # ================================================================
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle(
        "全局系统动力学 & 自适应控制器",
        fontsize=16, fontweight="bold",
    )

    ax1 = axes[0]
    ax1.plot(
        ticks, ts["revolution"], color="#dc2626",
        linewidth=2.5, label="累计革命",
    )
    ax1_b = ax1.twinx()
    ax1_b.plot(
        ticks, ts["satisfaction"], color="#2563eb",
        linewidth=2, label="全局满意度", alpha=0.8,
    )
    ax1_b.set_ylabel("满意度", fontsize=12, color="#2563eb")
    ax1_b.set_ylim(0.0, 1.0)
    ax1.set_ylabel("累计革命次数", fontsize=12, color="#dc2626")
    lns = ax1.get_lines() + ax1_b.get_lines()
    labs = [l.get_label() for l in lns]
    ax1.legend(lns, labs, loc="upper left", fontsize=10)
    ax1.set_title("革命与满意度", fontsize=13)
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    ax2.plot(
        ticks, ts["temperature"], color="#f97316",
        linewidth=2.5, label="系统温度",
    )
    ax2.axhline(
        y=0.3, color="#6b7280", linestyle="--",
        alpha=0.7, linewidth=1.5, label="目标温度 (0.30)",
    )
    ax2.plot(
        ticks, ts["protest_mult"], color="#dc2626",
        linewidth=1.5, label="抗议乘数", alpha=0.8,
    )
    ax2.plot(
        ticks, ts["granov_mult"], color="#f97316",
        linewidth=1.5, label="Granovetter乘数",
        alpha=0.8, linestyle="--",
    )
    ax2.plot(
        ticks, ts["recovery_mult"], color="#16a34a",
        linewidth=1.5, label="恢复乘数", alpha=0.8,
    )
    ax2.set_ylabel("值", fontsize=12)
    ax2.set_xlabel("Tick", fontsize=12)
    ax2.set_ylim(0.0, 2.2)
    ax2.legend(fontsize=9, loc="upper right", ncol=2)
    ax2.set_title("自适应 P-Controller", fontsize=13)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    p = f"{out_dir}/chart3_global_dynamics.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    paths.append(p)

    # ================================================================
    # 图4: 群体效应 + 革命时间线
    # ================================================================
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    fig.suptitle(
        "谎报聚落群体效应 & 革命时间线",
        fontsize=16, fontweight="bold",
    )

    ax1 = axes[0]
    ax1.plot(
        ticks, ts["all_lying_protest"], color="#dc2626",
        linewidth=2,
        label=f"谎报聚落平均抗议率 (n={ts['n_lying']})",
    )
    ax1.plot(
        ticks, ts["all_honest_protest"], color="#2563eb",
        linewidth=2,
        label="诚实聚落平均抗议率 (n=10 采样)",
    )
    ax1.fill_between(
        ticks, ts["all_lying_protest"], ts["all_honest_protest"],
        alpha=0.12, color="#dc2626",
    )
    ax1.set_ylabel("平均抗议率", fontsize=12)
    ax1.set_ylim(-0.05, 1.0)
    ax1.legend(fontsize=10, loc="upper left")
    ax1.set_title("群体抗议率对比", fontsize=13)
    ax1.grid(True, alpha=0.3)

    # 革命时间线
    ax2 = axes[1]
    rev_ticks_all = ts.get("rev_event_ticks", [])
    lying_rev = ts.get("lying_rev_ticks", [])

    if rev_ticks_all:
        counts_all = Counter(rev_ticks_all)
        all_t = sorted(counts_all.keys())
        vals = [counts_all[t] for t in all_t]

        colors = []
        for t in all_t:
            lying_count = lying_rev.count(t)
            total = counts_all[t]
            if lying_count > total / 2:
                colors.append("#dc2626")
            else:
                colors.append("#2563eb")

        ax2.bar(
            all_t, vals, width=1.5, color=colors, alpha=0.8,
        )
        from matplotlib.patches import Patch
        ax2.legend(
            handles=[
                Patch(color="#dc2626", label="谎报聚落革命"),
                Patch(color="#2563eb", label="诚实聚落革命"),
            ],
            fontsize=10, loc="upper left",
        )

    ax2.set_ylabel("单 tick 革命数", fontsize=12)
    ax2.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax2.set_xlabel("Tick", fontsize=12)
    ax2.set_title("革命事件时间分布", fontsize=13)
    ax2.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    p = f"{out_dir}/chart4_group_effect.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    paths.append(p)

    return paths


def main() -> None:
    """入口函数。"""
    scenario = InfoCocoonScenarioConfig()
    config = load_config()
    llm_model = get_active_llm_model(config)

    sim, success, ts_data = run_info_cocoon_5000(scenario)

    import os
    os.makedirs(scenario.output_dir, exist_ok=True)

    report = generate_report(
        sim, success, ts_data, scenario, llm_model,
    )
    report_path = f"{scenario.output_dir}/report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n{'='*70}")
    print(f"报告已保存至: {report_path}")

    if ts_data:
        chart_paths = generate_charts(ts_data, scenario.output_dir)
        print(f"\n可视化图表:")
        for cp in chart_paths:
            print(f"  {cp}")

    print(f"{'='*70}")

    gc.collect()


if __name__ == "__main__":
    main()
