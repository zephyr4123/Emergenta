"""Dash 应用工厂 — 仪表盘布局与标签页定义。"""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from civsim.dashboard.shared_state import SharedState


def _build_status_bar() -> dbc.Row:
    """顶部状态栏：显示关键实时指标。"""
    return dbc.Row(
        [
            dbc.Col(html.Div(id="status-tick", className="status-item")),
            dbc.Col(html.Div(id="status-time", className="status-item")),
            dbc.Col(html.Div(id="status-pop", className="status-item")),
            dbc.Col(html.Div(id="status-satisfaction", className="status-item")),
            dbc.Col(html.Div(id="status-protest", className="status-item")),
            dbc.Col(html.Div(id="status-revolutions", className="status-item")),
            dbc.Col(html.Div(id="status-speed", className="status-item")),
        ],
        className="status-bar mb-3 p-2",
    )


def _build_tab_overview() -> dbc.Tab:
    return dbc.Tab(
        label="总览",
        tab_id="tab-overview",
        children=dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(id="chart-population", style={"height": "350px"}),
                            md=6,
                        ),
                        dbc.Col(
                            dcc.Graph(id="chart-resources", style={"height": "350px"}),
                            md=6,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(id="chart-satisfaction", style={"height": "350px"}),
                            md=6,
                        ),
                        dbc.Col(
                            dcc.Graph(id="chart-revolution", style={"height": "350px"}),
                            md=6,
                        ),
                    ],
                ),
            ],
            fluid=True,
        ),
    )


def _build_tab_settlements() -> dbc.Tab:
    """聚落详情标签页。"""
    return dbc.Tab(
        label="聚落",
        tab_id="tab-settlements",
        children=dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(id="chart-settlement-table", style={"height": "500px"}),
                            md=12,
                        ),
                    ],
                ),
            ],
            fluid=True,
        ),
    )


def _build_tab_diplomacy() -> dbc.Tab:
    """标签页3：外交与贸易。"""
    return dbc.Tab(
        label="外交与贸易",
        tab_id="tab-diplomacy",
        children=dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(id="chart-diplomacy", style={"height": "400px"}),
                            md=6,
                        ),
                        dbc.Col(
                            dcc.Graph(id="chart-trade-sankey", style={"height": "400px"}),
                            md=6,
                        ),
                    ],
                ),
            ],
            fluid=True,
        ),
    )


def _build_tab_adaptive() -> dbc.Tab:
    """标签页4：自适应控制器。"""
    return dbc.Tab(
        label="自适应控制",
        tab_id="tab-adaptive",
        children=dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(id="chart-adaptive", style={"height": "400px"}),
                            md=12,
                        ),
                    ],
                ),
            ],
            fluid=True,
        ),
    )


def _build_tab_god_mode() -> dbc.Tab:
    """标签页5：造物主面板。"""
    return dbc.Tab(
        label="造物主面板",
        tab_id="tab-god-mode",
        children=dbc.Container(
            [
                dbc.Row(
                    [
                        # 左侧：控制面板
                        dbc.Col(
                            _build_god_mode_controls(),
                            md=5,
                        ),
                        # 右侧：事件日志
                        dbc.Col(
                            dbc.Card(
                                [
                                    dbc.CardHeader("事件日志"),
                                    dbc.CardBody(
                                        html.Div(
                                            id="event-log",
                                            style={
                                                "height": "500px",
                                                "overflowY": "auto",
                                                "fontFamily": "monospace",
                                                "fontSize": "12px",
                                                "whiteSpace": "pre-wrap",
                                            },
                                        ),
                                    ),
                                ],
                            ),
                            md=7,
                        ),
                    ],
                ),
            ],
            fluid=True,
        ),
    )


