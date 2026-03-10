<div align="center">

# Emergenta

### A Hybrid LLM-Driven Civilization Simulator

<p>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/LLM-Claude_Opus/Sonnet/Haiku-D97757?style=for-the-badge&logo=anthropic&logoColor=white" />
  <img src="https://img.shields.io/badge/Framework-Mesa_3.x-2ECC71?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Status-Active_Development-FF6B35?style=for-the-badge" />
</p>

<p><i>A cost-efficient framework for macroscopic social emergence.</i></p>

<p>
告别全量大模型昂贵的 Token 消耗！本项目创新性地采用了<br/>
<b>"底层有限状态机 (FSM) + 中层聚合数据 + 顶层 LLM 战略决策"</b> 的三层金字塔架构。<br/>
单次模拟并发 <b>1000+</b> 智能体，完美推演通货膨胀、信息茧房与地缘博弈等极端社会场景。
</p>

<br/>

</div>

---

## Architecture

<table>
<tr>
<td width="60%">

```
         ┌─────────────────────────────┐
         │     Leader Layer (3-8)      │
         │    Claude Opus / Sonnet     │
         │  Diplomacy · War · Strategy │
         ├─────────────────────────────┤
        ╱│    Governor Layer (20-50)   │╲
       ╱ │    Claude Haiku / Sonnet    │ ╲
      ╱  │   Tax · Security · Policy  │  ╲
     ├───┴─────────────────────────────┴───┤
     │       Civilian Layer (1000+)        │
     │       FSM + Markov Chains           │
     │  Work · Trade · Protest · Fight     │
     └─────────────────────────────────────┘
```

</td>
<td>

**Why this design?**

Traditional LLM agent simulators call an LLM for every agent per tick — 1000 agents = thousands of API calls.

Our approach:

| Layer | Agents | LLM Cost |
|-------|--------|----------|
| Civilians | 1000+ | **Zero** (FSM) |
| Governors | 20-50 | Haiku, per season |
| Leaders | 3-8 | Opus, per year |

**Result: 99%+ cost reduction** while preserving macroscopic emergence.

</td>
</tr>
</table>

---

## Tech Stack

<table>
<tr>
  <td align="center" width="120"><b>Mesa 3.x</b><br/><sub>ABM Framework</sub></td>
  <td align="center" width="120"><b>LiteLLM</b><br/><sub>LLM Gateway</sub></td>
  <td align="center" width="120"><b>DuckDB</b><br/><sub>Analytics DB</sub></td>
  <td align="center" width="120"><b>MQTT</b><br/><sub>Agent Comms</sub></td>
  <td align="center" width="120"><b>Perlin Noise</b><br/><sub>Map Generation</sub></td>
  <td align="center" width="120"><b>Pydantic</b><br/><sub>Config System</sub></td>
</tr>
</table>

---

## Quick Start

```bash
# 1. Create Conda environment
conda create -n civilization_simulator python=3.11 -y
conda activate civilization_simulator

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Configure API Key
cp .env.example .env
# Edit .env and fill in ANTHROPIC_API_KEY

# 4. Run simulation
python scripts/run_simulation.py --ticks 200 --civilians 100

# 5. Run extreme scenario stress tests
python scripts/run_extreme_scenarios.py
```

---

## Stress Test Results: 9 Extreme Scenarios

<div align="center">
<table>
<tr><th colspan="3">All 9/9 Scenarios Passed</th></tr>
<tr>
  <th>Scenario</th>
  <th>Ticks</th>
  <th>Key Outcome</th>
</tr>
<tr><td>Famine Crisis</td><td>300</td><td>3 revolutions triggered</td></tr>
<tr><td>Resource Inequality</td><td>200</td><td>Trade network emerged</td></tr>
<tr><td>Tyranny</td><td>400</td><td>4 revolutions, self-correction</td></tr>
<tr><td>Forced War</td><td>600</td><td>War → Peace via LLM diplomacy</td></tr>
<tr><td>Apocalypse</td><td>200</td><td>75% population recovered</td></tr>
<tr><td>Resource Curse</td><td>300</td><td>Wealthy settlement survived via trade</td></tr>
<tr><td>Information Cocoon</td><td>250</td><td>Revolution despite "perfect" reports</td></tr>
<tr><td>Proxy War</td><td>400</td><td>Neutral faction profited from war</td></tr>
<tr><td>Hyperinflation</td><td>300</td><td>7 trade network emergences</td></tr>
</table>
</div>

<br/>

<details>
<summary><h3>1. Famine Crisis — 饥荒危机</h3></summary>

> **Extreme starvation + high taxes + low security → mass protests → revolution**

| Parameter | Value |
|-----------|-------|
| Civilians | 200 |
| Initial Food | 50 (near zero) |
| Tax Rate | 0.6 |
| Security | 0.15 |

**Results:**
- Satisfaction dropped to **0** within 30 ticks
- Peak protest rate: **34%**
- **3 revolutions** triggered at ticks 33, 109, 187
- Post-revolution: tax rate auto-reset to 0.15, society gradually stabilized

</details>

<details>
<summary><h3>2. Resource Inequality — 资源极度不均</h3></summary>

> **3 wealthy settlements vs 3 impoverished settlements → trade emergence**

| Parameter | Value |
|-----------|-------|
| Settlements | 6 (3 rich, 3 poor) |
| Rich Food | 3,000 |
| Poor Food | 10 |

**Results:**
- Trade network spontaneously formed
- Trade volume grew steadily to **384**
- Resources redistributed through trade; poor settlements survived

</details>

<details>
<summary><h3>3. Tyranny — 高压统治</h3></summary>

> **Tax 0.8 + Security 0.9 → can suppression hold?**

