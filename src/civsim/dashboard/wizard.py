"""启动向导 — 仿真参数配置 + LLM 连接检测。

在启动 Dashboard 前弹出 tkinter 配置窗口，
用户可视化配置仿真规模、随机种子等参数，
并自动检测 LLM API 配置是否完整。
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox, ttk
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


# ── 颜色主题（与 Dashboard 暗色主题一致）──────────────────────

_BG = "#1a1a2e"
_BG2 = "#16213e"
_FG = "#ecf0f1"
_FG_DIM = "#95a5a6"
_ACCENT = "#3498db"
_ACCENT_HOVER = "#2980b9"
_GREEN = "#2ecc71"
_RED = "#e74c3c"
_ORANGE = "#f39c12"
_ENTRY_BG = "#2c3e50"
_BORDER = "#4a6785"


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
    """检查 LLM 配置是否完整。

    Returns:
        {"ok": bool, "api_key": str, "base_url": str, "models": dict}
    """
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    llm = raw.get("llm", {})
    api_key = llm.get("default_api_key", "")
    base_url = llm.get("default_base_url", "")
    models = llm.get("models", {})

    # 环境变量占位符视为空
    if api_key.startswith("${"):
        import os
        api_key = os.environ.get(api_key[2:-1], "")

    ok = bool(api_key) and bool(models)
    return {
        "ok": ok,
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
    """弹出 LLM 配置窗口。

    Args:
        config_path: config.yaml 路径。
        existing: 已有的 LLM 配置。

    Returns:
        True=用户完成配置，False=用户取消。
    """
    result = {"ok": False}

    win = tk.Tk()
    win.title("LLM API 配置")
    win.configure(bg=_BG)
    win.resizable(False, False)

    # 居中
    w, h = 520, 340
    sx = (win.winfo_screenwidth() - w) // 2
    sy = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{sx}+{sy}")

    # 标题
    tk.Label(
        win, text="LLM API 配置",
        bg=_BG, fg=_ACCENT, font=("", 16, "bold"),
    ).pack(pady=(16, 4))

    tk.Label(
        win,
        text="镇长和首领的决策需要 LLM 支持，请配置 API 连接信息",
        bg=_BG, fg=_FG_DIM, font=("", 11),
    ).pack(pady=(0, 12))

    # 表单区域
    form = tk.Frame(win, bg=_BG)
    form.pack(padx=30, fill="x")

    tk.Label(
        form, text="API Key", bg=_BG, fg=_FG,
        font=("", 11, "bold"), anchor="w",
    ).pack(fill="x")
    tk.Label(
        form,
        text="OpenAI / Anthropic / 中转站的 API 密钥",
        bg=_BG, fg=_FG_DIM, font=("", 9),
    ).pack(fill="x")
    api_key_var = tk.StringVar(value=existing.get("api_key", ""))
    api_entry = tk.Entry(
        form, textvariable=api_key_var, show="*",
        bg=_ENTRY_BG, fg=_FG, insertbackground=_FG,
        relief="flat", font=("", 11),
        highlightthickness=1, highlightcolor=_ACCENT,
        highlightbackground=_BORDER,
    )
    api_entry.pack(fill="x", pady=(2, 10), ipady=4)

    tk.Label(
        form, text="Base URL (可选)", bg=_BG, fg=_FG,
        font=("", 11, "bold"), anchor="w",
    ).pack(fill="x")
    tk.Label(
        form,
        text="API 端点地址，使用中转站或自部署时填写",
        bg=_BG, fg=_FG_DIM, font=("", 9),
    ).pack(fill="x")
    base_url_var = tk.StringVar(value=existing.get("base_url", ""))
    url_entry = tk.Entry(
        form, textvariable=base_url_var,
        bg=_ENTRY_BG, fg=_FG, insertbackground=_FG,
        relief="flat", font=("", 11),
        highlightthickness=1, highlightcolor=_ACCENT,
        highlightbackground=_BORDER,
    )
    url_entry.pack(fill="x", pady=(2, 16), ipady=4)

    # 按钮区
    btn_frame = tk.Frame(win, bg=_BG)
    btn_frame.pack(pady=(0, 16))

    def on_save() -> None:
        key = api_key_var.get().strip()
        if not key:
            messagebox.showwarning("提示", "请填写 API Key")
            return
        _save_llm_config(config_path, key, base_url_var.get().strip())
        result["ok"] = True
        win.destroy()

    def on_skip() -> None:
        result["ok"] = True
        win.destroy()

    tk.Button(
        btn_frame, text="保存并继续", bg=_ACCENT, fg="#fff",
        font=("", 11, "bold"), relief="flat", padx=20, pady=6,
        cursor="hand2", command=on_save,
    ).pack(side="left", padx=8)

    tk.Button(
        btn_frame, text="跳过（不启用 LLM）", bg=_BG2, fg=_FG_DIM,
        font=("", 10), relief="flat", padx=14, pady=6,
        cursor="hand2", command=on_skip,
    ).pack(side="left", padx=8)

    win.protocol("WM_DELETE_WINDOW", lambda: (
        result.update({"ok": False}), win.destroy(),
    ))
    win.mainloop()
    return result["ok"]


# ── 仿真配置向导窗口 ─────────────────────────────────────────

# 预设规模
_PRESETS: list[dict[str, Any]] = [
    {
        "name": "小型演示",
        "agents": 100,
        "desc": "100 平民 · 快速启动\n适合首次体验和功能探索",
        "color": _GREEN,
    },
    {
        "name": "中型仿真",
        "agents": 500,
        "desc": "500 平民 · 均衡体验\n涌现行为明显，运行流畅",
        "color": _ACCENT,
    },
    {
        "name": "大型仿真",
        "agents": 2000,
        "desc": "2000 平民 · 深度模拟\n贸易/外交/革命网络丰富",
        "color": _ORANGE,
    },
    {
        "name": "极限压测",
        "agents": 5000,
        "desc": "5000 平民 · 全系统压力\n需较强硬件，含真实 LLM 调用",
        "color": _RED,
    },
]


def _show_sim_setup(llm_ok: bool) -> LaunchConfig:
    """弹出仿真参数配置窗口。

    Args:
        llm_ok: LLM 是否已配置。

    Returns:
        用户配置的启动参数。
    """
    config = LaunchConfig(cancelled=True)

    win = tk.Tk()
    win.title("Emergenta — 启动配置")
    win.configure(bg=_BG)
    win.resizable(False, False)

    w, h = 560, 560
    sx = (win.winfo_screenwidth() - w) // 2
    sy = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{sx}+{sy}")

    # 标题
    title_font = tkfont.Font(family="", size=20, weight="bold")
    tk.Label(
        win, text="EMERGENTA",
        bg=_BG, fg=_ACCENT, font=title_font,
    ).pack(pady=(16, 0))
    tk.Label(
        win, text="AI Civilization Simulator",
        bg=_BG, fg=_FG_DIM, font=("", 10),
    ).pack(pady=(0, 12))

    # LLM 状态指示
    llm_text = "LLM 已配置" if llm_ok else "LLM 未配置（镇长/首领使用规则回退）"
    llm_color = _GREEN if llm_ok else _ORANGE
    tk.Label(
        win, text=f"● {llm_text}",
        bg=_BG, fg=llm_color, font=("", 10),
    ).pack(pady=(0, 8))

    # ── 规模预设 ──
    tk.Label(
        win, text="选择仿真规模",
        bg=_BG, fg=_FG, font=("", 12, "bold"), anchor="w",
    ).pack(fill="x", padx=30, pady=(4, 6))

    preset_frame = tk.Frame(win, bg=_BG)
    preset_frame.pack(fill="x", padx=30)

    agents_var = tk.IntVar(value=500)
    selected_preset = tk.IntVar(value=1)  # 默认中型

    def select_preset(idx: int) -> None:
        selected_preset.set(idx)
        agents_var.set(_PRESETS[idx]["agents"])
        # 更新按钮样式
        for i, btn in enumerate(preset_btns):
            if i == idx:
                btn.configure(
                    bg=_PRESETS[i]["color"], fg="#fff",
                    relief="solid",
                )
            else:
                btn.configure(bg=_BG2, fg=_FG_DIM, relief="flat")

    preset_btns: list[tk.Button] = []
    for i, p in enumerate(_PRESETS):
        frame = tk.Frame(preset_frame, bg=_BG)
        frame.pack(side="left", expand=True, fill="x", padx=3)

        btn = tk.Button(
            frame, text=f"{p['name']}\n{p['agents']}人",
            bg=_BG2 if i != 1 else p["color"],
            fg=_FG_DIM if i != 1 else "#fff",
            font=("", 9, "bold"),
            relief="flat" if i != 1 else "solid",
            cursor="hand2",
            width=10, height=2,
            command=lambda idx=i: select_preset(idx),
        )
        btn.pack(fill="x")
        preset_btns.append(btn)

    # 预设描述
    desc_label = tk.Label(
        win, text=_PRESETS[1]["desc"],
        bg=_BG, fg=_FG_DIM, font=("", 9),
        justify="center",
    )
    desc_label.pack(pady=(6, 0))

    def update_desc(*_args: Any) -> None:
        idx = selected_preset.get()
        desc_label.configure(text=_PRESETS[idx]["desc"])

    selected_preset.trace_add("write", update_desc)

    # ── 高级选项 ──
    sep = tk.Frame(win, bg=_BORDER, height=1)
    sep.pack(fill="x", padx=30, pady=12)

    adv = tk.Frame(win, bg=_BG)
    adv.pack(fill="x", padx=30)

    tk.Label(
        adv, text="高级选项", bg=_BG, fg=_FG,
        font=("", 11, "bold"),
    ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

    # 自定义 Agent 数
    tk.Label(
        adv, text="平民数量:", bg=_BG, fg=_FG, font=("", 10),
    ).grid(row=1, column=0, sticky="w")
    agent_entry = tk.Entry(
        adv, textvariable=agents_var, width=8,
        bg=_ENTRY_BG, fg=_FG, insertbackground=_FG,
        relief="flat", font=("", 10),
        highlightthickness=1, highlightcolor=_ACCENT,
        highlightbackground=_BORDER,
    )
    agent_entry.grid(row=1, column=1, sticky="w", padx=(4, 16), ipady=2)

    # 随机种子
    tk.Label(
        adv, text="随机种子:", bg=_BG, fg=_FG, font=("", 10),
    ).grid(row=1, column=2, sticky="w")
    seed_var = tk.StringVar(value="")
    seed_entry = tk.Entry(
        adv, textvariable=seed_var, width=8,
        bg=_ENTRY_BG, fg=_FG, insertbackground=_FG,
        relief="flat", font=("", 10),
        highlightthickness=1, highlightcolor=_ACCENT,
        highlightbackground=_BORDER,
    )
    seed_entry.grid(row=1, column=3, sticky="w", padx=(4, 0), ipady=2)

    tk.Label(
        adv, text="留空=随机", bg=_BG, fg=_FG_DIM, font=("", 8),
    ).grid(row=2, column=2, columnspan=2, sticky="w", padx=(0, 0))

    # 端口
    tk.Label(
        adv, text="端口:", bg=_BG, fg=_FG, font=("", 10),
    ).grid(row=3, column=0, sticky="w", pady=(8, 0))
    port_var = tk.IntVar(value=8050)
    port_entry = tk.Entry(
        adv, textvariable=port_var, width=8,
        bg=_ENTRY_BG, fg=_FG, insertbackground=_FG,
        relief="flat", font=("", 10),
        highlightthickness=1, highlightcolor=_ACCENT,
        highlightbackground=_BORDER,
    )
    port_entry.grid(row=3, column=1, sticky="w", padx=(4, 16), pady=(8, 0), ipady=2)

    # 镇长/首领开关
    gov_var = tk.BooleanVar(value=True)
    lead_var = tk.BooleanVar(value=True)

    style = ttk.Style()
    style.configure(
        "Dark.TCheckbutton",
        background=_BG, foreground=_FG,
    )

    gov_cb = ttk.Checkbutton(
        adv, text="启用镇长 (LLM 治理决策)",
        variable=gov_var, style="Dark.TCheckbutton",
    )
    gov_cb.grid(row=3, column=2, columnspan=2, sticky="w", pady=(8, 0))

    lead_cb = ttk.Checkbutton(
        adv, text="启用首领 (LLM 战略决策)",
        variable=lead_var, style="Dark.TCheckbutton",
    )
    lead_cb.grid(row=4, column=2, columnspan=2, sticky="w", pady=(2, 0))

    # 自适应提示
    auto_label = tk.Label(
        win,
        text="地图大小、聚落数量、首领数量将根据平民数自动计算",
        bg=_BG, fg=_FG_DIM, font=("", 9),
    )
    auto_label.pack(pady=(10, 0))

    # ── 启动按钮 ──
    btn_frame = tk.Frame(win, bg=_BG)
    btn_frame.pack(pady=(14, 16))

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
        seed_str = seed_var.get().strip()
        config.seed = int(seed_str) if seed_str else None
        config.enable_governors = gov_var.get()
        config.enable_leaders = lead_var.get()
        try:
            config.port = port_var.get()
        except tk.TclError:
            config.port = 8050
        config.cancelled = False
        win.destroy()

    start_btn = tk.Button(
        btn_frame, text="  启动仿真  ",
        bg=_ACCENT, fg="#fff",
        font=("", 13, "bold"), relief="flat",
        padx=30, pady=8, cursor="hand2",
        command=on_start,
    )
    start_btn.pack()

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
            # 重新检测
            llm_info = _check_llm_config(config_path)
            llm_ok = llm_info["ok"]

    return _show_sim_setup(llm_ok)
