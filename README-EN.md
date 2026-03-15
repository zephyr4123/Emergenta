<div align="center">

<img src="docs/images/logo.png" width="200" alt="Emergenta Logo" />

# EMERGENTA

### A Living Petri Dish for AI Civilizations

<p>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/LLM-Any_OpenAI_Compatible-00f2ff?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Framework-Mesa_3.x-10b981?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Dashboard-Plotly_Dash-ef4444?style=for-the-badge" />
  <img src="https://img.shields.io/badge/License-MIT-f59e0b?style=for-the-badge" />
</p>

<p>
<b>5,000+ Autonomous Agents · Real-time Creator Dashboard · Scenario Injection · 200+ Tunable Parameters</b>
</p>

<p>
<a href="README.md">简体中文</a> | <b>English</b>
</p>

<br/>

<img src="docs/images/hero-demo.gif" width="800" alt="Emergenta Demo" />

<br/>
<br/>

</div>

---

## What is Emergenta?

Emergenta is a **large-scale AI-driven civilization simulator**. Thousands of autonomous agents labor, trade, protest, form alliances, and wage wars in a procedurally generated 2D world — **with no scripted storylines**. All macro-level social phenomena emerge naturally from micro-level individual behaviors.

> *"Civilization-level complexity can arise from simple individual rules operating under information asymmetry within structured environments."*
>
> — [Product Documentation](docs/AI%20Civilization%20Simulator.pdf)

**Core Innovation**: A three-layer hybrid intelligence architecture — 5,000+ civilians use zero-cost Finite State Machines (FSM + Markov Chain) at the bottom, while LLM-powered governors and leaders make strategic decisions at the top. **Over 99% cost reduction compared to full-LLM simulators.**

---

## Architecture

<div align="center">
<img src="docs/images/architecture.png" width="750" alt="Three-layer Pyramid Architecture" />
</div>

<br/>

<table>
<tr>
<th align="center">Layer</th>
<th align="center">Count</th>
<th align="center">Intelligence Model</th>
<th align="center">Decision Frequency</th>
<th align="center">LLM Cost</th>
</tr>
<tr>
<td align="center"><b>Leaders</b></td>
<td align="center">2-15</td>
<td align="center">Frontier LLM</td>
<td align="center">Semi-annually</td>
<td align="center">Minimal (low volume)</td>
</tr>
<tr>
<td align="center"><b>Governors</b></td>
<td align="center">3-50</td>
<td align="center">Lightweight LLM</td>
<td align="center">Quarterly</td>
<td align="center">Low</td>
</tr>
<tr>
<td align="center"><b>Civilians</b></td>
<td align="center">100-5000+</td>
<td align="center">FSM + Markov Chain</td>
<td align="center">Every tick</td>
<td align="center"><b>Zero</b></td>
</tr>
</table>

**Information Asymmetry by Design** — Information degrades and aggregates as it moves up the hierarchy, while directives propagate downward but may be distorted by implementation. Governors cannot see individual civilian states, only aggregate statistics. Leaders may receive filtered or even falsified reports from governors. This creates genuine governance dilemmas and emergent conflicts.

---

## Emergent Phenomena

No pre-programmed storylines. The following phenomena emerge naturally from agent interactions:

| Phenomenon | Mechanism | Manifestation |
|-----------|-----------|---------------|
| **Revolution Cascades** | Granovetter threshold contagion | Protests spread from a few rebels to entire settlements; governors overthrown |
| **Trade Networks** | Supply-demand matching + trust accumulation | Spontaneous trade routes form; resources flow from rich to poor regions |
| **Geopolitical Dynamics** | LLM multi-turn negotiation | Leaders form alliances, betray, declare war — emergent geopolitics |
| **Economic Cycles** | Resource boom → population growth → depletion → collapse | Dutch Disease, hyperinflation emerge spontaneously |
| **Information Cocoons** | Selective governor reporting | Leaders kept in the dark about ground-level famine until revolution erupts |

---

## Screenshots

### Launch Wizard

One command to start. Browser opens automatically with a configuration page.

<table>
<tr>
<td align="center"><b>LLM Configured</b></td>
<td align="center"><b>First-time LLM Setup</b></td>
</tr>
<tr>
<td><img src="docs/images/launch-wizard-llm-ready.png" width="400" alt="Launch Wizard - Configured" /></td>
<td><img src="docs/images/launch-wizard-llm-not-ready.png" width="400" alt="Launch Wizard - Setup" /></td>
</tr>
</table>

