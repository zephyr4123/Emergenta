"""Dash 回调注册 — 连接 SharedState 数据到 UI 组件。

所有回调函数在此模块中定义并注册到 Dash app。
"""

from __future__ import annotations

from dash import Input, Output, State, callback_context, no_update
from dash.exceptions import PreventUpdate

from civsim.dashboard import charts
from civsim.dashboard.param_callbacks import register_param_callbacks
from civsim.dashboard.shared_state import (
    GodAction,
    GodModeAction,
    SharedState,
)


def register_callbacks(app: object) -> None:
    """将所有回调注册到 Dash app。

    Args:
        app: Dash 应用实例（含 shared_state 属性）。
    """
    _register_status_bar(app)
    _register_overview_charts(app)
    _register_settlement_chart(app)
    _register_diplomacy_charts(app)
    _register_adaptive_chart(app)
    _register_god_mode(app)
    _register_event_log(app)
    _register_settlement_dropdown(app)
    _register_scenario_description(app)
    register_param_callbacks(app)


def _get_state(app: object) -> SharedState:
    """从 app 获取 SharedState。"""
    return app.shared_state  # type: ignore[attr-defined]


# ------------------------------------------------------------------
# 状态栏
# ------------------------------------------------------------------

def _register_status_bar(app: object) -> None:
    @app.callback(  # type: ignore[union-attr]
        [
            Output("status-tick", "children"),
            Output("status-time", "children"),
            Output("status-pop", "children"),
            Output("status-satisfaction", "children"),
            Output("status-protest", "children"),
            Output("status-revolutions", "children"),
            Output("status-speed", "children"),
        ],
        Input("interval-refresh", "n_intervals"),
    )
    def update_status_bar(_n: int) -> tuple:
        ss = _get_state(app)
        snap = ss.get_latest()
        paused_txt = "⏸" if ss.is_paused else "▶"
        return (
            f"Tick: {snap.tick}",
            f"第{snap.year}年 {snap.season}",
            f"人口: {snap.population}",
            f"满意度: {snap.avg_satisfaction:.2f}",
            f"抗议率: {snap.protest_ratio:.1%}",
            f"革命: {snap.revolution_count}",
            f"{paused_txt} {ss.speed}x",
        )


# ------------------------------------------------------------------
# 总览标签页
# ------------------------------------------------------------------

def _register_overview_charts(app: object) -> None:
    @app.callback(  # type: ignore[union-attr]
        [
            Output("chart-population", "figure"),
            Output("chart-resources", "figure"),
            Output("chart-satisfaction", "figure"),
            Output("chart-revolution", "figure"),
        ],
        Input("interval-refresh", "n_intervals"),
    )
    def update_overview(_n: int) -> tuple:
        ss = _get_state(app)
        history = ss.get_history()
        return (
            charts.build_population_chart(history),
            charts.build_resource_chart(history),
            charts.build_satisfaction_chart(history),
            charts.build_revolution_timeline(history),
        )


# ------------------------------------------------------------------
# 聚落标签页
# ------------------------------------------------------------------

def _register_settlement_chart(app: object) -> None:
    @app.callback(  # type: ignore[union-attr]
        Output("chart-settlement-table", "figure"),
        Input("interval-refresh", "n_intervals"),
    )
    def update_settlements(_n: int) -> object:
        ss = _get_state(app)
        snap = ss.get_latest()
        return charts.build_settlement_table(snap)


# ------------------------------------------------------------------
# 外交与贸易标签页
# ------------------------------------------------------------------

def _register_diplomacy_charts(app: object) -> None:
    @app.callback(  # type: ignore[union-attr]
        [
            Output("chart-diplomacy", "figure"),
            Output("chart-trade-sankey", "figure"),
        ],
        Input("interval-refresh", "n_intervals"),
    )
    def update_diplomacy(_n: int) -> tuple:
        ss = _get_state(app)
        snap = ss.get_latest()
        diplomacy = ss.get_diplomacy_data()
        trades = ss.get_trade_routes()
        return (
            charts.build_diplomacy_network(diplomacy, snap.settlements),
            charts.build_trade_sankey(trades, snap.settlements),
        )


# ------------------------------------------------------------------
# 自适应控制器标签页
# ------------------------------------------------------------------

def _register_adaptive_chart(app: object) -> None:
    @app.callback(  # type: ignore[union-attr]
        Output("chart-adaptive", "figure"),
        Input("interval-refresh", "n_intervals"),
    )
    def update_adaptive(_n: int) -> object:
        ss = _get_state(app)
        history = ss.get_history()
        return charts.build_adaptive_chart(history)


# ------------------------------------------------------------------
# 造物主面板控制
# ------------------------------------------------------------------