def _build_god_mode_controls() -> dbc.Card:
    """造物主面板控制区。"""
    from civsim.dashboard.scenarios import get_preset_options

    return dbc.Card(
        [
            dbc.CardHeader("控制台"),
            dbc.CardBody(
                [
                    # 场景预设
                    html.H6("场景预设"),
                    dbc.Select(
                        id="select-scenario",
                        options=get_preset_options(),
                        placeholder="选择场景模板…",
                        className="mb-2",
                    ),
                    dbc.Button(
                        "一键应用场景",
                        id="btn-apply-scenario",
                        color="danger",
                        size="sm",
                        className="mb-2",
                    ),
                    html.Small(
                        id="scenario-description",
                        className="text-muted d-block mb-2",
                    ),
                    html.Hr(),
                    # 时间控制
                    html.H6("时间控制"),
                    dbc.ButtonGroup(
                        [
                            dbc.Button("▶ 运行", id="btn-play", color="success", size="sm"),
                            dbc.Button("⏸ 暂停", id="btn-pause", color="warning", size="sm"),
                            dbc.Button("⏭ 单步", id="btn-step", color="info", size="sm"),
                        ],
                        className="mb-2",
                    ),
                    html.Label("速度倍率"),
                    dcc.Slider(
                        id="slider-speed",
                        min=1,
                        max=20,
                        step=1,
                        value=1,
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
                        value="旱灾",
                        className="mb-2",
                    ),
                    dbc.Select(
                        id="select-target-settlement",
                        options=[],
                        placeholder="选择目标聚落",
                        className="mb-2",
                    ),
                    dbc.Button(
                        "注入事件",
                        id="btn-inject-event",
                        color="danger",
                        size="sm",
                        className="mb-3",
                    ),
                    html.Hr(),

                    # 参数调整
                    html.H6("参数调整"),
                    html.Label("目标温度"),
                    dcc.Slider(
                        id="slider-temperature",
                        min=0.0,
                        max=1.0,
                        step=0.05,
                        value=0.45,
                        marks={0: "0", 0.5: "0.5", 1: "1"},
                    ),
                    html.Label("食物再生率"),
                    dcc.Slider(
                        id="slider-food-regen",
                        min=0.0,
                        max=5.0,
                        step=0.1,
                        value=0.8,
                        marks={0: "0", 1: "1", 3: "3", 5: "5"},
                    ),
                    html.Hr(),

                    # 外交干预
                    html.H6("外交干预"),
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Input(
                                    id="input-faction-a",
                                    type="number",
                                    placeholder="阵营A",
                                    size="sm",
                                ),
                                md=4,
                            ),
                            dbc.Col(
                                dbc.Select(
                                    id="select-diplo-status",
                                    options=[
                                        {"label": "联盟", "value": "ALLIED"},
                                        {"label": "友好", "value": "FRIENDLY"},
                                        {"label": "中立", "value": "NEUTRAL"},
                                        {"label": "敌对", "value": "HOSTILE"},
                                        {"label": "战争", "value": "WAR"},
                                    ],
                                    value="ALLIED",
                                ),
                                md=4,
                            ),
                            dbc.Col(
                                dbc.Input(
                                    id="input-faction-b",
                                    type="number",
                                    placeholder="阵营B",
                                    size="sm",
                                ),
                                md=4,
                            ),
                        ],
                        className="mb-2",
                    ),
                    dbc.Button(
                        "执行外交操作",
                        id="btn-force-diplomacy",
                        color="primary",
                        size="sm",
                    ),

                    # 隐藏的 callback 输出占位
                    html.Div(id="god-mode-feedback", style={"display": "none"}),
                ],
            ),
        ],
    )


def create_app(shared_state: SharedState) -> dash.Dash:
    """创建并返回配置好的 Dash 应用实例。"""
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.DARKLY],
        title="CivSim 造物主面板",
        update_title=None,
        suppress_callback_exceptions=True,
    )

    # 自定义 CSS 修复深色主题下的可读性问题
    app.index_string = (
        '<!DOCTYPE html><html><head>{%metas%}{%title%}{%favicon%}{%css%}<style>'
        'body{background-color:#1a1a2e;color:#ecf0f1}'
        '.status-bar{background:#16213e;border-radius:8px}'
        '.status-item{text-align:center;font-weight:bold;color:#ecf0f1;font-size:14px;padding:4px}'
        '.card{background-color:#16213e!important;border-color:#2c3e6b}'
        '.card-header{background-color:#1a1a3e!important;color:#ecf0f1!important;font-weight:bold}'
        '.card-body{color:#ecf0f1}.nav-tabs .nav-link{color:#95a5a6!important}'
        '.nav-tabs .nav-link.active{color:#ecf0f1!important;background-color:#16213e!important;border-color:#3498db!important}'
        'h6{color:#ecf0f1!important}label{color:#bdc3c7!important}hr{border-color:#2c3e50}'
        '.form-control,.form-select{background-color:#2c3e50!important;color:#ecf0f1!important;border-color:#4a6785!important}'
        '.form-control::placeholder{color:#7f8c8d!important}'
        '.rc-slider-track{background-color:#3498db!important}.rc-slider-handle{border-color:#3498db!important}'
        '.rc-slider-dot{background-color:#2c3e50!important}.rc-slider-mark-text{color:#95a5a6!important}'
        '</style></head><body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>'
    )

    app.layout = dbc.Container(
        [
            # 标题
            dbc.Row(
                dbc.Col(
                    html.H3(
                        "CivSim 造物主面板",
                        className="text-center my-2",
                        style={"color": "#ecf0f1"},
                    ),
                ),
            ),

            # 状态栏
            _build_status_bar(),

            # 标签页
            dbc.Tabs(
                [
                    _build_tab_overview(),
                    _build_tab_settlements(),
                    _build_tab_diplomacy(),
                    _build_tab_adaptive(),
                    _build_tab_god_mode(),
                ],
                id="tabs",
                active_tab="tab-overview",
            ),

            # 自动刷新定时器
            dcc.Interval(
                id="interval-refresh",
                interval=1000,
                n_intervals=0,
            ),
        ],
        fluid=True,
        className="p-2",
    )

    # 在 app 上挂载 shared_state，供回调使用
    app.shared_state = shared_state  # type: ignore[attr-defined]
    return app
