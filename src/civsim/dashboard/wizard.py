"""启动向导 — 浏览器端仿真参数配置 + LLM 连接检测。

启动临时 HTTP 服务，在浏览器中展示配置页面。
用户提交后返回配置参数，临时服务自动关闭。
"""

from __future__ import annotations

import json
import os
import threading
import webbrowser
from dataclasses import dataclass
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import yaml


@dataclass
class LaunchConfig:
    """向导输出的启动配置。"""

    agents: int = 200
    seed: int | None = None
    enable_governors: bool = True
    enable_leaders: bool = True
    port: int = 8050
    cancelled: bool = False


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
        api_key = os.environ.get(api_key[2:-1], "")
    return {
        "ok": bool(api_key) and bool(models),
        "api_key": api_key,
        "base_url": base_url,
        "models": models,
    }


def _save_llm_config(
    config_path: Path,
    api_key: str,
    base_url: str,
    model_governor: str = "",
    model_leader: str = "",
) -> None:
    """将 LLM API 配置写回 config.yaml。"""
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if "llm" not in raw:
        raw["llm"] = {}
    raw["llm"]["default_api_key"] = api_key
    raw["llm"]["default_base_url"] = base_url

    # 更新模型名称（如果用户指定了）
    if model_governor or model_leader:
        if "models" not in raw["llm"]:
            raw["llm"]["models"] = {}
        models = raw["llm"]["models"]
        gov_model = model_governor or "gpt-4o-mini"
        lead_model = model_leader or "gpt-4o"
        models["governor"] = {
            "provider": "openai",
            "model": gov_model,
            "max_tokens": 1024,
            "temperature": 0.7,
        }
        models["leader"] = {
            "provider": "openai",
            "model": lead_model,
            "max_tokens": 2048,
            "temperature": 0.8,
        }
        models["leader_opus"] = {
            "provider": "openai",
            "model": lead_model,
            "max_tokens": 4096,
            "temperature": 0.9,
        }

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, allow_unicode=True, default_flow_style=False)


# ── HTML 页面生成 ─────────────────────────────────────────────


def _build_html(llm_ok: bool, show_llm_setup: bool) -> str:
    """生成向导 HTML 页面。"""
    llm_badge = (
        '<div class="status-badge green">'
        '<span class="status-dot"></span>LLM 已配置并就绪</div>'
        if llm_ok else
        '<div class="status-badge orange">'
        '<span class="status-dot orange"></span>'
        'LLM 未配置 — 使用规则回退</div>'
    )

    llm_section = ""
    if show_llm_setup:
        llm_section = """
        <section class="llm-setup">
            <p class="section-title">LLM API 配置 · API CONFIGURATION</p>
            <div class="config-panel">
                <div class="input-group">
                    <label>API Key</label>
                    <input type="password" name="api_key" id="api_key"
                           placeholder="OpenAI / Anthropic / 中转站密钥">
                </div>
                <div class="input-group">
                    <label>Base URL (可选，中转站/自部署时填写)</label>
                    <input type="text" name="base_url" id="base_url"
                           placeholder="https://api.openai.com/v1">
                </div>
                <div class="input-group">
                    <label>镇长模型 (轻量，每季度调用)</label>
                    <input type="text" name="model_governor" id="model_governor"
                           value="gpt-4o-mini"
                           placeholder="gpt-4o-mini / gemini-flash / haiku">
                </div>
                <div class="input-group">
                    <label>首领模型 (推理强，每半年调用)</label>
                    <input type="text" name="model_leader" id="model_leader"
                           value="gpt-4o"
                           placeholder="gpt-4o / sonnet / gemini-pro">
                </div>
                <div style="grid-column:span 2;padding-top:8px;border-top:1px solid var(--card-border);">
                    <p style="font-size:0.75rem;color:var(--text-dim);margin:0;">
                        点击下方「启动文明仿真」时自动保存到 config.yaml
                    </p>
                </div>
            </div>
        </section>
        """

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EMERGENTA - Launch</title>
<style>
:root {{
    --primary: #3b82f6;
    --primary-glow: rgba(59, 130, 246, 0.5);
    --bg: #05070a;
    --card-bg: rgba(255, 255, 255, 0.03);
    --card-border: rgba(255, 255, 255, 0.1);
    --text-main: #e2e8f0;
    --text-dim: #94a3b8;
    --accent-green: #10b981;
    --accent-orange: #f59e0b;
}}
* {{ margin:0; padding:0; box-sizing:border-box;
     font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif; }}
