"""communication 模块单元测试。

验证消息协议、频道构建和 MQTT 管理器。
"""

import pytest

from civsim.communication.channels import ChannelType, build_topic
from civsim.communication.protocol import Message, MessageType


class TestMessageType:
    """测试消息类型枚举。"""

    def test_all_types_have_values(self) -> None:
        """验证所有消息类型都有字符串值。"""
        for mt in MessageType:
            assert isinstance(mt.value, str)
            assert len(mt.value) > 0

    def test_diplomatic_types_exist(self) -> None:
        """验证外交消息类型存在。"""
        assert MessageType.DIPLOMATIC_PROPOSAL is not None
        assert MessageType.WAR_DECLARATION is not None
        assert MessageType.PEACE_OFFER is not None


class TestMessage:
    """测试消息数据类。"""

    def test_create_message(self) -> None:
        """验证消息创建。"""
        msg = Message(
            msg_type=MessageType.POLICY_DIRECTIVE,
            sender_id=1, receiver_id=2, tick=100,
            content={"tax_change": 0.05},
        )
        assert msg.sender_id == 1
        assert msg.receiver_id == 2
        assert msg.tick == 100

    def test_broadcast_message(self) -> None:
        """验证广播消息（receiver_id=None）。"""
        msg = Message(
            msg_type=MessageType.EVENT_NOTIFICATION,
            sender_id=1, receiver_id=None, tick=50,
            content={"event": "旱灾"},
        )
        assert msg.receiver_id is None

    def test_serialize_deserialize(self) -> None:
        """验证消息序列化/反序列化。"""
        msg = Message(
            msg_type=MessageType.TRADE_OFFER,
            sender_id=10, receiver_id=20, tick=200,
            content={"resource": "food", "amount": 50},
            metadata={"priority": "high"},
        )
        json_str = msg.to_json()
        restored = Message.from_json(json_str)

        assert restored.msg_type == MessageType.TRADE_OFFER
        assert restored.sender_id == 10
        assert restored.receiver_id == 20
        assert restored.tick == 200
        assert restored.content["resource"] == "food"
        assert restored.metadata["priority"] == "high"

    def test_repr(self) -> None:
        """验证字符串表示。"""
        msg = Message(
            msg_type=MessageType.WAR_DECLARATION,
            sender_id=1, receiver_id=2, tick=50,
            content={},
        )
        s = repr(msg)
        assert "war_declaration" in s
        assert "from=1" in s


class TestChannelType:
    """测试频道类型。"""

    def test_channel_types_exist(self) -> None:
        """验证四种频道类型。"""
        assert ChannelType.P2P is not None
        assert ChannelType.SETTLEMENT is not None
        assert ChannelType.FACTION is not None
        assert ChannelType.GLOBAL is not None


class TestBuildTopic:
    """测试主题构建。"""

    def test_p2p_topic(self) -> None:
        """验证 P2P 主题生成。"""
        topic = build_topic(ChannelType.P2P, agent_id=42)
        assert topic == "civsim/agent/42/direct"

    def test_settlement_topic(self) -> None:
        """验证聚落主题生成。"""
        topic = build_topic(ChannelType.SETTLEMENT, settlement_id=5)
        assert topic == "civsim/settlement/5/broadcast"

    def test_faction_topic(self) -> None:
        """验证阵营主题生成。"""
        topic = build_topic(ChannelType.FACTION, faction_id=3)
        assert topic == "civsim/faction/3/broadcast"

    def test_global_topic(self) -> None:
        """验证全局主题生成。"""
        topic = build_topic(ChannelType.GLOBAL)
        assert topic == "civsim/world/broadcast"

    def test_p2p_missing_agent_id_raises(self) -> None:
        """验证 P2P 缺少 agent_id 报错。"""
        with pytest.raises(ValueError, match="agent_id"):
            build_topic(ChannelType.P2P)

    def test_settlement_missing_id_raises(self) -> None:
        """验证聚落缺少 settlement_id 报错。"""
        with pytest.raises(ValueError, match="settlement_id"):
            build_topic(ChannelType.SETTLEMENT)

    def test_faction_missing_id_raises(self) -> None:
        """验证阵营缺少 faction_id 报错。"""
        with pytest.raises(ValueError, match="faction_id"):
            build_topic(ChannelType.FACTION)


class TestMQTTManager:
    """测试 MQTT 管理器（基础功能，不依赖 broker）。"""

    def test_init_defaults(self) -> None:
        """验证默认初始化。"""
        from civsim.communication.mqtt_broker import MQTTManager
        mgr = MQTTManager()
        assert mgr.host == "localhost"
        assert mgr.port == 1883
        assert mgr.connected is False

    def test_local_fallback_when_disconnected(self) -> None:
        """验证未连接时消息存入本地日志。"""
        from civsim.communication.mqtt_broker import MQTTManager
        mgr = MQTTManager()

        msg = Message(
            msg_type=MessageType.POLICY_DIRECTIVE,
            sender_id=1, receiver_id=2, tick=10,
            content={"directive": "test"},
        )
        result = mgr.publish("test/topic", msg)
        assert result is False  # 未连接

        local = mgr.get_local_messages()
        assert len(local) == 1
        assert local[0].sender_id == 1

    def test_local_messages_cleared_after_get(self) -> None:
        """验证获取后清空本地消息。"""
        from civsim.communication.mqtt_broker import MQTTManager
        mgr = MQTTManager()

        msg = Message(
            msg_type=MessageType.EVENT_NOTIFICATION,
            sender_id=0, receiver_id=None, tick=1,
            content={},
        )
        mgr.publish("test", msg)
        mgr.get_local_messages()
        assert len(mgr.get_local_messages()) == 0

    def test_subscribe_registers_callback(self) -> None:
        """验证订阅注册回调。"""
        from civsim.communication.mqtt_broker import MQTTManager
        mgr = MQTTManager()
        received = []
        mgr.subscribe("test/topic", lambda m: received.append(m))
        assert "test/topic" in mgr._callbacks

    def test_connect_to_real_broker(self) -> None:
        """验证连接到真实 MQTT Broker。"""
        from civsim.communication.mqtt_broker import MQTTManager
        mgr = MQTTManager(client_id="civsim_test")
        result = mgr.connect()
        if result:
            assert mgr.connected is True
            mgr.disconnect()
            assert mgr.connected is False
        else:
            # Broker 不可用，跳过
            pytest.skip("MQTT Broker 不可用")
