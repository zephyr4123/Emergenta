# Emergenta：一个支持 5000+ Agent 并发的混合智能文明模拟器

> 天津大学 记忆与推理实验室 | 作者：黄素翔 | 指导教师：王征

---

## 引言：群体智能模拟的成本困境

近年来，基于大语言模型（LLM）的多智能体系统成为 AI 研究的热点方向。从斯坦福"小镇"（Generative Agents）到清华 AgentSociety，研究者们试图让 AI Agent 在虚拟世界中自主交互，观察涌现出的社会行为。

然而，这些系统面临一个共同的瓶颈：**成本与规模的不可调和矛盾**。

设 Agent 总数为 $N$，仿真总步数为 $T$，每次 LLM 调用的平均 token 数为 $\bar{k}$，单位 token 价格为 $p$，则全量 LLM 方案的总成本为：

$$C_{full} = N \cdot T \cdot \bar{k} \cdot p$$

以 $N=5000,\ T=500,\ \bar{k}=500,\ p=1.5 \times 10^{-7}$（GPT-4o-mini）代入：

$$C_{full} = 5000 \times 500 \times 500 \times 1.5 \times 10^{-7} = \$187.5$$

若使用 GPT-4o（$p \approx 2.5 \times 10^{-6}$），成本飙升至 **$3,125**。这使得大规模社会模拟在实际研究中难以反复迭代验证。

**核心问题**：能否在保持宏观社会涌现效果的前提下，将 LLM 调用成本降低两个数量级？

![系统运行全景](docs/images/hero-demo.gif)
*图 1：Emergenta 系统运行全景 — 启动配置 → 数据总览 → 实时地图 → 场景注入 → 涌现观察*

![系统架构图](docs/images/architecture.png)
*图 2：Emergenta 三层金字塔架构*

---

## 一、系统设计：三层混合智能金字塔

我们提出了一种**层次化混合智能架构**，核心思想是：**智能复杂度与社会层级匹配**。

在真实社会中，并非每个人每时每刻都在做复杂决策 — 大多数人的日常行为遵循简单的习惯性模式（上班、吃饭、休息），只有管理者和领导者需要进行复杂的战略推理。我们将这一观察映射到系统架构中。

### 1.1 第一层：平民层（Population Base）

| 属性 | 规格 |
|------|------|
| 数量 | 100 - 5,000+ |
| 智能模型 | 有限状态机（FSM）+ 马尔可夫链 |
| LLM 依赖 | **零** |
| 决策频率 | 每 tick |
| 计算成本 | 近零（纯矩阵运算） |

每个平民 Agent 拥有 **7 种离散状态**：劳作（$s_0$）、休息（$s_1$）、交易（$s_2$）、社交（$s_3$）、迁徙（$s_4$）、抗议（$s_5$）、战斗（$s_6$）。

#### 动态马尔可夫转移矩阵

Agent $i$ 在时刻 $t$ 的状态转移由一个 $7 \times 7$ 动态转移矩阵 $\mathbf{P}^{(i)}(t)$ 决定。该矩阵在每个 tick 实时计算：

$$\mathbf{P}^{(i)}(t) = \text{normalize}\Big(\mathbf{M}_{base}^{(\pi_i)} + \Delta\mathbf{H}(t) + \Delta\mathbf{T}(t) + \Delta\mathbf{S}(t) + \Delta\mathbf{G}(t)\Big)$$

其中：

- $\mathbf{M}_{base}^{(\pi_i)} \in \mathbb{R}^{7 \times 7}$：性格 $\pi_i \in \{\text{顺从, 中立, 叛逆}\}$ 对应的基础转移矩阵
- $\Delta\mathbf{H}(t)$：**饥饿效应修正项**
- $\Delta\mathbf{T}(t)$：**税率效应修正项**
- $\Delta\mathbf{S}(t)$：**治安效应修正项**
- $\Delta\mathbf{G}(t)$：**Granovetter 传染修正项**