body {{
    background-color: var(--bg); color: var(--text-main);
    display:flex; justify-content:center; align-items:flex-start;
    min-height:100vh; overflow-y:auto;
    padding:40px 0;
    background-image:
        radial-gradient(circle at 50% 50%,rgba(59,130,246,0.08) 0%,transparent 50%),
        linear-gradient(rgba(18,18,18,0.7) 1px,transparent 1px),
        linear-gradient(90deg,rgba(18,18,18,0.7) 1px,transparent 1px);
    background-size:100% 100%,40px 40px,40px 40px;
}}
.container {{
    width:880px; padding:40px;
    background:rgba(10,12,16,0.85); backdrop-filter:blur(20px);
    border-radius:24px; border:1px solid var(--card-border);
    box-shadow:0 25px 50px -12px rgba(0,0,0,0.5);
    position:relative; z-index:10;
}}
header {{ text-align:center; margin-bottom:36px; }}
h1 {{
    font-size:2.8rem; letter-spacing:0.5rem; font-weight:800;
    background:linear-gradient(to bottom,#fff 30%,#60a5fa 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    margin-bottom:6px;
}}
.subtitle {{ color:var(--text-dim); letter-spacing:0.2rem; font-size:0.85rem; margin-bottom:18px; }}
.status-badge {{
    display:inline-flex; align-items:center; padding:5px 14px;
    border-radius:20px; font-size:0.8rem; font-weight:600;
}}
.status-badge.green {{
    background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.2); color:var(--accent-green);
}}
.status-badge.orange {{
    background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.2); color:var(--accent-orange);
}}
.status-dot {{
    width:7px; height:7px; background:var(--accent-green); border-radius:50%;
    margin-right:8px; box-shadow:0 0 8px var(--accent-green); animation:pulse 2s infinite;
}}
.status-dot.orange {{ background:var(--accent-orange); box-shadow:0 0 8px var(--accent-orange); }}
.section-title {{
    font-size:0.75rem; color:var(--text-dim); margin-bottom:14px;
    text-transform:uppercase; letter-spacing:1px;
}}
.scale-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:28px; }}
.scale-card {{
    background:var(--card-bg); border:1px solid var(--card-border);
    border-radius:14px; padding:22px 14px; text-align:center;
    cursor:pointer; transition:all .25s ease; position:relative; overflow:hidden;
}}
.scale-card:hover {{ border-color:var(--primary); background:rgba(59,130,246,0.05); transform:translateY(-3px); }}
.scale-card.active {{
    border-color:var(--primary);
    background:linear-gradient(135deg,rgba(59,130,246,0.18) 0%,transparent 100%);
    box-shadow:0 0 20px rgba(59,130,246,0.15);
}}
.scale-card.active::after {{
    content:''; position:absolute; top:0; left:0; width:100%; height:2px;
    background:var(--primary); box-shadow:0 0 8px var(--primary);
}}
.scale-num {{ font-size:1.7rem; font-weight:700; display:block; margin-bottom:3px; }}
.scale-label {{ font-size:0.85rem; font-weight:600; margin-bottom:6px; display:block; }}
.scale-desc {{ font-size:0.72rem; color:var(--text-dim); line-height:1.4; }}
.recommend-tag {{ font-size:0.68rem; color:var(--primary); margin-top:6px; display:block; }}
.config-panel {{
    background:rgba(255,255,255,0.02); border-radius:14px; padding:22px;
    border:1px solid var(--card-border);
    display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:30px;
}}
.input-group {{ display:flex; flex-direction:column; gap:6px; }}
.input-group label {{ font-size:0.8rem; color:var(--text-dim); }}
.input-group input {{
    background:rgba(0,0,0,0.3); border:1px solid var(--card-border);
    padding:10px 14px; border-radius:8px; color:white; font-size:0.95rem;
    transition:all .25s; outline:none;
}}
.input-group input:focus {{ border-color:var(--primary); box-shadow:0 0 0 2px var(--primary-glow); }}
.input-group input::placeholder {{ color:rgba(255,255,255,0.2); }}
.toggle-row {{
    display:flex; gap:28px; align-items:center; grid-column:span 2;
    padding-top:10px; border-top:1px solid var(--card-border);
}}
.cb {{ display:flex; align-items:center; cursor:pointer; font-size:0.85rem; color:var(--text-dim); gap:8px; }}
.cb input {{ display:none; }}
.cb .box {{
    width:16px; height:16px; border:2px solid var(--card-border);
    border-radius:4px; position:relative; transition:all .2s; flex-shrink:0;
}}
.cb input:checked + .box {{ background:var(--primary); border-color:var(--primary); }}
.cb input:checked + .box::after {{
    content:'✓'; position:absolute; color:white; font-size:11px; left:2px; top:-2px;
}}
.start-btn {{
    width:100%; padding:18px; background:var(--primary); color:white;
    border:none; border-radius:12px; font-size:1.15rem; font-weight:700;
    letter-spacing:4px; cursor:pointer; transition:all .25s;
    box-shadow:0 8px 25px -8px var(--primary);
}}
.start-btn:hover {{ transform:translateY(-2px); box-shadow:0 12px 35px -8px var(--primary); filter:brightness(1.1); }}
.start-btn:active {{ transform:translateY(1px); }}
.hint {{ text-align:center; margin-top:16px; color:var(--text-dim); font-size:0.78rem; }}
.llm-setup {{ margin-bottom:20px; }}
@keyframes pulse {{
    0% {{ opacity:.6; transform:scale(1); }}
    50% {{ opacity:1; transform:scale(1.2); }}
    100% {{ opacity:.6; transform:scale(1); }}
}}
.decor {{ position:fixed; width:400px; height:400px;
    background:radial-gradient(circle,var(--primary-glow) 0%,transparent 70%);
    z-index:1; filter:blur(60px); pointer-events:none; }}
