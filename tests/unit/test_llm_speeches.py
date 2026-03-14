"""LLM 发言实时展示功能测试。

覆盖 LLMSpeech dataclass、SharedState 发言存储、
Governor/Leader 发言捕获、回退决策不触发发言。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from civsim.dashboard.shared_state import LLMSpeech, SharedState


# ------------------------------------------------------------------
# LLMSpeech dataclass
# ------------------------------------------------------------------


class TestLLMSpeech:
    """LLMSpeech 数据类测试。"""

    def test_fields(self) -> None:
        """验证所有字段可正确赋值。"""
        speech = LLMSpeech(
            tick=10,
            agent_type="governor",
            agent_id=42,
            agent_name="测试聚落",
            reasoning="因为食物不足，我决定降税",
            decision_summary="税率-5%, 治安+0%, 重点:food",
        )
        assert speech.tick == 10
        assert speech.agent_type == "governor"
        assert speech.agent_id == 42
        assert speech.agent_name == "测试聚落"
        assert "食物不足" in speech.reasoning
        assert "税率" in speech.decision_summary


# ------------------------------------------------------------------
# SharedState 发言存储
# ------------------------------------------------------------------


class TestSharedStateSpeech:
    """SharedState 发言增删查测试。"""

    def test_add_and_get_speeches(self) -> None:
        """添加发言后可读取。"""
        ss = SharedState()
        s1 = LLMSpeech(1, "governor", 1, "A", "r1", "s1")
        s2 = LLMSpeech(2, "leader", 2, "B", "r2", "s2")
        ss.add_speech(s1)
        ss.add_speech(s2)
        result = ss.get_speeches(10)
        assert len(result) == 2
        assert result[0].agent_name == "A"
        assert result[1].agent_name == "B"

    def test_get_speeches_limit(self) -> None:
        """get_speeches(n) 只返回最近 n 条。"""
        ss = SharedState()
        for i in range(10):
            ss.add_speech(LLMSpeech(i, "governor", i, f"G{i}", f"r{i}", f"s{i}"))
        result = ss.get_speeches(3)
        assert len(result) == 3
        assert result[0].tick == 7

    def test_maxlen_100(self) -> None:
        """deque maxlen=100，超出自动淘汰旧记录。"""
        ss = SharedState()
        for i in range(120):
            ss.add_speech(LLMSpeech(i, "leader", i, f"L{i}", f"r{i}", f"s{i}"))
        result = ss.get_speeches(200)
        assert len(result) == 100
        assert result[0].tick == 20  # 前 20 条被淘汰

    def test_reset_clears_speeches(self) -> None:
        """reset() 清空发言记录。"""
        ss = SharedState()
        ss.add_speech(LLMSpeech(1, "governor", 1, "X", "r", "s"))
        assert len(ss.get_speeches()) == 1
        ss.reset()
        assert len(ss.get_speeches()) == 0


# ------------------------------------------------------------------
# Governor 发言捕获
# ------------------------------------------------------------------


class TestGovernorSpeechCapture:
    """Governor 调用 LLM 时捕获完整 reasoning。"""

    def test_decide_captures_speech(self) -> None:
        """decide() 成功调用 LLM 时保存完整 reasoning。"""
        from civsim.agents.governor import Governor, GovernorPerception

        model = MagicMock()
        model.clock.tick = 100
        model.config = MagicMock()
        model.config.clock.ticks_per_season = 120
        model.adaptive_controller = None

        gateway = MagicMock()
        long_reasoning = "这是一段很长的分析文本，超过200字" * 20
        gateway.call_json.return_value = {
            "tax_rate_change": 0.05,
            "security_change": 0.0,
            "resource_focus": "food",
            "reasoning": long_reasoning,
        }

        gov = Governor(model, settlement_id=1, gateway=gateway)
        gov.system_prompt_override = None

        perception = GovernorPerception(
            settlement_name="测试", population=50,
            food=100, wood=50, ore=20, gold=30,
            tax_rate=0.1, security_level=0.3,
            satisfaction_avg=0.6, protest_ratio=0.1,
            scarcity_index=0.2, per_capita_food=2.0,
            season="春",
        )

        result = gov.decide(perception)
        assert result is not None
        # 完整文本保存（不截断）
        assert gov.last_speech_text == long_reasoning
        assert gov.last_speech_tick == 100
        # validate 后 reasoning 被截断到 200 字
        assert len(result["reasoning"]) <= 200

    def test_fallback_no_speech(self) -> None:
        """回退决策不设置 speech 字段。"""
        from civsim.agents.governor import Governor, GovernorPerception

        model = MagicMock()
        model.clock.tick = 50
        model.config = MagicMock()
        model.config.clock.ticks_per_season = 120
        model.config.governor_fallback = None

        # 无 gateway → 回退
        gov = Governor(model, settlement_id=1, gateway=None)
        perception = GovernorPerception(
            settlement_name="回退测试", population=30,
            food=80, wood=40, ore=10, gold=20,
            tax_rate=0.1, security_level=0.3,
            satisfaction_avg=0.5, protest_ratio=0.05,
            scarcity_index=0.1, per_capita_food=2.5,
            season="夏",
        )

        result = gov.decide(perception)
        assert result is not None
        # 回退路径不触发 speech
        assert gov.last_speech_text is None
        assert gov.last_speech_tick == -1

    def test_llm_failure_no_speech(self) -> None:
        """LLM 调用失败时不设置 speech。"""
        from civsim.agents.governor import Governor, GovernorPerception

        model = MagicMock()
        model.clock.tick = 200
        model.config = MagicMock()
        model.config.clock.ticks_per_season = 120
        model.config.governor_fallback = None
        model.adaptive_controller = None

        gateway = MagicMock()
        gateway.call_json.side_effect = Exception("API error")

        gov = Governor(model, settlement_id=1, gateway=gateway)
        # 确保 unique_id 是整数（Mesa 需要）
        gov.unique_id = 99
        perception = GovernorPerception(
            settlement_name="失败测试", population=30,
            food=80, wood=40, ore=10, gold=20,
            tax_rate=0.1, security_level=0.3,
            satisfaction_avg=0.5, protest_ratio=0.05,
            scarcity_index=0.1, per_capita_food=2.5,
            season="秋",
        )

        result = gov.decide(perception)
        assert result is not None  # 使用回退
        assert gov.last_speech_text is None
        assert gov.last_speech_tick == -1


# ------------------------------------------------------------------
# Leader 发言捕获
# ------------------------------------------------------------------


class TestLeaderSpeechCapture:
    """Leader 调用 LLM 时捕获完整 reasoning。"""

    def test_decide_captures_speech(self) -> None:
        """decide() 成功调用 LLM 时保存完整 reasoning。"""
        from civsim.agents.leader import Leader, LeaderPerception

        model = MagicMock()
        model.clock.tick = 480
        model.config = MagicMock()
        model.config.leader_fallback = None

        gateway = MagicMock()
        long_reasoning = "首领深思熟虑后决定扩张领土" * 30
        gateway.call_json.return_value = {
            "diplomatic_actions": [],
            "policy_directives": [],
            "overall_strategy": "军事扩张",
            "reasoning": long_reasoning,
        }

        leader = Leader(
            model, faction_id=1,
            controlled_settlements=[1, 2],
            gateway=gateway,
        )
        leader.system_prompt_override = None

        perception = LeaderPerception(
            faction_id=1, year=1, season="春",
            settlements_info=[
                {"id": 1, "name": "A", "population": 50,
                 "food": 100, "satisfaction": 0.6, "protest_ratio": 0.1},
            ],
            total_population=50,
            total_resources={"food": 100, "wood": 50, "ore": 20, "gold": 30},
            avg_satisfaction=0.6,
            diplomatic_status={},
            active_treaties=[],
        )

        result = leader.decide(perception)
        assert result is not None
        assert leader.last_speech_text == long_reasoning
        assert leader.last_speech_tick == 480

    def test_fallback_no_speech(self) -> None:
        """回退决策不设置 speech。"""
        from civsim.agents.leader import Leader, LeaderPerception

        model = MagicMock()
        model.clock.tick = 480
        model.config = MagicMock()
        model.config.leader_fallback = None

        leader = Leader(
            model, faction_id=1,
            controlled_settlements=[1],
            gateway=None,
        )

        perception = LeaderPerception(
            faction_id=1, year=1, season="夏",
            settlements_info=[],
            total_population=0,
            total_resources={"food": 0, "wood": 0, "ore": 0, "gold": 0},
            avg_satisfaction=0.5,
            diplomatic_status={},
            active_treaties=[],
        )

        result = leader.decide(perception)
        assert result is not None
        assert leader.last_speech_text is None
        assert leader.last_speech_tick == -1
