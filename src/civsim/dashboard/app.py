"""Dash 应用工厂 — 仪表盘布局与标签页定义。"""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from civsim.dashboard.controls import build_god_mode_controls
from civsim.dashboard.param_controls import build_param_tab
from civsim.dashboard.shared_state import SharedState


# ── 全局 CSS（基于 Emergenta OS 设计稿）──────────────────────

_CSS = """
:root{
  --bg-deep:#0a0c10;
  --bg-panel:rgba(20,24,33,0.8);
  --accent-cyan:#00f2ff;
  --accent-green:#39FF14;
  --accent-red:#ff3e3e;
  --accent-orange:#ff9d00;
  --border:rgba(255,255,255,0.08);
  --text-main:#e2e8f0;
  --text-dim:#94a3b8;
}
*{margin:0;padding:0;box-sizing:border-box;
  font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif}
html,body{height:100%;overflow:hidden;background:var(--bg-deep);color:var(--text-main);
  background-image:radial-gradient(circle at 50% 50%,#1a1f2e 0%,#0a0c10 100%)}
#react-entry-point{height:100%}
.main-viewport{height:100vh;display:flex;flex-direction:column;overflow:hidden}

/* ── 顶部导航栏 ── */
.top-nav{height:54px;display:flex;align-items:center;padding:0 20px;
  background:rgba(0,0,0,0.4);border-bottom:1px solid var(--border);
  backdrop-filter:blur(10px);justify-content:space-between;flex-shrink:0}
.brand{font-size:20px;font-weight:900;letter-spacing:2px;
  background:linear-gradient(90deg,var(--accent-cyan),#00a2ff);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.stats-bar{display:flex;gap:32px}
.stat-item{display:flex;flex-direction:column;align-items:center}
.stat-label{font-size:9px;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px}
.stat-value{font-size:14px;font-weight:700;color:var(--accent-cyan)}

/* ── 标签页 ── */
.tab-content{flex:1;overflow-y:auto;min-height:0;padding-top:0}
.tab-pane.active{height:100%}
.nav-tabs{background:rgba(0,0,0,0.2)!important;padding:0 20px!important;
  border-bottom:1px solid var(--border)!important;gap:4px}
.nav-tabs .nav-link{color:var(--text-dim)!important;font-size:13px!important;
  padding:10px 16px!important;border:none!important;border-bottom:2px solid transparent!important;
  background:transparent!important;transition:all .25s;border-radius:0!important}
.nav-tabs .nav-link:hover{color:#fff!important}
.nav-tabs .nav-link.active{color:var(--accent-cyan)!important;
  border-bottom-color:var(--accent-cyan)!important;
  background:linear-gradient(to top,rgba(0,242,255,0.05),transparent)!important}

/* ── 面板/卡片 ── */
.card{background:var(--bg-panel)!important;border:1px solid var(--border)!important;
  border-radius:10px!important;box-shadow:0 8px 24px rgba(0,0,0,0.4)!important}
.card-header{background:rgba(255,255,255,0.03)!important;color:var(--text-main)!important;
  font-weight:600!important;font-size:13px!important;
  border-bottom:1px solid var(--border)!important;padding:12px 16px!important}
.card-body{color:var(--text-main)!important;padding:16px!important}

/* ── 状态栏（旧样式兼容移除，用 top-nav 替代） ── */
.status-bar{display:none}

/* ── 表单控件 ── */
h6{color:var(--text-main)!important;font-size:13px!important;font-weight:600!important}
label{color:var(--text-dim)!important;font-size:12px!important}
hr{border-color:var(--border)!important}
.form-control,.form-select{background:rgba(0,0,0,0.3)!important;
  color:#fff!important;border:1px solid var(--border)!important;
  border-radius:6px!important;font-size:13px!important;padding:8px 10px!important}
.form-control:focus,.form-select:focus{border-color:var(--accent-cyan)!important;
  box-shadow:0 0 0 2px rgba(0,242,255,0.15)!important}
.form-control::placeholder{color:rgba(255,255,255,0.2)!important}
input[type="number"]{background:rgba(0,0,0,0.3)!important;color:#fff!important;
  border:1px solid var(--border)!important;border-radius:4px!important;
  font-size:12px!important;text-align:center!important;padding:4px 6px!important}
input[type="number"]:focus{border-color:var(--accent-cyan)!important;
  outline:none!important;box-shadow:0 0 0 2px rgba(0,242,255,0.15)!important}

/* ── Slider ── */
.rc-slider-track{background-color:var(--accent-cyan)!important}
.rc-slider-handle{border-color:var(--accent-cyan)!important;background-color:var(--accent-cyan)!important}
.rc-slider-rail{background-color:rgba(255,255,255,0.08)!important}
.rc-slider-dot{background-color:rgba(255,255,255,0.08)!important;border-color:rgba(255,255,255,0.08)!important}
.rc-slider-mark-text{color:var(--text-dim)!important;font-size:10px!important}
.rc-slider-mark-text-active{color:#fff!important}
.rc-slider-tooltip{z-index:9999}
.rc-slider-tooltip-inner{background-color:var(--bg-deep)!important;color:#fff!important;
  border:1px solid var(--accent-cyan)!important;font-size:11px;padding:3px 8px;
  border-radius:4px;box-shadow:0 4px 12px rgba(0,0,0,0.5)}
.rc-slider-tooltip-arrow{border-top-color:var(--accent-cyan)!important}

/* ── 按钮 ── */
.btn{border-radius:6px!important;font-weight:600!important;font-size:12px!important;
  letter-spacing:0.3px;transition:all .25s!important}
.btn-sm{padding:5px 14px!important}
.btn-group .btn{border-radius:6px!important;margin-right:3px!important}
.btn-danger{background:#991b1b!important;border:none!important;color:#fff!important}
.btn-danger:hover{background:#b91c1c!important;box-shadow:0 0 12px rgba(185,28,28,0.3)!important}
.btn-success{background:#166534!important;border:none!important}
.btn-success:hover{background:#15803d!important}
.btn-warning{background:#92400e!important;border:none!important;color:#fff!important}
.btn-warning:hover{background:#b45309!important}
.btn-info{background:rgba(0,242,255,0.1)!important;border:1px solid var(--accent-cyan)!important;
  color:var(--accent-cyan)!important}
.btn-info:hover{background:rgba(0,242,255,0.2)!important}
.btn-primary{background:#334155!important;border:none!important;color:#fff!important}
.btn-primary:hover{background:#475569!important}
.btn-outline-secondary{background:rgba(255,62,62,0.1)!important;
  border:1px solid var(--accent-red)!important;color:var(--accent-red)!important;
  font-size:11px!important;padding:5px 12px!important;border-radius:4px!important}
.btn-outline-secondary:hover{background:var(--accent-red)!important;color:#fff!important;
  box-shadow:0 0 12px var(--accent-red)!important}

/* ── 手风琴（参数面板） ── */
.accordion-item{background:var(--bg-panel)!important;border:1px solid var(--border)!important}
.accordion-button{background:rgba(255,255,255,0.03)!important;color:var(--text-main)!important;
  font-weight:600!important;font-size:13px!important;padding:10px 16px!important}
.accordion-button:not(.collapsed){color:var(--accent-cyan)!important;
  background:rgba(0,242,255,0.03)!important}
.accordion-button::after{filter:invert(1)}
.accordion-body{background:var(--bg-panel)!important;padding:12px 16px!important}

/* ── 造物主面板 ── */
.god-controls{max-height:calc(100vh - 180px);overflow-y:auto}

/* ── AI 发言卡片 ── */
.speech-card{background:var(--bg-panel);border-left:3px solid var(--accent-cyan);
  border-radius:8px;padding:12px 16px;margin-bottom:8px;
  border:1px solid var(--border);border-left:3px solid var(--accent-cyan)}
.speech-card.leader{border-left-color:#a855f7}
.speech-card-header{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.speech-card-icon{font-size:16px}
.speech-card-name{font-weight:700;color:var(--text-main);font-size:13px}
.speech-card-tick{color:var(--text-dim);font-size:10px;margin-left:auto}
.speech-card-body{color:#cbd5e1;font-size:12px;line-height:1.6;
  white-space:pre-wrap;word-break:break-word}
.speech-card-summary{color:var(--text-dim);font-size:10px;margin-top:6px;
  border-top:1px solid var(--border);padding-top:6px}

/* ── 滚动条 ── */
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:10px}
::-webkit-scrollbar-track{background:transparent}
"""


