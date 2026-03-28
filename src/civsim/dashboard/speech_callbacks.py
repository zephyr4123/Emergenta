"""AI 发言标签页回调 — 实时展示 LLM 决策发言。"""

from __future__ import annotations

from dash import Input, Output, callback_context, html
from dash.exceptions import PreventUpdate

from civsim.dashboard.shared_state import SharedState


def _get_state(app: object) -> SharedState:
    """从 app 获取 SharedState。"""
    return app.shared_state  # type: ignore[attr-defined]


def register_speech_callbacks(app: object) -> None:
    """注册 AI 发言相关的 Dash 回调。

    Args:
        app: Dash 应用实例（含 shared_state 属性）。
    """
    _register_filter(app)
    _register_cards(app)


def _register_filter(app: object) -> None:
    """过滤按钮回调 — 切换全部/镇长/首领。"""

    @app.callback(  # type: ignore[union-attr]
        [
            Output("speech-filter", "data"),
            Output("btn-speech-all", "active"),
            Output("btn-speech-all", "outline"),
            Output("btn-speech-governor", "active"),
            Output("btn-speech-governor", "outline"),
            Output("btn-speech-leader", "active"),
            Output("btn-speech-leader", "outline"),
        ],
        [
            Input("btn-speech-all", "n_clicks"),
            Input("btn-speech-governor", "n_clicks"),
            Input("btn-speech-leader", "n_clicks"),
        ],
        prevent_initial_call=True,
    )
    def update_speech_filter(
        all_clicks: int | None,
        gov_clicks: int | None,
        leader_clicks: int | None,
    ) -> tuple:
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        # (filter, all_active, all_outline, gov_active, gov_outline,
        #  leader_active, leader_outline)
        if trigger_id == "btn-speech-governor":
            return "governor", False, True, True, False, False, True
        if trigger_id == "btn-speech-leader":
            return "leader", False, True, False, True, True, False
        return "all", True, False, False, True, False, True


def _register_cards(app: object) -> None:
    """发言卡片渲染回调。"""

    @app.callback(  # type: ignore[union-attr]
        Output("speech-cards", "children"),
        [
            Input("interval-refresh", "n_intervals"),
            Input("speech-filter", "data"),
        ],
    )
    def update_speech_cards(
        _n: int, filter_type: str | None,
    ) -> object:
        ss = _get_state(app)
        speeches = ss.get_speeches(30)
        ft = filter_type or "all"
        if ft != "all":
            speeches = [s for s in speeches if s.agent_type == ft]

        if not speeches:
            return html.Div(
                "等待 AI 决策...",
                style={
                    "color": "#8a8272", "textAlign": "center",
                    "padding": "40px", "fontSize": "15px",
                    "letterSpacing": "1px",
                },
            )

        cards = []
        for s in reversed(speeches):
            cards.append(_build_speech_card(s))
        return cards


def _build_speech_card(s: object) -> html.Div:
    """构建单张发言卡片。

    Args:
        s: LLMSpeech 实例。

    Returns:
        Dash html.Div 组件。
    """
    is_leader = s.agent_type == "leader"  # type: ignore[attr-defined]
    icon = "👑" if is_leader else "🏛"
    type_label = "首领" if is_leader else "镇长"
    css_class = "speech-card leader" if is_leader else "speech-card"
    return html.Div(
        [
            html.Div(
                [
                    html.Span(icon, className="speech-card-icon"),
                    html.Span(
                        f"[{type_label}] {s.agent_name}",  # type: ignore[attr-defined]
                        className="speech-card-name",
                    ),
                    html.Span(
                        f"Tick {s.tick}",  # type: ignore[attr-defined]
                        className="speech-card-tick",
                    ),
                ],
                className="speech-card-header",
            ),
            html.Div(
                s.reasoning,  # type: ignore[attr-defined]
                className="speech-card-body",
            ),
            html.Div(
                s.decision_summary,  # type: ignore[attr-defined]
                className="speech-card-summary",
            ),
        ],
        className=css_class,
    )
