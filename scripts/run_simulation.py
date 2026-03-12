"""仿真启动脚本。

命令行入口，支持指定 tick 数、seed、镇长开关、可视化开关。
"""

import argparse
import sys
import time
from pathlib import Path

# 确保 src 在路径中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from civsim.agents.governor import Governor
from civsim.config import load_config
from civsim.world.engine import CivilizationEngine


def main() -> None:
    """仿真主入口。"""
    parser = argparse.ArgumentParser(description="AI文明模拟器")
    parser.add_argument(
        "--ticks", type=int, default=100,
        help="仿真运行的 tick 数（默认 100）",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="随机种子",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="配置文件路径",
    )
    parser.add_argument(
        "--no-db", action="store_true",
        help="禁用数据库存储",
    )
    parser.add_argument(
        "--governors", action="store_true",
        help="启用 LLM 镇长 Agent",
    )
    parser.add_argument(
        "--visualize", action="store_true",
        help="运行结束后输出地图快照",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    engine = CivilizationEngine(
        config=config,
        enable_db=not args.no_db,
        seed=args.seed,
        enable_governors=args.governors,
    )

    governors = engine.get_governors()
    print(f"╔══════════════════════════════════════════════╗")
    print(f"║   AI文明模拟器 CivSim v{config.project.version}               ║")
    print(f"╠══════════════════════════════════════════════╣")
    print(f"║  地图: {config.world.grid.width}x{config.world.grid.height:<34}║")
    print(f"║  聚落: {len(engine.settlements)} 个{' ':36}║")
    print(f"║  平民: {config.agents.civilian.initial_count} 人{' ':34}║")
    print(f"║  镇长: {len(governors)} 个 {'(LLM驱动)' if governors else '(未启用)':<29}║")
    print(f"║  运行: {args.ticks} ticks{' ':32}║")
    print(f"╚══════════════════════════════════════════════╝")
    print()

    # 打印聚落初始状态
    print("--- 聚落初始状态 ---")
    for sid, s in engine.settlements.items():
        gov_info = ""
        if s.governor_id is not None:
            gov_info = f" | 镇长ID: {s.governor_id}"
        print(
            f"  [{sid}] {s.name} @ ({s.position[0]:>2},{s.position[1]:>2}) | "
            f"人口: {s.population:>3} | "
            f"食物: {s.stockpile['food']:.0f}{gov_info}"
        )
    print()

    start_time = time.monotonic()

    print("--- 仿真进行中 ---")
    print(f"{'Tick':>6} | {'季节':>2} | {'人口':>4} | {'食物':>8} | "
          f"{'木材':>7} | {'金币':>6} | {'满意':>4} | {'饥饿':>4} | "
          f"{'抗议率':>6} | {'劳作':>4} | {'抗议':>4}")
    print("-" * 95)

    season_names = {0: "春", 1: "夏", 2: "秋", 3: "冬"}

    for tick in range(args.ticks):
        engine.step()
        if (tick + 1) % 10 == 0:
            df = engine.datacollector.get_model_vars_dataframe()
            latest = df.iloc[-1]
            season = season_names.get(int(engine.clock.current_season), "?")
            print(
                f"{engine.clock.tick:>6} | {season:>2}  | "
                f"{int(latest['total_population']):>4} | "
                f"{latest['total_food']:>8.1f} | "
                f"{latest['total_wood']:>7.1f} | "
                f"{latest['total_gold']:>6.1f} | "
                f"{latest['avg_satisfaction']:>4.2f} | "
                f"{latest['avg_hunger']:>4.2f} | "
                f"{latest['protest_ratio']:>6.2%} | "
                f"{int(latest['working_count']):>4} | "
                f"{int(latest['protesting_count']):>4}"
            )

    elapsed = time.monotonic() - start_time

    # 最终统计
    df = engine.datacollector.get_model_vars_dataframe()
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║              仿真结束 - 最终报告              ║")
    print("╠══════════════════════════════════════════════╣")
    print(f"║  耗时: {elapsed:.2f} 秒{' ':33}║")
    print(f"║  总 tick: {engine.clock.tick}{' ':33}║")
    print(f"║  经过年数: {engine.clock.current_year}{' ':32}║")
    print(f"╚══════════════════════════════════════════════╝")

    # 聚落最终状态
    print()
    print("--- 聚落最终状态 ---")
    for sid, s in engine.settlements.items():
        print(
            f"  [{sid}] {s.name} | "
            f"人口: {s.population:>3} | "
            f"税率: {s.tax_rate:.2f} | "
            f"治安: {s.security_level:.2f} | "
            f"食物: {s.stockpile['food']:>7.1f} | "
            f"金币: {s.stockpile['gold']:>6.1f}"
        )

    # 镇长决策统计
    if governors:
        print()
        print("--- 镇长决策统计 ---")
        for gov in governors:
            s = engine.settlements.get(gov.settlement_id)
            s_name = s.name if s else "未知"
            print(
                f"  镇长 {gov.unique_id} ({s_name}) | "
                f"决策次数: {gov.decision_count} | "
                f"记忆条数: {gov.memory.short_term_count}"
            )
            if gov.last_decision:
                d = gov.last_decision
                print(
                    f"    最后决策: 税率{d['tax_rate_change']:+.2f}, "
                    f"治安{d['security_change']:+.2f}, "
                    f"重点: {d['resource_focus']}"
                )
                print(f"    理由: {d['reasoning'][:60]}")

        # LLM 调用统计
        if engine.llm_gateway:
            stats = engine.llm_gateway.stats
            print()
            print("--- LLM 调用统计 ---")
            print(f"  总调用次数: {stats.total_calls}")
            print(f"  总 Prompt Tokens: {stats.total_prompt_tokens}")
            print(f"  总 Completion Tokens: {stats.total_completion_tokens}")
            print(f"  平均延迟: {stats.avg_latency_ms:.0f} ms")
            print(f"  错误次数: {stats.errors}")
            if hasattr(governors[0], 'cache') and governors[0].cache:
                print(f"  缓存命中率: {governors[0].cache.hit_rate:.1%}")

    # 关键指标趋势
    print()
    print("--- 关键指标趋势 (每50 tick采样) ---")
    sample_points = range(0, len(df), max(1, len(df) // 10))
    for i in sample_points:
        row = df.iloc[i]
        print(
            f"  Tick {i+1:>4}: "
            f"人口={int(row['total_population']):>4}, "
            f"食物={row['total_food']:>7.0f}, "
            f"满意={row['avg_satisfaction']:.2f}, "
            f"抗议={row['protest_ratio']:.2%}"
        )

    if args.visualize:
        from civsim.visualization.map_renderer import render_agents_on_map
        Path("scripts/data/exports").mkdir(parents=True, exist_ok=True)
        output = "scripts/data/exports/final_map.png"
        render_agents_on_map(
            engine.tile_grid,
            list(engine.agents),
            output_path=output,
            title=f"CivSim Tick {engine.clock.tick}",
        )
        print(f"\n地图已保存: {output}")


if __name__ == "__main__":
    main()
