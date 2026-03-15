"""启动向导 — 仿真参数配置 + LLM 连接检测。

在启动 Dashboard 前弹出 tkinter 配置窗口，
用户可视化配置仿真规模、随机种子等参数，
并自动检测 LLM API 配置是否完整。
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox
from typing import Any

import yaml


@dataclass
class LaunchConfig:
    """向导输出的启动配置。

    Attributes:
        agents: 初始平民数量。
        seed: 随机种子（None=随机）。
        enable_governors: 是否启用镇长。
        enable_leaders: 是否启用首领。
        port: Dashboard 端口。
        cancelled: 用户是否取消了向导。
    """

    agents: int = 200
    seed: int | None = None
    enable_governors: bool = True
    enable_leaders: bool = True
    port: int = 8050
    cancelled: bool = False


# ── 颜色主题 ─────────────────────────────────────────────────

_BG = "#0f1019"
_BG_CARD = "#171b2d"
_BG_INPUT = "#0c0e18"
_FG = "#ffffff"
_FG_DIM = "#6b7280"
_FG_LABEL = "#9ca3af"
_ACCENT = "#3b82f6"
_GREEN = "#22c55e"
_RED = "#ef4444"
_ORANGE = "#f59e0b"
_BORDER = "#1e293b"
_BORDER_INPUT = "#334155"


# ── 通用组件 ─────────────────────────────────────────────────


def _make_entry(
    parent: tk.Widget,
    var: tk.Variable,
    width: int = 10,
    show: str = "",
) -> tk.Entry:
    """创建统一风格的输入框。"""
    entry = tk.Entry(
        parent,
        textvariable=var,
        width=width,
        show=show,
        bg=_BG_INPUT,
        fg=_FG,
        insertbackground=_ACCENT,
        relief="flat",
        font=("SF Mono, Menlo, Consolas", 11),
        highlightthickness=1,
        highlightcolor=_ACCENT,
        highlightbackground=_BORDER_INPUT,
        selectbackground=_ACCENT,
        selectforeground="#fff",
    )
    entry.configure(borderwidth=0)
    return entry


def _make_btn(
    parent: tk.Widget,
    text: str,
    command: Any,
    bg: str = _ACCENT,
    fg: str = "#fff",
    font_size: int = 11,
    bold: bool = True,
    padx: int = 20,
    pady: int = 7,
) -> tk.Label:
    """创建可点击的现代按钮（用 Label 模拟，避免 tk.Button 丑陋边框）。"""
    weight = "bold" if bold else "normal"
    btn = tk.Label(
        parent,
        text=text,
        bg=bg,
        fg=fg,
        font=("", font_size, weight),
        cursor="hand2",
        padx=padx,
        pady=pady,
    )

    def on_enter(_e: tk.Event) -> None:
        btn.configure(bg=_darken(bg, 0.15))

    def on_leave(_e: tk.Event) -> None:
        btn.configure(bg=bg)

    def on_click(_e: tk.Event) -> None:
        command()

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    btn.bind("<Button-1>", on_click)
    return btn


def _darken(hex_color: str, factor: float) -> str:
    """将颜色变暗。"""
    c = hex_color.lstrip("#")
    r, g, b = int(c[:2], 16), int(c[2:4], 16), int(c[4:], 16)
    r = max(0, int(r * (1 - factor)))
    g = max(0, int(g * (1 - factor)))
    b = max(0, int(b * (1 - factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


def _center_window(win: tk.Tk, w: int, h: int) -> None:
    """将窗口居中显示。"""
    sx = (win.winfo_screenwidth() - w) // 2
    sy = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{sx}+{sy}")


# ── LLM 配置检测 ─────────────────────────────────────────────


def _find_config_path() -> Path | None:
    """查找 config.yaml 路径。"""
    candidates = [
        Path.cwd() / "config.yaml",
        Path(__file__).resolve().parent.parent.parent.parent / "config.yaml",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _check_llm_config(config_path: Path) -> dict[str, Any]:
    """检查 LLM 配置是否完整。"""
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    llm = raw.get("llm", {})
    api_key = llm.get("default_api_key", "")
    base_url = llm.get("default_base_url", "")
    models = llm.get("models", {})

    if isinstance(api_key, str) and api_key.startswith("${"):
        import os
        api_key = os.environ.get(api_key[2:-1], "")

    return {
        "ok": bool(api_key) and bool(models),
        "api_key": api_key,
        "base_url": base_url,
        "models": models,
    }


def _save_llm_config(
    config_path: Path, api_key: str, base_url: str,
) -> None:
    """将 LLM API 配置写回 config.yaml。"""
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if "llm" not in raw:
        raw["llm"] = {}
    raw["llm"]["default_api_key"] = api_key
    raw["llm"]["default_base_url"] = base_url
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, allow_unicode=True, default_flow_style=False)


# ── LLM 配置向导窗口 ─────────────────────────────────────────


def _show_llm_setup(config_path: Path, existing: dict) -> bool:
    """弹出 LLM 配置窗口。"""
    result = {"ok": False}
    win = tk.Tk()
    win.title("Emergenta")
    win.configure(bg=_BG)
    win.resizable(False, False)
    _center_window(win, 500, 360)

    # 标题
    tk.Label(
        win, text="LLM API 配置", bg=_BG, fg=_FG,
        font=("", 18, "bold"),
    ).pack(pady=(24, 4))
    tk.Label(
        win, text="镇长和首领的决策需要 LLM 支持",
        bg=_BG, fg=_FG_DIM, font=("", 11),
    ).pack(pady=(0, 16))

    # 表单卡片
    card = tk.Frame(win, bg=_BG_CARD, highlightthickness=1,
                    highlightbackground=_BORDER)
    card.pack(padx=32, fill="x")
    inner = tk.Frame(card, bg=_BG_CARD)
    inner.pack(padx=20, pady=16, fill="x")

    tk.Label(inner, text="API Key", bg=_BG_CARD, fg=_FG_LABEL,
             font=("", 10), anchor="w").pack(fill="x")
    api_key_var = tk.StringVar(value=existing.get("api_key", ""))
    _make_entry(inner, api_key_var, width=40, show="*").pack(
        fill="x", pady=(4, 12), ipady=5,
    )

    tk.Label(inner, text="Base URL  (可选，中转站/自部署时填写)",
             bg=_BG_CARD, fg=_FG_LABEL, font=("", 10),
             anchor="w").pack(fill="x")
    base_url_var = tk.StringVar(value=existing.get("base_url", ""))
    _make_entry(inner, base_url_var, width=40).pack(
        fill="x", pady=(4, 0), ipady=5,
    )

    # 按钮
    btn_row = tk.Frame(win, bg=_BG)
    btn_row.pack(pady=(20, 0))

    def on_save() -> None:
        key = api_key_var.get().strip()
        if not key:
            messagebox.showwarning("提示", "请填写 API Key")
            return
        _save_llm_config(config_path, key, base_url_var.get().strip())
        result["ok"] = True
        win.destroy()

    _make_btn(btn_row, "  保存并继续  ", on_save).pack(
        side="left", padx=6,
    )
    _make_btn(
        btn_row, "跳过", lambda: (result.update(ok=True), win.destroy()),
        bg=_BG_CARD, fg=_FG_DIM, bold=False, font_size=10,
    ).pack(side="left", padx=6)

    win.protocol("WM_DELETE_WINDOW", lambda: (
        result.update({"ok": False}), win.destroy(),
    ))
    win.mainloop()
    return result["ok"]


# ── 仿真配置向导窗口 ─────────────────────────────────────────

_PRESETS: list[dict[str, Any]] = [
    {
        "name": "小型演示",
        "agents": 100,
        "icon": "100",
        "desc": "快速启动 · 首次体验",
        "color": _GREEN,
    },
    {
        "name": "中型仿真",
        "agents": 500,
        "icon": "500",
        "desc": "涌现明显 · 推荐",
        "color": _ACCENT,
    },
    {
        "name": "大型仿真",
        "agents": 2000,
        "icon": "2K",
        "desc": "深度模拟 · 网络丰富",
        "color": _ORANGE,
    },
    {
        "name": "极限压测",
        "agents": 5000,
        "icon": "5K",
        "desc": "全系统压力 · 需强硬件",
        "color": _RED,
    },
]


def _show_sim_setup(llm_ok: bool) -> LaunchConfig:
    """弹出仿真参数配置窗口。"""
    config = LaunchConfig(cancelled=True)

    win = tk.Tk()
    win.title("Emergenta")
    win.configure(bg=_BG)
    win.resizable(False, False)
    _center_window(win, 540, 530)

    # ── 标题 ──
    tk.Label(
        win, text="EMERGENTA", bg=_BG, fg=_FG,
        font=("", 22, "bold"),
    ).pack(pady=(20, 0))
    tk.Label(
        win, text="AI Civilization Simulator",
        bg=_BG, fg=_FG_DIM, font=("", 10),
    ).pack(pady=(2, 6))

    # LLM 状态
    llm_text = "LLM 已配置" if llm_ok else "LLM 未配置 — 使用规则回退"
    llm_color = _GREEN if llm_ok else _ORANGE
    tk.Label(
        win, text=f"●  {llm_text}", bg=_BG, fg=llm_color,
        font=("", 10),
    ).pack(pady=(0, 12))

    # ── 规模预设 ──
    tk.Label(
        win, text="仿真规模", bg=_BG, fg=_FG_LABEL,
        font=("", 10), anchor="w",
    ).pack(fill="x", padx=32, pady=(0, 6))

    preset_frame = tk.Frame(win, bg=_BG)
    preset_frame.pack(fill="x", padx=32)

    agents_var = tk.IntVar(value=500)
    selected_idx = tk.IntVar(value=1)

    preset_cards: list[tk.Frame] = []
    num_labels: list[tk.Label] = []
    name_labels: list[tk.Label] = []
    desc_labels: list[tk.Label] = []

    def select_preset(idx: int) -> None:
        selected_idx.set(idx)
        agents_var.set(_PRESETS[idx]["agents"])
        for i in range(len(_PRESETS)):
            is_sel = i == idx
            c = _PRESETS[i]["color"] if is_sel else _BG_CARD
            border = _PRESETS[i]["color"] if is_sel else _BORDER
            fg_num = "#fff" if is_sel else _FG_DIM
            fg_name = "#fff" if is_sel else _FG_LABEL
            fg_desc = (
                "rgba(255,255,255,0.7)" if is_sel else _FG_DIM
            )
            preset_cards[i].configure(
                bg=c, highlightbackground=border,
            )
            num_labels[i].configure(bg=c, fg=fg_num)
            name_labels[i].configure(bg=c, fg=fg_name)
            desc_labels[i].configure(bg=c, fg=_FG_DIM)

    for i, p in enumerate(_PRESETS):
        is_default = i == 1
        bg = p["color"] if is_default else _BG_CARD
        border = p["color"] if is_default else _BORDER

        card = tk.Frame(
            preset_frame, bg=bg,
            highlightthickness=1, highlightbackground=border,
            cursor="hand2",
        )
        card.pack(side="left", expand=True, fill="both", padx=3)

        num_lbl = tk.Label(
            card, text=p["icon"], bg=bg,
            fg="#fff" if is_default else _FG_DIM,
            font=("", 18, "bold"),
        )
        num_lbl.pack(pady=(10, 0))

        n_lbl = tk.Label(
            card, text=p["name"], bg=bg,
            fg="#fff" if is_default else _FG_LABEL,
            font=("", 9, "bold"),
        )
        n_lbl.pack(pady=(2, 0))

        d_lbl = tk.Label(
            card, text=p["desc"], bg=bg, fg=_FG_DIM,
            font=("", 8), wraplength=100,
        )
        d_lbl.pack(pady=(1, 10))

        preset_cards.append(card)
        num_labels.append(num_lbl)
        name_labels.append(n_lbl)
        desc_labels.append(d_lbl)

        # 绑定点击（card + 所有子组件）
        for widget in (card, num_lbl, n_lbl, d_lbl):
            widget.bind(
                "<Button-1>", lambda _e, idx=i: select_preset(idx),
            )

    # ── 高级选项卡片 ──
    adv_card = tk.Frame(
        win, bg=_BG_CARD, highlightthickness=1,
        highlightbackground=_BORDER,
    )
    adv_card.pack(fill="x", padx=32, pady=(14, 0))

    adv_inner = tk.Frame(adv_card, bg=_BG_CARD)
    adv_inner.pack(padx=16, pady=12, fill="x")

    # 行 1: 平民数 + 种子
    row1 = tk.Frame(adv_inner, bg=_BG_CARD)
    row1.pack(fill="x", pady=(0, 8))

    tk.Label(
        row1, text="平民数量", bg=_BG_CARD, fg=_FG_LABEL,
        font=("", 10), anchor="w",
    ).pack(side="left")
    _make_entry(row1, agents_var, width=7).pack(
        side="left", padx=(6, 20), ipady=4,
    )

    tk.Label(
        row1, text="随机种子", bg=_BG_CARD, fg=_FG_LABEL,
        font=("", 10), anchor="w",
    ).pack(side="left")
    seed_var = tk.StringVar(value="")
    _make_entry(row1, seed_var, width=7).pack(
        side="left", padx=(6, 6), ipady=4,
    )
    tk.Label(
        row1, text="空=随机", bg=_BG_CARD, fg=_FG_DIM,
        font=("", 8),
    ).pack(side="left")

    # 行 2: 端口 + 开关
    row2 = tk.Frame(adv_inner, bg=_BG_CARD)
    row2.pack(fill="x")

    tk.Label(
        row2, text="端口", bg=_BG_CARD, fg=_FG_LABEL,
        font=("", 10), anchor="w",
    ).pack(side="left")
    port_var = tk.IntVar(value=8050)
    _make_entry(row2, port_var, width=7).pack(
        side="left", padx=(6, 20), ipady=4,
    )

    # 自定义开关（用 Label 模拟 toggle）
    gov_var = tk.BooleanVar(value=True)
    lead_var = tk.BooleanVar(value=True)

    def _make_toggle(
        parent: tk.Widget, text: str, var: tk.BooleanVar,
    ) -> tk.Frame:
        frame = tk.Frame(parent, bg=_BG_CARD)

        dot = tk.Label(
            frame, text="●", bg=_BG_CARD,
            fg=_GREEN, font=("", 8),
        )
        dot.pack(side="left", padx=(0, 3))

        lbl = tk.Label(
            frame, text=text, bg=_BG_CARD, fg=_FG_LABEL,
            font=("", 9), cursor="hand2",
        )
        lbl.pack(side="left")

        def toggle(_e: tk.Event | None = None) -> None:
            var.set(not var.get())
            dot.configure(fg=_GREEN if var.get() else _FG_DIM)

        lbl.bind("<Button-1>", toggle)
        dot.bind("<Button-1>", toggle)
        return frame

    _make_toggle(row2, "镇长", gov_var).pack(side="left", padx=(0, 10))
    _make_toggle(row2, "首领", lead_var).pack(side="left")

    # 提示
    tk.Label(
        win, text="地图·聚落·首领数量 根据平民数自动计算",
        bg=_BG, fg=_FG_DIM, font=("", 9),
    ).pack(pady=(10, 0))

    # ── 启动按钮 ──
    def on_start() -> None:
        try:
            n = agents_var.get()
            if n < 10:
                messagebox.showwarning("提示", "平民数量至少为 10")
                return
        except tk.TclError:
            messagebox.showwarning("提示", "请输入有效的平民数量")
            return
        config.agents = n
        s = seed_var.get().strip()
        config.seed = int(s) if s else None
        config.enable_governors = gov_var.get()
        config.enable_leaders = lead_var.get()
        try:
            config.port = port_var.get()
        except tk.TclError:
            config.port = 8050
        config.cancelled = False
        win.destroy()

    start_btn = _make_btn(
        win, "  启动仿真  ", on_start,
        font_size=14, padx=40, pady=10,
    )
    start_btn.pack(pady=(14, 16))

    win.protocol("WM_DELETE_WINDOW", win.destroy)
    win.mainloop()
    return config


# ── 公共入口 ─────────────────────────────────────────────────


def run_wizard() -> LaunchConfig:
    """运行完整启动向导流程。

    流程:
      1. 检测 config.yaml LLM 配置
      2. 如果缺失，弹出 LLM 配置窗口
      3. 弹出仿真参数配置窗口

    Returns:
        用户配置的启动参数。
    """
    config_path = _find_config_path()
    llm_ok = False

    if config_path:
        llm_info = _check_llm_config(config_path)
        llm_ok = llm_info["ok"]

        if not llm_ok:
            user_ok = _show_llm_setup(config_path, llm_info)
            if not user_ok:
                return LaunchConfig(cancelled=True)
            llm_info = _check_llm_config(config_path)
            llm_ok = llm_info["ok"]

    return _show_sim_setup(llm_ok)
