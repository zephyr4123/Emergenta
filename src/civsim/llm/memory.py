"""Agent 记忆系统。

提供短期记忆（最近 N 次决策上下文）和长期记忆（关键事件摘要）。
支持记忆检索和上下文窗口构建。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class MemoryEntry:
    """单条记忆条目。

    Attributes:
        tick: 记忆对应的时间 tick。
        category: 记忆类别（decision / event / observation）。
        content: 记忆内容文本。
        importance: 重要度 [0, 1]，越高越重要。
        metadata: 额外元数据。
    """

    tick: int
    category: str
    content: str
    importance: float = 0.5
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """序列化为字典。"""
        return {
            "tick": self.tick,
            "category": self.category,
            "content": self.content,
            "importance": self.importance,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MemoryEntry:
        """从字典反序列化。"""
        return cls(
            tick=data["tick"],
            category=data["category"],
            content=data["content"],
            importance=data.get("importance", 0.5),
            metadata=data.get("metadata", {}),
        )


class AgentMemory:
    """Agent 记忆管理器。

    分为短期记忆和长期记忆两个层级：
    - 短期记忆：最近 N 次决策和观察，按时间排序
    - 长期记忆：重要事件摘要，按重要度筛选保留

    Attributes:
        short_term_limit: 短期记忆最大条目数。
        long_term_limit: 长期记忆最大条目数。
    """

    def __init__(
        self,
        short_term_limit: int = 10,
        long_term_limit: int = 50,
        importance_threshold: float = 0.7,
    ) -> None:
        self.short_term_limit = short_term_limit
        self.long_term_limit = long_term_limit
        self._importance_threshold = importance_threshold
        self._short_term: list[MemoryEntry] = []
        self._long_term: list[MemoryEntry] = []

    def add(self, entry: MemoryEntry) -> None:
        """添加一条记忆。

        自动根据重要度分配到短期或长期记忆。
        短期记忆始终存储，超限时淘汰最旧的。
        高重要度的记忆同时存入长期记忆。

        Args:
            entry: 记忆条目。
        """
        self._short_term.append(entry)
        if len(self._short_term) > self.short_term_limit:
            self._short_term.pop(0)

        if entry.importance >= self._importance_threshold:
            self._long_term.append(entry)
            if len(self._long_term) > self.long_term_limit:
                # 淘汰最不重要的
                self._long_term.sort(key=lambda e: e.importance, reverse=True)
                self._long_term = self._long_term[: self.long_term_limit]

    def add_decision(
        self,
        tick: int,
        decision: dict,
        result_summary: str = "",
    ) -> None:
        """记录一次决策。

        Args:
            tick: 决策发生的 tick。
            decision: 决策内容字典。
            result_summary: 决策结果摘要。
        """
        content = f"决策: {json.dumps(decision, ensure_ascii=False)}"
        if result_summary:
            content += f" → 结果: {result_summary}"
        self.add(MemoryEntry(
            tick=tick,
            category="decision",
            content=content,
            importance=0.8,
            metadata={"decision": decision},
        ))

    def add_event(
        self,
        tick: int,
        event_description: str,
        importance: float = 0.6,
    ) -> None:
        """记录一个事件。

        Args:
            tick: 事件发生的 tick。
            event_description: 事件描述。
            importance: 重要度。
        """
        self.add(MemoryEntry(
            tick=tick,
            category="event",
            content=event_description,
            importance=importance,
        ))

    def get_recent(self, n: int | None = None) -> list[MemoryEntry]:
        """获取最近的短期记忆。

        Args:
            n: 返回条目数，为 None 时返回全部短期记忆。

        Returns:
            按时间倒序的记忆列表。
        """
        entries = list(reversed(self._short_term))
        if n is not None:
            entries = entries[:n]
        return entries

    def get_important(self, n: int | None = None) -> list[MemoryEntry]:
        """获取重要的长期记忆。

        Args:
            n: 返回条目数，为 None 时返回全部长期记忆。

        Returns:
            按重要度排序的记忆列表。
        """
        entries = sorted(self._long_term, key=lambda e: e.importance, reverse=True)
        if n is not None:
            entries = entries[:n]
        return entries

    def build_context(self, max_entries: int = 5) -> str:
        """构建记忆上下文字符串，用于注入 Prompt。

        包含最近的短期记忆和最重要的长期记忆。

        Args:
            max_entries: 最大条目数。

        Returns:
            格式化的记忆上下文文本。
        """
        lines: list[str] = []
        recent = self.get_recent(max_entries // 2 + 1)
        for entry in recent:
            lines.append(f"[Tick {entry.tick}] {entry.content}")

        important = self.get_important(max_entries // 2)
        for entry in important:
            text = f"[Tick {entry.tick}, 重要] {entry.content}"
            if text not in lines:
                lines.append(text)

        return "\n".join(lines[:max_entries])

    @property
    def short_term_count(self) -> int:
        """短期记忆条目数。"""
        return len(self._short_term)

    @property
    def long_term_count(self) -> int:
        """长期记忆条目数。"""
        return len(self._long_term)

    def clear(self) -> None:
        """清空所有记忆。"""
        self._short_term.clear()
        self._long_term.clear()

    def to_dict(self) -> dict:
        """序列化全部记忆。"""
        return {
            "short_term": [e.to_dict() for e in self._short_term],
            "long_term": [e.to_dict() for e in self._long_term],
        }

    @classmethod
    def from_dict(
        cls,
        data: dict,
        short_term_limit: int = 10,
        long_term_limit: int = 50,
    ) -> AgentMemory:
        """从字典反序列化。"""
        memory = cls(short_term_limit=short_term_limit, long_term_limit=long_term_limit)
        for entry_data in data.get("short_term", []):
            memory._short_term.append(MemoryEntry.from_dict(entry_data))
        for entry_data in data.get("long_term", []):
            memory._long_term.append(MemoryEntry.from_dict(entry_data))
        return memory