</style>
</head>
<body>
<div class="decor" style="top:-100px;right:-100px;"></div>
<div class="decor" style="bottom:-100px;left:-100px;opacity:.5;"></div>

<main class="container">
<form id="wizard-form" method="POST" action="/submit">
    <header>
        <h1>Emergenta</h1>
        <p class="subtitle">AI CIVILIZATION SIMULATOR</p>
        {llm_badge}
    </header>

    {llm_section}

    <section>
        <p class="section-title">仿真规模选择 · SCALE SELECTION</p>
        <div class="scale-grid">
            <div class="scale-card" data-agents="100">
                <span class="scale-num">100</span>
                <span class="scale-label">小型演示</span>
                <p class="scale-desc">快速启动<br>初步体验文明演化</p>
            </div>
            <div class="scale-card active" data-agents="500">
                <span class="scale-num">500</span>
                <span class="scale-label">中型仿真</span>
                <p class="scale-desc">深度观察<br>社会网络关系丰富</p>
                <span class="recommend-tag">推荐</span>
            </div>
            <div class="scale-card" data-agents="2000">
                <span class="scale-num">2K</span>
                <span class="scale-label">大型仿真</span>
                <p class="scale-desc">文明兴起<br>需较高计算资源</p>
            </div>
            <div class="scale-card" data-agents="5000">
                <span class="scale-num">5K</span>
                <span class="scale-label">极限压测</span>
                <p class="scale-desc">全系统压力<br>需顶级硬件支撑</p>
            </div>
        </div>
    </section>

    <section class="config-panel">
        <div class="input-group">
            <label>平民初始数量 (Population)</label>
            <input type="number" name="agents" id="agents" value="500" min="10">
        </div>
        <div class="input-group">
            <label>随机种子 (Seed)</label>
            <input type="text" name="seed" id="seed" value="42" placeholder="留空则随机生成">
        </div>
        <div class="input-group">
            <label>访问端口 (Port)</label>
            <input type="number" name="port" id="port" value="8050">
        </div>
        <div class="input-group">
            <label>系统版本</label>
            <input type="text" value="Emergenta v1.0" disabled style="opacity:.4;">
        </div>
        <div class="toggle-row">
            <label class="cb">
                <input type="checkbox" name="governors" checked>
                <div class="box"></div>
                启用镇长 (LLM 治理)
            </label>
            <label class="cb">
                <input type="checkbox" name="leaders" checked>
                <div class="box"></div>
                启用首领 (LLM 战略)
            </label>
        </div>
    </section>

    <button type="submit" class="start-btn">启动文明仿真</button>
    <p class="hint" id="scaling-info">—</p>
</form>
</main>

