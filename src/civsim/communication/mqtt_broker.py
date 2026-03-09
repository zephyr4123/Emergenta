"""MQTT Broker 管理。

封装 paho-mqtt 客户端，提供发布/订阅接口。
未连接时自动降级为本地消息队列。
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as mqtt

from civsim.communication.protocol import Message

logger = logging.getLogger(__name__)


class MQTTManager:
    """MQTT 客户端管理器。

    Attributes:
        host: Broker 地址。
        port: Broker 端口。
        connected: 是否已连接。
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1883,
        client_id: str = "civsim_engine",
    ) -> None:
        self.host = host
        self.port = port
        self.connected = False
        self._client = mqtt.Client(
            client_id=client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self._callbacks: dict[str, list[Callable]] = {}
        self._message_log: list[Message] = []
        self._lock = threading.Lock()

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

    def connect(self) -> bool:
        """连接到 MQTT Broker。

        Returns:
            是否成功连接。
        """
        try:
            self._client.connect(self.host, self.port, keepalive=60)
            self._client.loop_start()
            self.connected = True
            logger.info("已连接 MQTT Broker: %s:%d", self.host, self.port)
            return True
        except (ConnectionRefusedError, OSError) as e:
            logger.warning("MQTT 连接失败: %s，使用本地消息队列", e)
            self.connected = False
            return False

    def disconnect(self) -> None:
        """断开 MQTT 连接。"""
        if self.connected:
            self._client.loop_stop()
            self._client.disconnect()
            self.connected = False
            logger.info("已断开 MQTT 连接")

    def publish(self, topic: str, message: Message) -> bool:
        """发布消息到指定主题。

        Args:
            topic: MQTT 主题。
            message: 消息对象。

        Returns:
            是否发布成功。
        """
        if not self.connected:
            with self._lock:
                self._message_log.append(message)
            return False

        payload = message.to_json()
        result = self._client.publish(topic, payload)
        return result.rc == mqtt.MQTT_ERR_SUCCESS

    def subscribe(
        self,
        topic: str,
        callback: Callable[[Message], None],
    ) -> None:
        """订阅主题并注册回调。

        Args:
            topic: MQTT 主题。
            callback: 收到消息时的回调函数。
        """
        with self._lock:
            if topic not in self._callbacks:
                self._callbacks[topic] = []
                if self.connected:
                    self._client.subscribe(topic)
            self._callbacks[topic].append(callback)

    def get_local_messages(self) -> list[Message]:
        """获取本地消息日志（MQTT 未连接时的备用）。

        Returns:
            消息列表（取后清空）。
        """
        with self._lock:
            msgs = list(self._message_log)
            self._message_log.clear()
            return msgs

    def _on_connect(
        self,
        client: Any,
        userdata: Any,
        flags: Any,
        rc: int,
        properties: Any = None,
    ) -> None:
        """连接成功回调。"""
        self.connected = True
        with self._lock:
            for topic in self._callbacks:
                client.subscribe(topic)

    def _on_message(
        self,
        client: Any,
        userdata: Any,
        msg: mqtt.MQTTMessage,
    ) -> None:
        """消息接收回调。"""
        try:
            message = Message.from_json(msg.payload.decode("utf-8"))
            with self._lock:
                callbacks = list(self._callbacks.get(msg.topic, []))
            for cb in callbacks:
                cb(message)
        except (ValueError, KeyError) as e:
            logger.error("消息解析失败: %s", e)

    def _on_disconnect(
        self,
        client: Any,
        userdata: Any,
        rc: Any,
        properties: Any = None,
        *args: Any,
    ) -> None:
        """断开连接回调。"""
        self.connected = False
        # paho-mqtt v2 传入 DisconnectFlags 对象，v1 传入 int
        try:
            rc_val = rc.value if hasattr(rc, "value") else rc
            if rc_val != 0:
                logger.warning("MQTT 异常断开: rc=%s", rc_val)
        except Exception:
            pass
