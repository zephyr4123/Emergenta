"""参数配置面板 UI 组件。

生成第6个标签页"参数配置"，按分类以手风琴布局展示所有可调参数。
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from civsim.dashboard.param_registry import (
    CATEGORIES,
    ParamSpec,
    get_params_by_category,
)


def _build_slider_control(spec: ParamSpec) -> dbc.Col:
    """构建 slider 类型控件。"""
    min_v = spec.min_val if spec.min_val is not None else 0.0
    max_v = spec.max_val if spec.max_val is not None else 1.0
    step = spec.step if spec.step is not None else 0.01
    marks = {min_v: str(min_v), max_v: str(max_v)}
    mid = round((min_v + max_v) / 2, 4)
    if mid != min_v and mid != max_v:
        marks[mid] = str(mid)
    return dbc.Col([
        html.Label(spec.label, className="small fw-bold"),
        dcc.Slider(
            id={"type": "param-input", "path": spec.config_path},
            min=min_v, max=max_v, step=step,
            value=spec.default,
            marks=marks,
            tooltip={"placement": "bottom", "always_visible": False},
        ),
        html.Small(spec.description, className="text-muted d-block mb-2"),
    ], md=12, className="mb-2")


def _build_number_control(spec: ParamSpec) -> dbc.Col:
    """构建 number 类型控件。"""
    return dbc.Col([
        html.Label(spec.label, className="small fw-bold"),
        dbc.Input(
            id={"type": "param-input", "path": spec.config_path},
            type="number",
            value=spec.default,
            min=spec.min_val,
            max=spec.max_val,
            step=spec.step or 1,
            size="sm",
        ),
        html.Small(spec.description, className="text-muted d-block mb-2"),
    ], md=6, className="mb-2")


def _build_switch_control(spec: ParamSpec) -> dbc.Col:
    """构建 switch 类型控件。"""
    return dbc.Col([
        dbc.Switch(
            id={"type": "param-input", "path": spec.config_path},
            label=spec.label,
            value=bool(spec.default),
            className="mb-1",
        ),
        html.Small(spec.description, className="text-muted d-block mb-2"),
    ], md=6, className="mb-2")


def _build_textarea_control(spec: ParamSpec) -> dbc.Col:
    """构建 textarea 类型控件（带独立应用按钮）。"""
    return dbc.Col([
        html.Label(spec.label, className="small fw-bold"),
        dbc.Textarea(
            id={"type": "param-textarea", "path": spec.config_path},
            value=str(spec.default) if spec.default else "",
            rows=6,
            className="mb-1",
            style={"fontSize": "12px"},
        ),
        dbc.Button(
            "应用", size="sm", color="primary",
            id={"type": "param-textarea-apply", "path": spec.config_path},
            className="mb-2",
        ),
        html.Small(spec.description, className="text-muted d-block mb-2"),
    ], md=12, className="mb-2")


def _build_control(spec: ParamSpec) -> dbc.Col:
    """根据 input_type 分发构建对应控件。"""
    builders = {
        "slider": _build_slider_control,
        "number": _build_number_control,
        "switch": _build_switch_control,
        "textarea": _build_textarea_control,
    }
    builder = builders.get(spec.input_type, _build_number_control)
    return builder(spec)


def _build_category_section(category: str) -> dbc.AccordionItem:
    """构建单个分类的手风琴区域。"""
    params = get_params_by_category(category)
    rows: list[dbc.Row] = []
    current_row: list = []
    for spec in params:
        ctrl = _build_control(spec)
        if spec.input_type in ("slider", "textarea"):
            if current_row:
                rows.append(dbc.Row(current_row))
                current_row = []
            rows.append(dbc.Row([ctrl]))
        else:
            current_row.append(ctrl)
            if len(current_row) >= 2:
                rows.append(dbc.Row(current_row))
                current_row = []
    if current_row:
        rows.append(dbc.Row(current_row))

    return dbc.AccordionItem(
        title=f"{category} ({len(params)})",
        children=rows,
    )


def build_param_tab() -> dbc.Tab:
    """构建参数配置标签页。"""
    accordion = dbc.Accordion(
        [_build_category_section(cat) for cat in CATEGORIES],
        flush=True,
        start_collapsed=True,
    )

    return dbc.Tab(
        label="参数配置",
        tab_id="tab-params",
        children=dbc.Container([
            dbc.Row([
                # 左侧：参数控件
                dbc.Col([
                    html.H6("运行时参数调整"),
                    html.Small(
                        "修改后即时生效。Prompt 类参数需点击「应用」。",
                        className="text-muted d-block mb-2",
                    ),
                    accordion,
                ], md=8, style={
                    "maxHeight": "calc(100vh - 200px)",
                    "overflowY": "auto",
                }),
                # 右侧：修改日志
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("参数修改日志"),
                        dbc.CardBody(
                            html.Div(
                                id="param-change-log",
                                style={
                                    "maxHeight": "calc(100vh - 260px)",
                                    "overflowY": "auto",
                                    "fontFamily": "monospace",
                                    "fontSize": "12px",
                                    "whiteSpace": "pre-wrap",
                                },
                            ),
                        ),
                    ]),
                ], md=4),
            ]),
        ], fluid=True),
    )
