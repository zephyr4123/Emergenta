"""Dash 应用工厂 — 仪表盘布局与标签页定义。"""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from civsim.dashboard.controls import build_god_mode_controls
from civsim.dashboard.param_controls import build_param_tab
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
                            build_god_mode_controls(),
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
                                                "maxHeight": "calc(100vh - 220px)",
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


def create_app(shared_state: SharedState) -> dash.Dash:
    """创建并返回配置好的 Dash 应用实例。"""
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.DARKLY],
        title="Emergenta — AI Civilization Simulator",
        update_title=None,
        suppress_callback_exceptions=True,
    )

    app.index_string = (
        '<!DOCTYPE html><html><head>{%metas%}<title>Emergenta</title>{%favicon%}{%css%}<style>'
        # 视口锁定 — 页面不滚动，内容在面板内滚动
        'html,body{height:100%;margin:0;overflow:hidden;background-color:#1a1a2e;color:#ecf0f1}'
        '#react-entry-point{height:100%}'
        '.main-viewport{height:100vh;display:flex;flex-direction:column;overflow:hidden;padding:8px}'
        '.tab-content{flex:1;overflow-y:auto;min-height:0;padding-top:8px}'
        '.tab-pane.active{height:100%}'
        # 品牌
        '.brand-bar{display:flex;align-items:center;gap:12px;padding:6px 12px}'
        '.brand-title{font-size:26px;font-weight:800;letter-spacing:3px;'
        'background:linear-gradient(135deg,#3498db 0%,#2ecc71 100%);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0}'
        '.brand-sub{font-size:11px;color:#7f8c8d;letter-spacing:1px;margin:0}'
        '.brand-divider{flex:1}.brand-badge{font-size:10px;color:#3498db;'
        'border:1px solid #3498db;border-radius:4px;padding:2px 8px}'
        # 组件主题
        '.status-bar{background:#16213e;border-radius:8px}'
        '.status-item{text-align:center;font-weight:bold;color:#ecf0f1;font-size:13px;padding:4px}'
        '.card{background-color:#16213e!important;border-color:#2c3e6b}'
        '.card-header{background-color:#1a1a3e!important;color:#ecf0f1!important;font-weight:bold}'
        '.card-body{color:#ecf0f1}'
        '.nav-tabs .nav-link{color:#95a5a6!important}'
        '.nav-tabs .nav-link.active{color:#ecf0f1!important;background-color:#16213e!important;'
        'border-color:#3498db!important}'
        'h6{color:#ecf0f1!important}label{color:#bdc3c7!important}hr{border-color:#2c3e50}'
        '.form-control,.form-select{background-color:#2c3e50!important;'
        'color:#ecf0f1!important;border-color:#4a6785!important}'
        '.form-control::placeholder{color:#7f8c8d!important}'
        '.rc-slider-track{background-color:#3498db!important}'
        '.rc-slider-handle{border-color:#3498db!important;background-color:#3498db!important}'
        '.rc-slider-rail{background-color:#4a5568!important}'
        '.rc-slider-dot{background-color:#4a5568!important;border-color:#4a5568!important}'
        '.rc-slider-mark-text{color:#ffffff!important;font-size:11px;font-weight:500}'
        '.rc-slider-mark-text-active{color:#ffffff!important}'
        # Slider tooltip
        '.rc-slider-tooltip{z-index:9999}'
        '.rc-slider-tooltip-inner{background-color:#1a1a2e!important;'
        'color:#ffffff!important;border:1px solid #3498db!important;'
        'font-size:12px;padding:3px 8px;border-radius:4px;min-width:auto;'
        'box-shadow:0 2px 8px rgba(0,0,0,0.4)}'
        '.rc-slider-tooltip-arrow{border-top-color:#3498db!important}'
        # Slider 直接输入框 — 全局兜底所有 number input
        'input[type="number"]{background-color:#2c3e50!important;'
        'color:#ecf0f1!important;border:1px solid #4a6785!important;'
        'border-radius:4px!important;font-size:12px!important;'
        'text-align:center!important;padding:2px 4px!important}'
        'input[type="number"]:focus{border-color:#3498db!important;'
        'outline:none!important;color:#ecf0f1!important;'
        'box-shadow:0 0 0 2px rgba(52,152,219,0.3)!important}'
        # 按钮美化
        '.btn{border-radius:6px;font-weight:500;letter-spacing:0.3px;transition:all 0.2s}'
        '.btn-sm{padding:5px 14px}'
        '.btn-group .btn{border-radius:6px;margin-right:4px}'
        '.btn-danger{background:linear-gradient(135deg,#e74c3c,#c0392b)!important;border:none}'
        '.btn-success{background:linear-gradient(135deg,#27ae60,#219a52)!important;border:none}'
        '.btn-warning{background:linear-gradient(135deg,#f39c12,#d68910)!important;border:none}'
        '.btn-info{background:linear-gradient(135deg,#2980b9,#2471a3)!important;border:none;color:#fff!important}'
        '.btn-primary{background:linear-gradient(135deg,#3498db,#2c80b4)!important;border:none}'
        # 手风琴(参数面板)
        '.accordion-item{background-color:#16213e!important;border-color:#2c3e6b!important}'
        '.accordion-button{background-color:#1a1a3e!important;color:#ecf0f1!important;'
        'font-weight:600;padding:10px 16px}'
        '.accordion-button:not(.collapsed){color:#3498db!important;'
        'background-color:#16213e!important}'
        '.accordion-button::after{filter:invert(1)}'
        '.accordion-body{background-color:#16213e!important;padding:12px 16px}'
        # 造物主面板内滚动
        '.god-controls{max-height:calc(100vh - 180px);overflow-y:auto}'
        '</style></head><body>'
        '{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer>'
        '</body></html>'
    )

    app.layout = html.Div(
        [
            # 品牌栏
            html.Div(
                [
                    html.H1("EMERGENTA", className="brand-title"),
                    html.Div([
                        html.P("AI Civilization Simulator", className="brand-sub"),
                    ]),
                    html.Div(className="brand-divider"),
                    html.Span("v0.1", className="brand-badge"),
                ],
                className="brand-bar",
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
                    build_param_tab(),
                ],
                id="tabs",
                active_tab="tab-overview",
            ),
            # 自动刷新定时器
            dcc.Interval(id="interval-refresh", interval=1000, n_intervals=0),
        ],
        className="main-viewport",
    )

    # 在 app 上挂载 shared_state，供回调使用
    app.shared_state = shared_state  # type: ignore[attr-defined]
    return app