### Dashboard — Creator Panel

<table>
<tr>
<td align="center"><b>Data Overview</b><br/><sub>Population · Resources · Satisfaction · Revolution Timeline</sub></td>
<td align="center"><b>Live Map</b><br/><sub>Agent Scatter + Markov Transition Scroll</sub></td>
</tr>
<tr>
<td><img src="docs/images/dashboard-overview.png" width="400" alt="Data Overview" /></td>
<td><img src="docs/images/dashboard-map.png" width="400" alt="Live Map" /></td>
</tr>
<tr>
<td align="center"><b>Settlement Rankings</b><br/><sub>Progress Bars · Glow Indicators · Color Grading</sub></td>
<td align="center"><b>Diplomacy & Trade</b><br/><sub>Diplomatic Network + Trade Sankey Diagram</sub></td>
</tr>
<tr>
<td><img src="docs/images/dashboard-settlements.png" width="400" alt="Settlement Rankings" /></td>
<td><img src="docs/images/dashboard-economy.png" width="400" alt="Diplomacy & Trade" /></td>
</tr>
<tr>
<td align="center"><b>God Mode Panel</b><br/><sub>Scenario Injection · Event Log · Time Control</sub></td>
<td align="center"><b>AI Neurons</b><br/><sub>Real-time LLM Governor/Leader Decision Reasoning</sub></td>
</tr>
<tr>
<td><img src="docs/images/dashboard-god-mode.png" width="400" alt="God Mode" /></td>
<td><img src="docs/images/dashboard-ai-speeches.png" width="400" alt="AI Neurons" /></td>
</tr>
<tr>
<td align="center"><b>Adaptive Controller</b><br/><sub>P-controller Thermostat Dynamic Tuning</sub></td>
<td align="center"><b>Parameter Config</b><br/><sub>200+ Runtime Parameters, Instant Effect</sub></td>
</tr>
<tr>
<td><img src="docs/images/dashboard-self-adjust.png" width="400" alt="Adaptive Controller" /></td>
<td><img src="docs/images/dashboard-config.png" width="400" alt="Parameter Config" /></td>
</tr>
</table>

---

## Features

<table>
<tr>
<td width="50%">

### Three-Layer AI Pyramid
5,000+ FSM civilians (zero LLM cost) + LLM governors (quarterly governance) + LLM leaders (semi-annual strategy). Over 99% cost reduction vs. full-LLM approaches.

### Creator Dashboard (God Mode)
Inject disasters in real-time (drought/plague/bandits), force diplomatic actions (alliance/war), one-click scenario presets (Dutch Disease / Information Cocoon / Apocalypse).

### Live Map + Markov Visualization
Perlin Noise procedural terrain + 5,000 agent real-time scatter plot + state coloring + random-sampled Markov transition matrix scrolling display.

</td>
<td>

### Adaptive Thermostat
P-controller dynamically adjusts system "temperature" — automatically balances protest intensity, revolution frequency, and satisfaction recovery to prevent overheating or overcooling.

### Scenario Injection Engine
Three built-in extreme scenarios (Dutch Disease / Information Cocoon / Apocalypse). One-click injection of extreme initial conditions to observe how civilizations respond to crisis.

### 200+ Tunable Parameters
From micro (hunger decay rate) to macro (revolution trigger threshold), 7 categories with 200+ parameters all adjustable at runtime with instant effect.

</td>
</tr>
</table>

---

## Quick Start

### 1. Install

```bash
# Create Conda environment
conda create -n civilization_simulator python=3.11 -y
conda activate civilization_simulator

# Install dependencies
pip install -e ".[dev]"

# Install MQTT Broker (for agent communication)
# macOS
brew install mosquitto && brew services start mosquitto
# Ubuntu/Debian
# sudo apt install mosquitto && sudo systemctl start mosquitto
# Windows
# choco install mosquitto
```

### 2. Launch

```bash
python scripts/run_dashboard.py
```

Browser opens automatically with the launch wizard → Configure API Key and model → Select simulation scale → Click launch.

> **Runs without LLM too** — Without an API Key configured, governors and leaders use rule-based fallback decisions. Core simulation functionality works fully.