每个修正项通过环境变量乘以可配置系数对特定转移概率进行增量调节。以饥饿效应为例：

$$\Delta H_{s_0 \to s_5}(t) = \alpha_1 \cdot h_i(t) \cdot \mu_p$$

$$\Delta H_{s_0 \to s_4}(t) = \alpha_2 \cdot h_i(t)$$

$$\Delta H_{s_3 \to s_5}(t) = \alpha_3 \cdot h_i(t) \cdot \mu_p$$

其中 $h_i(t) \in [0,1]$ 是 Agent $i$ 的饥饿度，$\mu_p$ 是自适应控制器提供的抗议系数乘数，$\alpha_1, \alpha_2, \alpha_3$ 是可配置系数（默认 $\alpha_1=0.60,\ \alpha_2=0.15,\ \alpha_3=0.50$）。

行归一化确保概率约束：

$$P_{ij}^{(i)}(t) = \frac{\max(0,\ \tilde{P}_{ij}^{(i)}(t))}{\sum_{k=0}^{6} \max(0,\ \tilde{P}_{ik}^{(i)}(t))}$$

#### Granovetter 阈值传染模型

这是产生集体行动级联的关键机制。每个平民有一个个人阈值 $\theta_i \sim \mathcal{N}(\mu_\theta, \sigma_\theta^2)$，被截断到 $[\theta_{min}, \theta_{max}]$（默认 $\mu_\theta=0.18,\ \sigma_\theta=0.12$）。

设 Agent $i$ 的邻域 $\mathcal{N}_i$（Moore 邻域，半径 $r=3$）中的抗议比例为：

$$\rho_i(t) = \frac{|\{j \in \mathcal{N}_i : s_j(t) = s_5\}|}{|\mathcal{N}_i|}$$

当 $\rho_i(t) \geq \theta_i$ 时，Granovetter 传染触发，对转移矩阵施加大幅修正：

$$\Delta G_{s_k \to s_5}(t) = \begin{cases} \beta_k \cdot \mu_g & \text{if } \rho_i(t) \geq \theta_i \\ 0 & \text{otherwise} \end{cases} \quad \forall k \in \{0,1,2,3,4\}$$

其中 $\beta_k$ 是各状态的突变系数（默认 $\beta_0=0.80,\ \beta_3=0.85$），$\mu_g$ 是自适应 Granovetter 乘数。

这产生了**临界点动力学** — 不满情绪可以在阈值以下静默积累，一旦突破临界比例便引发雪崩式级联。

#### 满意度动力学

每个 Agent 维护一个满意度变量 $\sigma_i(t) \in [0,1]$，受多因素驱动：

$$\sigma_i(t+1) = \sigma_i(t) + \underbrace{\delta_{scarcity}}_{\text{资源匮乏}} + \underbrace{\delta_{tax}}_{\text{税负压力}} + \underbrace{\delta_{hunger}}_{\text{饥饿}} + \underbrace{\delta_{security}}_{\text{治安效应}} + \underbrace{\delta_{honeymoon}}_{\text{革命蜜月期}}$$

其中每个分量根据聚落状态计算。例如：

$$\delta_{scarcity} = \begin{cases} -\gamma_h \cdot \mu_{pen} & \text{if } \xi > 0.5 \\ -\gamma_m \cdot \mu_{pen} & \text{if } 0.3 < \xi \leq 0.5 \\ +\gamma_l \cdot \mu_{rec} & \text{if } \xi < 0.2 \end{cases}$$

$\xi$ 为聚落稀缺指数，$\mu_{pen}$ 和 $\mu_{rec}$ 分别是自适应惩罚和恢复乘数。

### 1.2 第二层：镇长层（Middle Management）

| 属性 | 规格 |
|------|------|
| 数量 | 3 - 50 |
| 智能模型 | 轻量级 LLM（如 GPT-4o-mini / Gemini Flash） |
| 决策频率 | 每季度（每 $T_{season} = T_{tick/day} \times D_{season}$ tick） |
| 决策域 | 税率 $\tau$、治安投入 $\sigma$、资源分配策略 |

