#!/usr/bin/env python3
"""CivSim 造物主面板启动脚本。

启动仿真引擎后台线程 + Dash 实时仪表盘 Web UI。
首次启动弹出向导窗口配置仿真参数和 LLM 连接。

用法：
    python scripts/run_dashboard.py           # 向导模式（推荐）
    python scripts/run_dashboard.py --quick   # 跳过向导，使用默认参数
"""

from __future__ import annotations

import argparse
import logging
import socket
import sys
import threading
import webbrowser
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
        "--quick", action="store_true",
        help="跳过向导，使用默认参数直接启动",
    )
    parser.add_argument(
        "--port", type=int, default=None,
        help="Web 端口（默认 8050）",
    )
    parser.add_argument(
        "--agents", type=int, default=None,
        help="初始平民数量（默认由向导选择）",
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

    # ── 启动向导（除非 --quick 或指定了 --agents）──
    agents = args.agents or 200
    seed = args.seed
    enable_gov = not args.no_governors
    enable_lead = not args.no_leaders
    port = args.port or 8050

    if not args.quick and args.agents is None:
        from civsim.dashboard.wizard import run_wizard

        launch = run_wizard()
        if launch.cancelled:
            print("已取消启动")
            sys.exit(0)
        agents = launch.agents
        seed = launch.seed if launch.seed is not None else seed
        enable_gov = launch.enable_governors
        enable_lead = launch.enable_leaders
        port = launch.port if args.port is None else args.port

    # ── 日志 ──
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger = logging.getLogger("civsim.dashboard")

    # ── 加载配置 ──
    from civsim.config import load_config

    config = load_config(args.config)

    # ── 按平民数自动缩放所有参数 ──
    scaling = _compute_scaling(agents)
    config.agents.civilian.initial_count = agents
    config.world.grid.width = scaling["grid"]
    config.world.grid.height = scaling["grid"]
    config.world.settlement.initial_count = scaling["settlements"]
    config.world.settlement.min_suitability_score = scaling["min_suitability"]
    config.map_suitability.min_settlement_distance = scaling["min_distance"]
    config.resources.initial_stockpile.food = scaling["food"]
    config.resources.initial_stockpile.wood = scaling["wood"]
    config.resources.initial_stockpile.ore = scaling["ore"]
    config.resources.initial_stockpile.gold = scaling["gold"]

    if enable_gov:
        config.agents.governor.initial_count = 1
    if enable_lead:
        config.agents.leader.initial_count = scaling["leaders"]

    logger.info(
        "启动参数: %d 平民, %dx%d 地图, %d 聚落, %d 首领, seed=%s",
        agents, scaling["grid"], scaling["grid"],
        scaling["settlements"], scaling["leaders"], seed,
    )
    logger.info(
        "初始资源/聚落: 食物=%d, 木材=%d, 矿石=%d, 金币=%d",
        scaling["food"], scaling["wood"], scaling["ore"], scaling["gold"],
    )

    # ── 创建仿真运行器 ──
    from civsim.dashboard.sim_runner import SimulationRunner

    runner = SimulationRunner(
        config=config,
        seed=seed,
        enable_governors=enable_gov,
        enable_leaders=enable_lead,
    )

    # ── 创建 Dash 应用 ──
    from civsim.dashboard.app import create_app
    from civsim.dashboard.callbacks import register_callbacks

    app = create_app(runner.state)
    register_callbacks(app)

    # ── 端口占用检测 ──
    _ensure_port_free(port, logger)

    # ── 启动 ──
    runner.start()

    logger.info("造物主面板启动: http://localhost:%d", port)
    logger.info("按 Ctrl+C 停止")

    # 自动打开浏览器（延迟 1.5s 等服务就绪）
    def _open_browser() -> None:
        import time
        time.sleep(1.5)
        webbrowser.open(f"http://localhost:{port}")

    threading.Thread(target=_open_browser, daemon=True).start()

    try:
        app.run(
            host="0.0.0.0",
            port=port,
            debug=args.debug,
        )
    except KeyboardInterrupt:
        logger.info("正在停止...")
    finally:
        runner.stop()
        logger.info("已停止")


def _compute_scaling(agents: int) -> dict[str, int | float]:
    """根据平民数量计算所有自动缩放参数。

    缩放逻辑：
      - 地图边长 = sqrt(agents) * 2.5，范围 [20, 200]
      - 聚落数 = sqrt(agents) * 0.5，范围 [3, 50]
      - 首领数 = 聚落数 / 3，范围 [2, 15]
      - 聚落间距 = 地图边长 / (sqrt(聚落数) + 1)，自适应地图大小
      - 适宜度阈值 = 小地图降低以确保能放够聚落
      - 食物/聚落 = 400 + agents * 0.6
    """
    import math

    grid = max(20, min(200, round(math.sqrt(agents) * 2.5)))
    settlements = max(3, min(50, round(math.sqrt(agents) * 0.5)))
    leaders = max(2, min(15, round(settlements / 3)))
    food = round(400 + agents * 0.6)
    wood = round(150 + agents * 0.1)
    ore = round(30 + agents * 0.02)
    gold = round(80 + agents * 0.05)

    # 聚落间距随地图缩放：确保能放下足够聚落
    min_distance = max(3, round(grid / (math.sqrt(settlements) + 1)))
    # 小地图降低适宜度阈值
    min_suitability = 0.3 if grid <= 40 else (0.2 if grid <= 60 else 0.3)

    return {
        "grid": grid,
        "settlements": settlements,
        "leaders": leaders,
        "food": food,
        "wood": wood,
        "ore": ore,
        "gold": gold,
        "min_distance": min_distance,
        "min_suitability": min_suitability,
    }


def _ensure_port_free(port: int, logger: logging.Logger) -> None:
    """检查端口是否被占用，若占用则尝试释放。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", port)) != 0:
            return  # 端口空闲

    logger.warning("端口 %d 被占用，正在尝试释放...", port)
    import subprocess
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=5,
        )
        pids = result.stdout.strip().split("\n")
        for pid in pids:
            if pid.strip():
                subprocess.run(
                    ["kill", "-9", pid.strip()],
                    timeout=3,
                )
                logger.info("已终止占用进程 PID %s", pid.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.error(
            "无法释放端口 %d，请手动执行: lsof -ti:%d | xargs kill -9",
            port, port,
        )
        sys.exit(1)

    # 等待端口释放
    import time
    for _ in range(10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                logger.info("端口 %d 已释放", port)
                return
        time.sleep(0.3)
    logger.error("端口 %d 释放超时", port)
    sys.exit(1)


if __name__ == "__main__":
    main()
