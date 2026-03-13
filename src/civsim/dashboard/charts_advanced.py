"""高级图表构建器 — 外交网络、贸易桑基图。

从 charts.py 拆分，处理需要 networkx 的复杂图表。
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from civsim.dashboard.shared_state import TickSnapshot


# 统一配色常量
_CHART_PAPER_BG = "#1a1a2e"
_CHART_PLOT_BG = "#16213e"
_CHART_FONT_COLOR = "#ecf0f1"
_CHART_GRID_COLOR = "#2c3e50"


def _empty_figure(title: str = "") -> go.Figure:
    """生成空白占位图。"""
    fig = go.Figure()
    fig.update_layout(
        title=dict(text=title, font=dict(color=_CHART_FONT_COLOR, size=14)),
        template="plotly_dark",
        paper_bgcolor=_CHART_PAPER_BG,
        plot_bgcolor=_CHART_PLOT_BG,
        margin=dict(l=40, r=20, t=40, b=30),
        font=dict(size=11, color=_CHART_FONT_COLOR),
    )
    return fig


def build_trade_sankey(
    trade_routes: list[dict[str, Any]],
    settlements: list[dict[str, Any]],
) -> go.Figure:
    """贸易流量桑基图。"""
    if not trade_routes or not settlements:
        return _empty_figure("贸易流量")

    # 建立聚落 ID → 名称映射
    id_to_name = {s["id"]: s["name"] for s in settlements}
    all_ids = sorted(id_to_name.keys())
    id_to_idx = {sid: i for i, sid in enumerate(all_ids)}

    labels = [id_to_name.get(sid, f"#{sid}") for sid in all_ids]

    # 聚合贸易流
    flows: dict[tuple[int, int], float] = {}
    for route in trade_routes:
        key = (route["seller_id"], route["buyer_id"])
        flows[key] = flows.get(key, 0) + route.get("amount", 0)

    sources, targets, values = [], [], []
    for (seller, buyer), amount in flows.items():
        if seller in id_to_idx and buyer in id_to_idx:
            sources.append(id_to_idx[seller])
            targets.append(id_to_idx[buyer])
            values.append(amount)

    if not sources:
        return _empty_figure("贸易流量（无数据）")

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            label=labels,
            color="#3498db",
            pad=15,
            thickness=20,
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color="rgba(52, 152, 219, 0.3)",
        ),
    )])

    fig.update_layout(
        title=dict(text="贸易流量", font=dict(color=_CHART_FONT_COLOR, size=14)),
        template="plotly_dark",
        paper_bgcolor=_CHART_PAPER_BG,
        plot_bgcolor=_CHART_PLOT_BG,
        margin=dict(l=20, r=20, t=40, b=20),
        font=dict(size=11, color=_CHART_FONT_COLOR),
    )
    return fig


def build_diplomacy_network(
    diplomacy_data: dict[str, Any],
    settlements: list[dict[str, Any]],
) -> go.Figure:
    """外交关系网络图。"""
    if not diplomacy_data:
        return _empty_figure("外交关系网络")

    try:
        import networkx as nx
    except ImportError:
        return _empty_figure("外交关系网络（需要 networkx）")

    # 构建图
    g = nx.Graph()
    for _key, rel in diplomacy_data.items():
        a, b = rel["faction_a"], rel["faction_b"]
        g.add_edge(a, b, status=rel["status"], trust=rel["trust"])

    if not g.nodes:
        return _empty_figure("外交关系网络（无数据）")

    pos = nx.spring_layout(g, seed=42)

    # 边
    status_colors = {
        "WAR": "#e74c3c",
        "HOSTILE": "#e67e22",
        "NEUTRAL": "#95a5a6",
        "FRIENDLY": "#3498db",
        "ALLIED": "#2ecc71",
    }
    edge_traces = []
    for u, v, data in g.edges(data=True):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        color = status_colors.get(data["status"], "#95a5a6")
        edge_traces.append(go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode="lines",
            line=dict(width=2, color=color),
            hoverinfo="text",
            text=(
                f"阵营{u}↔阵营{v}: {data['status']} "
                f"(信任:{data['trust']:.2f})"
            ),
            showlegend=False,
        ))

    # 节点
    node_x = [pos[n][0] for n in g.nodes]
    node_y = [pos[n][1] for n in g.nodes]
    node_labels = [f"阵营 {n}" for n in g.nodes]

    # 计算阵营人口
    faction_pop: dict[int, int] = {}
    for s in settlements:
        fid = s.get("faction_id")
        if fid is not None:
            faction_pop[fid] = faction_pop.get(fid, 0) + s.get(
                "population", 0,
            )

    node_sizes = [
        max(15, min(50, faction_pop.get(n, 0) // 5))
        for n in g.nodes
    ]

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        marker=dict(
            size=node_sizes,
            color="#3498db",
            line=dict(width=2, color="white"),
        ),
        text=node_labels,
        textposition="top center",
        textfont=dict(color="white", size=11),
        hoverinfo="text",
    )

    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(
        title=dict(text="外交关系网络", font=dict(color=_CHART_FONT_COLOR, size=14)),
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        template="plotly_dark",
        paper_bgcolor=_CHART_PAPER_BG,
        plot_bgcolor=_CHART_PLOT_BG,
        margin=dict(l=10, r=10, t=40, b=10),
        font=dict(size=11, color=_CHART_FONT_COLOR),
    )
    return fig
