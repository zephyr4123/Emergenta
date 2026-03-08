"""仿真启动脚本。

命令行入口，支持指定 tick 数、seed、可视化开关。
"""

import argparse
import sys
from pathlib import Path

# 确保 src 在路径中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

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
        "--visualize", action="store_true",
        help="运行结束后输出地图快照",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    engine = CivilizationEngine(
        config=config,
        enable_db=not args.no_db,
        seed=args.seed,
    )

    print(f"=== AI文明模拟器 CivSim v{config.project.version} ===")
    print(f"地图: {config.world.grid.width}x{config.world.grid.height}")
    print(f"聚落: {len(engine.settlements)} 个")
    print(f"平民: {config.agents.civilian.initial_count} 人")
    print(f"运行: {args.ticks} ticks")
    print()

    for tick in range(args.ticks):
        engine.step()
        if (tick + 1) % 10 == 0:
            df = engine.datacollector.get_model_vars_dataframe()
            latest = df.iloc[-1]
            print(
                f"Tick {engine.clock.tick:>4d} | "
                f"人口: {int(latest['total_population']):>4d} | "
                f"食物: {latest['total_food']:>8.1f} | "
                f"满意: {latest['avg_satisfaction']:.2f} | "
                f"抗议: {latest['protest_ratio']:.2%}"
            )

    print("\n=== 仿真结束 ===")

    if args.visualize:
        from civsim.visualization.map_renderer import render_agents_on_map
        output = "data/exports/final_map.png"
        render_agents_on_map(
            engine.tile_grid,
            list(engine.agents),
            output_path=output,
            title=f"CivSim Tick {engine.clock.tick}",
        )
        print(f"地图已保存: {output}")


if __name__ == "__main__":
    main()
