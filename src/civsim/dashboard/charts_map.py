"""实时地图与马尔可夫转移可视化图表构建器。

提供 Plotly 实时地图（Heatmap 地块 + Scatter Agent）
和马尔可夫转移滚动卡片的 HTML 组件。
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from dash import html

from civsim.dashboard.shared_state import MarkovTransition, TickSnapshot

# 深色主题配色（Imperial Observatory）
_PAPER_BG = "#07080c"
_PLOT_BG = "#0b0d14"
_FONT_COLOR = "#e0dace"

# 地块类型序号→颜色映射（与 _serialize_tile_grid 一致）
# 0=farmland, 1=forest, 2=mine, 3=water, 4=mountain, 5=barren, 6=settlement
_TILE_COLORSCALE: list[list] = [
    [0.0, "#3a5e34"],     # 0 farmland  深苔绿
    [0.143, "#263d1e"],   # 1 forest    墨松绿
    [0.286, "#6b5c48"],   # 2 mine      赭石棕
    [0.429, "#2a4d6b"],   # 3 water     深靛蓝
    [0.571, "#4a4a4a"],   # 4 mountain  玄武灰
    [0.714, "#3a3225"],   # 5 barren    焦褐
    [1.0, "#8b7430"],     # 6 settlement 古铜金
]

_TILE_NAMES: list[str] = [
    "农田", "森林", "矿山", "水源", "山地", "荒地", "聚落",
]

# Agent 状态→颜色映射（暖色调）
_STATE_COLORS: dict[int, str] = {
    0: "#4a9e6e",  # WORKING   苔绿
    1: "#5b7fb5",  # RESTING   灰蓝
    2: "#c9a84c",  # TRADING   琥珀金
    3: "#6ba3a0",  # SOCIALIZING 青瓷
    4: "#c87f3b",  # MIGRATING 铜橙
    5: "#b5342a",  # PROTESTING 朱红
    6: "#7a1f1f",  # FIGHTING  殷红
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
                color="#c9a84c",
                size=12,
                symbol="diamond",
                line=dict(width=1.5, color="#e8d5a3"),
            ),
            text=names,
            textposition="top center",
            textfont=dict(color="#e8d5a3", size=9),
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
            style={"color": "#8a8272", "padding": "20px", "textAlign": "center"},
        )]

    cards: list[html.Div] = []
    for t in reversed(transitions):  # 最新的在最上面
        # 状态转移是否发生变化
        changed = t.prev_state != t.next_state
        arrow_color = "#b5342a" if changed else "#6b6358"
        prob_color = "#b5342a" if t.probability < 0.2 else (
            "#c9a84c" if t.probability < 0.5 else "#4a9e6e"
        )

        # 性格标签颜色
        personality_colors = {
            "顺从": "#4a9e6e", "中立": "#5b7fb5", "叛逆": "#b5342a",
        }
        p_color = personality_colors.get(t.personality, "#8a8272")

        # Granovetter 标识
        grano_badge = ""
        if t.granovetter_triggered:
            grano_badge = " 🔥"

        # 构建因子标签
        factor_spans = []
        for f in t.factors:
            f_color = "#b5342a" if "传染" in f else "#8b7a3e"
            factor_spans.append(html.Span(
                f,
                style={
                    "background": f_color,
                    "color": "#f5f0e6",
                    "padding": "2px 7px",
                    "borderRadius": "3px",
                    "fontSize": "10px",
                    "marginRight": "4px",
                    "letterSpacing": "0.2px",
                },
            ))

        card = html.Div([
            # 头部：Tick + Agent ID + 性格
            html.Div([
                html.Span(
                    f"T{t.tick}",
                    style={
                        "color": "#6b6358", "fontSize": "10px",
                        "fontFamily": "JetBrains Mono, monospace",
                    },
                ),
                html.Span(
                    f" #{t.agent_id} ",
                    style={"color": _FONT_COLOR, "fontWeight": "600"},
                ),
                html.Span(
                    f"[{t.personality}]",
                    style={"color": p_color, "fontSize": "11px"},
                ),
                html.Span(grano_badge),
                html.Span(
                    f"  饥饿:{t.hunger:.0%} 满意:{t.satisfaction:.0%}",
                    style={
                        "color": "#8a8272",
                        "fontSize": "10px",
                        "marginLeft": "auto",
                        "fontFamily": "JetBrains Mono, monospace",
                    },
                ),
            ], style={
                "display": "flex",
                "alignItems": "center",
                "gap": "4px",
                "marginBottom": "5px",
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
            "background": "rgba(14,17,26,0.85)",
            "borderLeft": (
                "3px solid #b5342a" if t.granovetter_triggered
                else "3px solid rgba(201,168,76,0.15)"
            ),
            "border": "1px solid rgba(201,168,76,0.08)",
            "borderLeftWidth": "3px",
            "borderLeftColor": (
                "#b5342a" if t.granovetter_triggered
                else "rgba(201,168,76,0.18)"
            ),
            "borderRadius": "5px",
            "padding": "9px 12px",
            "marginBottom": "7px",
        })
        cards.append(card)

    return cards


# ── 聚落排行榜 HTML 表格 ─────────────────────────────────────

_TH_STYLE: dict = {
    "padding": "14px 18px",
    "fontSize": "10.5px",
    "textTransform": "uppercase",
    "letterSpacing": "1.2px",
    "color": "#8b7a3e",
    "fontWeight": "600",
    "borderBottom": "1px solid rgba(201,168,76,0.10)",
    "background": "rgba(201,168,76,0.03)",
    "textAlign": "left",
    "fontFamily": "DM Sans, sans-serif",
}

_TD_STYLE: dict = {
    "padding": "14px 18px",
    "fontSize": "13px",
    "borderBottom": "1px solid rgba(201,168,76,0.06)",
    "color": "#e0dace",
    "fontFamily": "DM Sans, sans-serif",
}


def _bar(value: float, max_val: float, color: str) -> html.Div:
    """生成进度条组件。"""
    pct = min(100, max(0, (value / max_val * 100) if max_val > 0 else 0))
    return html.Div([
        html.Span(
            f"{value:.0f}",
            style={
                "minWidth": "40px", "fontSize": "12.5px",
                "fontFamily": "JetBrains Mono, monospace",
            },
        ),
        html.Div(
            html.Div(style={
                "width": f"{pct:.0f}%",
                "height": "100%",
                "borderRadius": "2px",
                "background": f"linear-gradient(90deg, {color}, {color}cc)",
            }),
            style={
                "width": "80px",
                "height": "5px",
                "background": "rgba(201,168,76,0.06)",
                "borderRadius": "2px",
                "overflow": "hidden",
            },
        ),
    ], style={"display": "flex", "alignItems": "center", "gap": "8px"})


def _sat_dot(value: float) -> html.Div:
    """满意度圆点 + 数值。"""
    if value >= 0.6:
        color, shadow = "#4a9e6e", "0 0 6px rgba(74,158,110,0.5)"
    elif value >= 0.35:
        color, shadow = "#c9a84c", "0 0 6px rgba(201,168,76,0.4)"
    else:
        color, shadow = "#b5342a", "0 0 6px rgba(181,52,42,0.5)"
    return html.Div([
        html.Span(style={
            "width": "8px", "height": "8px",
            "borderRadius": "50%",
            "background": color,
            "boxShadow": shadow,
            "display": "inline-block",
        }),
        html.Span(f"{value:.2f}"),
    ], style={"display": "flex", "alignItems": "center", "gap": "6px"})


def _protest_cell(value: float) -> html.Span:
    """抗议率着色。"""
    color = "#4a9e6e" if value < 0.05 else (
        "#c9a84c" if value < 0.15 else "#b5342a"
    )
    weight = "bold" if value >= 0.1 else "normal"
    return html.Span(
        f"{value:.1%}",
        style={"color": color, "fontWeight": weight},
    )


def build_settlement_html(snapshot: TickSnapshot) -> list:
    """构建聚落排行榜 HTML 表格。"""
    settlements = sorted(
        snapshot.settlements,
        key=lambda s: s.get("population", 0),
        reverse=True,
    )
    if not settlements:
        return [html.Div(
            "暂无聚落数据",
            style={"color": "#8a8272", "textAlign": "center", "padding": "40px"},
        )]

    # 计算最大值用于进度条缩放
    max_food = max((s.get("food", 0) for s in settlements), default=1) or 1
    max_gold = max((s.get("gold", 0) for s in settlements), default=1) or 1

    headers = ["聚落名称", "人口", "食物储备", "金币", "税率", "治安", "满意度", "抗议率"]
    thead = html.Thead(html.Tr(
        [html.Th(h, style=_TH_STYLE) for h in headers],
    ))

    rows: list = []
    for s in settlements:
        pop = s.get("population", 0)
        food = s.get("food", 0)
        gold = s.get("gold", 0)
        tax = s.get("tax_rate", 0)
        sec = s.get("security_level", 0)
        sat = s.get("satisfaction", 0)
        protest = s.get("protest_ratio", 0)
        name = s.get("name", "?")

        # 治安条颜色
        sec_color = (
            "#5b7fb5" if sec >= 0.6 else
            "#c9a84c" if sec >= 0.3 else "#b5342a"
        )

        row = html.Tr([
            # 聚落名称
            html.Td(
                html.Div([
                    html.Div(
                        "🏛",
                        style={
                            "width": "30px", "height": "30px",
                            "background": "linear-gradient(135deg,rgba(201,168,76,0.08),rgba(14,17,26,0.6))",
                            "borderRadius": "5px",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "border": "1px solid rgba(201,168,76,0.12)",
                            "fontSize": "14px",
                            "flexShrink": "0",
                        },
                    ),
                    html.Span(name, style={"fontWeight": "600"}),
                ], style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "10px",
                }),
                style=_TD_STYLE,
            ),
            # 人口
            html.Td(
                html.Span(
                    f"{pop:,}",
                    style={
                        "fontFamily": "JetBrains Mono, monospace",
                        "fontSize": "12.5px",
                    },
                ),
                style=_TD_STYLE,
            ),
            # 食物储备（进度条）
            html.Td(_bar(food, max_food, "#4a9e6e"), style=_TD_STYLE),
            # 金币
            html.Td(
                html.Span(
                    f"{gold:,.0f}",
                    style={
                        "color": "#c9a84c", "fontWeight": "600",
                        "fontFamily": "JetBrains Mono, monospace",
                    },
                ),
                style=_TD_STYLE,
            ),
            # 税率
            html.Td(
                html.Span(
                    f"{tax:.0%}",
                    style={
                        "padding": "3px 9px",
                        "borderRadius": "3px",
                        "fontSize": "11px",
                        "fontWeight": "600",
                        "background": "rgba(201,168,76,0.06)",
                        "border": "1px solid rgba(201,168,76,0.1)",
                        "fontFamily": "JetBrains Mono, monospace",
                    },
                ),
                style=_TD_STYLE,
            ),
            # 治安（进度条）
            html.Td(
                _bar(sec * 100, 100, sec_color),
                style=_TD_STYLE,
            ),
            # 满意度（发光圆点）
            html.Td(_sat_dot(sat), style=_TD_STYLE),
            # 抗议率
            html.Td(_protest_cell(protest), style=_TD_STYLE),
        ], style={"transition": "all 0.2s", "cursor": "default"})
        rows.append(row)

    table = html.Table(
        [thead, html.Tbody(rows)],
        style={
            "width": "100%",
            "borderCollapse": "collapse",
        },
    )

    return [html.Div(
        table,
        style={
            "background": "rgba(14,17,26,0.85)",
            "border": "1px solid rgba(201,168,76,0.10)",
            "borderRadius": "8px",
            "overflow": "hidden",
            "boxShadow": "0 4px 20px rgba(0,0,0,0.35)",
        },
    )]