镇长 Agent 每个季度接收管辖聚落的**聚合统计向量**：

$$\mathbf{x}_{gov} = \left[ N_{pop},\ \bar{\sigma},\ \rho_{protest},\ \xi_{scarcity},\ \bar{h},\ \tau_{current},\ s_{current} \right]$$

通过 Prompt 工程将此向量格式化后送入 LLM，输出结构化 JSON 决策：

```json
{
  "tax_rate_change": -0.05,
  "security_change": 0.12,
  "resource_focus": "food",
  "reasoning": "当前满意度极低且抗议率逼近临界点..."
}
```

**信息不对称**：镇长的观测函数 $\mathcal{O}_{gov}$ 是一个有损聚合：

$$\mathcal{O}_{gov}: \{(s_i, h_i, \sigma_i, \theta_i)\}_{i \in \mathcal{S}} \mapsto \mathbf{x}_{gov}$$

个体多样性信息（性格分布、阈值分布）在聚合过程中被丢弃，镇长只能根据均值做决策。

**规则回退**：当 LLM 不可用时，系统使用基于阈值的规则决策：

$$\Delta\tau = \begin{cases} -0.05 & \text{if } \xi > 0.5 \\ -0.03 & \text{if } \rho > 0.4 \\ +0.03 & \text{if } \xi < 0.2 \wedge \rho < 0.1 \wedge \bar{\sigma} > 0.6 \end{cases}$$

### 1.3 第三层：首领层（Strategic Command）

| 属性 | 规格 |
|------|------|
| 数量 | 2 - 15 |
| 智能模型 | 前沿 LLM（如 GPT-4o / Claude Sonnet） |
| 决策频率 | 每半年（每 $2 \times T_{season}$ tick） |
| 决策域 | 外交 $\mathcal{D}$、军事 $\mathcal{M}$、全局政策 $\mathcal{P}$ |

首领 Agent 拥有**长期情景记忆** $\mathcal{E} = \{(t_k, e_k, w_k)\}$，记录外交历史、条约、背叛事件及其重要度权重 $w_k$。

外交决策空间：

$$\mathcal{D} = \{\text{propose\_alliance},\ \text{declare\_war},\ \text{offer\_peace},\ \text{break\_treaty},\ \text{trade\_embargo},\ \text{none}\}$$

首领间的信任度 $\tau_{AB}(t)$ 服从衰减-事件驱动动力学：

$$\tau_{AB}(t+1) = \tau_{AB}(t) - \lambda_{decay} + \sum_{e \in \mathcal{E}_t} \Delta\tau_e$$

其中 $\lambda_{decay}$ 是自然衰减率，$\Delta\tau_e$ 是事件驱动的信任变化（签约 $+0.1$，毁约 $-0.3$，成功贸易 $+0.05$）。

当 $\tau_{AB}$ 降至阈值以下，外交关系自动降级。

### 1.4 成本分析

设镇长数 $N_g$，首领数 $N_l$，镇长决策间隔 $T_g$ tick，首领决策间隔 $T_l$ tick。混合架构的 LLM 调用总次数：

$$C_{hybrid} = \frac{T}{T_g} \cdot N_g \cdot \bar{k}_g \cdot p_g + \frac{T}{T_l} \cdot N_l \cdot \bar{k}_l \cdot p_l$$

以 $N_g=10,\ N_l=3,\ T_g=120,\ T_l=240,\ T=500$ 代入：

$$C_{hybrid} = \frac{500}{120} \times 10 \times 800 \times 1.5 \times 10^{-7} + \frac{500}{240} \times 3 \times 1500 \times 1.5 \times 10^{-7} \approx \$0.005 + \$0.001 \approx \$0.006$$

$$\text{成本比} = \frac{C_{hybrid}}{C_{full}} = \frac{0.006}{187.5} \approx 0.003\%$$

**成本降低超过 99.99%**。

