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
/* ══════════════════════════════════════════════════════════════
   EMERGENTA — Imperial Observatory Theme
   A refined dark interface with warm gold accents,
   classical typography, and atmospheric depth.
   ══════════════════════════════════════════════════════════════ */

@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=DM+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500;600&display=swap');

:root{
  --bg-deep:#07080c;
  --bg-panel:rgba(14,17,26,0.88);
  --bg-surface:rgba(20,24,36,0.65);
  --accent-gold:#c9a84c;
  --accent-gold-dim:#8b7a3e;
  --accent-gold-light:#e8d5a3;
  --accent-green:#4a9e6e;
  --accent-red:#b5342a;
  --accent-orange:#c8870d;
  --accent-purple:#8b6fb0;
  --border:rgba(201,168,76,0.10);
  --border-subtle:rgba(255,255,255,0.05);
  --text-main:#e0dace;
  --text-dim:#8a8272;
  --text-bright:#f5f0e6;
  --shadow-heavy:0 12px 40px rgba(0,0,0,0.55);
  --shadow-card:0 4px 20px rgba(0,0,0,0.35);
  --font-display:'Cormorant Garamond',Georgia,'Noto Serif SC',serif;
  --font-ui:'DM Sans','PingFang SC','Microsoft YaHei',sans-serif;
  --font-mono:'JetBrains Mono','Fira Code',monospace;
}

