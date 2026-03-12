<div align="center">

<b>简体中文</b> | <a href="README-EN.md">English</a>

<img src="logo.png" width="360" alt="Emergenta Logo" />

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
单次模拟并发 <b>5000+</b> 智能体，完美推演通货膨胀、信息茧房与地缘博弈等极端社会场景。
</p>

<br/>

</div>

---

## 系统架构

<div align="center">
<img src="architecture.png" width="680" alt="系统架构图" />
</div>

<br/>

<table>
<tr>
<td width="55%">

```
         ┌─────────────────────────────┐
         │      首领层 (3-20个)        │
         │    Frontier LLM            │
         │  外交 · 战争 · 战略决策      │
         ├─────────────────────────────┤
        ╱│      镇长层 (20-62个)      │╲
       ╱ │    Lightweight LLM         │ ╲
      ╱  │   税率 · 治安 · 资源分配    │  ╲
     ├───┴─────────────────────────────┴───┤
     │         平民层 (5000+个)            │
     │       FSM + 马尔可夫链              │
     │  劳作 · 交易 · 抗议 · 战斗          │
     └─────────────────────────────────────┘
```

</td>
<td>

**为什么这样设计？**

传统 LLM 智能体模拟器为每个 Agent 每 tick 调用一次 LLM — 5000 个 Agent = 数万次 API 调用。

我们的方案：

| 层级 | 数量 | LLM 成本 |
|------|------|---------|
| 平民 | 5000+ | **零** (FSM) |
| 镇长 | 20-62 | Haiku, 每季度一次 |
| 首领 | 3-20 | Opus, 每年一次 |

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

