"""极端场景压力测试。

设计 5 个极端场景，压测贸易/革命/战争/饥荒/级联效应。
结果输出到 data/exports/extreme_scenarios_report.md
"""

import sys
import time
from dataclasses import dataclass, field
from io import StringIO

from civsim.agents.behaviors.fsm import CivilianState
from civsim.config import load_config
from civsim.politics.diplomacy import DiplomaticStatus
from civsim.world.engine import CivilizationEngine


@dataclass
class ScenarioResult:
    """单个场景的运行结果。"""

    name: str
    description: str
    ticks: int
    duration_sec: float = 0.0
    logs: list[str] = field(default_factory=list)
    success: bool = False
    error: str = ""


def log(result: ScenarioResult, msg: str) -> None:
    """记录日志到结果和标准输出。"""
    result.logs.append(msg)
    print(msg)
    sys.stdout.flush()


def snapshot(engine: CivilizationEngine, tick: int) -> dict:
    """获取当前仿真快照。"""
    state_counts: dict[str, int] = {}
    sats: list[float] = []
    for agent in engine.agents:
        if type(agent).__name__ == "Civilian":
            st = agent.state.value if hasattr(agent.state, "value") else str(agent.state)
            state_counts[st] = state_counts.get(st, 0) + 1
            sats.append(agent.satisfaction)

    total_pop = sum(s.population for s in engine.settlements.values())
    total_food = sum(s.stockpile.get("food", 0) for s in engine.settlements.values())
    total_gold = sum(s.stockpile.get("gold", 0) for s in engine.settlements.values())
    avg_sat = sum(sats) / max(len(sats), 1)

    trade_vol = engine.trade_manager.total_volume if engine.trade_manager else 0
    rev_count = engine.revolution_tracker.revolution_count if engine.revolution_tracker else 0
    alliance_cnt = war_cnt = 0
    if engine.diplomacy:
        for status in getattr(engine.diplomacy, "_relations", {}).values():
            sv = int(status)
            if sv >= 4:
                alliance_cnt += 1
            elif sv == 0:
                war_cnt += 1

    return {
        "tick": tick,
        "population": total_pop,
        "food": total_food,
        "gold": total_gold,
        "avg_satisfaction": avg_sat,
        "states": state_counts,
        "trade_volume": trade_vol,
        "revolution_count": rev_count,
        "alliance_count": alliance_cnt,
        "war_count": war_cnt,
    }


# ============================================================
# 场景 1: 饥荒危机 - 食物耗尽引发抗议和革命
# ============================================================
def scenario_famine_crisis() -> ScenarioResult:
    """极低食物 + 高税率 → 饥荒 → 大规模抗议 → 革命。"""
    result = ScenarioResult(
        name="饥荒危机",
        description="极低初始食物(50) + 高税率(0.5) + 低治安(0.2)，"
        "200平民在高压下挣扎。目标：触发大规模抗议和革命。",
        ticks=300,
    )

    try:
        config = load_config()
        config.world.grid.width = 40
        config.world.grid.height = 40
        config.agents.civilian.initial_count = 200
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 2
        config.world.settlement.initial_count = 4
        config.world.settlement.min_suitability_score = 0.2

        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True, enable_leaders=True,
        )

        # 制造饥荒：极低食物 + 高税 + 低治安
        for s in engine.settlements.values():
            s.stockpile["food"] = 50.0
            s.stockpile["gold"] = 20.0
            s.tax_rate = 0.5
            s.security_level = 0.2

        log(result, f"聚落数: {len(engine.settlements)}, 首领数: {len(engine.leaders)}")

        t0 = time.time()
        max_protest = 0.0
        min_sat = 1.0
        for tick in range(1, result.ticks + 1):
            engine.step()
            if tick % 30 == 0 or tick <= 5:
                snap = snapshot(engine, tick)
                protest_n = snap["states"].get("抗议", 0) + snap["states"].get("5", 0)
                total_civs = sum(v for v in snap["states"].values())
                pr = protest_n / max(total_civs, 1)
                max_protest = max(max_protest, pr)
                min_sat = min(min_sat, snap["avg_satisfaction"])
                log(result, f"  [Tick {tick:3d}] 人口={snap['population']} "
                    f"食物={snap['food']:.0f} 满意度={snap['avg_satisfaction']:.3f} "
                    f"抗议率={pr:.3f} 革命={snap['revolution_count']} "
                    f"状态={snap['states']}")

        result.duration_sec = time.time() - t0
        final = snapshot(engine, result.ticks)
        log(result, f"\n  最终: 人口={final['population']} 食物={final['food']:.0f} "
            f"革命次数={final['revolution_count']}")
        log(result, f"  峰值抗议率={max_protest:.3f} 最低满意度={min_sat:.3f}")

        emergence = engine.emergence_detector.events if engine.emergence_detector else []
        if emergence:
            log(result, f"  涌现事件({len(emergence)}个):")
            for e in emergence:
                log(result, f"    [{e.tick}] {e.event_type}: {e.description}")

        result.success = True
    except Exception as e:
        result.error = str(e)
        log(result, f"  错误: {e}")

    return result