# ── 布局构建 ─────────────────────────────────────────────────


def _build_top_nav() -> html.Nav:
    """顶部导航栏：品牌 + 实时指标 + 重置按钮。"""
    return html.Nav(
        [
            html.Div("EMERGENTA", className="brand"),
            html.Div(
                [
                    _stat_item("status-tick", "世界时间"),
                    _stat_item("status-time", "当前季节"),
                    _stat_item("status-pop", "存活人口"),
                    _stat_item("status-satisfaction", "满意度"),
                    _stat_item("status-protest", "抗议率"),
                    _stat_item("status-revolutions", "革命"),
                    _stat_item("status-speed", "速度"),
                ],
                className="stats-bar",
            ),
            dbc.Button(
                "重置模拟", id="btn-reset-sim",
                color="outline-secondary", size="sm",
            ),
        ],
        className="top-nav",
    )


def _stat_item(div_id: str, label: str) -> html.Div:
    """单个状态指标。"""
    return html.Div(
        [
            html.Span(label, className="stat-label"),
            html.Span("—", id=div_id, className="stat-value"),
        ],
        className="stat-item",
    )


def _build_tab_overview() -> dbc.Tab:
    return dbc.Tab(
        label="数据总览",
        tab_id="tab-overview",
        children=dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="chart-population",
                                style={"height": "350px"},
                            ),
                            md=6,
                        ),
                        dbc.Col(
                            dcc.Graph(
                                id="chart-resources",
                                style={"height": "350px"},
                            ),
                            md=6,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="chart-satisfaction",
                                style={"height": "350px"},
                            ),
                            md=6,
                        ),
                        dbc.Col(
                            dcc.Graph(
                                id="chart-revolution",
                                style={"height": "350px"},
                            ),
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
        label="聚落观察",
        tab_id="tab-settlements",
        children=dbc.Container(
            [
                html.Div(
                    id="settlement-table-html",
                    style={
                        "maxHeight": "calc(100vh - 160px)",
                        "overflowY": "auto",
                    },
                ),
            ],
            fluid=True,
        ),
    )


