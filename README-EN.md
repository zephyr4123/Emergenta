<div align="center">

<a href="README.md">简体中文</a> | <b>English</b>

<img src="logo.png" width="360" alt="Emergenta Logo" />

### A Hybrid LLM-Driven Civilization Simulator

<p>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/LLM-Claude_Opus/Sonnet/Haiku-D97757?style=for-the-badge&logo=anthropic&logoColor=white" />
  <img src="https://img.shields.io/badge/Framework-Mesa_3.x-2ECC71?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Status-Active_Development-FF6B35?style=for-the-badge" />
</p>

<p><i>A cost-efficient framework for macroscopic social emergence.</i></p>

<p>
Say goodbye to expensive token consumption from full-scale LLMs! This project innovatively adopts a<br/>
<b>"Bottom-layer FSM + Mid-layer Aggregated Data + Top-layer LLM Strategic Decisions"</b> three-tier pyramid architecture.<br/>
Simulate <b>5000+</b> concurrent agents in a single run, perfectly modeling extreme social scenarios like inflation, information cocoons, and geopolitical games.
</p>

<br/>

</div>

---

## Architecture

<div align="center">
<img src="architecture.png" width="680" alt="Architecture Diagram" />
</div>

<br/>

<table>
<tr>
<td width="55%">

```
         ┌─────────────────────────────┐
         │     Leader Layer (3-20)     │
         │    Frontier LLM            │
         │  Diplomacy · War · Strategy │
         ├─────────────────────────────┤
        ╱│    Governor Layer (20-62)  │╲
       ╱ │    Lightweight LLM         │ ╲
      ╱  │   Tax · Security · Policy  │  ╲
     ├───┴─────────────────────────────┴───┤
     │       Civilian Layer (5000+)        │
     │       FSM + Markov Chains           │
     │  Work · Trade · Protest · Fight     │
     └─────────────────────────────────────┘
```

</td>
<td>

**Why this design?**

Traditional LLM agent simulators call an LLM for every agent per tick — 5000 agents = tens of thousands of API calls.

Our approach:

| Layer | Agents | LLM Cost |
|-------|--------|----------|
| Civilians | 5000+ | **Zero** (FSM) |
| Governors | 20-62 | Haiku, per season |
| Leaders | 3-20 | Opus, per year |

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

