"""2D 地图渲染器。

使用 Matplotlib 渲染世界网格地图，支持 Agent 状态着色。
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.civilian import Civilian
from civsim.world.tiles import TileType

# 地块颜色映射
_TILE_COLORS: dict[TileType, tuple[float, float, float]] = {
    TileType.FARMLAND: (0.6, 0.8, 0.3),
    TileType.FOREST: (0.1, 0.5, 0.1),
    TileType.MINE: (0.5, 0.4, 0.3),
    TileType.WATER: (0.2, 0.4, 0.8),
    TileType.MOUNTAIN: (0.6, 0.6, 0.6),
    TileType.BARREN: (0.8, 0.7, 0.5),
    TileType.SETTLEMENT: (0.9, 0.2, 0.2),
}

# Agent 状态颜色
_STATE_COLORS: dict[CivilianState, str] = {
    CivilianState.WORKING: "green",
    CivilianState.RESTING: "blue",
    CivilianState.TRADING: "gold",
    CivilianState.SOCIALIZING: "cyan",
    CivilianState.MIGRATING: "orange",
    CivilianState.PROTESTING: "red",
    CivilianState.FIGHTING: "darkred",
}


def render_terrain(
    tile_grid: list[list],
    output_path: str | None = None,
    title: str = "CivSim 地形图",
) -> None:
    """渲染地形图。

    Args:
        tile_grid: 地块网格 [x][y]。
        output_path: 输出文件路径，为 None 时显示。
        title: 图表标题。
    """
    width = len(tile_grid)
    height = len(tile_grid[0]) if width > 0 else 0
    image = np.zeros((height, width, 3))

    for x in range(width):
        for y in range(height):
            color = _TILE_COLORS.get(
                tile_grid[x][y].tile_type, (0.5, 0.5, 0.5)
            )
            image[y][x] = color

    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    ax.imshow(image, origin="lower")
    ax.set_title(title)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=100, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()


def render_agents_on_map(
    tile_grid: list[list],
    agents: list,
    output_path: str | None = None,
    title: str = "CivSim Agent 分布图",
) -> None:
    """渲染带 Agent 标记的地图。

    Args:
        tile_grid: 地块网格。
        agents: Agent 列表。
        output_path: 输出路径。
        title: 图表标题。
    """
    width = len(tile_grid)
    height = len(tile_grid[0]) if width > 0 else 0
    image = np.zeros((height, width, 3))

    for x in range(width):
        for y in range(height):
            color = _TILE_COLORS.get(
                tile_grid[x][y].tile_type, (0.5, 0.5, 0.5)
            )
            image[y][x] = color

    fig, ax = plt.subplots(1, 1, figsize=(12, 12))
    ax.imshow(image, origin="lower")

    for agent in agents:
        if not isinstance(agent, Civilian) or agent.pos is None:
            continue
        x, y = agent.pos
        color = _STATE_COLORS.get(agent.state, "white")
        ax.plot(x, y, "o", color=color, markersize=2, alpha=0.6)

    ax.set_title(title)

    # 图例
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", label=s.name,
               markerfacecolor=c, markersize=8)
        for s, c in _STATE_COLORS.items()
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=8)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=100, bbox_inches="tight")
        plt.close(fig)
    else:
        plt.show()