# ============================================================
# 场景 2: 资源极度不均 - 贫富分化触发贸易
# ============================================================
def scenario_resource_imbalance() -> ScenarioResult:
    """一半聚落极富、一半极穷 → 强制贸易需求。"""
    result = ScenarioResult(
        name="资源极度不均",
        description="3个聚落食物2000+，3个聚落食物仅10。"
        "强制创造贸易的供需条件。目标：触发聚落间贸易。",
        ticks=200,
    )

    try:
        config = load_config()
        config.world.grid.width = 50
        config.world.grid.height = 50
        config.agents.civilian.initial_count = 120
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 2
        config.world.settlement.initial_count = 6
        config.world.settlement.min_suitability_score = 0.2

        engine = CivilizationEngine(
            config=config, seed=123,
            enable_governors=True, enable_leaders=True,
        )

        sids = list(engine.settlements.keys())
        log(result, f"聚落数: {len(sids)}, 首领数: {len(engine.leaders)}")

        # 极端分化: 前半富裕，后半贫穷
        for i, sid in enumerate(sids):
            s = engine.settlements[sid]
            if i < len(sids) // 2:
                s.stockpile["food"] = 3000.0
                s.stockpile["gold"] = 500.0
                s.population = 20  # 少人口 → 高人均
            else:
                s.stockpile["food"] = 10.0
                s.stockpile["gold"] = 200.0
                s.population = 40  # 多人口 → 低人均
            log(result, f"  聚落{sid}({s.name}): 人口={s.population} "
                f"食物={s.stockpile['food']:.0f} 金={s.stockpile['gold']:.0f} "
                f"阵营={s.faction_id}")

        # 确保外交至少是中立（允许贸易）
        if engine.diplomacy:
            factions = set(s.faction_id for s in engine.settlements.values() if s.faction_id)
            for f1 in factions:
                for f2 in factions:
                    if f1 < f2:
                        engine.diplomacy.set_relation(
                            f1, f2, DiplomaticStatus.NEUTRAL, 0
                        )

        t0 = time.time()
        for tick in range(1, result.ticks + 1):
            engine.step()
            if tick % 20 == 0 or tick <= 3:
                snap = snapshot(engine, tick)
                log(result, f"  [Tick {tick:3d}] 人口={snap['population']} "
                    f"食物={snap['food']:.0f} 贸易量={snap['trade_volume']:.0f} "
                    f"联盟={snap['alliance_count']} 战争={snap['war_count']}")

        result.duration_sec = time.time() - t0
        final = snapshot(engine, result.ticks)
        log(result, f"\n  最终贸易量: {final['trade_volume']:.0f}")

        # 各聚落最终状态
        for sid, s in engine.settlements.items():
            log(result, f"  聚落{sid}: 食物={s.stockpile['food']:.0f} "
                f"金={s.stockpile['gold']:.0f} 人口={s.population}")

        result.success = True
    except Exception as e:
        result.error = str(e)
        log(result, f"  错误: {e}")

    return result