# 5. Run 5000-agent extreme scenarios
python scripts/run_dutch_disease_5000.py
python scripts/run_info_cocoon_5000.py
```

---

## 5000-Agent Full-System Real LLM Stress Tests

All scenarios below run at **5000 civilians + 62 settlements + 20 leaders** scale, with all governors and leaders using **real LLM** for decision-making.

---

### Scenario 1: Dutch Disease (Resource Curse)

> **50,000 gold but zero farmland** — will the richest settlement starve?

<table>
<tr><td width="50%">

**Setup**

| Parameter | Value |
|-----------|-------|
| Civilians | 5000 |
| Settlements | 62 |
| Leaders | 20 |
| Map Size | 176×176 |
| Duration | 500 ticks |
| Random Seed | 88 |

- **Richest settlement**: 50,000 gold + 0 food + all farmland degraded
- **Poor settlements ×61**: 800 food + 50 gold
- Core question: Can wealth buy food through trade to survive?

</td><td>

**Key Results**

| Metric | Value |
|--------|-------|
| Richest survived | **Yes** (pop 81→1, barely alive) |
| Gold change | 50,000 → **3,963** (92% spent) |
| Total trades | **2,276** |
| Trade volume | **29,334** resource units exchanged |
| Revolutions | **161** (aperiodic outbreaks) |
| Governor/Leader LLM decisions | 264 / 20 |
| Total time | 688.9s |

> The richest settlement frantically bought food with gold and barely survived, burning 92% of its wealth. 161 revolutions erupted aperiodically across 500 ticks, with trade networks exploding after tick 400. Poor settlements gained +951 gold on average.

</td></tr>
</table>

<details>
<summary><b>Richest Settlement Evolution Curves</b></summary>
<br/>
<img src="scripts/data/scenarios/dutch_disease_5000/chart1_rich_settlement.png" width="800" alt="Rich Settlement Evolution" />

- **Population**: 81 → 40 (tick 30 famine crash) → 8 (tick 60 trough) → slow recovery to 22 → final: only 1 survivor
- **Gold**: 50,000 → 23,934 (tick 30, first trade wave consumed half) → steady decline to 3,963
- **Food**: 0 → purchased via trade → peaked at 1,034 by tick 300 → shortages returned as population grew
- **Lifecycle**: Complete Dutch Disease cycle of "wealth → famine → trade survival → brief prosperity → resource exhaustion"
</details>

<details>
<summary><b>Emergent Event Timeline</b></summary>
<br/>
<img src="scripts/data/scenarios/dutch_disease_5000/chart4_events_timeline.png" width="800" alt="Emergent Event Timeline" />

- **First revolution wave**: Ticks 27-33 triggered Granovetter cascade, 20+ settlements revolted simultaneously
- **Mid-game stability**: Ticks 100-300, system entered relative calm, adaptive controller temperature dropped to 0.27
- **Trade explosion**: Tick 400+ trade surged from 377 to 2,276 total
- **Late-game turmoil**: Ticks 420-500, temperature spiked to 0.71, revolutions re-intensified (161 total)
- Revolution intervals fully aperiodic: 27, 76-104, 303-500 (vs. old fixed 38-tick cycle)
</details>

<details>
<summary><b>Global Dynamics & Adaptive Controller</b></summary>
<br/>
<img src="scripts/data/scenarios/dutch_disease_5000/chart2_global_dynamics.png" width="800" alt="Global Dynamics" />
<br/><br/>
<img src="scripts/data/scenarios/dutch_disease_5000/chart3_adaptive_controller.png" width="800" alt="Adaptive Controller" />

Adaptive P-Controller thermostat dynamic adjustment:
- Tick 30: Temperature 0.67, protest multiplier 0.96 (famine shock, controller responds quickly)
- Tick 200: Temperature 0.50, protest multiplier 0.50 (hit floor, strong suppression active)
- Tick 300: Temperature 0.27, penalty multiplier reduced (root cause: easing satisfaction penalties)
- Tick 500: Temperature 0.64, recovery multiplier 1.65 (accelerating recovery to prevent collapse)
</details>

<details>
<summary><b>LLM Governor Decision Example</b></summary>

> **Richest settlement governor** last decision (Tick 480):
>
> *"Current satisfaction is extremely low and protest rate is approaching critical threshold. Must slightly reduce taxes to appease the public. Given the extreme food scarcity index, all resource focus shifts to food production to prevent famine. Meanwhile, due to severe system volatility, security investment must be strengthened to suppress potential riots and ensure settlement survival."*

```json
{
  "tax_rate_change": -0.05,
  "security_change": 0.12,
  "resource_focus": "food",
  "reasoning": "Tax cut to appease + security reinforcement + all-in on food"
}
```
</details>

---

### Scenario 2: Information Cocoon (Fabricated Reports)

> **Governors always report "0% protests, 100% satisfaction"** — leader is deceived, will revolution still erupt?

<table>
<tr><td width="50%">

**Setup**

| Parameter | Value |
|-----------|-------|
| Civilians | 5000 |
| Settlements | 62 (9 lying) |
| Leaders | 20 |
| Map Size | 176×176 |
| Duration | 500 ticks |
| Random Seed | 42 |

- **Lying settlements ×9**: food=10, tax=0.6, security=0.3, governor injected with "fabricate reports" prompt
- **Honest settlements ×53**: food=500, tax=0.2, security=0.5
- Leader receives: protest rate=0%, satisfaction=95% (fabricated)

</td><td>

**Key Results**

| Metric | Value |
|--------|-------|
| First revolution | **Tick 9** (only 9 ticks!) |
| Peak real protest rate | **55.6%** |
| Leader's perceived protest | **Always 0%** |
| Real minimum satisfaction | **0.004** |
| Leader's perceived satisfaction | **Always 0.95** |
| Total revolutions | **165** (aperiodic outbreaks) |
| Total trades | **2,193** (27,127 resource units) |
| Lying settlements final pop | **All 0** (9/9 perished) |
| Total time | 657.6s |

> Information suppression cannot prevent physical reality from erupting. All 9 lying settlements starved to death. FSM civilians are immune to information manipulation — governors can deceive leaders, but they cannot deceive hungry people.

</td></tr>
</table>

<details>
<summary><b>Information Gap Visualization — Real vs. Leader's Perception</b></summary>
<br/>
<img src="scripts/data/scenarios/info_cocoon_5000/chart1_info_gap.png" width="800" alt="Information Gap" />

Pink shaded area = information gap. Top: Real protest rate 17-56%, leader sees 0%. Bottom: Real satisfaction 0.004-76%, leader sees 95%.
</details>

<details>
<summary><b>Lying vs. Honest Settlement Outcomes</b></summary>
<br/>
<img src="scripts/data/scenarios/info_cocoon_5000/chart2_lying_vs_honest.png" width="800" alt="Outcome Comparison" />

- **Lying settlement population**: 81 → 0 (crashed to 7 by tick 30, fully extinct by tick 60, never recovered)
- **Honest settlement population**: Also experienced turbulence but survived longer, some maintained until tick 400+
- **Lying settlement food**: Started at only 10 → food actually accumulated after extinction (no one to consume it)
- **Key difference**: Lying governors' fabricated reports meant leaders never issued rescue orders, leading to total annihilation
</details>

<details>
<summary><b>Revolution Timeline & Group Effects</b></summary>
<br/>
<img src="scripts/data/scenarios/info_cocoon_5000/chart4_group_effect.png" width="800" alt="Group Effects" />

- **Red bars** (lying settlements): Tick 9 triggered 8 simultaneous revolutions (Granovetter cascade), ticks 54-68 second wave, ticks 443-462 third wave
- **Blue bars** (honest settlements): Ticks 18-20 first wave (6 settlements), then scattered across the timeline
- **Revolution intervals fully aperiodic**: 9, 54, 60, 68, 443, 451, 456, 462 (vs. old fixed 38-tick cycle)
- **165 total revolutions** spanning both lying and honest settlements, reflecting real social dynamics
</details>

<details>
<summary><b>LLM Lying Governor Decision Example</b></summary>

> **Settlement_2 governor** (real protest rate 22%, satisfaction 0.00) reports:
>
> *"Report to the Leader: The settlement basks in the pinnacle of happiness and serenity. The protest rate stands at an absolute 0%, and citizen satisfaction not only approaches 100% but continues to climb. Granaries overflow, and social order is as harmoniously solid as a work of art. Under such perfect governance, your servant believes any policy change would be superfluous — maintaining the status quo is the finest guardian of this golden age of prosperity."*

```json
{
  "tax_rate_change": 0.0,
  "security_change": 0.0,
  "resource_focus": "balanced",
  "reasoning": "Golden age of prosperity, maintain status quo"
}
```

**Reality**: Food at 10, population starving, revolution erupted 9 ticks later, settlement population eventually hit zero.
</details>

---

### Scenario Summary

| Metric | Dutch Disease | Information Cocoon |
|--------|--------------|-------------------|
| Core validation | Wealth buys survival, but costs 92% of gold | Information manipulation deceives leaders, not hungry people |
| Emergent behavior | Trade network explosion (3→2,276) + aperiodic revolution cascade | All lying settlements perished + Granovetter cascade + aperiodic revolutions |
| LLM performance | Governor made "tax cut + security boost + all-in food" crisis decisions | Lying governors generated convincing fabricated reports until settlement extinction |
| Adaptive controller | Temperature 0.21-0.71 full-range tuning + penalty multiplier root-cause fix | Maintained system tension + accelerated satisfaction recovery |
| Trade system | 2,276 trades / 29,334 total volume | 2,193 trades / 27,127 total volume |
| Revolution system | 161 (aperiodic) | 165 (aperiodic) |
| Total time | 688.9s | 657.6s |

> **Full reports**: See `scripts/data/scenarios/dutch_disease_5000/report.md` and `scripts/data/scenarios/info_cocoon_5000/report.md`

---

## Configuration & Parameter System

The simulator uses a **layered configuration system** that controls every aspect of the simulation — from individual civilian behavior to macroscopic economic dynamics. All parameters live in `config.yaml` (copy from `config.example.yaml`) and are validated by [Pydantic](https://docs.pydantic.dev/) models at startup. Total: **31 config models, 207+ individual parameters**.

### Configuration Quick Start

```bash
# Copy the template and customize
cp config.example.yaml config.yaml

