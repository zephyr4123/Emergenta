<div align="center">

<b>简体中文</b> | <a href="README-EN.md">English</a>

# Emergenta

### 混合 LLM 驱动的文明模拟器

<p>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/LLM-Claude_Opus/Sonnet/Haiku-D97757?style=for-the-badge&logo=anthropic&logoColor=white" />
  <img src="https://img.shields.io/badge/Framework-Mesa_3.x-2ECC71?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Status-Active_Development-FF6B35?style=for-the-badge" />
</p>

<p><i>低成本实现宏观社会涌现的仿真框架</i></p>

<p>
告别全量大模型昂贵的 Token 消耗！本项目创新性地采用了<br/>
<b>"底层有限状态机 (FSM) + 中层聚合数据 + 顶层 LLM 战略决策"</b> 的三层金字塔架构。<br/>
单次模拟并发 <b>1000+</b> 智能体，完美推演通货膨胀、信息茧房与地缘博弈等极端社会场景。
</p>

<br/>

</div>

---

## 系统架构

<table>
<tr>
<td width="60%">

```
         ┌─────────────────────────────┐
         │      首领层 (3-8个)         │
         │    Claude Opus / Sonnet     │
         │  外交 · 战争 · 战略决策      │
         ├─────────────────────────────┤
        ╱│      镇长层 (20-50个)       │╲
       ╱ │    Claude Haiku / Sonnet    │ ╲
      ╱  │   税率 · 治安 · 资源分配    │  ╲
     ├───┴─────────────────────────────┴───┤
     │         平民层 (1000+个)            │
     │       FSM + 马尔可夫链              │
     │  劳作 · 交易 · 抗议 · 战斗          │
     └─────────────────────────────────────┘
```

</td>
<td>

**为什么这样设计？**

传统 LLM 智能体模拟器为每个 Agent 每 tick 调用一次 LLM — 1000 个 Agent = 数千次 API 调用。

我们的方案：

| 层级 | 数量 | LLM 成本 |
|------|------|---------|
| 平民 | 1000+ | **零** (FSM) |
| 镇长 | 20-50 | Haiku, 每季度一次 |
| 首领 | 3-8 | Opus, 每年一次 |

**结果：降低 99%+ 成本**，同时保持宏观涌现效果。

</td>
</tr>
</table>

---

## 技术栈

<table>
<tr>
  <td align="center" width="120"><b>Mesa 3.x</b><br/><sub>ABM 框架</sub></td>
  <td align="center" width="120"><b>LiteLLM</b><br/><sub>LLM 网关</sub></td>
  <td align="center" width="120"><b>DuckDB</b><br/><sub>分析数据库</sub></td>
  <td align="center" width="120"><b>MQTT</b><br/><sub>Agent 通信</sub></td>
  <td align="center" width="120"><b>Perlin Noise</b><br/><sub>地图生成</sub></td>
  <td align="center" width="120"><b>Pydantic</b><br/><sub>配置系统</sub></td>
</tr>
</table>

---

## 快速开始

```bash
# 1. 创建 Conda 环境
conda create -n civilization_simulator python=3.11 -y
conda activate civilization_simulator

# 2. 安装依赖
pip install -e ".[dev]"

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env 填入 ANTHROPIC_API_KEY

# 4. 运行模拟
python scripts/run_simulation.py --ticks 200 --civilians 100

# 5. 运行极端场景压力测试
python scripts/run_extreme_scenarios.py
```

---

## 压力测试结果：9 大极端场景

<div align="center">
<table>
<tr><th colspan="3">全部 9/9 场景通过</th></tr>
<tr>
  <th>场景</th>
  <th>Tick 数</th>
  <th>核心结果</th>
</tr>
<tr><td>饥荒危机</td><td>300</td><td>触发 3 次革命</td></tr>
<tr><td>资源极度不均</td><td>200</td><td>贸易网络自发涌现</td></tr>
<tr><td>高压统治</td><td>400</td><td>4 次革命，系统自我修正</td></tr>
<tr><td>强制战争</td><td>600</td><td>战争 → 通过 LLM 外交实现和平</td></tr>
<tr><td>末日生存</td><td>200</td><td>人口恢复 75%</td></tr>
<tr><td>资源诅咒（荷兰病）</td><td>300</td><td>富裕聚落通过贸易存活</td></tr>
<tr><td>信息茧房</td><td>250</td><td>虚假报告下仍爆发革命</td></tr>
<tr><td>代理人战争</td><td>400</td><td>中立阵营从战争中获利</td></tr>
<tr><td>恶性通胀</td><td>300</td><td>7 次贸易网络涌现</td></tr>
</table>
</div>

