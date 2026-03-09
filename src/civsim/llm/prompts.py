"""Prompt 模板管理。

为镇长 Agent 提供感知数据格式化和决策输出模板。
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