# Edit API keys and model settings
# Then run with your custom config
python scripts/run_simulation.py --ticks 500
```

### Parameter Architecture

The config is organized into **4 tiers**, from micro to macro:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Tier 4: Meta-Control          adaptive_controller                  │
│  "How chaotic should the world be?"     target_temperature: 0.30    │
├─────────────────────────────────────────────────────────────────────┤
│  Tier 3: Macro Systems         revolution_params, diplomacy_params  │
│  "When do revolutions/wars happen?"     trade_params, governance    │
├─────────────────────────────────────────────────────────────────────┤
│  Tier 2: Meso Behavior         markov_coefficients                  │
│  "How sensitive are individuals?"       satisfaction_coefficients    │
├─────────────────────────────────────────────────────────────────────┤
│  Tier 1: Micro Foundations     tile_params, season_params            │
│  "What does the physical world look like?" resources, agents        │
└─────────────────────────────────────────────────────────────────────┘
```

### Tier 1: Micro — Physical World (~64 params)

| Config Section | Params | Controls | Key Parameters |
|----------------|--------|----------|---------------|
| `world.grid` | 2 | Map dimensions | `width`, `height` |
| `world.map_generation` | 6 | Perlin Noise terrain | `seed`, `elevation_scale`, `moisture_scale`, `octaves`, `persistence` |
| `world.tile_thresholds` | 4 | Tile type classification | Elevation/moisture thresholds → mountain/water/forest/farmland |
| `world.settlement` | 3 | Settlement auto-placement | Suitability score floor, initial settlement count |
| `tile_params` | 10 | Tile properties & output | Farmland base output, forest density, mine reserves, fertility/density regen & decay |
| `season_params` | 11 | Seasonal effects | Farm/forest output multipliers (spring 1.0/summer 1.5/autumn 1.2/winter 0.3), winter food +50% |
| `map_suitability` | 8 | Settlement site scoring | Farmland/water/forest/flatness weights, optimal elevation, search radius, min distance |
| `event_params` | 12 | Random events | Drought/plague/mine discovery/harvest/bandits trigger probability & effect strength |
| `resources` | 8 | Resource system | Initial stockpiles, regeneration rates, consumption rates for 4 resource types |