| Parameter | Value |
|-----------|-------|
| Civilians | 200 |
| Tax Rate | 0.8 |
| Security Level | 0.9 |

**Results:**
- **4 revolutions** triggered, each reducing security by 0.4
- Final satisfaction recovered to **0.711**
- System self-corrected through revolutionary cycles

</details>

<details>
<summary><h3>4. Forced War — 强制战争</h3></summary>

> **Manual war declaration → trade blockade → economic decline → peace**

| Parameter | Value |
|-----------|-------|
| Settlements | 6 across 2 factions |
| War Start | Tick 10 |

**Results:**
- War lasted **490 ticks**, then shifted to **FRIENDLY** status
- 1 revolution during wartime
- LLM leaders actively pushed for diplomatic resolution

</details>

<details>
<summary><h3>5. Apocalypse — 末日生存</h3></summary>

> **All resources zeroed → system collapse → recovery observation**

| Parameter | Value |
|-----------|-------|
| Civilians | 300 |
| All Food | 5 per settlement |

**Results:**
- Population dropped to **226** (25% loss), then recovered to **781**
- Revolution at tick 76 overthrew high-tax policy
- Post-revolution economic recovery

</details>

<details>
<summary><h3>6. Resource Curse (Dutch Disease) — 资源诅咒</h3></summary>

> **50,000 gold but zero farmland — will the richest settlement starve?**

| Parameter | Value |
|-----------|-------|
| Rich Settlement Gold | 50,000 |
| Rich Settlement Food | 0 |
| Farmland Fertility | 0 (destroyed) |

**Results:**
- Rich settlement **survived** by purchasing food through trade
- Trade volume grew to **3,030**
- **10 trade network emergence events** detected
- Wealth flowed to food-producing regions

</details>

<details>
<summary><h3>7. Information Cocoon — 信息茧房</h3></summary>

> **Governor always reports "0% protests, 100% satisfaction" — leader is blind**

| Parameter | Value |
|-----------|-------|
| Lying Settlement Food | 10 |
| Tax Rate | 0.6 |
| Governor Prompt | "Always report perfect conditions" |

**Results:**
- Real protest rate peaked at **50.8%**
- Revolution triggered at **tick 37**
- Leader failed to intervene due to falsified reports
- Validated the information cocoon effect

</details>

<details>
<summary><h3>8. Proxy War — 代理人战争</h3></summary>

> **Faction A vs B at war, Faction C is a wealthy neutral — will C profit?**

| Parameter | Value |
|-----------|-------|
| Factions | 3 (A fights B, C neutral) |
| Faction C Gold | 20,000+ |

**Results:**
- Faction C gold: 20,508 → **20,987** (+479)
- C remained neutral throughout
- C profited through continued trade during the conflict

</details>

<details>
<summary><h3>9. Hyperinflation — 通货膨胀</h3></summary>

> **50,000 gold injected + food production halved → stagflation**

| Parameter | Value |
|-----------|-------|
| Gold per Settlement | 50,000 |
| Food Production | 50% of normal |

**Results:**
- Average protest rate: **30.1%**
- No revolution (food was still sufficient)
- **7 trade network emergences** — excess gold drove trade activity

</details>

---

## Core Algorithms

<table>
<tr>
<td width="50%">

### Markov State Transition

Each civilian has **7 states** with personality-based transition matrices (Compliant / Neutral / Rebellious), dynamically adjusted by:

```python
# Hunger effect
P(work→protest) += 0.15 * hunger

# Tax effect
P(work→protest) += 0.12 * tax_rate

# Security effect
P(protest→fight) += 0.15 * insecurity

# Granovetter threshold contagion
if neighbors_protesting >= threshold:
    P(any→protest) += 0.40  # mass revolt
```

</td>
<td>

### Revolution Mechanism

**Trigger conditions** (sustained for 15 ticks):
- Protest rate >= 30%
- Avg satisfaction <= 30%

**Consequences:**
- Tax rate → 0.15
- Security level −0.4
- Gold reserves halved
- Governor dismissed
- 60-tick cooldown

**Self-correction loop:**
> High tax → Protests → Revolution → Tax reset → Recovery → Stability

</td>
</tr>
</table>

---

## Project Structure

```
src/civsim/
├── world/            # World engine (map gen, clock, tiles)
├── agents/           # Agents (Civilian FSM, Governor LLM, Leader Opus)
│   └── behaviors/    # Markov chains, Granovetter threshold model
├── economy/          # Economy (resources, settlements, trade)
├── politics/         # Politics (governance, diplomacy, revolution)
├── llm/              # LLM integration (gateway, prompts, memory, cache)
├── communication/    # Communication (MQTT broker)
├── data/             # Data (collector, DuckDB, emergence detection)
└── visualization/    # Visualization (map renderer, dashboard)
```

---

## Roadmap

<table>
<tr><td>&#9745;</td><td><b>Phase 0</b></td><td>Environment setup & project architecture</td></tr>
<tr><td>&#9745;</td><td><b>Phase 1</b></td><td>World engine MVP — map + resources + Markov civilians</td></tr>
<tr><td>&#9745;</td><td><b>Phase 2</b></td><td>LLM Governor layer — Haiku/Sonnet governance decisions</td></tr>
<tr><td>&#9745;</td><td><b>Phase 3</b></td><td>Leader layer & emergence — diplomacy / trade / revolution / war</td></tr>
<tr><td>&#9744;</td><td><b>Phase 4</b></td><td>10K-scale parallelism — Ray distributed execution + LLM cost optimization</td></tr>
<tr><td>&#9744;</td><td><b>Phase 5</b></td><td>God Mode & visualization — real-time event injection + Plotly dashboard</td></tr>
</table>

---

<div align="center">

**MIT License**

</div>