# ============================================================
# 场景 3: 高压统治 - 极高税率 + 极高治安
# ============================================================
def scenario_tyranny() -> ScenarioResult:
    """极高税率(0.8) + 极高治安(0.9)，观察是否能压制抗议。"""
    result = ScenarioResult(
        name="高压统治",
        description="税率0.8 + 治安0.9，200平民在高压下。"
        "目标：观察治安能否压制不满，以及抗议是否仍会爆发。",
        ticks=400,
    )

    try:
        config = load_config()
        config.world.grid.width = 40
        config.world.grid.height = 40
        config.agents.civilian.initial_count = 200
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 2
        config.world.settlement.initial_count = 4
        config.world.settlement.min_suitability_score = 0.2

        engine = CivilizationEngine(
            config=config, seed=77,
            enable_governors=True, enable_leaders=True,
        )

        for s in engine.settlements.values():
            s.tax_rate = 0.8
            s.security_level = 0.9
            s.stockpile["food"] = 300.0  # 中等食物

        log(result, f"聚落数: {len(engine.settlements)}")

        t0 = time.time()
        max_protest = 0.0
        for tick in range(1, result.ticks + 1):
            engine.step()
            if tick % 40 == 0:
                snap = snapshot(engine, tick)
                protest_n = snap["states"].get("抗议", 0) + snap["states"].get("5", 0)
                total_civs = sum(v for v in snap["states"].values())
                pr = protest_n / max(total_civs, 1)
                max_protest = max(max_protest, pr)
                log(result, f"  [Tick {tick:3d}] 人口={snap['population']} "
                    f"食物={snap['food']:.0f} 满意度={snap['avg_satisfaction']:.3f} "
                    f"抗议率={pr:.3f} 革命={snap['revolution_count']} "
                    f"状态={snap['states']}")

        result.duration_sec = time.time() - t0
        final = snapshot(engine, result.ticks)
        log(result, f"\n  峰值抗议率: {max_protest:.3f}")
        log(result, f"  最终革命次数: {final['revolution_count']}")
        log(result, f"  最终满意度: {final['avg_satisfaction']:.3f}")

        for sid, s in engine.settlements.items():
            log(result, f"  聚落{sid}: 税={s.tax_rate:.2f} "
                f"治安={s.security_level:.2f} 食物={s.stockpile['food']:.0f}")

        result.success = True
    except Exception as e:
        result.error = str(e)
        log(result, f"  错误: {e}")

    return result