def _build_tab_diplomacy() -> dbc.Tab:
    """外交与贸易。"""
    return dbc.Tab(
        label="外交与贸易",
        tab_id="tab-diplomacy",
        children=dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="chart-diplomacy",
                                style={"height": "400px"},
                            ),
                            md=6,
                        ),
                        dbc.Col(
                            dcc.Graph(
                                id="chart-trade-sankey",
                                style={"height": "400px"},
                            ),
                            md=6,
                        ),
                    ],
                ),
            ],
            fluid=True,
        ),
    )


def _build_tab_adaptive() -> dbc.Tab:
    """自适应控制器。"""
    return dbc.Tab(
        label="自适应控制",
        tab_id="tab-adaptive",
        children=dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="chart-adaptive",
                                style={"height": "400px"},
                            ),
                            md=12,
                        ),
                    ],
                ),
            ],
            fluid=True,
        ),
    )


def _build_tab_live_map() -> dbc.Tab:
    """实时地图 + 马尔可夫转移滚动。"""
    return dbc.Tab(
        label="实时地图",
        tab_id="tab-live-map",
        children=dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Graph(
                                id="chart-live-map",
                                style={"height": "calc(100vh - 180px)"},
                                config={
                                    "scrollZoom": True,
                                    "displayModeBar": True,
                                    "modeBarButtonsToRemove": [
                                        "select2d", "lasso2d",
                                    ],
                                },
                            ),
                            md=8,
                        ),
                        dbc.Col(
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        "马尔可夫状态转移 (实时抽样)",
                                    ),
                                    dbc.CardBody(
                                        html.Div(
                                            id="markov-scroll",
                                            style={
                                                "maxHeight": (
                                                    "calc(100vh - 240px)"
                                                ),
                                                "overflowY": "auto",
                                            },
                                        ),
                                    ),
                                ],
                            ),
                            md=4,
                        ),
                    ],
                ),
            ],
            fluid=True,
        ),
    )


