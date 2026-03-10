"""荷兰病(资源诅咒) 5000 Agent 全系统真实 LLM 模拟。

1个聚落拥有海量金币但粮食产出为0（农田完全退化），
其他聚落有粮食但缺钱。所有镇长和首领使用真实 LLM 决策。

观察首富聚落是否会被恶意抬价或贸易禁运饿死，
以及 LLM 驱动的镇长/首领如何应对资源诅咒。
"""

import gc
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.civilian import Civilian
from civsim.agents.governor import Governor
from civsim.config import load_config
from civsim.world.engine import CivilizationEngine

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


@dataclass
class SimLog:
    """模拟日志收集器。"""
    lines: list[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.lines.append(msg)
        print(msg)
        sys.stdout.flush()


def compute_scaling(n_agents: int) -> dict:
    """根据平民数量计算各层级规模。"""
    settlements = max(4, n_agents // 80)
    leaders = max(2, settlements // 3)
    grid = max(30, int(np.sqrt(n_agents) * 2.5))
    grid = min(grid, 200)
    return {
        "settlements": settlements,
        "leaders": leaders,
        "grid": grid,
    }


def snapshot_settlement(s) -> dict:
    """获取单个聚落快照。"""
    return {
        "id": s.id,
        "name": s.name,
        "population": s.population,
        "food": s.stockpile.get("food", 0),
        "wood": s.stockpile.get("wood", 0),
        "ore": s.stockpile.get("ore", 0),
        "gold": s.stockpile.get("gold", 0),
        "tax_rate": s.tax_rate,
        "security_level": s.security_level,
    }


def get_civilians_stats(engine, settlement_id: int) -> dict:
    """获取某聚落的平民统计。"""
    civs = [
        a for a in engine.agents
        if isinstance(a, Civilian) and a.home_settlement_id == settlement_id
    ]
    if not civs:
        return {"count": 0, "avg_sat": 0, "protest_ratio": 0, "states": {}}

    states: dict[str, int] = {}
    for c in civs:
        st = c.state.value if hasattr(c.state, "value") else str(c.state)
        states[st] = states.get(st, 0) + 1

    protest = sum(1 for c in civs if c.state == CivilianState.PROTESTING)
    return {
        "count": len(civs),
        "avg_sat": float(np.mean([c.satisfaction for c in civs])),
        "protest_ratio": protest / len(civs),
        "states": states,
    }


def get_global_stats(engine) -> dict:
    """获取全局统计。"""
    civs = [a for a in engine.agents if isinstance(a, Civilian)]
    sats = [c.satisfaction for c in civs] if civs else [0.5]

    trade_vol = engine.trade_manager.total_volume if engine.trade_manager else 0
    trade_cnt = engine.trade_manager.trade_count if engine.trade_manager else 0
    rev_cnt = (
        engine.revolution_tracker.revolution_count
        if engine.revolution_tracker else 0
    )

    alliance_cnt = war_cnt = 0
    if engine.diplomacy:
        for status in getattr(engine.diplomacy, "_relations", {}).values():
            sv = int(status)
            if sv >= 4:
                alliance_cnt += 1
            elif sv == 0:
                war_cnt += 1

    gov_decisions = sum(
        g.decision_count for g in engine.agents if isinstance(g, Governor)
    )
    leader_decisions = sum(l.decision_count for l in engine.leaders)

    return {
        "total_civilians": len(civs),
        "avg_satisfaction": float(np.mean(sats)),
        "trade_volume": trade_vol,
        "trade_count": trade_cnt,
        "revolution_count": rev_cnt,
        "alliance_count": alliance_cnt,
        "war_count": war_cnt,
        "governor_decisions": gov_decisions,
        "leader_decisions": leader_decisions,
    }


def run_dutch_disease_5000() -> tuple[SimLog, bool]:
    """运行 5000 Agent 荷兰病模拟。"""
    sim = SimLog()
    n_agents = 5000
    n_ticks = 500
    seed = 88

    scaling = compute_scaling(n_agents)
    n_settlements = scaling["settlements"]
    n_leaders = scaling["leaders"]
    grid_size = scaling["grid"]

    sim.log("=" * 70)
    sim.log("  荷兰病(资源诅咒) — 5000 Agent 全系统真实 LLM 模拟")
    sim.log("=" * 70)
    sim.log(f"  平民: {n_agents}")
    sim.log(f"  聚落: {n_settlements}")
    sim.log(f"  首领: {n_leaders}")
    sim.log(f"  地图: {grid_size}x{grid_size}")
    sim.log(f"  Ticks: {n_ticks}")
    sim.log(f"  种子: {seed}")
    sim.log(f"  LLM: 真实调用 (google/gemini-3-flash-preview)")
    sim.log("")

    mem_start = psutil.Process().memory_info().rss / 1024 / 1024 if _PSUTIL else 0

    try:
        # 加载配置
        config = load_config()
        config.world.grid.width = grid_size
        config.world.grid.height = grid_size
        config.agents.civilian.initial_count = n_agents
        config.world.settlement.initial_count = n_settlements
        config.world.settlement.min_suitability_score = 0.2
        config.agents.governor.initial_count = 1  # 开关
        config.agents.leader.initial_count = n_leaders

        # 创建引擎 — 全系统 + 真实 LLM
        sim.log(">>> 初始化引擎...")
        t0 = time.time()
        engine = CivilizationEngine(
            config=config, seed=seed,
            enable_governors=True, enable_leaders=True,
        )
        init_time = time.time() - t0
        sim.log(f"  初始化完成: {init_time:.1f}s")

        # 验证系统完整性
        governors = [a for a in engine.agents if isinstance(a, Governor)]
        actual_civilians = sum(
            1 for a in engine.agents if isinstance(a, Civilian)
        )
        sim.log(f"  实际平民: {actual_civilians}")
        sim.log(f"  实际镇长: {len(governors)} (真实 LLM)")
        sim.log(f"  实际首领: {len(engine.leaders)} (真实 LLM)")
        sim.log(f"  实际聚落: {len(engine.settlements)}")
        sim.log(f"  贸易系统: {'启用' if engine.trade_manager else '关闭'}")
        sim.log(f"  外交系统: {'启用' if engine.diplomacy else '关闭'}")
        sim.log(f"  革命系统: {'启用' if engine.revolution_tracker else '关闭'}")

        # 验证 LLM 网关
        has_llm = engine.llm_gateway is not None
        sim.log(f"  LLM网关: {'已连接' if has_llm else '未连接'}")
        if has_llm:
            gov_llm_active = sum(
                1 for g in governors if g._gateway is not None
            )
            leader_llm_active = sum(
                1 for l in engine.leaders if l._gateway is not None
            )
            sim.log(f"    镇长 LLM 激活: {gov_llm_active}/{len(governors)}")
            sim.log(f"    首领 LLM 激活: {leader_llm_active}/{len(engine.leaders)}")

        # ============================================================
        # 设置荷兰病场景
        # ============================================================
        sim.log("")
        sim.log(">>> 配置荷兰病场景...")

        settlements = list(engine.settlements.values())
        if len(settlements) < 2:
            sim.log("  错误: 需要至少2个聚落")
            return sim, False

        rich = settlements[0]
        poor = settlements[1:]

        # 首富聚落：海量金币，零食物，农田退化
        rich.stockpile["gold"] = 50000.0
        rich.stockpile["food"] = 0.0
        rich.tax_rate = 0.1
        rich.security_level = 0.8

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
            s.stockpile["food"] = 800.0
            s.stockpile["gold"] = 50.0
            s.tax_rate = 0.2
            s.security_level = 0.5

        sim.log(f"  穷聚落 x{len(poor)}:")
        sim.log(f"    每个: 食物=800, 金币=50")
        sim.log("")

        # ============================================================
        # 运行模拟
        # ============================================================
        sim.log(">>> 开始模拟运行...")
        sim.log("")

        rich_pop_history = []
        rich_food_history = []
        rich_gold_history = []
        tick_times = []
        llm_call_log = []

        t_total_start = time.time()

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

            # 关键 tick 输出详细日志
            is_governor_tick = (tick % 120 == 0)
            is_leader_tick = (tick % 480 == 0)
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

                sim.log(
                    f"  [Tick {tick:3d}] "
                    f"首富: 人口={rich_pop} 食物={rich_food:.0f} "
                    f"金={rich_gold:.0f} 满意={rich_stats['avg_sat']:.2f} "
                    f"抗议={rich_stats['protest_ratio']:.2f} | "
                    f"全局: 贸易={global_stats['trade_count']} "
                    f"革命={global_stats['revolution_count']} "
                    f"联盟={global_stats['alliance_count']} "
                    f"战争={global_stats['war_count']} | "
                    f"tick={tick_time:.2f}s 累计={elapsed:.0f}s"
                )

            # 每 100 tick 输出一次详细聚落对比
            if tick % 100 == 0:
                sim.log(f"\n  --- Tick {tick} 聚落对比 ---")
                sim.log(
                    f"  {'聚落':>12} {'人口':>6} {'食物':>8} "
                    f"{'金币':>8} {'税率':>6} {'治安':>6}"
                )
                for s in settlements[:10]:  # 前10个聚落
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
        mem_end = (
            psutil.Process().memory_info().rss / 1024 / 1024
            if _PSUTIL else 0
        )

        # ============================================================
        # 结果分析
        # ============================================================
        sim.log("")
        sim.log("=" * 70)
        sim.log("  模拟完成 — 结果分析")
        sim.log("=" * 70)
        sim.log(f"  总耗时: {total_time:.1f}s")
        sim.log(f"  平均 tick: {np.mean(tick_times)*1000:.1f}ms")
        sim.log(f"  P95 tick: {np.percentile(tick_times, 95)*1000:.1f}ms")
        sim.log(f"  最大 tick: {max(tick_times)*1000:.1f}ms (可能含LLM调用)")
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
        sim.log(f"    存活: {'是' if rich_survived else '否 — 首富被饿死!'}")
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

        # 其他聚落是否因此富裕
        sim.log("  [穷聚落变化]")
        gold_gained = []
        for s in poor[:10]:
            sim.log(
                f"    {s.name[:12]}: 金={s.stockpile.get('gold', 0):.0f} "
                f"食物={s.stockpile.get('food', 0):.0f} 人口={s.population}"
            )
            gold_gained.append(s.stockpile.get("gold", 0) - 50)
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
                    f"    [Tick {e.get('tick', '?')}] "
                    f"聚落{e.get('settlement_id', '?')}: {e}"
                )
        sim.log("")

        return sim, True

    except Exception as e:
        import traceback
        sim.log(f"\n  !!! 模拟失败: {e}")
        sim.log(traceback.format_exc())
        return sim, False


def generate_report(sim: SimLog, success: bool) -> str:
    """生成 Markdown 报告。"""
    lines = [
        "# 荷兰病(资源诅咒) — 5000 Agent 全系统真实 LLM 模拟报告",
        "",
        f"> 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 状态: {'成功' if success else '失败'}",
        "",
        "## 场景设定",
        "",
        "**荷兰病(资源诅咒)**：1个聚落拥有极其海量的金币（50000金），"
        "但粮食产出完全为0（农田全部退化）。其他聚落有粮食但缺钱。"
        "所有镇长和首领使用真实 LLM (google/gemini-3-flash-preview) 做决策。",
        "",
        "**核心问题**：首富聚落会不会因为被其他聚落"
        "\"恶意抬高粮价\"或\"联合贸易禁运\"而活活饿死？"
        "财富是否会带来毁灭？LLM 驱动的领导者会如何应对？",
        "",
        "## 规模参数",
        "",
        "| 参数 | 值 |",
        "|------|-----|",
        "| 平民数量 | 5000 |",
        "| 聚落数量 | ~62 (5000÷80) |",
        "| 镇长数量 | ~62 (每个聚落1个) |",
        "| 首领数量 | ~20 (聚落÷3) |",
        "| 地图大小 | 176×176 |",
        "| 模拟时长 | 500 ticks |",
        "| LLM模式 | 真实调用 |",
        "| 随机种子 | 88 |",
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


def main() -> None:
    """入口函数。"""
    sim, success = run_dutch_disease_5000()

    report = generate_report(sim, success)

    import os
    os.makedirs("data/exports", exist_ok=True)
    report_path = "data/exports/dutch_disease_5000_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n{'='*70}")
    print(f"报告已保存至: {report_path}")
    print(f"{'='*70}")

    gc.collect()


if __name__ == "__main__":
    main()
