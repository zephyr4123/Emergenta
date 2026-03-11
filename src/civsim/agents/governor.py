"""镇长 Agent 完整实现。

LLM 驱动的聚落管理者，每季度执行一次感知→决策→应用循环。
通过 LiteLLM 网关调用 LLM，输出结构化治理决策。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import mesa
import numpy as np

from civsim.agents.base import BaseAgent
from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.civilian import Civilian
from civsim.llm.cache import BehaviorCache
from civsim.llm.memory import AgentMemory
from civsim.llm.prompts import (
    build_governor_perception_prompt,
    build_governor_system_prompt,
    validate_governor_decision,
)
from civsim.politics.governance import GovernanceAction, apply_governance_action

if TYPE_CHECKING:
    from civsim.economy.settlement import Settlement
    from civsim.llm.gateway import LLMGateway

logger = logging.getLogger(__name__)


class GovernorPerception:
    """镇长感知数据。

    聚合管辖区域内的统计信息。

    Attributes:
        settlement_name: 聚落名称。
        population: 人口数。
        food: 食物储备。
        wood: 木材储备。
        ore: 矿石储备。
        gold: 金币储备。
        tax_rate: 当前税率。
        security_level: 当前治安。
        satisfaction_avg: 平均满意度。
        protest_ratio: 抗议率。
        scarcity_index: 食物稀缺指数。
        per_capita_food: 人均食物。
        season: 当前季节名称。
        recent_events: 近期事件列表。
    """

    def __init__(
        self,
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
    ) -> None:
        self.settlement_name = settlement_name
        self.population = population
        self.food = food
        self.wood = wood
        self.ore = ore
        self.gold = gold
        self.tax_rate = tax_rate
        self.security_level = security_level
        self.satisfaction_avg = satisfaction_avg
        self.protest_ratio = protest_ratio
        self.scarcity_index = scarcity_index
        self.per_capita_food = per_capita_food
        self.season = season
        self.recent_events = recent_events or []

    def to_features(self) -> dict[str, float]:
        """转换为缓存用特征向量。"""
        return {
            "population": float(self.population),
            "food": self.food,
            "wood": self.wood,
            "ore": self.ore,
            "gold": self.gold,
            "tax_rate": self.tax_rate,
            "security_level": self.security_level,
            "satisfaction_avg": self.satisfaction_avg,
            "protest_ratio": self.protest_ratio,
            "scarcity_index": self.scarcity_index,
        }


class Governor(BaseAgent):
    """镇长 Agent。

    每季度执行一次 perceive → decide → apply 决策循环。

    Attributes:
        settlement_id: 管辖聚落 ID。
        memory: 记忆系统。
        cache: 行为缓存。
        last_decision: 上一次决策内容。
        decision_count: 总决策次数。
    """

    def __init__(
        self,
        model: mesa.Model,
        settlement_id: int,
        gateway: LLMGateway | None = None,
        memory_limit: int = 10,
        cache_enabled: bool = True,
    ) -> None:
        super().__init__(model, home_settlement_id=settlement_id)
        self.settlement_id = settlement_id
        self._gateway = gateway
        self.memory = AgentMemory(short_term_limit=memory_limit)
        self.cache = BehaviorCache() if cache_enabled else None
        self.last_decision: dict | None = None
        self.decision_count: int = 0
        self._prev_perception: GovernorPerception | None = None
        self.system_prompt_override: str | None = None

    def step(self) -> None:
        """每 tick 执行。仅在季度开始时进行决策。"""
        if not hasattr(self.model, "clock"):
            return
        if not self.model.clock.is_governor_decision_tick():
            return
        if self.model.clock.tick == 0:
            return

        self._decision_cycle()

    def _decision_cycle(self) -> None:
        """完整的感知→决策→应用循环。"""
        # 1. 感知
        perception = self.perceive()
        if perception is None:
            return

        # 2. 尝试缓存命中
        decision = None
        cache_hit = False
        if self.cache is not None:
            features = perception.to_features()
            cached = self.cache.query(features)
            if cached is not None:
                decision = cached
                cache_hit = True
                logger.info(
                    "镇长 %d 缓存命中，复用历史决策", self.unique_id
                )

        # 3. 调用 LLM 决策
        if decision is None:
            decision = self.decide(perception)

        if decision is None:
            return

        # 4. 存入缓存
        if self.cache is not None and not cache_hit:
            self.cache.store(perception.to_features(), decision)

        # 5. 应用决策
        self.apply_decision(decision)

        # 6. 记录到记忆
        self.memory.add_decision(
            tick=self.model.clock.tick,
            decision=decision,
        )
        self.last_decision = decision
        self._prev_perception = perception
        self.decision_count += 1

    def perceive(self) -> GovernorPerception | None:
        """聚合管辖区域内的统计数据。

        Returns:
            感知数据对象，无聚落时返回 None。
        """
        if not hasattr(self.model, "settlements"):
            return None

        settlement: Settlement | None = self.model.settlements.get(
            self.settlement_id
        )
        if settlement is None:
            return None

        # 计算管辖区域平民的满意度和抗议率
        civilians = self._get_settlement_civilians()
        if civilians:
            sat_avg = float(np.mean([c.satisfaction for c in civilians]))
            protest_count = sum(
                1 for c in civilians if c.state == CivilianState.PROTESTING
            )
            protest_r = protest_count / len(civilians)
        else:
            sat_avg = 0.5
            protest_r = 0.0

        season_name = "春"
        if hasattr(self.model, "clock"):
            season_names = {0: "春", 1: "夏", 2: "秋", 3: "冬"}
            season_name = season_names.get(
                int(self.model.clock.current_season), "春"
            )

        return GovernorPerception(
            settlement_name=settlement.name,
            population=settlement.population,
            food=settlement.stockpile.get("food", 0.0),
            wood=settlement.stockpile.get("wood", 0.0),
            ore=settlement.stockpile.get("ore", 0.0),
            gold=settlement.stockpile.get("gold", 0.0),
            tax_rate=settlement.tax_rate,
            security_level=settlement.security_level,
            satisfaction_avg=sat_avg,
            protest_ratio=protest_r,
            scarcity_index=min(1.0, settlement.scarcity_index),
            per_capita_food=min(999.0, settlement.per_capita_food),
            season=season_name,
        )

    def decide(self, perception: GovernorPerception) -> dict | None:
        """调用 LLM 生成结构化决策。

        Args:
            perception: 感知数据。

        Returns:
            验证后的决策字典，失败时返回 None。
        """
        if self._gateway is None:
            return self._fallback_decision(perception)

        memory_context = self.memory.build_context(max_entries=5)

        # 构建全局上下文
        global_context = self._build_global_context()
        # 构建上季决策效果
        decision_outcomes = self._compute_decision_outcomes(perception)

        system_msg = (
            self.system_prompt_override
            if self.system_prompt_override
            else build_governor_system_prompt()
        )
        user_msg = build_governor_perception_prompt(
            settlement_name=perception.settlement_name,
            population=perception.population,
            food=perception.food,
            wood=perception.wood,
            ore=perception.ore,
            gold=perception.gold,
            tax_rate=perception.tax_rate,
            security_level=perception.security_level,
            satisfaction_avg=perception.satisfaction_avg,
            protest_ratio=perception.protest_ratio,
            scarcity_index=perception.scarcity_index,
            per_capita_food=perception.per_capita_food,
            season=perception.season,
            recent_events=perception.recent_events,
            memory_context=memory_context,
            global_context=global_context,
            decision_outcomes=decision_outcomes,
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        try:
            raw = self._gateway.call_json("governor", messages)
            return validate_governor_decision(raw)
        except Exception as e:
            logger.warning("镇长 %d LLM 决策失败: %s，使用回退策略", self.unique_id, e)
            return self._fallback_decision(perception)

    def _fallback_decision(self, perception: GovernorPerception) -> dict:
        """LLM 不可用时的规则回退策略。

        基于简单启发式规则生成决策。

        Args:
            perception: 感知数据。

        Returns:
            回退决策字典。
        """
        # 获取回退参数配置
        fb = None
        if hasattr(self.model, "config"):
            fb = self.model.config.governor_fallback
        from civsim.config_params_ext import GovernorFallbackConfig
        if fb is None:
            fb = GovernorFallbackConfig()

        tax_change = 0.0
        sec_change = 0.0
        focus = "balanced"
        reasoning = "规则回退策略"

        # 食物紧缺时降税
        if perception.scarcity_index > fb.scarcity_threshold:
            tax_change = fb.scarcity_tax_change
            focus = "food"
            reasoning = "食物紧缺，降低税率促进生产"

        # 抗议率高时增加治安
        if perception.protest_ratio > fb.protest_threshold:
            sec_change = fb.protest_security_change
            if perception.protest_ratio > fb.high_protest_threshold:
                tax_change = min(tax_change, fb.high_protest_tax_change)
            reasoning = "抗议率较高，加强治安并适度降税"

        # 满意度低时降税
        if perception.satisfaction_avg < fb.low_satisfaction_threshold:
            tax_change = max(tax_change, fb.low_satisfaction_tax_change)
            reasoning = "民众满意度低，降税安抚"

        # 资源充裕时可加税
        if (
            perception.scarcity_index < fb.stable_scarcity_max
            and perception.protest_ratio < fb.stable_protest_max
            and perception.satisfaction_avg > fb.stable_satisfaction_min
        ):
            tax_change = fb.stable_tax_change
            reasoning = "局势稳定资源充裕，适度加税积累储备"

        return validate_governor_decision({
            "tax_rate_change": tax_change,
            "security_change": sec_change,
            "resource_focus": focus,
            "reasoning": reasoning,
        })

    def apply_decision(self, decision: dict) -> None:
        """将决策应用到管辖聚落。

        Args:
            decision: 验证后的决策字典。
        """
        if not hasattr(self.model, "settlements"):
            return

        settlement = self.model.settlements.get(self.settlement_id)
        if settlement is None:
            return

        action = GovernanceAction.from_decision(decision)
        changes = apply_governance_action(settlement, action)

        logger.info(
            "镇长 %d 对聚落「%s」执行决策: 税率 %.2f→%.2f, 治安 %.2f→%.2f, 重点: %s",
            self.unique_id,
            settlement.name,
            changes["tax_rate_old"],
            changes["tax_rate_new"],
            changes["security_old"],
            changes["security_new"],
            changes["resource_focus"],
        )

        # 记录到数据库
        if hasattr(self.model, "db") and self.model.db is not None:
            import json
            self.model.db.write_event(
                tick=self.model.clock.tick,
                agent_id=self.unique_id,
                agent_type="governor",
                event_type="decision",
                detail=json.dumps(decision, ensure_ascii=False),
            )

    def _get_settlement_civilians(self) -> list[Civilian]:
        """获取管辖聚落内的所有平民。

        Returns:
            平民 Agent 列表。
        """
        return [
            a for a in self.model.agents
            if isinstance(a, Civilian)
            and a.home_settlement_id == self.settlement_id
        ]

    def _build_global_context(self) -> dict | None:
        """构建全局上下文供 LLM 注入。

        Returns:
            全局态势字典，无控制器时返回 None。
        """
        if not hasattr(self.model, "adaptive_controller"):
            return None
        ctrl = self.model.adaptive_controller
        if ctrl is None:
            return None

        ctx = ctrl.get_global_context()

        # 补充额外统计
        if hasattr(self.model, "revolution_tracker") and self.model.revolution_tracker:
            rt = self.model.revolution_tracker
            ctx["revolution_count"] = rt.revolution_count
            ctx["revolutions_recent"] = rt.recent_revolution_count(
                self.model.clock.tick,
            )

        if hasattr(self.model, "trade_manager") and self.model.trade_manager:
            stats = self.model.trade_manager.get_tick_stats()
            ctx["trade_volume"] = stats.get("total_volume", 0)

        if hasattr(self.model, "diplomacy") and self.model.diplomacy:
            ctx["active_wars"] = self.model.diplomacy.count_wars()

        return ctx

    def _compute_decision_outcomes(
        self, current: GovernorPerception,
    ) -> str:
        """对比前后 perception 生成上季决策效果描述。

        Args:
            current: 当前感知数据。

        Returns:
            决策效果描述字符串，无前次感知时返回空串。
        """
        prev = self._prev_perception
        if prev is None or self.last_decision is None:
            return ""

        lines = []
        d = self.last_decision

        # 税率变化
        tax_change = d.get("tax_rate_change", 0)
        if abs(tax_change) > 0.001:
            action = f"{'加' if tax_change > 0 else '降'}税{abs(tax_change):.2f}"
            sat_delta = current.satisfaction_avg - prev.satisfaction_avg
            pr_delta = current.protest_ratio - prev.protest_ratio
            lines.append(
                f"- 上季「{action}」→ "
                f"满意度 {prev.satisfaction_avg:.2f}→"
                f"{current.satisfaction_avg:.2f}"
                f"({sat_delta:+.2f}), "
                f"抗议率 {prev.protest_ratio:.0%}→"
                f"{current.protest_ratio:.0%}"
            )

        # 治安变化
        sec_change = d.get("security_change", 0)
        if abs(sec_change) > 0.001:
            action = f"{'增' if sec_change > 0 else '减'}安{abs(sec_change):.2f}"
            pr_delta = current.protest_ratio - prev.protest_ratio
            lines.append(
                f"- 上季「{action}」→ "
                f"抗议率 {prev.protest_ratio:.0%}→"
                f"{current.protest_ratio:.0%}"
            )

        return "\n".join(lines)

    async def decide_async(
        self, perception: GovernorPerception,
    ) -> dict | None:
        """异步调用 LLM 生成结构化决策。

        Args:
            perception: 感知数据。

        Returns:
            验证后的决策字典，失败时返回 None。
        """
        if self._gateway is None:
            return self._fallback_decision(perception)

        memory_context = self.memory.build_context(max_entries=5)
        global_context = self._build_global_context()
        decision_outcomes = self._compute_decision_outcomes(perception)

        system_msg = (
            self.system_prompt_override
            if self.system_prompt_override
            else build_governor_system_prompt()
        )
        user_msg = build_governor_perception_prompt(
            settlement_name=perception.settlement_name,
            population=perception.population,
            food=perception.food,
            wood=perception.wood,
            ore=perception.ore,
            gold=perception.gold,
            tax_rate=perception.tax_rate,
            security_level=perception.security_level,
            satisfaction_avg=perception.satisfaction_avg,
            protest_ratio=perception.protest_ratio,
            scarcity_index=perception.scarcity_index,
            per_capita_food=perception.per_capita_food,
            season=perception.season,
            recent_events=perception.recent_events,
            memory_context=memory_context,
            global_context=global_context,
            decision_outcomes=decision_outcomes,
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        try:
            raw = await self._gateway.acall_json("governor", messages)
            return validate_governor_decision(raw)
        except Exception as e:
            logger.warning(
                "镇长 %d 异步LLM决策失败: %s，使用回退策略",
                self.unique_id, e,
            )
            return self._fallback_decision(perception)

    async def decision_cycle_async(self) -> None:
        """异步版完整感知→决策→应用循环。"""
        perception = self.perceive()
        if perception is None:
            return

        decision = None
        cache_hit = False
        if self.cache is not None:
            features = perception.to_features()
            cached = self.cache.query(features)
            if cached is not None:
                decision = cached
                cache_hit = True
                logger.info(
                    "镇长 %d 缓存命中，复用历史决策", self.unique_id,
                )

        if decision is None:
            decision = await self.decide_async(perception)

        if decision is None:
            return

        if self.cache is not None and not cache_hit:
            self.cache.store(perception.to_features(), decision)

        self.apply_decision(decision)
        self.memory.add_decision(
            tick=self.model.clock.tick,
            decision=decision,
        )
        self.last_decision = decision
        self._prev_perception = perception
        self.decision_count += 1
