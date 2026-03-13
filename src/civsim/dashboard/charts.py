"""Plotly 图表构建器。

为仪表盘的各个面板生成 Plotly Figure 对象。
所有函数接收 SharedState 或其产出的数据，返回 go.Figure。
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from civsim.dashboard.shared_state import SharedState, TickSnapshot

# 状态中文标签与颜色
_STATE_LABELS: dict[str, str] = {
    "WORKING": "劳作",
    "RESTING": "休息",
    "TRADING": "交易",
    "SOCIALIZING": "社交",
    "MIGRATING": "迁徙",
    "PROTESTING": "抗议",
    "FIGHTING": "战斗",
}
_STATE_COLORS: dict[str, str] = {
    "WORKING": "#2ecc71",
    "RESTING": "#3498db",
    "TRADING": "#f1c40f",
    "SOCIALIZING": "#1abc9c",
    "MIGRATING": "#e67e22",
    "PROTESTING": "#e74c3c",
    "FIGHTING": "#8b0000",
}

# 资源颜色
_RESOURCE_COLORS: dict[str, str] = {
    "food": "#27ae60",
    "wood": "#8B4513",
    "ore": "#7f8c8d",
    "gold": "#f39c12",
}

_RESOURCE_LABELS: dict[str, str] = {
    "food": "食物",
    "wood": "木材",
    "ore": "矿石",
    "gold": "金币",
}


# 统一图表深色主题配色
_CHART_PAPER_BG = "#1a1a2e"
_CHART_PLOT_BG = "#16213e"
_CHART_FONT_COLOR = "#ecf0f1"
_CHART_GRID_COLOR = "#2c3e50"


def _apply_dark_layout(fig: go.Figure, title: str = "") -> go.Figure:
    """应用统一的深色主题布局。"""
    fig.update_layout(
        title=dict(text=title, font=dict(color=_CHART_FONT_COLOR, size=14)),
        template="plotly_dark",
        paper_bgcolor=_CHART_PAPER_BG,
        plot_bgcolor=_CHART_PLOT_BG,
        margin=dict(l=40, r=20, t=40, b=30),
        font=dict(size=11, color=_CHART_FONT_COLOR),
        xaxis=dict(gridcolor=_CHART_GRID_COLOR),
        yaxis=dict(gridcolor=_CHART_GRID_COLOR),
    )
    return fig


def _empty_figure(title: str = "") -> go.Figure:
    """生成空白占位图。"""
    return _apply_dark_layout(go.Figure(), title)


def build_population_chart(history: list[TickSnapshot]) -> go.Figure:
    """人口状态分布堆叠面积图。"""
    if not history:
        return _empty_figure("人口状态分布")

    ticks = [s.tick for s in history]
    fig = go.Figure()

    for state_key in _STATE_LABELS:
        counts = [s.state_counts.get(state_key, 0) for s in history]
        fig.add_trace(go.Scatter(
            x=ticks,
            y=counts,
            name=_STATE_LABELS[state_key],
            mode="lines",
            stackgroup="pop",
            line=dict(width=0.5, color=_STATE_COLORS.get(state_key)),
            fillcolor=_STATE_COLORS.get(state_key),
        ))

    _apply_dark_layout(fig, "人口状态分布")
    fig.update_layout(
        xaxis_title="Tick",
        yaxis_title="人数",
        legend=dict(orientation="h", y=-0.15),
    )
    return fig


def build_resource_chart(history: list[TickSnapshot]) -> go.Figure:
    """四大资源趋势折线图。"""
    if not history:
        return _empty_figure("资源总量趋势")

    ticks = [s.tick for s in history]
    fig = go.Figure()

    for res in ("food", "wood", "ore", "gold"):
        values = [s.resources.get(res, 0) for s in history]
        fig.add_trace(go.Scatter(
            x=ticks,
            y=values,
            name=_RESOURCE_LABELS.get(res, res),
            mode="lines",
            line=dict(color=_RESOURCE_COLORS.get(res), width=2),
        ))

    _apply_dark_layout(fig, "资源总量趋势")
    fig.update_layout(
        xaxis_title="Tick",
        yaxis_title="数量",
        legend=dict(orientation="h", y=-0.15),
    )
    return fig


def build_satisfaction_chart(history: list[TickSnapshot]) -> go.Figure:
    """满意度 + 抗议率 + 饥饿度趋势图。"""
    if not history:
        return _empty_figure("社会指标趋势")

    ticks = [s.tick for s in history]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ticks,
        y=[s.avg_satisfaction for s in history],
        name="平均满意度",
        mode="lines",
        line=dict(color="#2ecc71", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=ticks,
        y=[s.protest_ratio for s in history],
        name="抗议率",
        mode="lines",
        line=dict(color="#e74c3c", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=ticks,
        y=[s.avg_hunger for s in history],
        name="平均饥饿度",
        mode="lines",
        line=dict(color="#e67e22", width=2, dash="dash"),
    ))

    _apply_dark_layout(fig, "社会指标趋势")
    fig.update_layout(
        xaxis_title="Tick",
        yaxis_title="比率 (0-1)",
        yaxis=dict(range=[0, 1], gridcolor=_CHART_GRID_COLOR),
        legend=dict(orientation="h", y=-0.15),
    )
    return fig


def build_settlement_table(snapshot: TickSnapshot) -> go.Figure:
    """聚落排行榜表格。"""
    settlements = sorted(
        snapshot.settlements,
        key=lambda s: s.get("population", 0),
        reverse=True,
    )
    if not settlements:
        return _empty_figure("聚落排行榜")

    headers = ["聚落", "人口", "食物", "金币", "税率", "治安", "满意度", "抗议率"]
    cells: list[list[Any]] = [[] for _ in headers]
    for s in settlements:
        cells[0].append(s.get("name", ""))
        cells[1].append(s.get("population", 0))
        cells[2].append(f"{s.get('food', 0):.0f}")
        cells[3].append(f"{s.get('gold', 0):.0f}")
        cells[4].append(f"{s.get('tax_rate', 0):.0%}")
        cells[5].append(f"{s.get('security_level', 0):.0%}")
        cells[6].append(f"{s.get('satisfaction', 0):.2f}")
        cells[7].append(f"{s.get('protest_ratio', 0):.1%}")

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=headers,
            fill_color="#1a1a2e",
            font=dict(color="white", size=12),
            align="center",
        ),
        cells=dict(
            values=cells,
            fill_color="#16213e",
            font=dict(color="white", size=11),
            align="center",
        ),
    )])

    _apply_dark_layout(fig, "聚落排行榜")
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        height=max(200, 40 * len(settlements) + 80),
    )
    return fig


# 复杂图表（外交网络、贸易桑基图）已拆分至 charts_advanced.py
from civsim.dashboard.charts_advanced import (  # noqa: E402, F401
    build_diplomacy_network,
    build_trade_sankey,
)


def build_revolution_timeline(
    history: list[TickSnapshot],
) -> go.Figure:
    """革命事件时间线。"""
    if not history:
        return _empty_figure("革命时间线")

    ticks = [s.tick for s in history]
    rev_counts = [s.revolution_count for s in history]

    # 检测革命发生的 tick（计数增加的点）
    rev_ticks = []
    rev_increments = []
    for i in range(1, len(history)):
        delta = history[i].revolution_count - history[i - 1].revolution_count
        if delta > 0:
            rev_ticks.append(history[i].tick)
            rev_increments.append(delta)

    fig = go.Figure()

    # 累计曲线
    fig.add_trace(go.Scatter(
        x=ticks,
        y=rev_counts,
        name="累计革命次数",
        mode="lines",
        line=dict(color="#e74c3c", width=2),
    ))

    # 事件标记点
    if rev_ticks:
        fig.add_trace(go.Scatter(
            x=rev_ticks,
            y=[
                history[i].revolution_count
                for i in range(1, len(history))
                if history[i].revolution_count
                > history[i - 1].revolution_count
            ],
            name="革命爆发",
            mode="markers",
            marker=dict(color="#e74c3c", size=8, symbol="star"),
        ))

    _apply_dark_layout(fig, "革命时间线")
    fig.update_layout(
        xaxis_title="Tick",
        yaxis_title="累计次数",
    )
    return fig


def build_adaptive_chart(history: list[TickSnapshot]) -> go.Figure:
    """自适应控制器温度与系数曲线。"""
    if not history:
        return _empty_figure("自适应控制器")

    # 筛选有 adaptive_info 的快照
    valid = [s for s in history if s.adaptive_info]
    if not valid:
        return _empty_figure("自适应控制器（未启用）")

    ticks = [s.tick for s in valid]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=ticks,
        y=[s.adaptive_info.get("temperature", 0) for s in valid],
        name="系统温度",
        mode="lines",
        line=dict(color="#e74c3c", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=ticks,
        y=[
            s.adaptive_info.get("markov_protest_multiplier", 1)
            for s in valid
        ],
        name="抗议系数",
        mode="lines",
        line=dict(color="#e67e22", width=1.5, dash="dash"),
    ))
    fig.add_trace(go.Scatter(
        x=ticks,
        y=[
            s.adaptive_info.get("satisfaction_recovery_multiplier", 1)
            for s in valid
        ],
        name="恢复系数",
        mode="lines",
        line=dict(color="#2ecc71", width=1.5, dash="dash"),
    ))

    _apply_dark_layout(fig, "自适应控制器")
    fig.update_layout(
        xaxis_title="Tick",
        yaxis_title="值",
        legend=dict(orientation="h", y=-0.15),
    )
    return fig