### 3. Quick Launch (skip wizard)

```bash
# 500 civilians + seed 42
python scripts/run_dashboard.py --quick --agents 500 --seed 42
```

---

## Tech Stack

<div align="center">
<img src="docs/images/tech-stack.png" width="750" alt="Tech Stack" />
</div>

<br/>

| Component | Technology | Purpose |
|-----------|-----------|---------|
| ABM Framework | Mesa 3.x | Grid world, agent scheduling, data collection |
| LLM Gateway | LiteLLM | Unified OpenAI/Anthropic/any compatible API |
| Dashboard | Plotly Dash | 8-tab Web UI with real-time charts |
| Analytics DB | DuckDB | Columnar storage, efficient aggregation |
| Agent Communication | MQTT | Async message queues, P2P/broadcast |
| Config System | Pydantic | Type-safe validation of 200+ parameters |
| Map Generation | Perlin Noise | Procedural terrain (elevation/moisture → tile types) |
| Data Analysis | NumPy + Pandas | Markov matrices, emergence detection |

---

## Scenario Presets

Three extreme scenarios built into the Creator Dashboard, one-click injection:

| Scenario | Setup | Core Question |
|----------|-------|---------------|
| **Dutch Disease** | One settlement has 50,000 gold but zero food, farmland destroyed | Can wealth buy survival through trade? |
| **Information Cocoon** | 25% of settlements in extreme crisis, governors may falsify reports | Can information control prevent ground-level revolution? |
| **Apocalypse** | All settlements collapse simultaneously, 70% farmland destroyed | Can civilization survive on the brink of extinction? |

---

## Research Value

This project explores the intersection of AI, sociology, and complexity science:

- How do decentralized agents self-organize into hierarchical societies?
- What conditions trigger collective action cascades (revolutions, mass migrations)?
- How does **information asymmetry** between social layers affect governance stability?
- Can AI societies "discover" game-theoretic concepts like Nash equilibria?
- What role does individual diversity play in civilization resilience?

> For detailed architecture design, agent specifications, and emergence mechanism analysis, see the [Product Documentation (PDF)](docs/AI%20Civilization%20Simulator.pdf)

---

## Project Structure

```
emergenta/
├── scripts/
│   ├── run_dashboard.py          # Main entry: Launch Wizard + Dashboard
│   └── run_simulation.py         # CLI entry: Command-line simulation
├── src/civsim/
│   ├── world/                    # World engine (map gen, clock, tiles)
│   ├── agents/                   # Agents (civilian FSM, governor LLM, leader LLM)
│   │   └── behaviors/            # Markov chains, Granovetter threshold model
│   ├── economy/                  # Economic system (resources, settlements, trade)
│   ├── politics/                 # Political system (governance, diplomacy, revolution)
│   ├── llm/                      # LLM integration (gateway, prompts, memory, cache)
│   ├── dashboard/                # Creator Dashboard (Dash Web UI, 8 tabs)
│   ├── data/                     # Data collection (DuckDB, emergence detection)
│   └── communication/            # Agent communication (MQTT)
├── tests/                        # 800+ tests (unit/integration/e2e)
├── config.example.yaml           # Config template (200+ parameters)
└── docs/                         # Product docs + screenshots
```

---

## Configuration

Copy the config template and fill in your LLM API information:

```bash
cp config.example.yaml config.yaml
```

Or just launch — the wizard will guide you through configuration.

Supports any OpenAI-compatible API (OpenAI, Anthropic, relay stations, local deployment). Three model roles:

| Role | Purpose | Recommended Models |
|------|---------|-------------------|
| `governor` | Governor governance decisions (lightweight) | gpt-4o-mini / gemini-flash / haiku |
| `leader` | Leader strategic decisions (reasoning) | gpt-4o / sonnet / gemini-pro |
| `leader_opus` | Advanced diplomacy fallback | Can use same model as leader |

---

## License

[MIT License](LICENSE)

---

<div align="center">

### Contact

**Huang Suxiang**

[huangsuxiang5@gmail.com](mailto:huangsuxiang5@gmail.com) · QQ: 1736672988 · WeChat: 13976457218

<br/>

<sub>Emergenta — where AI civilizations emerge, evolve, and surprise.</sub>

</div>
