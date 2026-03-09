"""消息协议与序列化。

定义 Agent 间通信的消息类型、结构和序列化规则。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class MessageType(Enum):
    """消息类型枚举。"""

    # 外交消息
    DIPLOMATIC_PROPOSAL = "diplomatic_proposal"
    DIPLOMATIC_RESPONSE = "diplomatic_response"
    WAR_DECLARATION = "war_declaration"
    PEACE_OFFER = "peace_offer"

    # 政策指令
    POLICY_DIRECTIVE = "policy_directive"

    # 状态汇报
    STATUS_REPORT = "status_report"

    # 贸易消息
    TRADE_OFFER = "trade_offer"
    TRADE_RESPONSE = "trade_response"

    # 事件通知
    EVENT_NOTIFICATION = "event_notification"


@dataclass
class Message:
    """通信消息数据类。

    Attributes:
        msg_type: 消息类型。
        sender_id: 发送者 Agent ID。
        receiver_id: 接收者 Agent ID（None 表示广播）。
        tick: 发送时的 tick。
        content: 消息内容。
        metadata: 附加元数据。
    """

    msg_type: MessageType
    sender_id: int
    receiver_id: int | None
    tick: int
    content: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """序列化为 JSON 字符串。"""
        data = asdict(self)
        data["msg_type"] = self.msg_type.value
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> Message:
        """从 JSON 字符串反序列化。"""
        data = json.loads(raw)
        data["msg_type"] = MessageType(data["msg_type"])
        return cls(**data)

    def __repr__(self) -> str:
        return (
            f"Message({self.msg_type.value}, "
            f"from={self.sender_id}, to={self.receiver_id})"
        )
