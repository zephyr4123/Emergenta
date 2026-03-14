"""参数配置面板回调 — 连接 UI 控件到 GodModeAction 队列。

使用 Dash pattern-matching 回调处理所有 slider/number/switch 参数，
Prompt textarea 使用独立按钮触发回调。

参数同步机制（事件驱动）：
  服务端批量修改参数（场景预设/重置）时递增 param_version；
  前端定时检测版本号变化 → 拉取最新参数 → 推送到 UI 控件。
  对比 sync store 中的值避免反馈循环。
"""

from __future__ import annotations

import json
from typing import Any

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


def _values_equal(a: Any, b: Any) -> bool:
    """比较参数值，处理浮点精度问题。"""
    if isinstance(a, float) and isinstance(b, (int, float)):
        return abs(a - float(b)) < 1e-9
    if isinstance(b, float) and isinstance(a, (int, float)):
        return abs(float(a) - b) < 1e-9
    return a == b


def register_param_callbacks(app: object) -> None:
    """注册参数配置面板的所有回调。

    Args:
        app: Dash 应用实例（含 shared_state 属性）。
    """
    _register_param_sync(app)
    _register_slider_number_switch(app)
    _register_textarea_apply(app)
    _register_param_log(app)


# ------------------------------------------------------------------
# 参数同步（服务端 → 前端）
# ------------------------------------------------------------------


def _register_param_sync(app: object) -> None:
    """注册参数同步回调：版本号检测 + 值推送到控件。"""

    @app.callback(  # type: ignore[union-attr]
        Output("param-sync-store", "data"),
        Input("interval-refresh", "n_intervals"),
        State("param-sync-store", "data"),
    )
    def _check_param_version(
        _n: int, current_store: dict | None,
    ) -> dict:
        """O(1) 版本号检测，仅在版本变化时拉取参数快照。"""
        state = _get_state(app)
        client_ver = (
            current_store.get("version", 0) if current_store else 0
        )
        server_ver = state.param_version
        if server_ver <= client_ver:
            raise PreventUpdate
        return {
            "version": server_ver,
            "values": state.get_current_params(),
        }

    @app.callback(  # type: ignore[union-attr]
        [
            Output({"type": "param-input", "path": ALL}, "value"),
            Output({"type": "param-textarea", "path": ALL}, "value"),
        ],
        Input("param-sync-store", "data"),
        [
            State({"type": "param-input", "path": ALL}, "id"),
            State({"type": "param-textarea", "path": ALL}, "id"),
        ],
        prevent_initial_call=True,
    )
    def _push_params_to_controls(
        store_data: dict | None,
        input_ids: list[dict],
        textarea_ids: list[dict],
    ) -> tuple[list, list]:
        """将参数快照推送到所有 UI 控件。"""
        if not store_data or not store_data.get("values"):
            raise PreventUpdate

        values = store_data["values"]

        input_results: list = []
        for id_obj in input_ids:
            path = id_obj["path"]
            if path in values:
                input_results.append(values[path])
            else:
                input_results.append(no_update)

        textarea_results: list = []
        for id_obj in textarea_ids:
            path = id_obj["path"]
            if path in values:
                val = values[path]
                textarea_results.append(str(val) if val else "")
            else:
                textarea_results.append(no_update)

        return input_results, textarea_results


# ------------------------------------------------------------------
# 前端 → 服务端
# ------------------------------------------------------------------


def _register_slider_number_switch(app: object) -> None:
    """注册 slider/number/switch 类型参数的 MATCH 回调。"""

    @app.callback(  # type: ignore[union-attr]
        Output("param-change-log", "children", allow_duplicate=True),
        Input({"type": "param-input", "path": ALL}, "value"),
        State("param-sync-store", "data"),
        prevent_initial_call=True,
    )
    def _on_param_change(
        values: list, sync_data: dict | None,
    ) -> str:
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

        # 如果值与同步快照一致，说明是服务端推送触发的回调，跳过
        if sync_data:
            synced_val = sync_data.get("values", {}).get(path)
            if synced_val is not None and _values_equal(synced_val, value):
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


# ------------------------------------------------------------------
# 参数修改日志
# ------------------------------------------------------------------


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