![技术栈](docs/images/tech-stack.png)
*图 3：Emergenta 技术栈全景*

---

## 二、世界引擎：确定性物理环境

与 LLM 驱动的"幻觉"环境不同，Emergenta 的世界物理是**完全确定性**的 — 资源产出、地理约束、经济规则全部基于数学公式，不存在 LLM 幻觉问题。

### 2.1 Perlin Noise 地图生成

使用双层 Perlin Noise 生成海拔场 $E(x,y)$ 和湿度场 $M(x,y)$：

$$E(x,y) = \sum_{i=0}^{O-1} p^i \cdot \text{noise}\left(\frac{x}{S_E \cdot 2^{-i}}, \frac{y}{S_E \cdot 2^{-i}}\right)$$

其中 $O$ 为倍频数，$p$ 为持续度，$S_E$ 为尺度参数。归一化到 $[0,1]$ 后，通过阈值映射为地块类型：

$$\text{TileType}(x,y) = \begin{cases} \text{Mountain} & \text{if } E > 0.70 \\ \text{Water} & \text{if } M > 0.60 \\ \text{Forest} & \text{if } E > 0.50 \\ \text{Farmland} & \text{if } M > 0.30 \\ \text{Barren} & \text{otherwise} \end{cases}$$

### 2.2 季节系统与食物经济

食物经济的核心方程：

$$F_{net}(t) = \underbrace{N_{farmer}^{work}(t) \cdot \omega_f \cdot m_{season}(t)}_{\text{产出}} - \underbrace{N_{pop}(t) \cdot c_f \cdot m_{winter}(t)}_{\text{消耗}}$$

其中 $\omega_f$ 为农民劳作产出基数，$c_f$ 为人均消耗率，$m_{season}(t)$ 为季节产出倍率，$m_{winter}(t)$ 为冬季消耗倍率。

| 季节 | 产出倍率 $m_{season}$ | 消耗倍率 $m_{winter}$ | 特殊效果 |
|------|---------------------|---------------------|---------|
| 春 | 1.0 | 1.0 | 人口增长率 $\times 1.5$ |
| 夏 | 1.5 | 1.0 | — |
| 秋 | 1.2 | 1.0 | 贸易收益 $\times 1.3$ |
| 冬 | **0.45** | **1.3** | 迁徙困难 |

冬季的食物净收支可能为负，触发 $\xi \uparrow \to h_i \uparrow \to \sigma_i \downarrow \to \rho \uparrow$ 的危机级联。

### 2.3 聚落稀缺指数

聚落 $s$ 的稀缺指数定义为：

$$\xi_s(t) = \max\left(0,\ 1 - \frac{F_s(t)}{N_s(t) \cdot \phi}\right)$$

其中 $F_s(t)$ 是食物储备，$N_s(t)$ 是人口，$\phi$ 是人均满足阈值。$\xi \to 1$ 表示极端匮乏。

---

## 三、涌现系统：没有剧本的社会动力学

以下现象**没有被显式编程**，完全从 Agent 交互中涌现：

### 3.1 革命级联

革命触发需同时满足两个条件，持续 $D_{rev}$ tick：

$$\rho_s(t) \geq \rho_{thresh} \quad \wedge \quad \bar{\sigma}_s(t) \leq \sigma_{thresh}$$

默认 $\rho_{thresh}=0.25,\ \sigma_{thresh}=0.40,\ D_{rev}=8$。

革命后果：

- 税率重置：$\tau_s \leftarrow 0.15$
- 资源惩罚：$F_s \leftarrow F_s \cdot (1 - \eta_F),\quad G_s \leftarrow G_s \cdot (1 - \eta_G)$
- 人口损失：$N_s \leftarrow N_s \cdot (1 - \eta_N)$
- 冷却期 $T_{cool}$ + 蜜月期 $T_{honey}$

这形成了一个**极限环**：高压 → 抗议 → 革命 → 重置 → 蜜月恢复 → 稳定 → 新一轮高压…

