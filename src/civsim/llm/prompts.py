"""Prompt 模板管理。

为镇长和首领 Agent 提供感知数据格式化和决策输出模板。
使用 Python f-string 构建 Prompt，确保输出结构化 JSON。
"""


def build_governor_system_prompt() -> str:
    """构建镇长的系统 Prompt。

    Returns:
        系统角色描述文本。
    """
    return (
        "你是一个文明模拟器中的聚落镇长AI。你负责管理一个聚落的税率、治安投入和资源分配。\n"
        "你的目标是维持聚落的稳定和繁荣：保持食物供应充足、民众满意度高、控制抗议率。\n"
        "你必须在经济发展和社会稳定之间做出权衡。\n\n"
        "决策原则：\n"
        "1. 食物紧缺时应降低税率，增加农业投入\n"
        "2. 抗议率高时应提高治安投入，同时适当降税安抚\n"
        "3. 资源充裕时可适当加税积累储备\n"
        "4. 单次税率调整幅度不应超过 0.1\n"
        "5. 治安投入变化幅度不应超过 0.15\n"
    )


def build_governor_perception_prompt(
    settlement_name: str,
    population: int,
    food: float,
    wood: float,
    ore: float,
    gold: float,
    tax_rate: float,
    security_level: float,
    satisfaction_avg: float,
    protest_ratio: float,
    scarcity_index: float,
    per_capita_food: float,
    season: str,
    recent_events: list[str] | None = None,
    memory_context: str = "",
) -> str:
    """构建镇长的感知数据 Prompt。

    Args:
        settlement_name: 聚落名称。
        population: 当前人口。
        food: 食物储备。
        wood: 木材储备。
        ore: 矿石储备。
        gold: 金币储备。
        tax_rate: 当前税率。
        security_level: 当前治安水平。
        satisfaction_avg: 平均满意度。
        protest_ratio: 抗议率。
        scarcity_index: 食物稀缺指数。
        per_capita_food: 人均食物。
        season: 当前季节名称。
        recent_events: 近期事件列表。
        memory_context: 历史决策记忆上下文。

    Returns:
        格式化的感知 Prompt 文本。
    """
    events_text = ""
    if recent_events:
        events_text = "\n近期事件：\n" + "\n".join(f"- {e}" for e in recent_events)

    memory_text = ""
    if memory_context:
        memory_text = f"\n历史决策参考：\n{memory_context}\n"

    return (
        f"当前季节：{season}\n"
        f"聚落「{settlement_name}」状态报告：\n"
        f"- 人口：{population}\n"
        f"- 食物：{food:.1f}（人均 {per_capita_food:.2f}，稀缺指数 {scarcity_index:.2f}）\n"
        f"- 木材：{wood:.1f}\n"
        f"- 矿石：{ore:.1f}\n"
        f"- 金币：{gold:.1f}\n"
        f"- 当前税率：{tax_rate:.2f}\n"
        f"- 当前治安：{security_level:.2f}\n"
        f"- 平均满意度：{satisfaction_avg:.2f}\n"
        f"- 抗议率：{protest_ratio:.2%}\n"
        f"{events_text}"
        f"{memory_text}\n"
        "请根据以上信息做出本季度的治理决策。\n"
        "你必须严格以 JSON 格式回复，不要包含其他文字。JSON 格式如下：\n"
        '{\n'
        '  "tax_rate_change": <float, 税率变化量，范围 [-0.1, 0.1]>,\n'
        '  "security_change": <float, 治安投入变化量，范围 [-0.15, 0.15]>,\n'
        '  "resource_focus": <string, 资源重点，可选 "food"|"wood"|"ore"|"gold"|"balanced">,\n'
        '  "reasoning": <string, 决策理由，简短说明>\n'
        '}\n'
    )