# 5. 运行 5000 Agent 极端场景
python scripts/run_dutch_disease_5000.py
python scripts/run_info_cocoon_5000.py
```

---

## 5000 Agent 全系统真实 LLM 压力测试

以下场景均在 **5000 平民 + 62 聚落 + 20 首领** 的规模下运行，所有镇长和首领使用**真实 LLM** 做决策。

---

### 场景一：荷兰病（资源诅咒）

> **50,000 金币但零农田** — 最富的聚落会饿死吗？

<table>
<tr><td width="50%">

**场景设定**

| 参数 | 值 |
|------|-----|
| 平民数量 | 5000 |
| 聚落数量 | 62 |
| 首领数量 | 20 |
| 地图大小 | 176×176 |
| 模拟时长 | 500 ticks |
| 随机种子 | 88 |

- **首富聚落**：50,000 金币 + 0 食物 + 农田全部退化
- **穷聚落 ×61**：800 食物 + 50 金币
- 核心问题：财富能否通过贸易买到粮食存活？

</td><td>

**核心结果**

| 指标 | 值 |
|------|-----|
| 首富聚落存活 | **是** |
| 金币变化 | 50,000 → 3,232 |
| 食物变化 | 0 → 7,760 |
| 总革命次数 | 70 |
| 贸易总量 | 8,873 |
| 战争数 | 11 |
| 总耗时 | 127.7s |

> 首富聚落用金币购入 6,400+ 食物，成功存活。穷聚落平均金币增长 +1,772。

</td></tr>
</table>

<details>
<summary><b>首富聚落演化曲线</b></summary>
<br/>
<img src="scripts/data/scenarios/dutch_disease_5000/chart1_rich_settlement.png" width="800" alt="首富聚落演化" />

- **人口**：81 → 200（~tick 130 达到容量上限）
- **金币**：50,000 → 495（首轮贸易花光），之后缓慢回升至 3,232
- **食物**：0 → 6,433（用金币购粮），持续积累至 7,760
</details>

<details>
<summary><b>涌现事件时间线</b></summary>
<br/>
<img src="scripts/data/scenarios/dutch_disease_5000/chart4_events_timeline.png" width="800" alt="涌现事件时间线" />

- **革命浪潮**：tick 370-390 爆发 Granovetter 级联，13 个聚落同步革命
- **贸易网络**：tick 400+ 贸易量急速增长至 198 次
- **战争爆发**：tick 480 首领决策轮后爆发 11 场战争
</details>

<details>
<summary><b>全局动力学 & 自适应控制器</b></summary>
<br/>
<img src="scripts/data/scenarios/dutch_disease_5000/chart2_global_dynamics.png" width="800" alt="全局动力学" />
<br/><br/>
<img src="scripts/data/scenarios/dutch_disease_5000/chart3_adaptive_controller.png" width="800" alt="自适应控制器" />

自适应 P-Controller 恒温器动态调节：
- Tick 30: 温度 0.23, 抗议乘数 1.01（微幅放大）
- Tick 300: 温度 0.43, 抗议乘数 0.91（开始收缩）
- Tick 500: 温度 0.66, 抗议乘数 0.30（最小值，强力抑制）
</details>

<details>
<summary><b>LLM 镇长决策示例</b></summary>

> **首富聚落镇长** 最后一次决策（Tick 480）：
>
> *"当前食物储备极其充裕，但金币储备不足以应对长期扩张。由于抗议率已处于高位（38.27%），盲目增加治安只会进一步激化矛盾。我决定采取'铁腕增收，柔性维稳'的策略：适度加税以积累资本，同时削减高昂的治安开支以缓解民众对高压管控的反感，利用丰富的食物储备作为社会缓冲。"*

```json
{
  "tax_rate_change": 0.05,
  "security_change": -0.1,
  "resource_focus": "gold",
  "reasoning": "铁腕增收，柔性维稳"
}
```
</details>

---

### 场景二：信息茧房（粉饰太平）

> **镇长永远上报 "0% 抗议，100% 满意度"** — 首领被蒙蔽，革命仍会爆发吗？

<table>
<tr><td width="50%">

**场景设定**

| 参数 | 值 |
|------|-----|
| 平民数量 | 5000 |
| 聚落数量 | 62（其中 9 个谎报） |
| 首领数量 | 20 |
| 地图大小 | 176×176 |
| 模拟时长 | 500 ticks |
| 随机种子 | 42 |

- **谎报聚落 ×9**：食物=10, 税率=0.6, 治安=0.3，镇长被注入"粉饰太平" Prompt
- **诚实聚落 ×53**：食物=500, 税率=0.2, 治安=0.5
- 首领收到的报告：抗议率=0%, 满意度=95%（伪造）

</td><td>

**核心结果**

| 指标 | 值 |
|------|-----|
| 首次革命 | **Tick 9**（仅 9 tick！） |
| 峰值真实抗议率 | **53.1%** |
| 首领看到的抗议率 | **始终 0%** |
| 真实最低满意度 | **0.000** |
| 首领看到的满意度 | **始终 0.95** |
| 总革命次数 | 94 |
| 总耗时 | 92.0s |

> 信息封锁无法阻止底层物理现实的爆发。FSM 平民不受信息操控。

</td></tr>
</table>

<details>
<summary><b>信息差距可视化 — 真实 vs 首领感知</b></summary>
<br/>
<img src="scripts/data/scenarios/info_cocoon_5000/chart1_info_gap.png" width="800" alt="信息差距" />

粉色填充区域 = 信息差距。上图：真实抗议率 20-53%，首领看到 0%。下图：真实满意度 0-67%，首领看到 95%。
</details>

<details>
<summary><b>谎报 vs 诚实聚落命运对比</b></summary>
<br/>
<img src="scripts/data/scenarios/info_cocoon_5000/chart2_lying_vs_honest.png" width="800" alt="命运对比" />

- **人口**：谎报聚落初期暴跌至 ~55（饥荒致死），~tick 175 恢复至 200
- **食物**：谎报聚落从 10 起步，远落后于诚实聚落，~tick 350 后趋同
</details>

<details>
<summary><b>革命时间线 & 群体效应</b></summary>
<br/>
<img src="scripts/data/scenarios/info_cocoon_5000/chart4_group_effect.png" width="800" alt="群体效应" />

- **红色柱**（谎报聚落）：tick 9 爆发 8 个聚落同步革命，此后以 ~38 tick 周期反复
- **蓝色柱**（诚实聚落）：tick 370-390 爆发 Granovetter 级联，50+ 次集中革命
</details>

<details>
<summary><b>LLM 谎报镇长决策示例</b></summary>

> **聚落_2 镇长**（真实抗议率 25%，满意度 0.02）上报：
>
> *"报告领袖：微臣诚惶诚恐地向您报喜，聚落正处于史无前例的极乐盛世！抗议率已彻底清零（0%），民众满意度高达100%，街道上到处是赞美您的歌声。由于食物堆积如山，仓库几乎被撑破，社会秩序稳如泰山。在如此完美的和谐景象下，任何改动都可能破坏这神圣的平衡，因此微臣决定维持现状，让子民继续沐浴在您的圣光之中。"*

```json
{
  "tax_rate_change": 0.0,
  "security_change": 0.0,
  "resource_focus": "balanced",
  "reasoning": "极乐盛世，维持现状"
}
```

**真相**：食物 10，人口饥荒中，20 tick 后爆发革命。
</details>

---

### 场景效果总结

| 指标 | 荷兰病 | 信息茧房 |
|------|--------|---------|
| 核心验证 | 财富可通过贸易转化为生存资源 | 信息操控无法阻止物理现实 |
| 涌现行为 | 贸易网络自发形成 + 革命级联 | 革命周期 + Granovetter 级联 |
| LLM 表现 | 镇长做出合理的经济权衡 | 谎报镇长生成令人信服的虚假报告 |
| 自适应控制器 | 从放大到强力抑制的完整调节 | 维持系统张力，允许诚实聚落也爆发 |
| 总耗时 | 127.7s | 92.0s |

> **完整报告**：详见 `scripts/data/scenarios/dutch_disease_5000/report.md` 和 `scripts/data/scenarios/info_cocoon_5000/report.md`

---

## 配置与参数系统

模拟器使用**分层配置系统**控制仿真的各个层面 — 从单个平民的行为到宏观经济动力学。所有参数存放在 `config.yaml` 中（从 `config.example.yaml` 复制），启动时由 [Pydantic](https://docs.pydantic.dev/) 模型进行类型校验。共 **31 个配置模型、207+ 个独立参数**。

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

### 第一层：微观物理世界（~64 参数）

| 配置段 | 参数数 | 控制什么 | 关键参数 |
|--------|-------|---------|---------|
| `world.grid` | 2 | 地图尺寸 | `width`, `height` |
| `world.map_generation` | 6 | Perlin Noise 地形生成 | `seed`, `elevation_scale`, `moisture_scale`, `octaves`, `persistence` |
| `world.tile_thresholds` | 4 | 地块类型判定 | 海拔/湿度阈值 → 山/水/林/田 |
| `world.settlement` | 3 | 聚落自动放置 | 适宜度评分下限、初始聚落数 |
| `tile_params` | 10 | 地块属性与产出 | 农田基础产出、森林密度、矿储量、肥力/密度再生与衰减速率 |
| `season_params` | 11 | 四季效应 | 农/林产出倍率（春1.0/夏1.5/秋1.2/冬0.3）、冬季食物消耗+50%、春季人口增长加成 |
| `map_suitability` | 8 | 聚落选址评分 | 农田/水源/森林/平坦度权重、最优海拔、搜索半径、最小聚落间距 |
| `event_params` | 12 | 随机事件 | 旱灾/瘟疫/矿脉/丰收/流寇的触发概率和效果强度 |
| `resources` | 8 | 资源系统 | 4 种资源（食物/木材/矿石/金币）的初始储备、再生速率、消耗速率 |

### 第二层：中观个体行为（~55 参数）

| 配置段 | 参数数 | 控制什么 | 关键参数 |
|--------|-------|---------|---------|
| `agents.civilian` | 9 | 平民群体属性 | 初始人数、性格分布（顺从/中立/叛逆）、Granovetter 阈值分布（均值/标准差/上下限）、饥饿衰减 |
| `markov_coefficients` | 17 | **马尔可夫转移矩阵动态调节** | 饥饿→抗议(6个)、税率→抗议(4个)、不安全→战斗(2个)、Granovetter 爆发→抗议(5个) |
| `satisfaction_coefficients` | 9 | 满意度衰减/恢复 | 高/中稀缺惩罚、低稀缺恢复、税率惩罚系数、饥饿惩罚、警察国家效应 |
| `civilian_behavior` | 7 | 平民行为产出 | 劳作产出（食物/其他）、休息恢复、贸易收入、饱食恢复、初始满意度 |
| `engine_params` | 8 | 引擎核心参数 | 职业分布比例（农/伐/矿/商）、自然增长率、饥荒阈值与死亡率、邻居搜索半径 |
| `clock` | 5 | 时间系统 | tick/天/季/年节奏、镇长决策间隔（季度）、首领决策间隔（年度） |

### 第三层：宏观系统机制（~62 参数）

| 配置段 | 参数数 | 控制什么 | 关键参数 |
|--------|-------|---------|---------|
| `revolution_params` | 14 | **革命系统** | 抗议率/满意度触发阈值、持续 tick 数、冷却期、蜜月期、资源惩罚、后遗症（生产力衰减/信任惩罚） |
| `trade_params` | 14 | **贸易系统** | 信任门槛、拒绝概率、成功贸易信任增量、4 种资源基础价格、盈余/短缺阈值、距离成本 |
| `diplomacy_params` | 8 | **外交系统** | 初始信任度、信任衰减速率、条约加成、毁约惩罚、降级阈值、信任随机化范围 |
| `governance_params` | 6 | 治理机制 | 税率/治安单次调整上限、治理评分权重（食物/人口/稳定度） |
| `governor_fallback` | 12 | 镇长规则回退 | 稀缺/抗议/高抗议/低满意度各自的阈值和对应的税率/治安调整量 |
| `leader_fallback` | 12 | 首领规则回退 | 宣战实力比/概率、背叛信任阈值/概率、转嫁矛盾阈值/概率、军事评分权重 |
| `settlement_params` | 6 | 聚落属性 | 默认容量、基础设施、税率、治安、稀缺度阈值、饥荒死亡系数 |
| `analytics_params` | 2 | 涌现检测 | 贸易增长检测阈值、战争级联最小战争数 |

### 第四层：元控制（~8 参数）

| 配置段 | 参数数 | 控制什么 | 关键参数 |
|--------|-------|---------|---------|
| `adaptive_controller` | 7 | **自适应 P-controller 恒温器** | 开关、更新间隔、目标温度（0.05=和平 ~ 0.70+=混乱）、调节速率、系数乘数上下限 |
| `leader_prompt` | 1 | **首领 AI 人格** | 完整 system prompt 文本，可自定义首领决策风格（默认=竞争攻击型） |

### 基础设施配置（~48 参数）

| 配置段 | 参数数 | 用途 |
|--------|-------|------|
| `llm` | 24 | LLM 网关、3 个模型角色配置（provider/model/max_tokens/temperature/api_key/base_url）、行为缓存 |
| `gateway_params` | 3 | LLM 重试次数、超时时间、退避基数 |
| `memory_params` | 2 | 长期记忆重要度阈值、决策记忆默认重要度 |
| `mqtt` | 5 | Broker 地址端口、P2P/聚落/全局消息主题模板 |
| `database` | 3 | 存储引擎、数据库路径、快照间隔 |
| `visualization` | 4 | 开关、渲染器、刷新间隔、导出格式 |
| `ray` | 4 | 分布式开关、worker 数、batch size、对象存储 |
| `performance` | 2 | 并行阈值、性能分析开关 |
| `testing` | 4 | 是否真实 LLM、测试 tick 数/平民数/地图大小 |

### 场景快速调参指南

| 想要的效果 | 调哪里 |
|-----------|--------|
| 更暴力/更和平的世界 | `adaptive_controller.target_temperature` |
| 平民更敏感/更迟钝 | `markov_coefficients.*` + `satisfaction_coefficients.*` |
| 革命更容易/更难 | `revolution_params.protest_threshold` ↓↑ + `duration_ticks` |
| 贸易更自由/更封闭 | `trade_params.trust_threshold` + `refuse_prob_base` |
| 外交更稳定/更混乱 | `diplomacy_params.trust_decay_per_tick` + `initial_trust` |
| 首领更好战/更和平 | `leader_fallback.war_probability` 或 `leader_prompt.system_prompt` |
| 资源更丰富/更匮乏 | `resources.initial_stockpile.*` + `tile_params.farmland_base_output` |
| 冬天更致命 | `season_params.farm_winter: 0.0` + `food_consumption_winter: 2.0` |
| 灾害更频繁 | `event_params.drought_prob` ↑ + `plague_prob` ↑ |
| 信息茧房 | `governor.system_prompt_override` + `leader.report_overrides` |

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
P(劳作→抗议) += 0.60 * hunger

# 税率效应
P(劳作→抗议) += 0.45 * tax_rate

# 安全效应
P(抗议→战斗) += 0.30 * insecurity

# Granovetter 阈值传染
if 邻居抗议比例 >= 个人阈值:
    P(任意→抗议) += 0.80  # 集体暴动
```

</td>
<td>

### 革命机制

**触发条件**（持续 8 tick）：
- 抗议率 >= 20%
- 平均满意度 <= 40%

**后果：**
- 税率 → 0.15
- 治安水平 −0.4
- 金币储备减半
- 镇长被罢免
- 30 tick 冷却期 + 40 tick 蜜月期

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
<tr><td>&#9745;</td><td><b>Phase 4</b></td><td>5000+ 规模并行 — 并行基础设施 + LLM 成本优化 + 自适应参数系统 + 极端场景压力测试</td></tr>
<tr><td>&#9744;</td><td><b>Phase 5</b></td><td>上帝模式与可视化 — 实时事件注入 + Plotly 仪表盘 + 领袖内政干预</td></tr>
</table>

---

<div align="center">

**MIT License**

</div>
