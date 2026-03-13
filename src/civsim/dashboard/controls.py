"""造物主面板控制区布局组件。"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html


def build_god_mode_controls() -> dbc.Card:
    """造物主面板控制区。"""
    from civsim.dashboard.scenarios import get_preset_options

    return dbc.Card([
        dbc.CardHeader("控制台"),
        dbc.CardBody(className="god-controls", children=[
            # 场景预设
            html.H6("场景预设"),
            dbc.Select(
                id="select-scenario",
                options=get_preset_options(),
                placeholder="选择场景模板…",
                className="mb-2",
            ),
            dbc.Button(
                "一键应用场景", id="btn-apply-scenario",
                color="danger", size="sm", className="mb-2",
            ),
            html.Small(id="scenario-description", className="text-muted d-block mb-2"),
            html.Hr(),
            # 时间控制
            html.H6("时间控制"),
            dbc.ButtonGroup([
                dbc.Button("▶ 运行", id="btn-play", color="success", size="sm"),
                dbc.Button("⏸ 暂停", id="btn-pause", color="warning", size="sm"),
                dbc.Button("⏭ 单步", id="btn-step", color="info", size="sm"),
            ], className="mb-2"),
            html.Label("速度倍率"),
            dcc.Slider(
                id="slider-speed", min=1, max=20, step=1, value=1,
                marks={1: "1x", 5: "5x", 10: "10x", 20: "20x"},
            ),
            html.Hr(),
            # 事件注入
            html.H6("事件注入"),
            dbc.Select(
                id="select-event",
                options=[
                    {"label": "旱灾", "value": "旱灾"},
                    {"label": "瘟疫", "value": "瘟疫"},
                    {"label": "丰收", "value": "丰收"},
                    {"label": "流寇", "value": "流寇"},
                    {"label": "矿脉发现", "value": "矿脉发现"},
                ],
                value="旱灾", className="mb-2",
            ),
            dbc.Select(
                id="select-target-settlement", options=[],
                placeholder="选择目标聚落", className="mb-2",
            ),
            dbc.Button(
                "注入事件", id="btn-inject-event",
                color="danger", size="sm", className="mb-3",
            ),
            html.Hr(),
            # 参数调整
            html.H6("参数调整"),
            html.Label("目标温度"),
            dcc.Slider(
                id="slider-temperature", min=0.0, max=1.0, step=0.05, value=0.45,
                marks={0: "0", 0.5: "0.5", 1: "1"},
            ),
            html.Label("食物再生率"),
            dcc.Slider(
                id="slider-food-regen", min=0.0, max=5.0, step=0.1, value=0.8,
                marks={0: "0", 1: "1", 3: "3", 5: "5"},
            ),
            html.Hr(),
            # 外交干预
            html.H6("外交干预"),
            dbc.Row([
                dbc.Col(dbc.Input(
                    id="input-faction-a", type="number",
                    placeholder="阵营A", size="sm",
                ), md=4),
                dbc.Col(dbc.Select(
                    id="select-diplo-status",
                    options=[
                        {"label": "联盟", "value": "ALLIED"},
                        {"label": "友好", "value": "FRIENDLY"},
                        {"label": "中立", "value": "NEUTRAL"},
                        {"label": "敌对", "value": "HOSTILE"},
                        {"label": "战争", "value": "WAR"},
                    ],
                    value="ALLIED",
                ), md=4),
                dbc.Col(dbc.Input(
                    id="input-faction-b", type="number",
                    placeholder="阵营B", size="sm",
                ), md=4),
            ], className="mb-2"),
            dbc.Button(
                "执行外交操作", id="btn-force-diplomacy",
                color="primary", size="sm",
            ),
            # 隐藏的 callback 输出占位
            html.Div(id="god-mode-feedback", style={"display": "none"}),
        ]),
    ])