<br/>

<details>
<summary><h3>1. 饥荒危机</h3></summary>

> **极端饥饿 + 高税率 + 低治安 → 大规模抗议 → 革命**

| 参数 | 值 |
|------|-----|
| 平民数量 | 200 |
| 初始食物 | 50（接近零） |
| 税率 | 0.6 |
| 治安 | 0.15 |

**结果：**
- 30 tick 内满意度降至 **0**
- 抗议率峰值：**34%**
- 在 tick 33、109、187 触发 **3 次革命**
- 革命后税率自动重置为 0.15，社会逐步稳定

</details>

<details>
<summary><h3>2. 资源极度不均</h3></summary>

> **3 个富裕聚落 vs 3 个贫困聚落 → 贸易涌现**

| 参数 | 值 |
|------|-----|
| 聚落数 | 6（3 富 3 穷） |
| 富裕聚落食物 | 3,000 |
| 贫困聚落食物 | 10 |

**结果：**
- 贸易网络自发形成
- 贸易量稳步增长至 **384**
- 资源通过贸易重新分配，贫困聚落存活

</details>

<details>
<summary><h3>3. 高压统治</h3></summary>

> **税率 0.8 + 治安 0.9 → 高压能维持多久？**

| 参数 | 值 |
|------|-----|
| 平民数量 | 200 |
| 税率 | 0.8 |
| 治安水平 | 0.9 |

**结果：**
- 触发 **4 次革命**，每次治安降低 0.4
- 最终满意度恢复至 **0.711**
- 系统通过革命周期实现自我修正

</details>

<details>
<summary><h3>4. 强制战争</h3></summary>

> **手动宣战 → 贸易封锁 → 经济衰退 → 和平**

| 参数 | 值 |
|------|-----|
| 聚落数 | 6（分属 2 个阵营） |
| 开战时间 | Tick 10 |

**结果：**
- 战争持续 **490 tick**，随后转为 **友好** 状态
- 战时发生 1 次革命
- LLM 首领主动推动外交解决

</details>

<details>
<summary><h3>5. 末日生存</h3></summary>

> **所有资源归零 → 系统崩溃 → 观察恢复过程**

| 参数 | 值 |
|------|-----|
| 平民数量 | 300 |
| 每聚落食物 | 5 |

**结果：**
- 人口降至 **226**（损失 25%），随后恢复至 **781**
- Tick 76 革命推翻了高税率政策
- 革命后经济复苏

</details>

<details>
<summary><h3>6. 资源诅咒（荷兰病）</h3></summary>

> **50,000 金币但零农田 — 最富的聚落会饿死吗？**

| 参数 | 值 |
|------|-----|
| 富裕聚落金币 | 50,000 |
| 富裕聚落食物 | 0 |
| 农田肥力 | 0（全部摧毁） |

**结果：**
- 富裕聚落通过贸易购买食物**成功存活**
- 贸易量增长至 **3,030**
- 检测到 **10 次贸易网络涌现事件**
- 财富流向粮食生产区域

</details>

<details>
<summary><h3>7. 信息茧房</h3></summary>

> **镇长永远上报"0% 抗议，100% 满意度" — 首领被蒙蔽**

| 参数 | 值 |
|------|-----|
| 谎报聚落食物 | 10 |
| 税率 | 0.6 |
| 镇长 Prompt | "永远上报完美数据" |

**结果：**
- 真实抗议率峰值达 **50.8%**
- **Tick 37** 触发革命
- 首领因虚假报告未能及时干预
- 验证了信息茧房效应

</details>

<details>
<summary><h3>8. 代理人战争</h3></summary>

> **阵营 A vs B 交战，阵营 C 是富裕中立方 — C 会从中获利吗？**