def build_governor_decision_schema() -> dict:
    """返回镇长决策的 JSON Schema。

    Returns:
        用于验证 LLM 输出的 JSON Schema 字典。
    """
    return {
        "type": "object",
        "properties": {
            "tax_rate_change": {
                "type": "number",
                "minimum": -0.1,
                "maximum": 0.1,
            },
            "security_change": {
                "type": "number",
                "minimum": -0.15,
                "maximum": 0.15,
            },
            "resource_focus": {
                "type": "string",
                "enum": ["food", "wood", "ore", "gold", "balanced"],
            },
            "reasoning": {
                "type": "string",
            },
        },
        "required": ["tax_rate_change", "security_change", "resource_focus", "reasoning"],
    }


def validate_governor_decision(decision: dict) -> dict:
    """验证并修正镇长决策数据。

    确保各字段在合法范围内。超出范围的值将被截断到边界。

    Args:
        decision: LLM 返回的原始决策字典。

    Returns:
        验证后的决策字典。

    Raises:
        ValueError: 决策缺少必要字段。
    """
    required = ["tax_rate_change", "security_change", "resource_focus", "reasoning"]
    for key in required:
        if key not in decision:
            msg = f"镇长决策缺少必要字段: {key}"
            raise ValueError(msg)

    # 截断到合法范围
    decision["tax_rate_change"] = max(-0.1, min(0.1, float(decision["tax_rate_change"])))
    decision["security_change"] = max(-0.15, min(0.15, float(decision["security_change"])))

    valid_focus = {"food", "wood", "ore", "gold", "balanced"}
    if decision["resource_focus"] not in valid_focus:
        decision["resource_focus"] = "balanced"

    decision["reasoning"] = str(decision["reasoning"])[:200]

    return decision


# ============================================================
# 首领 Prompt 模板
# ============================================================


def build_leader_system_prompt() -> str:
    """构建首领的系统 Prompt。

    Returns:
        系统角色描述文本。
    """
    return (
        "你是一个文明模拟器中的阵营首领AI。你统领多个聚落，负责战略级决策。\n"
        "你的目标是：扩张阵营势力、维护内部稳定、与其他阵营进行外交博弈。\n\n"
        "决策范围：\n"
        "1. 外交行动：与其他阵营提议联盟、贸易协定、宣战或求和\n"
        "2. 政策指令：向下属聚落发布税率/治安/资源重点调整指令\n"
        "3. 军事命令：对敌对阵营发起攻击或防御\n\n"
        "决策原则：\n"
        "1. 优先保障阵营内部稳定（食物充足、抗议率低）\n"
        "2. 信任度高的阵营优先考虑联盟\n"
        "3. 实力悬殊时避免战争\n"
        "4. 贸易是互利的，优先与友好阵营交易\n"
    )


def build_leader_perception_prompt(
    faction_id: int,
    year: int,
    season: str,
    settlements_info: list[dict],
    total_population: int,
    total_resources: dict[str, float],
    avg_satisfaction: float,
    diplomatic_status: dict[int, str],
    active_treaties: list[str],
    memory_context: str = "",
) -> str:
    """构建首领的感知数据 Prompt。

    Args:
        faction_id: 阵营 ID。
        year: 当前年份。
        season: 当前季节。
        settlements_info: 下属聚落信息列表。
        total_population: 总人口。
        total_resources: 总资源。
        avg_satisfaction: 平均满意度。
        diplomatic_status: 与其他阵营的外交状态。
        active_treaties: 活跃条约描述列表。
        memory_context: 历史决策记忆。

    Returns:
        格式化的感知 Prompt 文本。
    """
    settlements_text = ""
    for s in settlements_info:
        settlements_text += (
            f"  - {s.get('name', '?')}: 人口{s.get('population', 0)}, "
            f"食物{s.get('food', 0):.0f}, 满意度{s.get('satisfaction', 0):.2f}, "
            f"抗议率{s.get('protest_ratio', 0):.1%}\n"
        )

    diplo_text = ""
    for fid, status in diplomatic_status.items():
        diplo_text += f"  - 阵营{fid}: {status}\n"

    treaties_text = ""
    if active_treaties:
        treaties_text = "\n活跃条约：\n" + "\n".join(
            f"  - {t}" for t in active_treaties
        )

    memory_text = ""
    if memory_context:
        memory_text = f"\n历史决策参考：\n{memory_context}\n"

    return (
        f"第{year}年 {season}季 | 阵营{faction_id} 战略报告\n\n"
        f"总人口：{total_population}\n"
        f"总资源：食物{total_resources.get('food', 0):.0f}, "
        f"木材{total_resources.get('wood', 0):.0f}, "
        f"矿石{total_resources.get('ore', 0):.0f}, "
        f"金币{total_resources.get('gold', 0):.0f}\n"
        f"平均满意度：{avg_satisfaction:.2f}\n\n"
        f"下属聚落：\n{settlements_text}\n"
        f"外交关系：\n{diplo_text}"
        f"{treaties_text}"
        f"{memory_text}\n"
        "请做出本年度的战略决策。严格以 JSON 格式回复：\n"
        '{\n'
        '  "diplomatic_actions": [\n'
        '    {"target_faction": <int>, '
        '"action": "propose_alliance"|"propose_trade"|'
        '"declare_war"|"offer_peace"|"none", '
        '"reasoning": <string>}\n'
        '  ],\n'
        '  "policy_directives": [\n'
        '    {"settlement_id": <int>, '
        '"tax_change": <float, -0.1~0.1>, '
        '"security_change": <float, -0.15~0.15>, '
        '"resource_focus": "food"|"wood"|"ore"|"gold"|"balanced"}\n'
        '  ],\n'
        '  "overall_strategy": <string, 总体战略简述>,\n'
        '  "reasoning": <string, 决策理由>\n'
        '}\n'
    )