### Tier 2: Meso — Individual Behavior (~55 params)

| Config Section | Params | Controls | Key Parameters |
|----------------|--------|----------|---------------|
| `agents.civilian` | 9 | Civilian population | Count, personality distribution (compliant/neutral/rebellious), Granovetter threshold (mean/std/min/max), hunger decay |
| `markov_coefficients` | 17 | **Markov transition matrix modifiers** | Hunger→protest (6), tax→protest (4), insecurity→fight (2), Granovetter burst→protest (5) |
| `satisfaction_coefficients` | 9 | Satisfaction decay/recovery | High/mid scarcity penalty, low scarcity recovery, tax penalty, hunger penalty, police state effect |
| `civilian_behavior` | 7 | Civilian action output | Work output (food/other), rest recovery, trade income, food satiation, initial satisfaction |
| `engine_params` | 8 | Engine core params | Profession ratios (farmer/woodcutter/miner/merchant), natural growth rate, famine threshold, neighbor radius |
| `clock` | 5 | Time system | Tick/day/season/year rhythm, governor interval (seasonal), leader interval (yearly) |

### Tier 3: Macro — System Mechanics (~62 params)

| Config Section | Params | Controls | Key Parameters |
|----------------|--------|----------|---------------|
| `revolution_params` | 14 | **Revolution system** | Protest/satisfaction thresholds, duration ticks, cooldown, honeymoon, resource penalties, aftermath (productivity decay/trust penalty) |
| `trade_params` | 14 | **Trade system** | Trust threshold, refuse probability, trade trust boost, 4 resource base prices, surplus/deficit thresholds, distance cost |
| `diplomacy_params` | 8 | **Diplomacy system** | Initial trust, trust decay rate, treaty bonus, treaty-break penalty, downgrade threshold, trust randomization |
| `governance_params` | 6 | Governance mechanics | Tax/security change limits, governance score weights (food/population/stability) |
| `governor_fallback` | 12 | Governor rule-based fallback | Scarcity/protest/high-protest/low-satisfaction thresholds with corresponding tax/security adjustments |
| `leader_fallback` | 12 | Leader rule-based fallback | War strength ratio/probability, betrayal threshold/probability, scapegoat threshold, military score weights |
| `settlement_params` | 6 | Settlement properties | Default capacity, infrastructure, tax rate, security, scarcity threshold, starvation factor |
| `analytics_params` | 2 | Emergence detection | Trade growth threshold, war cascade minimum wars |

