<div align="center">

<a href="README.md">简体中文</a> | <b>English</b>

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
Say goodbye to expensive token consumption from full-scale LLMs! This project innovatively adopts a<br/>
<b>"Bottom-layer FSM + Mid-layer Aggregated Data + Top-layer LLM Strategic Decisions"</b> three-tier pyramid architecture.<br/>
Simulate <b>1000+</b> concurrent agents in a single run, perfectly modeling extreme social scenarios like inflation, information cocoons, and geopolitical games.
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

## Configuration & Parameter System

The simulator uses a **layered configuration system** that controls every aspect of the simulation — from individual civilian behavior to macroscopic economic dynamics. All parameters live in `config.yaml` (copy from `config.example.yaml`) and are validated by [Pydantic](https://docs.pydantic.dev/) models at startup.

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
│  Tier 4: Meta-Control          adaptive_controller                 │
│  "How chaotic should the world be?"     target_temperature: 0.30   │
├─────────────────────────────────────────────────────────────────────┤
│  Tier 3: Macro Systems         revolution_params, diplomacy_params │
│  "When do revolutions/wars happen?"     trade_params, governance   │
├─────────────────────────────────────────────────────────────────────┤
│  Tier 2: Meso Behavior         markov_coefficients                 │
│  "How sensitive are individuals?"       satisfaction_coefficients   │
├─────────────────────────────────────────────────────────────────────┤
│  Tier 1: Micro Foundations     tile_params, season_params           │
│  "What does the physical world look like?" resources, agents       │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Parameter Groups

<details>
<summary><h4>Tier 1 — Physical World</h4></summary>

These define the world's physical rules: resource production, seasons, map layout.

| Config Section | What It Controls | Example Tuning |
|----------------|-----------------|----------------|
| `tile_params` | Farmland output, forest density, mine reserves, regeneration rates | Lower `farmland_base_output` for famine scenarios |
| `season_params` | Seasonal multipliers for farming, forestry, trade, food consumption | Set `farm_winter: 0.0` for harsh winters |
| `map_suitability` | Settlement placement weights (farmland, water, flatness) | Adjust `min_settlement_distance` for dense/sparse maps |
| `resources` | Initial stockpiles, regeneration rates per tick | Slash `initial_stockpile.food` for survival scenarios |
| `event_params` | Random event probabilities and effects (drought, plague, harvest, bandits) | Increase `drought_prob` for hostile environments |

```yaml
# Example: Create a resource-scarce world
tile_params:
  farmland_base_output: 1.0          # Halved from default 2.0
  fertility_regen_factor: 0.0005     # Slower recovery
resources:
  regeneration:
    farmland_per_tick: 0.2           # Reduced from 0.5
  initial_stockpile:
    food: 100                        # Reduced from 300
```

</details>

<details>
<summary><h4>Tier 2 — Individual Behavior</h4></summary>

These control how individual civilians react to hunger, taxes, and social pressure. **This is where most emergent behaviors originate.**

| Config Section | What It Controls | Key Insight |
|----------------|-----------------|-------------|
| `markov_coefficients` | State transition modifiers (hunger→protest, tax→protest, Granovetter burst) | Higher values = more volatile population |
| `satisfaction_coefficients` | How fast satisfaction decays under scarcity, taxes, hunger, oppression | Controls the "fuse length" before explosion |
| `civilian_behavior` | Work output, rest recovery, trade income, initial satisfaction | Affects economic productivity and baseline mood |
| `agents.civilian` | Personality distribution, revolt thresholds | Structural predisposition to rebellion |

```yaml
# Example: Docile population (hard to trigger revolts)
agents:
  civilian:
    personality_distribution:
      compliant: 0.70
      neutral: 0.25
      rebellious: 0.05
    revolt_threshold:
      mean: 0.60              # Need 60% neighbors protesting to join
markov_coefficients:
  hunger_to_protest_working: 0.20
  granovetter_burst_working: 0.30
satisfaction_coefficients:
  scarcity_high_penalty: 0.03
```

```yaml
# Example: Powder keg population (revolts at the slightest provocation)
agents:
  civilian:
    personality_distribution:
      compliant: 0.15
      neutral: 0.35
      rebellious: 0.50
    revolt_threshold:
      mean: 0.10              # Only 10% neighbors needed
markov_coefficients:
  hunger_to_protest_working: 0.80
  granovetter_burst_working: 0.95
satisfaction_coefficients:
  scarcity_high_penalty: 0.15
```

</details>

<details>
<summary><h4>Tier 3 — Macro Systems</h4></summary>

These govern system-level mechanics: trade friction, revolution triggers, diplomacy, and governance.

| Config Section | What It Controls | Key Insight |
|----------------|-----------------|-------------|
| `revolution_params` | Protest/satisfaction thresholds, cooldown, resource penalties | Lower thresholds = more frequent regime changes |
| `trade_params` | Trust barriers, pricing, distance costs, surplus requirements | Higher friction = more economic inequality |
| `diplomacy_params` | Trust decay, treaty bonuses, downgrade thresholds | Controls alliance stability and war likelihood |
| `governance_params` | Tax/security change limits, governance scoring weights | Constrains how fast governors can act |
| `governor_fallback` | Rule-based decision thresholds when LLM is unavailable | Determines fallback AI governor behavior |
| `leader_fallback` | War probability, betrayal thresholds, military weights | Controls AI leader aggression |

```yaml
# Example: Free trade paradise
trade_params:
  trust_threshold: 0.1
  refuse_prob_base: 0.05
  distance_cost_factor: 0.01
diplomacy_params:
  initial_trust: 0.8
  trust_decay_per_tick: 0.0

# Example: Cutthroat mercantilism
trade_params:
  trust_threshold: 0.6
  refuse_prob_base: 0.5
  distance_cost_factor: 0.10
  food_surplus_threshold: 12.0
diplomacy_params:
  initial_trust: 0.3
  trust_decay_per_tick: 0.003
```

</details>

<details>
<summary><h4>Tier 4 — Meta-Control (Adaptive Controller)</h4></summary>

The **adaptive P-controller** is the most powerful single parameter group. It acts as a "thermostat" that dynamically adjusts Tier 2 coefficients to maintain a target level of social tension.

```yaml
adaptive_controller:
  enabled: true
  target_temperature: 0.30     # Target protest rate (0.0 - 1.0)
  adjustment_rate: 0.15        # How fast the controller reacts
  min_multiplier: 0.3          # Floor for coefficient scaling
  max_multiplier: 2.0          # Ceiling for coefficient scaling
  update_interval: 10          # Ticks between adjustments
  lookback_ticks: 200          # Historical window for metrics
```

**How it works:**

| System State | Controller Action | Effect |
|-------------|-------------------|--------|
| Protest rate < target | Increase markov/granovetter multipliers | Civilians become more volatile |
| Protest rate > target | Decrease multipliers, increase recovery | System calms down |
| Revolutions too frequent | Increase cooldown multiplier | Longer pause between revolts |
| Satisfaction too low | Increase recovery multiplier | Faster mood recovery |

**Tuning guide:**

| `target_temperature` | Resulting World |
|----------------------|----------------|
| 0.05 - 0.15 | Peaceful development — rare protests, stable growth |
| 0.20 - 0.35 | Dynamic tension — periodic unrest, occasional revolts |
| 0.40 - 0.60 | Perpetual crisis — frequent revolts, rapid regime change |
| 0.70+ | Total chaos — constant revolution, societal collapse |

> **Tip:** Set `enabled: false` to disable the controller and let raw parameters drive the simulation. This gives more extreme but less balanced outcomes.

</details>

### Scenario Design Cookbook

To create a custom scenario, follow this pattern:

1. **Start from `config.example.yaml`** — all defaults produce a balanced simulation
2. **Choose your Tier 4 temperature** — this sets the overall tension level
3. **Adjust Tier 3 systems** — enable/disable trade friction, revolution sensitivity, etc.
4. **Fine-tune Tier 2 behavior** — if you need specific individual-level dynamics
5. **Set Tier 1 physical conditions** — resource levels, map size, population
6. **Write a scenario script** — for asymmetric initial conditions (e.g., one rich settlement, farmland destruction)

| Scenario Goal | Primary Levers | Secondary Levers |
|---------------|---------------|-----------------|
| Study trade networks | `trade_params.*`, `diplomacy_params.initial_trust` | `resources.initial_stockpile` (create imbalance) |
| Trigger mass revolution | `revolution_params.protest_threshold` ↓, `markov_coefficients.granovetter_burst_*` ↑ | `agents.civilian.revolt_threshold.mean` ↓ |
| Test governance strategies | `governor_fallback.*`, `governance_params.*` | `agents.governor.initial_count` > 0 to enable |
| Simulate resource curse | Script: destroy farmland + inject gold | `trade_params.trust_threshold` ↑ (friction) |
| Observe war dynamics | `leader_fallback.war_probability` ↑, `diplomacy_params.trust_decay_per_tick` ↑ | `agents.leader.initial_count` > 0 to enable |
| Peaceful long-run growth | `adaptive_controller.target_temperature: 0.10`, `personality_distribution.compliant: 0.70` | `resources.regeneration.*` ↑ |

> **Full parameter reference**: See `config.example.yaml` for all available parameters with Chinese comments explaining each field.

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
<tr><td>&#9745;</td><td><b>Phase 4</b></td><td>5000+ scale parallelism — parallel infrastructure + LLM cost optimization + adaptive parameter system + 9 extreme scenario stress tests</td></tr>
<tr><td>&#9744;</td><td><b>Phase 5</b></td><td>God Mode & visualization — real-time event injection + Plotly dashboard</td></tr>
</table>

---

<div align="center">

**MIT License**

</div>