def _register_god_mode(app: object) -> None:
    @app.callback(  # type: ignore[union-attr]
        Output("god-mode-feedback", "children"),
        [
            Input("btn-play", "n_clicks"),
            Input("btn-pause", "n_clicks"),
            Input("btn-step", "n_clicks"),
            Input("slider-speed", "value"),
            Input("btn-inject-event", "n_clicks"),
            Input("slider-temperature", "value"),
            Input("slider-food-regen", "value"),
            Input("btn-force-diplomacy", "n_clicks"),
            Input("btn-apply-scenario", "n_clicks"),
        ],
        [
            State("select-event", "value"),
            State("select-target-settlement", "value"),
            State("input-faction-a", "value"),
            State("select-diplo-status", "value"),
            State("input-faction-b", "value"),
            State("select-scenario", "value"),
        ],
        prevent_initial_call=True,
    )
    def handle_god_mode(
        play_clicks: int | None,
        pause_clicks: int | None,
        step_clicks: int | None,
        speed: int | None,
        inject_clicks: int | None,
        temperature: float | None,
        food_regen: float | None,
        diplo_clicks: int | None,
        scenario_clicks: int | None,
        event_name: str | None,
        target_settlement: str | None,
        faction_a: int | None,
        diplo_status: str | None,
        faction_b: int | None,
        scenario_key: str | None,
    ) -> str:
        ss = _get_state(app)
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "btn-play":
            ss.enqueue_action(GodModeAction(action=GodAction.RESUME))
        elif trigger_id == "btn-pause":
            ss.enqueue_action(GodModeAction(action=GodAction.PAUSE))
        elif trigger_id == "btn-step":
            ss.enqueue_action(GodModeAction(action=GodAction.STEP))
        elif trigger_id == "slider-speed" and speed is not None:
            ss.enqueue_action(
                GodModeAction(
                    action=GodAction.SET_SPEED,
                    params={"speed": speed},
                ),
            )
        elif trigger_id == "btn-inject-event":
            if event_name and target_settlement:
                ss.enqueue_action(
                    GodModeAction(
                        action=GodAction.INJECT_EVENT,
                        params={
                            "event_name": event_name,
                            "settlement_id": int(target_settlement),
                        },
                    ),
                )
        elif trigger_id == "slider-temperature" and temperature is not None:
            ss.enqueue_action(
                GodModeAction(
                    action=GodAction.SET_PARAMETER,
                    params={
                        "param_name": "target_temperature",
                        "value": temperature,
                    },
                ),
            )
        elif trigger_id == "slider-food-regen" and food_regen is not None:
            ss.enqueue_action(
                GodModeAction(
                    action=GodAction.SET_PARAMETER,
                    params={
                        "param_name": "food_regen",
                        "value": food_regen,
                    },
                ),
            )
        elif trigger_id == "btn-force-diplomacy":
            if faction_a is not None and faction_b is not None and diplo_status:
                ss.enqueue_action(
                    GodModeAction(
                        action=GodAction.FORCE_DIPLOMACY,
                        params={
                            "faction_a": int(faction_a),
                            "faction_b": int(faction_b),
                            "status": diplo_status,
                        },
                    ),
                )
        elif trigger_id == "btn-apply-scenario":
            if scenario_key:
                ss.enqueue_action(
                    GodModeAction(
                        action=GodAction.APPLY_SCENARIO,
                        params={"scenario_key": scenario_key},
                    ),
                )

        return ""


# ------------------------------------------------------------------
# 事件日志
# ------------------------------------------------------------------

def _register_event_log(app: object) -> None:
    @app.callback(  # type: ignore[union-attr]
        Output("event-log", "children"),
        Input("interval-refresh", "n_intervals"),
    )
    def update_event_log(_n: int) -> str:
        ss = _get_state(app)
        logs = ss.get_event_log(100)
        return "\n".join(reversed(logs))


# ------------------------------------------------------------------
# 聚落下拉框动态更新
# ------------------------------------------------------------------

def _register_settlement_dropdown(app: object) -> None:
    @app.callback(  # type: ignore[union-attr]
        Output("select-target-settlement", "options"),
        Input("interval-refresh", "n_intervals"),
    )
    def update_settlement_options(_n: int) -> list[dict]:
        ss = _get_state(app)
        snap = ss.get_latest()
        return [
            {"label": s["name"], "value": str(s["id"])}
            for s in snap.settlements
        ]


# ------------------------------------------------------------------
# 场景预设描述更新
# ------------------------------------------------------------------

def _register_scenario_description(app: object) -> None:
    @app.callback(  # type: ignore[union-attr]
        Output("scenario-description", "children"),
        Input("select-scenario", "value"),
        prevent_initial_call=True,
    )
    def update_scenario_desc(key: str | None) -> str:
        if not key:
            return ""
        from civsim.dashboard.scenarios import SCENARIO_REGISTRY

        for p in SCENARIO_REGISTRY:
            if p.key == key:
                return p.description
        return ""