*{margin:0;padding:0;box-sizing:border-box;font-family:var(--font-ui)}
html,body{height:100%;overflow:hidden;background:var(--bg-deep);color:var(--text-main);
  background-image:
    radial-gradient(ellipse at 20% 0%,rgba(201,168,76,0.04) 0%,transparent 60%),
    radial-gradient(ellipse at 80% 100%,rgba(139,111,176,0.03) 0%,transparent 50%),
    radial-gradient(circle at 50% 50%,#0e111a 0%,#07080c 100%)}
#react-entry-point{height:100%}
.main-viewport{height:100vh;display:flex;flex-direction:column;overflow:hidden}

/* ── 顶部导航栏 ── */
.top-nav{height:56px;display:flex;align-items:center;padding:0 28px;
  background:linear-gradient(180deg,rgba(14,17,26,0.95) 0%,rgba(14,17,26,0.85) 100%);
  border-bottom:1px solid var(--border);
  backdrop-filter:blur(20px);justify-content:space-between;flex-shrink:0;
  box-shadow:0 1px 0 rgba(201,168,76,0.06)}
.brand{font-family:var(--font-display);font-size:22px;font-weight:600;
  letter-spacing:4px;
  background:linear-gradient(135deg,var(--accent-gold-light) 0%,var(--accent-gold) 50%,var(--accent-gold-dim) 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  text-shadow:none;position:relative}
.stats-bar{display:flex;gap:36px}
.stat-item{display:flex;flex-direction:column;align-items:center;gap:2px}
.stat-label{font-size:9px;color:var(--text-dim);text-transform:uppercase;
  letter-spacing:1.5px;font-weight:500}
.stat-value{font-family:var(--font-mono);font-size:13px;font-weight:500;
  color:var(--accent-gold-light);letter-spacing:0.5px}

/* ── 标签页 ── */
.tab-content{flex:1;overflow-y:auto;min-height:0;padding-top:0}
.tab-pane.active{height:100%}
.nav-tabs{background:rgba(10,12,18,0.6)!important;padding:0 28px!important;
  border-bottom:1px solid var(--border)!important;gap:2px}
.nav-tabs .nav-link{color:var(--text-dim)!important;font-size:12.5px!important;
  padding:11px 20px!important;border:none!important;
  border-bottom:2px solid transparent!important;
  background:transparent!important;transition:all .3s ease;border-radius:0!important;
  font-weight:500!important;letter-spacing:0.3px}
.nav-tabs .nav-link:hover{color:var(--text-main)!important}
.nav-tabs .nav-link.active{color:var(--accent-gold-light)!important;
  border-bottom-color:var(--accent-gold)!important;
  background:linear-gradient(to top,rgba(201,168,76,0.06),transparent)!important}

/* ── 面板/卡片 ── */
.card{background:var(--bg-panel)!important;
  border:1px solid var(--border)!important;
  border-radius:8px!important;box-shadow:var(--shadow-card)!important}
.card-header{background:rgba(201,168,76,0.03)!important;color:var(--text-main)!important;
  font-weight:600!important;font-size:12.5px!important;
  border-bottom:1px solid var(--border)!important;padding:13px 18px!important;
  letter-spacing:0.4px;text-transform:uppercase}
.card-body{color:var(--text-main)!important;padding:18px!important}

/* ── 状态栏 ── */
.status-bar{display:none}

/* ── 表单控件 ── */
h6{color:var(--accent-gold-light)!important;font-size:12.5px!important;
  font-weight:600!important;letter-spacing:0.4px;text-transform:uppercase}
label{color:var(--text-dim)!important;font-size:11.5px!important;font-weight:500!important}
hr{border-color:var(--border)!important;opacity:1!important}
.form-control,.form-select{background:rgba(0,0,0,0.25)!important;
  color:var(--text-main)!important;border:1px solid var(--border-subtle)!important;
  border-radius:5px!important;font-size:12.5px!important;padding:9px 12px!important;
  font-family:var(--font-ui)!important;transition:all .2s ease!important}
.form-control:focus,.form-select:focus{border-color:var(--accent-gold-dim)!important;
  box-shadow:0 0 0 2px rgba(201,168,76,0.12)!important}
.form-control::placeholder{color:rgba(232,208,163,0.2)!important}
input[type="number"]{background:rgba(0,0,0,0.25)!important;color:var(--text-main)!important;
  border:1px solid var(--border-subtle)!important;border-radius:4px!important;
  font-family:var(--font-mono)!important;font-size:12px!important;
  text-align:center!important;padding:5px 8px!important}
input[type="number"]:focus{border-color:var(--accent-gold-dim)!important;
  outline:none!important;box-shadow:0 0 0 2px rgba(201,168,76,0.12)!important}

/* ── Slider ── */
.rc-slider-track{background:linear-gradient(90deg,var(--accent-gold-dim),var(--accent-gold))!important}
.rc-slider-handle{border-color:var(--accent-gold)!important;
  background:var(--accent-gold)!important;
  box-shadow:0 0 8px rgba(201,168,76,0.3)!important}
.rc-slider-rail{background-color:rgba(255,255,255,0.06)!important}
.rc-slider-dot{background-color:rgba(255,255,255,0.06)!important;
  border-color:rgba(255,255,255,0.06)!important}
.rc-slider-mark-text{color:var(--text-dim)!important;font-size:10px!important;
  font-family:var(--font-mono)!important}
.rc-slider-mark-text-active{color:var(--accent-gold-light)!important}
.rc-slider-tooltip{z-index:9999}
.rc-slider-tooltip-inner{background-color:var(--bg-deep)!important;
  color:var(--accent-gold-light)!important;
  border:1px solid var(--accent-gold-dim)!important;
  font-family:var(--font-mono)!important;
  font-size:11px;padding:4px 10px;border-radius:4px;
  box-shadow:0 4px 16px rgba(0,0,0,0.6)}
.rc-slider-tooltip-arrow{border-top-color:var(--accent-gold-dim)!important}

/* ── 按钮 ── */
.btn{border-radius:5px!important;font-weight:600!important;font-size:11.5px!important;
  letter-spacing:0.5px;transition:all .25s ease!important;
  text-transform:uppercase;font-family:var(--font-ui)!important}
.btn-sm{padding:6px 16px!important}
.btn-group .btn{border-radius:5px!important;margin-right:3px!important}
.btn-danger{background:linear-gradient(135deg,#8b2920,#a63428)!important;
  border:none!important;color:#f5e6e4!important}
.btn-danger:hover{background:linear-gradient(135deg,#a63428,#c0392b)!important;
  box-shadow:0 4px 16px rgba(181,52,42,0.25)!important}
.btn-success{background:linear-gradient(135deg,#2d6b47,#3d8b5e)!important;
  border:none!important;color:#e0f0e8!important}
.btn-success:hover{background:linear-gradient(135deg,#3d8b5e,#4a9e6e)!important;
  box-shadow:0 4px 16px rgba(74,158,110,0.2)!important}
.btn-warning{background:linear-gradient(135deg,#8b6a10,#a67e14)!important;
  border:none!important;color:#f5ecd4!important}
.btn-warning:hover{background:linear-gradient(135deg,#a67e14,#c8960d)!important}
.btn-info{background:rgba(201,168,76,0.08)!important;
  border:1px solid var(--accent-gold-dim)!important;
  color:var(--accent-gold-light)!important}
.btn-info:hover{background:rgba(201,168,76,0.15)!important;
  box-shadow:0 0 12px rgba(201,168,76,0.12)!important}
.btn-primary{background:linear-gradient(135deg,#2a3148,#384460)!important;
  border:1px solid rgba(201,168,76,0.12)!important;color:var(--text-main)!important}
.btn-primary:hover{background:linear-gradient(135deg,#384460,#465778)!important;
  border-color:rgba(201,168,76,0.2)!important}
.btn-outline-secondary{background:rgba(181,52,42,0.08)!important;
  border:1px solid rgba(181,52,42,0.4)!important;color:#d4736b!important;
  font-size:11px!important;padding:6px 14px!important;border-radius:4px!important}
.btn-outline-secondary:hover{background:rgba(181,52,42,0.18)!important;
  border-color:rgba(181,52,42,0.6)!important;color:#e8958e!important;
  box-shadow:0 4px 16px rgba(181,52,42,0.15)!important}

/* ── 手风琴（参数面板） ── */
.accordion-item{background:var(--bg-panel)!important;
  border:1px solid var(--border)!important}
.accordion-button{background:rgba(201,168,76,0.02)!important;
  color:var(--text-main)!important;
  font-weight:600!important;font-size:12.5px!important;padding:12px 18px!important;
  letter-spacing:0.3px}
.accordion-button:not(.collapsed){color:var(--accent-gold-light)!important;
  background:rgba(201,168,76,0.05)!important}
.accordion-button::after{filter:invert(0.7) sepia(1) saturate(2) hue-rotate(10deg)}
.accordion-body{background:var(--bg-panel)!important;padding:14px 18px!important}

/* ── 造物主面板 ── */
.god-controls{max-height:calc(100vh - 180px);overflow-y:auto}

/* ── AI 发言卡片 ── */
.speech-card{background:var(--bg-panel);
  border:1px solid var(--border);
  border-left:3px solid var(--accent-gold-dim);
  border-radius:6px;padding:14px 18px;margin-bottom:10px;
  transition:all .2s ease}
.speech-card:hover{border-left-color:var(--accent-gold);
  box-shadow:0 2px 12px rgba(201,168,76,0.08)}
.speech-card.leader{border-left-color:var(--accent-purple)}
.speech-card.leader:hover{border-left-color:#a07fd0;
  box-shadow:0 2px 12px rgba(139,111,176,0.1)}
.speech-card-header{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.speech-card-icon{font-size:15px}
.speech-card-name{font-weight:600;color:var(--text-bright);font-size:12.5px;
  letter-spacing:0.3px}
.speech-card-tick{color:var(--text-dim);font-size:10px;margin-left:auto;
  font-family:var(--font-mono)}
.speech-card-body{color:var(--text-main);font-size:12px;line-height:1.7;
  white-space:pre-wrap;word-break:break-word;opacity:0.85}
.speech-card-summary{color:var(--text-dim);font-size:10.5px;margin-top:8px;
  border-top:1px solid var(--border);padding-top:8px;
  font-style:italic;letter-spacing:0.2px}

/* ── 滚动条 ── */
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-thumb{background:rgba(201,168,76,0.15);border-radius:10px}
::-webkit-scrollbar-thumb:hover{background:rgba(201,168,76,0.25)}
::-webkit-scrollbar-track{background:transparent}

/* ── 全局微调 ── */
.container-fluid{padding:16px 20px!important}
.text-muted{color:var(--text-dim)!important}
.small,small{font-size:11px!important;color:var(--text-dim)!important}
.mb-2{margin-bottom:0.6rem!important}
.mb-3{margin-bottom:1rem!important}
.w-100{width:100%!important}
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
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
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