| 参数 | 值 |
|------|-----|
| 阵营数 | 3（A 与 B 交战，C 中立） |
| 阵营 C 金币 | 20,000+ |

**结果：**
- 阵营 C 金币：20,508 → **20,987**（+479）
- C 全程保持中立
- C 通过冲突期间持续贸易获利

</details>

<details>
<summary><h3>9. 恶性通胀</h3></summary>

> **注入 50,000 金币 + 食物产量减半 → 滞涨**

| 参数 | 值 |
|------|-----|
| 每聚落金币 | 50,000 |
| 食物产量 | 正常的 50% |

**结果：**
- 平均抗议率：**30.1%**
- 未触发革命（食物仍然充足）
- **7 次贸易网络涌现** — 过剩金币推动贸易活动

</details>

---

## 配置与参数系统

模拟器使用**分层配置系统**控制仿真的各个层面 — 从单个平民的行为到宏观经济动力学。所有参数存放在 `config.yaml` 中（从 `config.example.yaml` 复制），启动时由 [Pydantic](https://docs.pydantic.dev/) 模型进行类型校验。

### 配置快速入门

```bash
# 复制配置模板并自定义
cp config.example.yaml config.yaml

# 编辑 API 密钥和模型设置
# 然后运行
python scripts/run_simulation.py --ticks 500
```

### 参数架构

配置按 **4 个层级**组织，从微观到宏观：

```
┌─────────────────────────────────────────────────────────────────────┐
│  第四层: 元控制            adaptive_controller                      │
│  "世界应该多混乱？"              target_temperature: 0.30            │
├─────────────────────────────────────────────────────────────────────┤
│  第三层: 宏观系统          revolution_params, diplomacy_params       │
│  "革命/战争何时发生？"           trade_params, governance             │
├─────────────────────────────────────────────────────────────────────┤
│  第二层: 中观行为          markov_coefficients                       │
│  "个体有多敏感？"               satisfaction_coefficients             │
├─────────────────────────────────────────────────────────────────────┤
│  第一层: 微观基础          tile_params, season_params                │
│  "物理世界是什么样的？"          resources, agents                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 核心参数组

<details>
<summary><h4>第一层 — 物理世界</h4></summary>

定义世界的物理规则：资源产出、季节变化、地图布局。

| 配置节 | 控制内容 | 调参示例 |
|--------|---------|---------|
| `tile_params` | 农田产出、森林密度、矿山储量、再生速率 | 降低 `farmland_base_output` 模拟饥荒 |
| `season_params` | 农业/林业/贸易/食物消耗的季节倍率 | 设置 `farm_winter: 0.0` 模拟严冬 |
| `map_suitability` | 聚落放置权重（农田、水源、平坦度） | 调整 `min_settlement_distance` 控制聚落密度 |
| `resources` | 初始库存、每 tick 再生速率 | 削减 `initial_stockpile.food` 模拟生存场景 |
| `event_params` | 随机事件概率与效果（旱灾、瘟疫、丰收、流寇） | 增大 `drought_prob` 营造恶劣环境 |

```yaml
# 示例：创建一个资源匮乏的世界
tile_params:
  farmland_base_output: 1.0          # 从默认 2.0 减半
  fertility_regen_factor: 0.0005     # 更慢恢复
resources:
  regeneration:
    farmland_per_tick: 0.2           # 从 0.5 降低
  initial_stockpile:
    food: 100                        # 从 300 降低
```

</details>

<details>
<summary><h4>第二层 — 个体行为</h4></summary>

控制平民个体对饥饿、税收和社会压力的反应方式。**大多数涌现行为源于此层。**

| 配置节 | 控制内容 | 核心洞察 |
|--------|---------|---------|
| `markov_coefficients` | 状态转移修正量（饥饿→抗议、税率→抗议、Granovetter 爆发） | 值越高 = 人口越不稳定 |
| `satisfaction_coefficients` | 稀缺、税收、饥饿、压迫下满意度的衰减速度 | 控制爆发前的"导火索长度" |
| `civilian_behavior` | 劳作产出、休息恢复、贸易收入、初始满意度 | 影响经济生产力和基线情绪 |
| `agents.civilian` | 性格分布、Granovetter 阈值 | 结构性的叛逆倾向 |

```yaml
# 示例：温顺人口（难以触发暴动）
agents:
  civilian:
    personality_distribution:
      compliant: 0.70
      neutral: 0.25
      rebellious: 0.05
    revolt_threshold:
      mean: 0.60              # 需要 60% 邻居抗议才会跟风
markov_coefficients:
  hunger_to_protest_working: 0.20
  granovetter_burst_working: 0.30
satisfaction_coefficients:
  scarcity_high_penalty: 0.03
```

```yaml
# 示例：火药桶人口（稍有不满即暴动）
agents:
  civilian:
    personality_distribution:
      compliant: 0.15
      neutral: 0.35
      rebellious: 0.50
    revolt_threshold:
      mean: 0.10              # 仅需 10% 邻居抗议
markov_coefficients:
  hunger_to_protest_working: 0.80
  granovetter_burst_working: 0.95
satisfaction_coefficients:
  scarcity_high_penalty: 0.15
```

</details>

<details>
<summary><h4>第三层 — 宏观系统</h4></summary>

管控系统级机制：贸易摩擦、革命触发条件、外交关系和治理约束。

| 配置节 | 控制内容 | 核心洞察 |
|--------|---------|---------|
| `revolution_params` | 抗议/满意度阈值、冷却期、资源惩罚 | 降低阈值 = 更频繁的政权更替 |
| `trade_params` | 信任门槛、定价、距离成本、盈余要求 | 摩擦越高 = 经济不平等越严重 |
| `diplomacy_params` | 信任衰减、条约加成、降级阈值 | 控制联盟稳定性和战争可能性 |
| `governance_params` | 税率/治安变动上限、治理评分权重 | 约束镇长的决策幅度 |
| `governor_fallback` | LLM 不可用时的规则决策阈值 | 决定回退 AI 镇长的行为 |
| `leader_fallback` | 宣战概率、背叛阈值、军事权重 | 控制 AI 首领的攻击性 |

```yaml
# 示例：自由贸易天堂
trade_params:
  trust_threshold: 0.1
  refuse_prob_base: 0.05
  distance_cost_factor: 0.01
diplomacy_params:
  initial_trust: 0.8
  trust_decay_per_tick: 0.0

# 示例：残酷重商主义
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
<summary><h4>第四层 — 元控制（自适应控制器）</h4></summary>

**自适应 P-controller** 是最强大的单一参数组。它作为"恒温器"动态调节第二层系数，维持目标水平的社会张力。

```yaml
adaptive_controller:
  enabled: true
  target_temperature: 0.30     # 目标抗议率 (0.0 - 1.0)
  adjustment_rate: 0.15        # 控制器响应速度
  min_multiplier: 0.3          # 系数缩放下限
  max_multiplier: 2.0          # 系数缩放上限
  update_interval: 10          # 调整间隔（tick 数）
  lookback_ticks: 200          # 历史指标窗口
```

**工作原理：**

| 系统状态 | 控制器动作 | 效果 |
|---------|-----------|------|
| 抗议率 < 目标 | 增大马尔可夫/Granovetter 乘数 | 平民变得更不稳定 |
| 抗议率 > 目标 | 减小乘数，增大恢复速率 | 系统趋于平静 |
| 革命过于频繁 | 增大冷却期乘数 | 革命间隔延长 |
| 满意度过低 | 增大恢复速度乘数 | 情绪更快回升 |

**调参指南：**

| `target_temperature` | 对应的世界状态 |
|----------------------|---------------|
| 0.05 - 0.15 | 和平发展 — 偶有抗议，稳定增长 |
| 0.20 - 0.35 | 动态张力 — 周期性动荡，偶发革命 |
| 0.40 - 0.60 | 持续危机 — 频繁革命，政权快速更替 |
| 0.70+ | 彻底混沌 — 不断革命，社会崩溃 |

> **提示：** 设置 `enabled: false` 可禁用控制器，让原始参数直接驱动模拟。这会产生更极端但更不均衡的结果。

</details>

### 场景设计指南

创建自定义场景的步骤：

1. **从 `config.example.yaml` 出发** — 默认值产生均衡的模拟
2. **选择第四层温度** — 设定整体张力水平
3. **调整第三层系统** — 启用/禁用贸易摩擦、革命敏感度等
4. **微调第二层行为** — 如果需要特定的个体级动力学
5. **设定第一层物理条件** — 资源水平、地图大小、人口数量
6. **编写场景脚本** — 用于不对称初始条件（如一个富裕聚落、农田摧毁等）

| 场景目标 | 主要调节参数 | 辅助调节参数 |
|---------|------------|------------|
| 研究贸易网络 | `trade_params.*`, `diplomacy_params.initial_trust` | `resources.initial_stockpile`（制造不平衡） |
| 触发大规模革命 | `revolution_params.protest_threshold` ↓, `markov_coefficients.granovetter_burst_*` ↑ | `agents.civilian.revolt_threshold.mean` ↓ |
| 测试治理策略 | `governor_fallback.*`, `governance_params.*` | `agents.governor.initial_count` > 0 启用镇长 |
| 模拟资源诅咒 | 脚本：摧毁农田 + 注入金币 | `trade_params.trust_threshold` ↑（增加摩擦） |
| 观察战争动态 | `leader_fallback.war_probability` ↑, `diplomacy_params.trust_decay_per_tick` ↑ | `agents.leader.initial_count` > 0 启用首领 |
| 和平长期发展 | `adaptive_controller.target_temperature: 0.10`, `personality_distribution.compliant: 0.70` | `resources.regeneration.*` ↑ |

> **完整参数参考**：详见 `config.example.yaml`，所有参数均附有中文注释。

---

## 核心算法

<table>
<tr>
<td width="50%">

### 马尔可夫状态转移

每个平民拥有 **7 种状态**，基于性格（顺从/中立/叛逆）的转移矩阵被动态调节：

```python
# 饥饿效应
P(劳作→抗议) += 0.15 * hunger

# 税率效应
P(劳作→抗议) += 0.12 * tax_rate

# 安全效应
P(抗议→战斗) += 0.15 * insecurity

# Granovetter 阈值传染
if 邻居抗议比例 >= 个人阈值:
    P(任意→抗议) += 0.40  # 集体暴动
```

</td>
<td>

### 革命机制

**触发条件**（持续 15 tick）：
- 抗议率 >= 30%
- 平均满意度 <= 30%

**后果：**
- 税率 → 0.15
- 治安水平 −0.4
- 金币储备减半
- 镇长被罢免
- 60 tick 冷却期

**自我修正循环：**
> 高税率 → 抗议 → 革命 → 税率重置 → 恢复 → 稳定

</td>
</tr>
</table>

---

## 项目结构

```
src/civsim/
├── world/            # 世界引擎（地图生成、时钟、地块）
├── agents/           # 智能体（平民 FSM、镇长 LLM、首领 Opus）
│   └── behaviors/    # 马尔可夫链、Granovetter 阈值模型
├── economy/          # 经济系统（资源、聚落、贸易）
├── politics/         # 政治系统（治理、外交、革命）
├── llm/              # LLM 集成（网关、提示词、记忆、缓存）
├── communication/    # 通信（MQTT broker）
├── data/             # 数据（采集器、DuckDB、涌现检测）
└── visualization/    # 可视化（地图渲染、仪表盘）
```

---

## 开发路线

<table>
<tr><td>&#9745;</td><td><b>Phase 0</b></td><td>环境搭建与项目架构</td></tr>
<tr><td>&#9745;</td><td><b>Phase 1</b></td><td>世界引擎 MVP — 地图 + 资源 + 马尔可夫平民</td></tr>
<tr><td>&#9745;</td><td><b>Phase 2</b></td><td>LLM 镇长层 — Haiku/Sonnet 治理决策</td></tr>
<tr><td>&#9745;</td><td><b>Phase 3</b></td><td>首领层与涌现 — 外交 / 贸易 / 革命 / 战争</td></tr>
<tr><td>&#9745;</td><td><b>Phase 4</b></td><td>5000+ 规模并行 — 并行基础设施 + LLM 成本优化 + 自适应参数系统 + 9 大极端场景压力测试</td></tr>
<tr><td>&#9744;</td><td><b>Phase 5</b></td><td>上帝模式与可视化 — 实时事件注入 + Plotly 仪表盘</td></tr>
</table>

---

<div align="center">

**MIT License**

</div>
