"""参数配置面板回调 — 连接 UI 控件到 GodModeAction 队列。

使用 Dash pattern-matching 回调处理所有 slider/number/switch 参数，
Prompt textarea 使用独立按钮触发回调。
"""

from __future__ import annotations

import json

from dash import ALL, Input, Output, State, callback_context, no_update
from dash.exceptions import PreventUpdate

from civsim.dashboard.shared_state import (
    GodAction,
    GodModeAction,
    SharedState,
)


def _get_state(app: object) -> SharedState:
    """从 app 获取 SharedState。"""
    return app.shared_state  # type: ignore[attr-defined]


def register_param_callbacks(app: object) -> None:
    """注册参数配置面板的所有回调。

    Args:
        app: Dash 应用实例（含 shared_state 属性）。
    """
    _register_slider_number_switch(app)
    _register_textarea_apply(app)
    _register_param_log(app)


def _register_slider_number_switch(app: object) -> None:
    """注册 slider/number/switch 类型参数的 MATCH 回调。"""

    @app.callback(  # type: ignore[union-attr]
        Output("param-change-log", "children", allow_duplicate=True),
        Input({"type": "param-input", "path": ALL}, "value"),
        prevent_initial_call=True,
    )
    def _on_param_change(values: list) -> str:
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        state = _get_state(app)
        triggered = ctx.triggered[0]
        prop_id = triggered["prop_id"]
        value = triggered["value"]

        if value is None:
            raise PreventUpdate

        # 从 prop_id 解析 path: '{"path":"xxx","type":"param-input"}.value'
        try:
            id_part = prop_id.rsplit(".", 1)[0]
            id_dict = json.loads(id_part)
            path = id_dict["path"]
        except (json.JSONDecodeError, KeyError):
            raise PreventUpdate

        state.enqueue_action(GodModeAction(
            action=GodAction.SET_PARAMETER,
            params={"param_name": path, "value": value},
        ))
        return no_update


def _register_textarea_apply(app: object) -> None:
    """注册 textarea 类型参数的"应用"按钮回调。"""

    @app.callback(  # type: ignore[union-attr]
        Output("param-change-log", "children", allow_duplicate=True),
        Input({"type": "param-textarea-apply", "path": ALL}, "n_clicks"),
        State({"type": "param-textarea", "path": ALL}, "value"),
        prevent_initial_call=True,
    )
    def _on_textarea_apply(n_clicks_list: list, values: list) -> str:
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        triggered = ctx.triggered[0]
        if not triggered["value"]:
            raise PreventUpdate

        prop_id = triggered["prop_id"]
        try:
            id_part = prop_id.rsplit(".", 1)[0]
            id_dict = json.loads(id_part)
            path = id_dict["path"]
        except (json.JSONDecodeError, KeyError):
            raise PreventUpdate

        # 从 State 中找到同 path 的 textarea 值
        text_value = None
        for inp in ctx.states_list[0]:
            if inp.get("id", {}).get("path") == path:
                text_value = inp.get("value", "")
                break

        if text_value is None:
            raise PreventUpdate

        state = _get_state(app)
        state.enqueue_action(GodModeAction(
            action=GodAction.SET_PARAMETER,
            params={"param_name": path, "value": text_value},
        ))
        return no_update


def _register_param_log(app: object) -> None:
    """注册参数修改日志的定时刷新回调。"""

    @app.callback(  # type: ignore[union-attr]
        Output("param-change-log", "children"),
        Input("interval-refresh", "n_intervals"),
    )
    def _update_param_log(_n: int) -> str:
        state = _get_state(app)
        events = state.get_event_log(50)
        # 过滤参数相关事件
        param_events = [e for e in events if any(
            kw in e for kw in ("→", "已同步", "参数", "Prompt", "温度")
        )]
        if not param_events:
            return "暂无参数修改记录"
        return "\n".join(reversed(param_events[-50:]))