# ============================================================
# 场景 4: 强制战争 - 手动设置战争状态观察连锁反应
# ============================================================
def scenario_forced_war() -> ScenarioResult:
    """直接设置两个阵营为战争状态，观察贸易封锁和后续影响。"""
    result = ScenarioResult(
        name="强制战争",
        description="在 tick 10 手动宣战，观察贸易封锁、聚落衰退、"
        "首领决策应对。运行到首领年度决策后看是否求和。",
        ticks=600,
    )

    try:
        config = load_config()
        config.world.grid.width = 50
        config.world.grid.height = 50
        config.agents.civilian.initial_count = 150
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 2
        config.world.settlement.initial_count = 6
        config.world.settlement.min_suitability_score = 0.2

        engine = CivilizationEngine(
            config=config, seed=99,
            enable_governors=True, enable_leaders=True,
        )

        # 制造贸易条件
        sids = list(engine.settlements.keys())
        for i, sid in enumerate(sids):
            s = engine.settlements[sid]
            if i % 2 == 0:
                s.stockpile["food"] = 2000.0
                s.population = 15
            else:
                s.stockpile["food"] = 20.0
                s.population = 35

        factions = sorted(set(
            s.faction_id for s in engine.settlements.values() if s.faction_id
        ))
        log(result, f"聚落数: {len(sids)}, 阵营: {factions}")

        t0 = time.time()
        war_declared = False
        pre_war_trade = 0.0
        for tick in range(1, result.ticks + 1):
            engine.step()

            # tick 10 时记录战前贸易量，然后宣战
            if tick == 10 and not war_declared and len(factions) >= 2:
                pre_war_trade = engine.trade_manager.total_volume if engine.trade_manager else 0
                engine.diplomacy.set_relation(
                    factions[0], factions[1], DiplomaticStatus.WAR, tick
                )
                war_declared = True
                log(result, f"  [Tick {tick}] *** 宣战! 阵营{factions[0]} vs {factions[1]} ***")
                log(result, f"  战前贸易量: {pre_war_trade:.0f}")

            if tick % 50 == 0 or tick in [1, 5, 10, 11, 15, 20]:
                snap = snapshot(engine, tick)
                log(result, f"  [Tick {tick:3d}] 食物={snap['food']:.0f} "
                    f"贸易量={snap['trade_volume']:.0f} "
                    f"联盟={snap['alliance_count']} 战争={snap['war_count']} "
                    f"革命={snap['revolution_count']}")

        result.duration_sec = time.time() - t0
        final = snapshot(engine, result.ticks)

        # 检查战争是否结束
        if engine.diplomacy and len(factions) >= 2:
            final_status = engine.diplomacy.get_relation(factions[0], factions[1])
            log(result, f"\n  最终外交状态: {final_status.name}")
        log(result, f"  最终贸易量: {final['trade_volume']:.0f}")
        log(result, f"  最终革命次数: {final['revolution_count']}")

        for leader in engine.leaders:
            log(result, f"  首领{leader.unique_id}: 决策={getattr(leader, 'decision_count', 0)}")

        emergence = engine.emergence_detector.events if engine.emergence_detector else []
        if emergence:
            log(result, f"  涌现事件({len(emergence)}个):")
            for e in emergence:
                log(result, f"    [{e.tick}] {e.event_type}: {e.description}")

        result.success = True
    except Exception as e:
        result.error = str(e)
        log(result, f"  错误: {e}")

    return result


# ============================================================
# 场景 5: 末日生存 - 全面资源枯竭
# ============================================================
def scenario_apocalypse() -> ScenarioResult:
    """所有资源接近 0，人口密度极高，观察系统崩溃过程。"""
    result = ScenarioResult(
        name="末日生存",
        description="所有聚落: 食物=5, 木材=0, 矿石=0, 金=5。"
        "300平民挤在4个聚落中。观察饥荒死亡、抗议、革命级联。",
        ticks=200,
    )

    try:
        config = load_config()
        config.world.grid.width = 30
        config.world.grid.height = 30
        config.agents.civilian.initial_count = 300
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 2
        config.world.settlement.initial_count = 4
        config.world.settlement.min_suitability_score = 0.1

        engine = CivilizationEngine(
            config=config, seed=666,
            enable_governors=True, enable_leaders=True,
        )

        # 极端资源匮乏
        for s in engine.settlements.values():
            s.stockpile["food"] = 5.0
            s.stockpile["wood"] = 0.0
            s.stockpile["ore"] = 0.0
            s.stockpile["gold"] = 5.0
            s.tax_rate = 0.3
            s.security_level = 0.3

        initial_pop = sum(s.population for s in engine.settlements.values())
        log(result, f"聚落数: {len(engine.settlements)}, 初始人口: {initial_pop}")

        t0 = time.time()
        for tick in range(1, result.ticks + 1):
            engine.step()
            if tick % 10 == 0 or tick <= 5:
                snap = snapshot(engine, tick)
                protest_n = snap["states"].get("抗议", 0) + snap["states"].get("5", 0)
                fight_n = snap["states"].get("战斗", 0) + snap["states"].get("6", 0)
                total_civs = sum(v for v in snap["states"].values())
                log(result, f"  [Tick {tick:3d}] 人口={snap['population']} "
                    f"食物={snap['food']:.0f} 满意度={snap['avg_satisfaction']:.3f} "
                    f"抗议={protest_n}/{total_civs} 战斗={fight_n} "
                    f"革命={snap['revolution_count']}")

        result.duration_sec = time.time() - t0
        final = snapshot(engine, result.ticks)
        final_pop = final["population"]
        log(result, f"\n  人口变化: {initial_pop} → {final_pop} "
            f"(损失 {initial_pop - final_pop})")
        log(result, f"  最终革命次数: {final['revolution_count']}")
        log(result, f"  最终食物: {final['food']:.0f}")

        for sid, s in engine.settlements.items():
            log(result, f"  聚落{sid}: 人口={s.population} "
                f"食物={s.stockpile['food']:.0f} "
                f"税={s.tax_rate:.2f} 治安={s.security_level:.2f}")

        emergence = engine.emergence_detector.events if engine.emergence_detector else []
        if emergence:
            log(result, f"  涌现事件({len(emergence)}个):")
            for e in emergence:
                log(result, f"    [{e.tick}] {e.event_type}: {e.description}")

        result.success = True
    except Exception as e:
        result.error = str(e)
        log(result, f"  错误: {e}")

    return result