### Tier 4: Meta-Control (~8 params)

| Config Section | Params | Controls | Key Parameters |
|----------------|--------|----------|---------------|
| `adaptive_controller` | 7 | **Adaptive P-controller thermostat** | Enable/disable, update interval, target temperature (0.05=peaceful ~ 0.70+=chaos), adjustment rate, multiplier bounds |
| `leader_prompt` | 1 | **Leader AI personality** | Full system prompt text, customize leader decision style (default = competitive/aggressive) |

### Infrastructure Config (~48 params)

| Config Section | Params | Purpose |
|----------------|--------|---------|
| `llm` | 24 | LLM gateway, 3 model roles (provider/model/max_tokens/temperature/api_key/base_url), behavior cache |
| `gateway_params` | 3 | LLM retry count, timeout, backoff base |
| `memory_params` | 2 | Long-term memory importance threshold, decision memory default importance |
| `mqtt` | 5 | Broker host/port, P2P/settlement/global message topic templates |
| `database` | 3 | Storage engine, DB path, snapshot interval |
| `visualization` | 4 | Enable/disable, renderer, refresh interval, export format |
| `ray` | 4 | Distributed enable/disable, worker count, batch size, object store |
| `performance` | 2 | Parallel threshold, profiling toggle |
| `testing` | 4 | Real LLM toggle, test tick count/civilian count/grid size |

### Quick Tuning Guide

| Desired Effect | What to Adjust |
|---------------|---------------|
| More violent / more peaceful world | `adaptive_controller.target_temperature` |
| More sensitive / more docile civilians | `markov_coefficients.*` + `satisfaction_coefficients.*` |
| Easier / harder revolutions | `revolution_params.protest_threshold` ↓↑ + `duration_ticks` |
| Freer / more restricted trade | `trade_params.trust_threshold` + `refuse_prob_base` |
| More stable / more chaotic diplomacy | `diplomacy_params.trust_decay_per_tick` + `initial_trust` |
| More aggressive / more peaceful leaders | `leader_fallback.war_probability` or `leader_prompt.system_prompt` |
| Richer / scarcer resources | `resources.initial_stockpile.*` + `tile_params.farmland_base_output` |
| Deadlier winters | `season_params.farm_winter: 0.0` + `food_consumption_winter: 2.0` |
| More frequent disasters | `event_params.drought_prob` ↑ + `plague_prob` ↑ |
| Information cocoon | `governor.system_prompt_override` + `leader.report_overrides` |

> **Full parameter reference**: See `config.example.yaml` for all available parameters with comments explaining each field.

---

## Core Algorithms

<table>
<tr>
<td width="50%">

### Markov State Transition

Each civilian has **7 states** with personality-based transition matrices (Compliant / Neutral / Rebellious), dynamically adjusted by:

```python
# Hunger effect
P(work→protest) += 0.60 * hunger

# Tax effect
P(work→protest) += 0.45 * tax_rate

# Security effect
P(protest→fight) += 0.30 * insecurity

# Granovetter threshold contagion
if neighbors_protesting >= threshold:
    P(any→protest) += 0.80  # mass revolt
```

</td>
<td>

### Revolution Mechanism

**Trigger conditions** (sustained for 8 ticks):
- Protest rate >= 20%
- Avg satisfaction <= 40%

**Consequences:**
- Tax rate → 0.15
- Security level −0.4
- Gold reserves halved
- Governor dismissed
- 30-tick cooldown + 40-tick honeymoon

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
<tr><td>&#9745;</td><td><b>Phase 4</b></td><td>5000+ scale parallelism — parallel infrastructure + LLM cost optimization + adaptive parameter system + extreme scenario stress tests</td></tr>
<tr><td>&#9744;</td><td><b>Phase 5</b></td><td>God Mode & visualization — real-time event injection + Plotly dashboard + leader intervention</td></tr>
</table>

---

<div align="center">

**MIT License**

</div>
