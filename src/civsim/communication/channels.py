"""消息频道定义。

定义 P2P、P2G 和广播频道的 MQTT 主题模式。
"""

from __future__ import annotations

from enum import Enum


class ChannelType(Enum):
    """频道类型枚举。"""

    P2P = "p2p"
    SETTLEMENT = "settlement"
    FACTION = "faction"
    GLOBAL = "global"


# MQTT 主题模板
_TOPIC_TEMPLATES: dict[ChannelType, str] = {
    ChannelType.P2P: "civsim/agent/{agent_id}/direct",
    ChannelType.SETTLEMENT: "civsim/settlement/{settlement_id}/broadcast",
    ChannelType.FACTION: "civsim/faction/{faction_id}/broadcast",
    ChannelType.GLOBAL: "civsim/world/broadcast",
}


def build_topic(
    channel_type: ChannelType,
    agent_id: int | None = None,
    settlement_id: int | None = None,
    faction_id: int | None = None,
) -> str:
    """构建 MQTT 主题字符串。

    Args:
        channel_type: 频道类型。
        agent_id: Agent ID（P2P 频道需要）。
        settlement_id: 聚落 ID（聚落频道需要）。
        faction_id: 阵营 ID（阵营频道需要）。

    Returns:
        MQTT 主题字符串。

    Raises:
        ValueError: 缺少必要参数。
    """
    template = _TOPIC_TEMPLATES[channel_type]

    if channel_type == ChannelType.P2P:
        if agent_id is None:
            msg = "P2P 频道需要 agent_id"
            raise ValueError(msg)
        return template.format(agent_id=agent_id)

    if channel_type == ChannelType.SETTLEMENT:
        if settlement_id is None:
            msg = "聚落频道需要 settlement_id"
            raise ValueError(msg)
        return template.format(settlement_id=settlement_id)

    if channel_type == ChannelType.FACTION:
        if faction_id is None:
            msg = "阵营频道需要 faction_id"
            raise ValueError(msg)
        return template.format(faction_id=faction_id)

    return template