### 3.2 贸易网络涌现

聚落间贸易的发生条件：

$$\frac{F_{seller}}{N_{seller}} > \phi_{surplus} \quad \wedge \quad \frac{F_{buyer}}{N_{buyer}} < \phi_{deficit} \quad \wedge \quad \tau_{AB} > \tau_{trade}$$

每次成功贸易：$\tau_{AB} \leftarrow \tau_{AB} + \Delta\tau_{trade}$

随时间推移，高频贸易对的信任不断累积，形成稳定的贸易网络拓扑。

### 3.3 信息茧房效应

在实验中，约 25% 聚落的镇长被注入"粉饰太平"Prompt，向首领谎报 $\bar{\sigma}=0.95,\ \rho=0$。

实际结果：

| 指标 | 首领感知 | 真实值 |
|------|---------|-------|
| 满意度 | 0.95 | **0.005** |
| 抗议率 | 0% | **51.9%** |
| 首次革命 | — | **Tick 9** |

**底层物理现实不受信息操控** — FSM 平民的 $h_i(t)$ 不会因为镇长的谎言而下降。

![Dashboard 数据总览](docs/images/dashboard-overview.png)
*图 4：Dashboard 数据总览 — 实时监控人口、资源、满意度、革命*

---

## 四、自适应恒温器：P-Controller 动态平衡

大规模 Agent 系统面临参数敏感性问题。我们引入 P-controller 恒温器，定义系统温度：

$$\mathcal{T}(t) = w_\rho \cdot \bar{\rho}(t) + w_r \cdot f_{rev}(t) + w_w \cdot n_{war}(t)$$

其中 $w_\rho, w_r, w_w$ 是可配置权重（默认 $0.30, 0.25, 0.15$），$f_{rev}$ 是窗口内革命频率，$n_{war}$ 是战争数。

误差信号与调节：

$$e(t) = \mathcal{T}(t) - \mathcal{T}_{target}$$

$$\mu_k(t+1) = \text{clip}\left(\mu_k(t) + K_p \cdot e(t),\ \mu_{min},\ \mu_{max}\right)$$

恒温器输出四个自适应乘数 $\mu_p,\ \mu_g,\ \mu_{cool},\ \mu_{rec}$，分别调节抗议系数、Granovetter 突变量、革命冷却期和满意度恢复速度。

![实时地图](docs/images/dashboard-map.png)
*图 5：实时地图 — 5000 个 Agent 实时散点 + 马尔可夫状态转移抽样*

---

## 五、造物主面板：交互式实验平台

Emergenta 提供了一个**实时交互式 Web 面板**（基于 Plotly Dash），8 个标签页覆盖仿真的全部维度：

| 标签页 | 功能 | 交互能力 |
|--------|------|---------|
| 数据总览 | 人口曲线、资源趋势、满意度、革命时间线 | 实时刷新 |
| 实时地图 | Agent 散点 + 地块热力图 + 马尔可夫转移滚动 | 缩放/平移 |
| 聚落观察 | 排行榜（进度条、发光指示器、颜色分级） | — |
| 外交与贸易 | 外交网络图 + 贸易桑基图 | — |
| 自适应控制 | 恒温器温度曲线 + 四个乘数动态 | — |
| 造物主面板 | 场景注入 + 灾难事件 + 外交干预 + 时间控制 | **全交互** |
| AI 神经元 | LLM 决策推理全文实时展示 | 筛选镇长/首领 |
| 参数配置 | 200+ 参数滑块面板（7 大分类） | **实时生效** |

启动体验：一条命令 → 浏览器自动打开配置向导 → 选择规模 → 点击启动。

![启动向导](docs/images/launch-wizard-llm-ready.png)
*图 6：启动向导 — 浏览器端配置页面*

![造物主面板](docs/images/dashboard-god-mode.png)
*图 7：造物主面板 — 场景注入、时间控制、事件日志*

![聚落排行榜](docs/images/dashboard-settlements.png)
*图 8：聚落排行榜 — 进度条、发光圆点、颜色分级*