def _build_tab_speeches() -> dbc.Tab:
    """AI 发言 — 实时展示 LLM 决策发言。"""
    return dbc.Tab(
        label="AI 神经元",
        tab_id="tab-speeches",
        children=dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.ButtonGroup(
                                [
                                    dbc.Button(
                                        "全部", id="btn-speech-all",
                                        color="info", size="sm", active=True,
                                    ),
                                    dbc.Button(
                                        "镇长", id="btn-speech-governor",
                                        color="info", size="sm", outline=True,
                                    ),
                                    dbc.Button(
                                        "首领", id="btn-speech-leader",
                                        color="info", size="sm", outline=True,
                                    ),
                                ],
                            ),
                            md=12,
                            className="mb-3",
                        ),
                    ],
                ),
                html.Div(
                    id="speech-cards",
                    style={
                        "maxHeight": "calc(100vh - 210px)",
                        "overflowY": "auto",
                    },
                ),
                dcc.Store(id="speech-filter", data="all"),
            ],
            fluid=True,
        ),
    )


def _build_tab_god_mode() -> dbc.Tab:
    """造物主面板。"""
    return dbc.Tab(
        label="造物主面板",
        tab_id="tab-god-mode",
        children=dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            build_god_mode_controls(),
                            md=5,
                        ),
                        dbc.Col(
                            dbc.Card(
                                [
                                    dbc.CardHeader("实时事件日志"),
                                    dbc.CardBody(
                                        html.Div(
                                            id="event-log",
                                            style={
                                                "maxHeight": (
                                                    "calc(100vh - 200px)"
                                                ),
                                                "overflowY": "auto",
                                                "fontFamily": (
                                                    "'Fira Code','Courier New'"
                                                    ",monospace"
                                                ),
                                                "fontSize": "12px",
                                                "whiteSpace": "pre-wrap",
                                                "lineHeight": "1.8",
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


# ── 应用工厂 ─────────────────────────────────────────────────


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
        "<!DOCTYPE html><html><head>"
        "{%metas%}<title>Emergenta</title>{%favicon%}{%css%}"
        "<style>" + _CSS + "</style>"
        "</head><body>"
        "{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer>"
        "</body></html>"
    )

    app.layout = html.Div(
        [
            # 顶部导航栏
            _build_top_nav(),
            # 标签页
            dbc.Tabs(
                [
                    _build_tab_overview(),
                    _build_tab_live_map(),
                    _build_tab_settlements(),
                    _build_tab_diplomacy(),
                    _build_tab_adaptive(),
                    _build_tab_god_mode(),
                    _build_tab_speeches(),
                    build_param_tab(),
                ],
                id="tabs",
                active_tab="tab-overview",
            ),
            # 自动刷新定时器
            dcc.Interval(
                id="interval-refresh", interval=1000, n_intervals=0,
            ),
            # 参数同步存储
            dcc.Store(
                id="param-sync-store",
                data={"version": 0, "values": {}},
            ),
        ],
        className="main-viewport",
    )

    app.shared_state = shared_state  # type: ignore[attr-defined]
    return app
