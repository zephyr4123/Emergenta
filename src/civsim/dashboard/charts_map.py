"""实时地图与马尔可夫转移可视化图表构建器。

提供 Plotly 实时地图（Heatmap 地块 + Scatter Agent）
和马尔可夫转移滚动卡片的 HTML 组件。
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from dash import html

from civsim.dashboard.shared_state import MarkovTransition, TickSnapshot

# 深色主题配色（与 app.py 一致）
_PAPER_BG = "#0a0c10"
_PLOT_BG = "#0f1118"
_FONT_COLOR = "#e2e8f0"

# 地块类型序号→颜色映射（与 _serialize_tile_grid 一致）
# 0=farmland, 1=forest, 2=mine, 3=water, 4=mountain, 5=barren, 6=settlement
_TILE_COLORSCALE: list[list] = [
    [0.0, "#3d6b35"],     # 0 farmland 深绿
    [0.143, "#2d5016"],   # 1 forest   墨绿
    [0.286, "#7f6b52"],   # 2 mine     棕灰
    [0.429, "#2b5f8a"],   # 3 water    深蓝
    [0.571, "#5c5c5c"],   # 4 mountain 灰
    [0.714, "#3a3520"],   # 5 barren   暗黄
    [1.0, "#8b6914"],     # 6 settlement 金棕
]

_TILE_NAMES: list[str] = [
    "农田", "森林", "矿山", "水源", "山地", "荒地", "聚落",
]

# Agent 状态→颜色映射
_STATE_COLORS: dict[int, str] = {
    0: "#2ecc71",  # WORKING   绿
    1: "#3498db",  # RESTING   蓝
    2: "#f1c40f",  # TRADING   黄
    3: "#1abc9c",  # SOCIALIZING 青
    4: "#e67e22",  # MIGRATING 橙
    5: "#e74c3c",  # PROTESTING 红
    6: "#8b0000",  # FIGHTING  暗红
}

_STATE_NAMES_CN: dict[int, str] = {
    0: "劳作", 1: "休息", 2: "交易", 3: "社交",
    4: "迁徙", 5: "抗议", 6: "战斗",
}


def build_interactive_map(snapshot: TickSnapshot) -> go.Figure:
    """构建实时交互地图：地块热力图 + Agent 散点 + 聚落标注。

    Args:
        snapshot: 当前 tick 快照。

    Returns:
        Plotly Figure 对象。
    """
    fig = go.Figure()

    grid = snapshot.tile_grid
    w = snapshot.grid_width
    h = snapshot.grid_height

    # --- 底层：地块热力图 ---
    if grid and w > 0 and h > 0:
        # 转置使 x=列, y=行（Plotly heatmap z[row][col]）
        z_transposed = [[grid[x][y] for x in range(w)] for y in range(h)]
        hover_texts = [
            [_TILE_NAMES[grid[x][y]] for x in range(w)]
            for y in range(h)
        ]
        fig.add_trace(go.Heatmap(
            z=z_transposed,
            colorscale=_TILE_COLORSCALE,
            zmin=0,
            zmax=6,
            showscale=False,
            hovertext=hover_texts,
            hovertemplate="(%{x}, %{y}) %{hovertext}<extra></extra>",
        ))

    # --- 中层：Agent 散点 ---
    if snapshot.agent_positions:
        # 按状态分组绘制（这样图例更清晰）
        state_groups: dict[int, tuple[list[int], list[int]]] = {}
        for (ax, ay), state in zip(
            snapshot.agent_positions, snapshot.agent_states,
        ):
            if state not in state_groups:
                state_groups[state] = ([], [])
            state_groups[state][0].append(ax)
            state_groups[state][1].append(ay)

        for state_idx in sorted(state_groups.keys()):
            xs, ys = state_groups[state_idx]
            color = _STATE_COLORS.get(state_idx, "#ffffff")
            name = _STATE_NAMES_CN.get(state_idx, "?")
            fig.add_trace(go.Scatter(
                x=xs,
                y=ys,
                mode="markers",
                name=name,
                marker=dict(
                    color=color,
                    size=4,
                    opacity=0.8,
                    line=dict(width=0),
                ),
                hovertemplate=f"{name}<br>(%{{x}}, %{{y}})<extra></extra>",
            ))

    # --- 上层：聚落标注 ---
    if snapshot.settlements:
        sx = [s["position"][0] for s in snapshot.settlements]
        sy = [s["position"][1] for s in snapshot.settlements]
        labels = [
            f"{s['name']}<br>人口:{s['population']}"
            for s in snapshot.settlements
        ]
        names = [s["name"] for s in snapshot.settlements]
        fig.add_trace(go.Scatter(
            x=sx,
            y=sy,
            mode="markers+text",
            name="聚落",
            marker=dict(
                color="#f39c12",
                size=12,
                symbol="diamond",
                line=dict(width=1.5, color="#ffffff"),
            ),
            text=names,
            textposition="top center",
            textfont=dict(color="#f39c12", size=9),
            hovertext=labels,
            hovertemplate="%{hovertext}<extra></extra>",
            showlegend=False,
        ))

    # --- 布局 ---
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_PLOT_BG,
        font=dict(size=11, color=_FONT_COLOR),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            scaleanchor="y",
            constrain="domain",
            showgrid=False,
            zeroline=False,
            range=[-0.5, max(w, 1) - 0.5] if w > 0 else None,
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            range=[-0.5, max(h, 1) - 0.5] if h > 0 else None,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="center",
            x=0.5,
            font=dict(size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
        dragmode="pan",
    )

    return fig


def build_markov_cards(
    transitions: list[MarkovTransition],
) -> list[html.Div]:
    """构建马尔可夫转移滚动卡片列表。

    Args:
        transitions: 最近的转移记录（已排序，最新在前）。

    Returns:
        Dash html.Div 组件列表。
    """
    if not transitions:
        return [html.Div(
            "等待仿真运行...",
            style={"color": "#7f8c8d", "padding": "20px", "textAlign": "center"},
        )]

    cards: list[html.Div] = []
    for t in reversed(transitions):  # 最新的在最上面
        # 状态转移是否发生变化
        changed = t.prev_state != t.next_state
        arrow_color = "#e74c3c" if changed else "#7f8c8d"
        prob_color = "#e74c3c" if t.probability < 0.2 else (
            "#f39c12" if t.probability < 0.5 else "#2ecc71"
        )

        # 性格标签颜色
        personality_colors = {
            "顺从": "#2ecc71", "中立": "#3498db", "叛逆": "#e74c3c",
        }
        p_color = personality_colors.get(t.personality, "#95a5a6")

        # Granovetter 标识
        grano_badge = ""
        if t.granovetter_triggered:
            grano_badge = " 🔥"

        # 构建因子标签
        factor_spans = []
        for f in t.factors:
            f_color = "#e74c3c" if "传染" in f else "#e67e22"
            factor_spans.append(html.Span(
                f,
                style={
                    "background": f_color,
                    "color": "#fff",
                    "padding": "1px 6px",
                    "borderRadius": "3px",
                    "fontSize": "10px",
                    "marginRight": "4px",
                },
            ))

        card = html.Div([
            # 头部：Tick + Agent ID + 性格
            html.Div([
                html.Span(
                    f"T{t.tick}",
                    style={"color": "#7f8c8d", "fontSize": "10px"},
                ),
                html.Span(
                    f" #{t.agent_id} ",
                    style={"color": _FONT_COLOR, "fontWeight": "700"},
                ),
                html.Span(
                    f"[{t.personality}]",
                    style={"color": p_color, "fontSize": "11px"},
                ),
                html.Span(grano_badge),
                html.Span(
                    f"  饥饿:{t.hunger:.0%} 满意:{t.satisfaction:.0%}",
                    style={
                        "color": "#95a5a6",
                        "fontSize": "10px",
                        "marginLeft": "auto",
                    },
                ),
            ], style={
                "display": "flex",
                "alignItems": "center",
                "gap": "4px",
                "marginBottom": "4px",
            }),
            # 状态转移行
            html.Div([
                html.Span(
                    t.prev_state,
                    style={
                        "fontWeight": "700",
                        "color": _FONT_COLOR,
                        "fontSize": "13px",
                    },
                ),
                html.Span(
                    f" ──({t.probability:.0%})──▶ ",
                    style={"color": arrow_color, "fontSize": "12px"},
                ),
                html.Span(
                    t.next_state,
                    style={
                        "fontWeight": "700",
                        "color": prob_color,
                        "fontSize": "13px",
                    },
                ),
            ]),
            # 因子行
            html.Div(
                factor_spans,
                style={"marginTop": "3px"},
            ) if factor_spans else None,
        ], style={
            "background": "#16213e",
            "borderLeft": (
                "3px solid #e74c3c" if t.granovetter_triggered
                else "3px solid #2c3e6b"
            ),
            "borderRadius": "4px",
            "padding": "8px 10px",
            "marginBottom": "6px",
        })
        cards.append(card)

    return cards