![AI 神经元](docs/images/dashboard-ai-speeches.png)
*图 9：AI 神经元 — LLM 镇长/首领实时决策推理*

![自适应控制器](docs/images/dashboard-self-adjust.png)
*图 10：自适应 P-Controller 恒温器动态*

![参数配置](docs/images/dashboard-config.png)
*图 11：200+ 运行时参数实时调节面板*

---

## 六、实验场景与观察

### 场景一：荷兰病（资源诅咒）

**设定**：一个聚落 $G_s=50000,\ F_s=0$，农田肥力降至 $f=0.02$。其余聚落 $F_s=1500,\ G_s=30$。

**核心问题**：$G \gg 0,\ F=0$ 的聚落能否通过贸易存活？

**观察**：富裕聚落通过 $G \to F$ 贸易存活，但人口先暴跌后恢复。78% 的金币用于购粮。贸易网络在模拟早期爆发式增长。

### 场景二：信息茧房

**设定**：25% 聚落 $F_s=30,\ \tau=0.65$，镇长 Prompt 注入 $\hat{\sigma}=0.95,\ \hat{\rho}=0$。

**核心问题**：信息操控 $\mathcal{O}_{gov}^{fake} \neq \mathcal{O}_{gov}^{real}$ 能否阻止底层革命？

**观察**：**不能。** FSM 平民的物理状态不受信息层影响。$h_i(t)$ 持续上升 → $\sigma_i(t)$ 持续下降 → $\rho(t)$ 突破 $\theta_i$ → 级联革命。首领在全程中收到的都是"太平盛世"报告。

### 场景三：世界末日

**设定**：所有聚落 $F_s=30,\ G_s=5$，70% 农田 $f \to 0.03$。

**核心问题**：全局同时崩溃下，文明存活率 $\frac{N_{final}}{N_0} = ?$

**观察**：人口断崖式暴跌，但无一聚落完全灭亡。LLM 镇长自主选择"降税 + 治安 + 保粮"策略。自适应恒温器 $\mu_p \downarrow,\ \mu_{rec} \uparrow$ 持续调控。

---

## 七、研究意义与展望

### 解决的核心问题

1. **规模化群体智能模拟的成本瓶颈**：$C_{hybrid}/C_{full} < 0.01\%$，实现 5000+ Agent 并发仿真
2. **涌现行为的可观测性**：实时造物主面板 + 马尔可夫转移可视化
3. **参数空间探索**：200+ 可调参数 + 场景注入引擎，支持系统性实验设计
4. **可复现性**：确定性物理引擎 + 固定种子 = 完全可复现的实验

### 可探索的研究问题

- 去中心化 Agent 如何自组织为层级社会？
- 集体行动级联的临界条件 $(\rho_{thresh}, \theta_i)$ 与社会结构的关系？
- 信息不对称 $\mathcal{O}_{gov}^{real} \neq \mathcal{O}_{leader}^{received}$ 对治理稳定性的影响？
- 阈值分布 $\theta_i \sim \mathcal{N}(\mu, \sigma^2)$ 的参数如何影响文明韧性？
- 自适应控制器的目标温度 $\mathcal{T}_{target}$ 与涌现丰富度的关系？

### 未来方向

- **科技树系统**：让文明发展农业、冶金、军事等技术路线
- **文化传播**：意识形态在 Agent 社交网络中的传播和演化
- **跨文明外交**：多个独立文明的大规模地缘政治模拟
- **强化学习集成**：用 RL 训练最优治理策略 $\pi^*_{gov}$

---

## 开源地址

项目已完全开源：

**GitHub**：[https://github.com/你的用户名/AI-CIVILIZATION-SIMULATOR](https://github.com/你的用户名/AI-CIVILIZATION-SIMULATOR)

欢迎 Star、Fork 和贡献代码。

---

*天津大学 记忆与推理实验室*
*联系方式：huangsuxiang5@gmail.com*
