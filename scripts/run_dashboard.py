#!/usr/bin/env python3
"""CivSim 造物主面板启动脚本。

启动仿真引擎后台线程 + Dash 实时仪表盘 Web UI。

用法：
    python scripts/run_dashboard.py [选项]

选项：
    --port PORT         Web 端口（默认 8050）
    --agents N          初始平民数量（默认 200）
    --seed SEED         随机种子
    --no-governors      不启用镇长
    --no-leaders        不启用首领
    --config PATH       配置文件路径
    --debug             Dash 调试模式
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# 确保项目根目录在路径中
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "src"))


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="CivSim 造物主面板",
    )
    parser.add_argument(
        "--port", type=int, default=8050,
        help="Web 端口（默认 8050）",
    )
    parser.add_argument(
        "--agents", type=int, default=200,
        help="初始平民数量（默认 200）",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="随机种子",
    )
    parser.add_argument(
        "--no-governors", action="store_true",
        help="不启用镇长",
    )
    parser.add_argument(
        "--no-leaders", action="store_true",
        help="不启用首领",
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="配置文件路径",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Dash 调试模式",
    )
    return parser.parse_args()


def main() -> None:
    """主入口。"""
    args = parse_args()

    # 日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger = logging.getLogger("civsim.dashboard")

    # 加载配置
    from civsim.config import load_config

    config = load_config(args.config)
    config.agents.civilian.initial_count = args.agents

    # 自动启用镇长/首领
    enable_gov = not args.no_governors
    enable_lead = not args.no_leaders

    if enable_gov:
        config.agents.governor.initial_count = 1
    if enable_lead:
        config.agents.leader.initial_count = 1

    logger.info(
        "启动参数: agents=%d, governors=%s, leaders=%s, seed=%s",
        args.agents,
        enable_gov,
        enable_lead,
        args.seed,
    )

    # 创建仿真运行器
    from civsim.dashboard.sim_runner import SimulationRunner

    runner = SimulationRunner(
        config=config,
        seed=args.seed,
        enable_governors=enable_gov,
        enable_leaders=enable_lead,
    )

    # 创建 Dash 应用
    from civsim.dashboard.app import create_app
    from civsim.dashboard.callbacks import register_callbacks

    app = create_app(runner.state)
    register_callbacks(app)

    # 启动仿真线程
    runner.start()

    logger.info("造物主面板启动: http://localhost:%d", args.port)
    logger.info("按 Ctrl+C 停止")

    try:
        app.run(
            host="0.0.0.0",
            port=args.port,
            debug=args.debug,
        )
    except KeyboardInterrupt:
        logger.info("正在停止...")
    finally:
        runner.stop()
        logger.info("已停止")


if __name__ == "__main__":
    main()