def build_negotiation_prompt(
    my_faction_id: int,
    other_faction_id: int,
    topic: str,
    my_strength: dict,
    diplomatic_history: str = "",
    previous_messages: list[str] | None = None,
) -> str:
    """构建外交谈判 Prompt。

    Args:
        my_faction_id: 己方阵营 ID。
        other_faction_id: 对方阵营 ID。
        topic: 谈判议题。
        my_strength: 己方实力数据。
        diplomatic_history: 外交历史。
        previous_messages: 之前的对话消息。

    Returns:
        谈判 Prompt 文本。
    """
    history_text = ""
    if previous_messages:
        history_text = "\n之前的对话：\n" + "\n".join(
            f"  {m}" for m in previous_messages
        )
    if diplomatic_history:
        history_text += f"\n外交历史：\n{diplomatic_history}\n"

    return (
        f"你是阵营{my_faction_id}的首领，正在与阵营{other_faction_id}谈判。\n"
        f"议题：{topic}\n"
        f"你的实力：人口{my_strength.get('population', 0)}, "
        f"军力{my_strength.get('military', 0):.0f}\n"
        f"{history_text}\n"
        "请给出你的回应。严格以 JSON 格式回复：\n"
        '{"response": <string, 谈判回应>, '
        '"decision": "accept"|"reject"|"counter", '
        '"terms": <string, 条款（如有）>}\n'
    )


def validate_leader_decision(decision: dict) -> dict:
    """验证并修正首领决策数据。

    Args:
        decision: LLM 返回的原始决策字典。

    Returns:
        验证后的决策字典。
    """
    if "diplomatic_actions" not in decision:
        decision["diplomatic_actions"] = []
    if "policy_directives" not in decision:
        decision["policy_directives"] = []
    if "overall_strategy" not in decision:
        decision["overall_strategy"] = ""
    if "reasoning" not in decision:
        decision["reasoning"] = ""

    valid_actions = {
        "propose_alliance", "propose_trade",
        "declare_war", "offer_peace", "none",
    }
    for action in decision["diplomatic_actions"]:
        if action.get("action") not in valid_actions:
            action["action"] = "none"

    for directive in decision["policy_directives"]:
        if "tax_change" in directive:
            directive["tax_change"] = max(
                -0.1, min(0.1, float(directive["tax_change"])),
            )
        if "security_change" in directive:
            directive["security_change"] = max(
                -0.15, min(0.15, float(directive["security_change"])),
            )

    decision["reasoning"] = str(decision["reasoning"])[:300]
    decision["overall_strategy"] = str(
        decision["overall_strategy"],
    )[:200]

    return decision