<script>
const cards = document.querySelectorAll('.scale-card');
const agentsInput = document.getElementById('agents');
const infoEl = document.getElementById('scaling-info');
cards.forEach(card => {{
    card.addEventListener('click', () => {{
        cards.forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        agentsInput.value = card.dataset.agents;
        updateInfo();
    }});
}});
agentsInput.addEventListener('input', () => {{
    cards.forEach(c => c.classList.remove('active'));
    updateInfo();
}});
function updateInfo() {{
    const n = parseInt(agentsInput.value) || 100;
    const grid = Math.max(30, Math.min(200, Math.round(Math.sqrt(n) * 3.5)));
    const sett = Math.max(3, Math.min(50, Math.round(Math.sqrt(n) * 0.5)));
    const lead = Math.max(2, Math.min(15, Math.round(sett / 3)));
    const food = Math.round(400 + n * 0.6);
    infoEl.textContent = `${{grid}}x${{grid}} 地图 · ${{sett}} 聚落 · ${{lead}} 首领 · ${{food}} 食物/聚落`;
}}
updateInfo();
</script>
</body>
</html>"""


_LOADING_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Emergenta — 启动中</title>
<style>
body{background:#05070a;color:#e2e8f0;display:flex;
justify-content:center;align-items:center;height:100vh;
font-family:Inter,-apple-system,sans-serif;flex-direction:column;}
.spinner{width:40px;height:40px;border:3px solid rgba(255,255,255,.1);
border-top-color:#3b82f6;border-radius:50%;animation:spin .8s linear infinite;
margin-bottom:20px;}
@keyframes spin{to{transform:rotate(360deg)}}
h2{font-weight:600;margin-bottom:8px;}
p{color:#94a3b8;font-size:.9rem;}
</style>
</head><body>
<div class="spinner"></div>
<h2>正在初始化仿真引擎</h2>
<p>Dashboard 启动后将自动跳转...</p>
<script>setTimeout(()=>window.location='REDIRECT_URL',DELAY_MS);</script>
</body></html>"""


# ── HTTP 向导服务器 ───────────────────────────────────────────


class _WizardHandler(BaseHTTPRequestHandler):
    """处理向导 HTML 页面和表单提交。"""

    html: str = ""
    result: dict[str, Any] = {}
    config_path: Path | None = None
    dashboard_port: int = 8050

    def do_GET(self) -> None:
        """返回向导页面。"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(self.html.encode("utf-8"))

    def do_POST(self) -> None:
        """处理表单提交。"""
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        params = parse_qs(body)

        # 解析参数
        agents = int(params.get("agents", ["200"])[0])
        seed_str = params.get("seed", [""])[0].strip()
        port = int(params.get("port", ["8050"])[0])
        governors = "governors" in params
        leaders = "leaders" in params

        # 保存 LLM 配置（如果提供了）
        api_key = params.get("api_key", [""])[0].strip()
        base_url = params.get("base_url", [""])[0].strip()
        model_gov = params.get("model_governor", [""])[0].strip()
        model_lead = params.get("model_leader", [""])[0].strip()
        if api_key and self.config_path:
            _save_llm_config(
                self.config_path, api_key, base_url,
                model_gov, model_lead,
            )

        self.__class__.result = {
            "agents": agents,
            "seed": int(seed_str) if seed_str else None,
            "port": port,
            "governors": governors,
            "leaders": leaders,
        }
        self.__class__.dashboard_port = port

        # 返回加载页面（带自动跳转）
        redirect_url = f"http://localhost:{port}"
        loading = _LOADING_HTML.replace(
            "REDIRECT_URL", redirect_url,
        ).replace("DELAY_MS", "4000")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(loading.encode("utf-8"))

        # 关闭服务器（在新线程中，避免死锁）
        threading.Thread(
            target=self.server.shutdown, daemon=True,
        ).start()

    def log_message(self, format: str, *args: Any) -> None:
        """静默日志。"""
        pass


# ── 公共入口 ─────────────────────────────────────────────────


def run_wizard(wizard_port: int = 8051) -> LaunchConfig:
    """运行浏览器端启动向导。

    Args:
        wizard_port: 向导临时服务器端口。

    Returns:
        用户配置的启动参数。
    """
    config_path = _find_config_path()
    llm_ok = False
    show_llm_setup = False

    if config_path:
        llm_info = _check_llm_config(config_path)
        llm_ok = llm_info["ok"]
        show_llm_setup = not llm_ok

    html = _build_html(llm_ok, show_llm_setup)

    _WizardHandler.html = html
    _WizardHandler.result = {}
    _WizardHandler.config_path = config_path

    server = HTTPServer(("127.0.0.1", wizard_port), _WizardHandler)

    # 自动打开浏览器
    url = f"http://localhost:{wizard_port}"
    print(f"\n  启动向导已打开: {url}\n")
    webbrowser.open(url)

    # 阻塞直到用户提交
    server.serve_forever()
    server.server_close()

    result = _WizardHandler.result
    if not result:
        return LaunchConfig(cancelled=True)

    return LaunchConfig(
        agents=result.get("agents", 200),
        seed=result.get("seed"),
        enable_governors=result.get("governors", True),
        enable_leaders=result.get("leaders", True),
        port=result.get("port", 8050),
        cancelled=False,
    )
