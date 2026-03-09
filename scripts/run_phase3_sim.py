"""Phase 3 完整文明模拟运行脚本。

运行 600 tick 的三层文明模拟，记录详细过程。
"""

import sys
import time

from civsim.config import load_config
from civsim.world.engine import CivilizationEngine


def main() -> None:
    """运行 Phase 3 文明模拟。"""
    print("=" * 60)
    print("AI 文明模拟器 - Phase 3 完整仿真")
    print("=" * 60)

    config = load_config()
    config.world.grid.width = 60
    config.world.grid.height = 60
    config.agents.civilian.initial_count = 200
    config.agents.governor.initial_count = 1
    config.agents.leader.initial_count = 2
    config.world.settlement.initial_count = 6
    config.world.settlement.min_suitability_score = 0.3

    print(f"\n地图: {config.world.grid.width}x{config.world.grid.height}")
    print(f"平民: {config.agents.civilian.initial_count}")
    print(f"首领: {config.agents.leader.initial_count}")
    print(f"聚落: {config.world.settlement.initial_count}")

    print("\n初始化引擎...")
    t0 = time.time()
    engine = CivilizationEngine(
        config=config,
        seed=42,
        enable_governors=True,
        enable_leaders=True,
    )
    init_time = time.time() - t0
    print(f"初始化完成 ({init_time:.1f}s)")

    print(f"\n聚落数: {len(engine.settlements)}")
    print(f"首领数: {len(engine.leaders)}")
    print(f"外交系统: {'启用' if engine.diplomacy is not None else '未启用'}")
    print(f"贸易系统: {'启用' if engine.trade_manager is not None else '未启用'}")
    print(f"革命追踪: {'启用' if engine.revolution_tracker is not None else '未启用'}")
    print(f"涌现检测: {'启用' if engine.emergence_detector is not None else '未启用'}")

    for sid, s in engine.settlements.items():
        print(f"  聚落 {sid} ({s.name}): 人口={s.population}, "
              f"阵营={s.faction_id}, 位置={s.position}")

    for leader in engine.leaders:
        print(f"  首领 {leader.unique_id}: 阵营={leader.faction_id}, "
              f"管辖={leader.controlled_settlements}")

    total_ticks = 600
    report_interval = 50
    print(f"\n开始仿真 ({total_ticks} ticks)...")
    print("-" * 60)

    sim_start = time.time()
    for tick in range(1, total_ticks + 1):
        engine.step()

        if tick % report_interval == 0:
            elapsed = time.time() - sim_start
            speed = tick / elapsed if elapsed > 0 else 0

            # 统计各状态平民数
            state_counts: dict[str, int] = {}
            for agent in engine.agents:
                cls_name = type(agent).__name__
                if cls_name == "Civilian":
                    st = str(agent.state.value) if hasattr(agent.state, "value") else str(agent.state)
                    state_counts[st] = state_counts.get(st, 0) + 1

            # 聚落资源
            total_food = sum(s.stockpile.get("food", 0) for s in engine.settlements.values())
            total_pop = sum(s.population for s in engine.settlements.values())

            # Phase 3 指标
            trade_vol = 0
            if engine.trade_manager is not None:
                trade_vol = engine.trade_manager.total_volume

            rev_count = 0
            if engine.revolution_tracker is not None:
                rev_count = engine.revolution_tracker.revolution_count

            alliance_cnt = 0
            war_cnt = 0
            if engine.diplomacy is not None:
                relations = getattr(engine.diplomacy, "_relations", {})
                for status in relations.values():
                    sv = int(status)
                    if sv >= 4:
                        alliance_cnt += 1
                    elif sv == 0:
                        war_cnt += 1

            leader_decisions = sum(
                getattr(l, "decision_count", 0) for l in engine.leaders
            )

            print(f"\n[Tick {tick:4d}] ({speed:.1f} tick/s)")
            print(f"  人口: {total_pop} | 食物: {total_food:.0f}")
            print(f"  状态: {state_counts}")
            print(f"  贸易量: {trade_vol:.0f} | 联盟: {alliance_cnt} | "
                  f"战争: {war_cnt} | 革命: {rev_count}")
            print(f"  首领决策次数: {leader_decisions}")
            sys.stdout.flush()

    total_time = time.time() - sim_start
    print("\n" + "=" * 60)
    print(f"仿真完成! 总耗时: {total_time:.1f}s ({total_ticks / total_time:.1f} tick/s)")

    # 最终数据
    df = engine.datacollector.get_model_vars_dataframe()
    print(f"\n数据采集: {len(df)} 条记录, 列: {list(df.columns)}")

    if "total_population" in df.columns:
        print(f"  人口范围: {df['total_population'].min()} - {df['total_population'].max()}")
    if "avg_satisfaction" in df.columns:
        print(f"  满意度范围: {df['avg_satisfaction'].min():.3f} - {df['avg_satisfaction'].max():.3f}")
    if "protest_ratio" in df.columns:
        print(f"  抗议率范围: {df['protest_ratio'].min():.3f} - {df['protest_ratio'].max():.3f}")
    if "trade_volume" in df.columns:
        print(f"  最终贸易量: {df['trade_volume'].iloc[-1]:.0f}")
    if "faction_count" in df.columns:
        print(f"  最终阵营数: {df['faction_count'].iloc[-1]}")

    print("\n聚落最终状态:")
    for sid, s in engine.settlements.items():
        print(f"  {s.name}: 人口={s.population}, 食物={s.stockpile.get('food', 0):.0f}, "
              f"税率={s.tax_rate:.2f}, 治安={s.security_level:.2f}")

    print("\n首领最终状态:")
    for leader in engine.leaders:
        print(f"  首领 {leader.unique_id}: 阵营={leader.faction_id}, "
              f"管辖={leader.controlled_settlements}, "
              f"决策次数={getattr(leader, 'decision_count', 0)}")

    if engine.emergence_detector is not None:
        events = engine.emergence_detector.events
        if events:
            print(f"\n涌现事件 ({len(events)} 个):")
            for e in events[:20]:
                print(f"  [{e.tick}] {e.event_type}: {e.description}")
        else:
            print("\n未检测到涌现事件")

    print("\n" + "=" * 60)
    print("仿真报告结束")


if __name__ == "__main__":
    main()