# ============================================================
# 报告生成
# ============================================================
def generate_report(results: list[ScenarioResult]) -> str:
    """生成 Markdown 格式报告。"""
    lines = [
        "# AI 文明模拟器 - 极端场景压力测试报告",
        "",
        f"> 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 概览",
        "",
        "| 场景 | Ticks | 耗时 | 状态 |",
        "|------|-------|------|------|",
    ]
    for r in results:
        status = "通过" if r.success else f"失败: {r.error[:30]}"
        lines.append(f"| {r.name} | {r.ticks} | {r.duration_sec:.1f}s | {status} |")

    for r in results:
        lines.append("")
        lines.append(f"## 场景: {r.name}")
        lines.append("")
        lines.append(f"**描述**: {r.description}")
        lines.append("")
        lines.append(f"**运行时间**: {r.duration_sec:.1f}s | **Ticks**: {r.ticks}")
        lines.append("")
        lines.append("### 详细日志")
        lines.append("")
        lines.append("```")
        for log_line in r.logs:
            lines.append(log_line)
        lines.append("```")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 总结与发现")
    lines.append("")
    lines.append("（基于以上场景运行结果的自动生成摘要）")
    lines.append("")

    # 自动摘要
    for r in results:
        lines.append(f"### {r.name}")
        if not r.success:
            lines.append(f"- **运行失败**: {r.error}")
        else:
            # 提取关键指标
            rev_lines = [l for l in r.logs if "革命" in l and "最终" in l]
            trade_lines = [l for l in r.logs if "贸易量" in l and "最终" in l]
            for l in rev_lines:
                lines.append(f"- {l.strip()}")
            for l in trade_lines:
                lines.append(f"- {l.strip()}")
            emergence_lines = [l for l in r.logs if "涌现事件" in l]
            for l in emergence_lines:
                lines.append(f"- {l.strip()}")
        lines.append("")

    return "\n".join(lines)


# ============================================================
# 主函数
# ============================================================
def main() -> None:
    """运行所有极端场景。"""
    print("=" * 60)
    print("AI 文明模拟器 - 极端场景压力测试")
    print("=" * 60)

    scenarios = [
        ("1/5 饥荒危机", scenario_famine_crisis),
        ("2/5 资源极度不均", scenario_resource_imbalance),
        ("3/5 高压统治", scenario_tyranny),
        ("4/5 强制战争", scenario_forced_war),
        ("5/5 末日生存", scenario_apocalypse),
    ]

    results = []
    for label, fn in scenarios:
        print(f"\n{'='*60}")
        print(f"场景 {label}")
        print(f"{'='*60}")
        result = fn()
        results.append(result)
        print(f"\n场景完成: {'成功' if result.success else '失败'} "
              f"({result.duration_sec:.1f}s)")

    # 生成报告
    report = generate_report(results)

    import os
    os.makedirs("data/exports", exist_ok=True)
    report_path = "data/exports/extreme_scenarios_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n{'='*60}")
    print(f"全部完成! 报告已保存至: {report_path}")
    total_time = sum(r.duration_sec for r in results)
    passed = sum(1 for r in results if r.success)
    print(f"通过: {passed}/{len(results)} | 总耗时: {total_time:.1f}s")


if __name__ == "__main__":
    main()
