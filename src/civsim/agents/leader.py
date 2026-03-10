"""首领 Agent 完整实现。

LLM 驱动的阵营战略决策者，每年执行一次感知→决策→应用循环。
支持与其他首领进行自然语言外交谈判。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import mesa
import numpy as np

from civsim.agents.base import BaseAgent
from civsim.agents.behaviors.fsm import CivilianState
from civsim.llm.cache import BehaviorCache
from civsim.llm.memory import AgentMemory
from civsim.llm.prompts import (
    build_leader_perception_prompt,
    build_leader_system_prompt,
    build_negotiation_prompt,
    validate_leader_decision,
)

if TYPE_CHECKING:
    from civsim.economy.settlement import Settlement
    from civsim.llm.gateway import LLMGateway
    from civsim.politics.diplomacy import DiplomacyManager

logger = logging.getLogger(__name__)


class LeaderPerception:
    """首领感知数据。

    聚合阵营内所有聚落的统计信息和外交态势。

    Attributes:
        faction_id: 阵营 ID。
        year: 当前年份。
        season: 当前季节名称。
        settlements_info: 下属聚落摘要列表。
        total_population: 总人口。
        total_resources: 总资源。
        avg_satisfaction: 平均满意度。
        diplomatic_status: 与其他阵营的外交状态。
        active_treaties: 活跃条约描述。
    """

    def __init__(
        self,
        faction_id: int,
        year: int,
        season: str,
        settlements_info: list[dict],
        total_population: int,
        total_resources: dict[str, float],
        avg_satisfaction: float,
        diplomatic_status: dict[int, str],
        active_treaties: list[str],
    ) -> None:
        self.faction_id = faction_id
        self.year = year
        self.season = season
        self.settlements_info = settlements_info
        self.total_population = total_population
        self.total_resources = total_resources
        self.avg_satisfaction = avg_satisfaction
        self.diplomatic_status = diplomatic_status
        self.active_treaties = active_treaties

    def to_features(self) -> dict[str, float]:
        """转换为缓存用特征向量。"""
        return {
            "population": float(self.total_population),
            "food": self.total_resources.get("food", 0),
            "wood": self.total_resources.get("wood", 0),
            "gold": self.total_resources.get("gold", 0),
            "satisfaction": self.avg_satisfaction,
            "num_settlements": float(len(self.settlements_info)),
        }


class Leader(BaseAgent):
    """首领 Agent。

    每年执行一次 perceive → decide → apply 战略决策循环。

    Attributes:
        faction_id: 所属阵营 ID。
        controlled_settlements: 控制的聚落 ID 列表。
        ideology: 意识形态风格。
        memory: 记忆系统（含外交历史）。
        cache: 行为缓存。
        last_decision: 上一次决策内容。
        decision_count: 总决策次数。
    """

    def __init__(
        self,
        model: mesa.Model,
        faction_id: int,
        controlled_settlements: list[int],
        gateway: LLMGateway | None = None,
        memory_limit: int = 50,
        cache_enabled: bool = True,
        ideology: str = "务实",
    ) -> None:
        super().__init__(model, home_settlement_id=0)
        self.faction_id = faction_id
        self.controlled_settlements = list(controlled_settlements)
        self._gateway = gateway
        self.memory = AgentMemory(
            short_term_limit=memory_limit,
            long_term_limit=memory_limit * 2,
        )
        self.cache = BehaviorCache() if cache_enabled else None
        self.ideology = ideology
        self.last_decision: dict | None = None
        self.decision_count: int = 0
        self._rng = np.random.default_rng(self.unique_id)

    def step(self) -> None:
        """每 tick 执行。仅在年度开始时进行决策。"""
        if not hasattr(self.model, "clock"):
            return
        if not self.model.clock.is_leader_decision_tick():
            return
        if self.model.clock.tick == 0:
            return

        self._decision_cycle()

    def _decision_cycle(self) -> None:
        """完整的感知→决策→应用循环。"""
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

        if decision is None:
            decision = self.decide(perception)

        if decision is None:
            return

        if self.cache is not None and not cache_hit:
            self.cache.store(perception.to_features(), decision)

        self.apply_decision(decision)
        self.memory.add_decision(
            tick=self.model.clock.tick, decision=decision,
        )
        self.last_decision = decision
        self.decision_count += 1

    def perceive(self) -> LeaderPerception | None:
        """聚合阵营内所有聚落的数据。"""
        if not hasattr(self.model, "settlements"):
            return None

        settlements_info = []
        total_pop = 0
        total_res = {"food": 0.0, "wood": 0.0, "ore": 0.0, "gold": 0.0}
        sat_sum = 0.0
        count = 0

        for sid in self.controlled_settlements:
            s = self.model.settlements.get(sid)
            if s is None:
                continue
            civilians = self._get_faction_civilians(sid)
            sat = (
                float(np.mean([c.satisfaction for c in civilians]))
                if civilians else 0.5
            )
            protest = (
                sum(1 for c in civilians
                    if c.state == CivilianState.PROTESTING)
                / max(1, len(civilians))
            )

            settlements_info.append({
                "id": sid, "name": s.name,
                "population": s.population,
                "food": s.stockpile.get("food", 0),
                "satisfaction": sat, "protest_ratio": protest,
            })
            total_pop += s.population
            for key in total_res:
                total_res[key] += s.stockpile.get(key, 0)
            sat_sum += sat
            count += 1

        avg_sat = sat_sum / max(1, count)

        diplo_status = self._get_diplomatic_status()
        treaties = self._get_active_treaties_desc()

        season_names = {0: "春", 1: "夏", 2: "秋", 3: "冬"}
        season = season_names.get(int(self.model.clock.current_season), "春")

        return LeaderPerception(
            faction_id=self.faction_id,
            year=self.model.clock.current_year,
            season=season,
            settlements_info=settlements_info,
            total_population=total_pop,
            total_resources=total_res,
            avg_satisfaction=avg_sat,
            diplomatic_status=diplo_status,
            active_treaties=treaties,
        )

    def decide(self, perception: LeaderPerception) -> dict | None:
        """调用 LLM 生成战略决策。"""
        if self._gateway is None:
            return self._fallback_decision(perception)

        memory_context = self.memory.build_context(max_entries=5)
        system_msg = build_leader_system_prompt()
        user_msg = build_leader_perception_prompt(
            faction_id=perception.faction_id,
            year=perception.year,
            season=perception.season,
            settlements_info=perception.settlements_info,
            total_population=perception.total_population,
            total_resources=perception.total_resources,
            avg_satisfaction=perception.avg_satisfaction,
            diplomatic_status=perception.diplomatic_status,
            active_treaties=perception.active_treaties,
            memory_context=memory_context,
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        try:
            raw = self._gateway.call_json("leader", messages)
            return validate_leader_decision(raw)
        except Exception as e:
            logger.warning(
                "首领 %d LLM 决策失败: %s，使用回退策略",
                self.unique_id, e,
            )
            return self._fallback_decision(perception)

    def _fallback_decision(self, perception: LeaderPerception) -> dict:
        """LLM 不可用时的规则回退策略。

        增加攻击性决策：宣战、破约、转嫁矛盾。
        """
        directives = []
        for s_info in perception.settlements_info:
            tax_change = 0.0
            sec_change = 0.0
            focus = "balanced"

            if s_info.get("protest_ratio", 0) > 0.3:
                tax_change = -0.05
                sec_change = 0.1
            if s_info.get("satisfaction", 0.5) < 0.3:
                tax_change = -0.05
                focus = "food"

            directives.append({
                "settlement_id": s_info["id"],
                "tax_change": tax_change,
                "security_change": sec_change,
                "resource_focus": focus,
            })

        diplo_actions = []
        my_strength = self._compute_strength()
        my_pop = my_strength.get("population", 0)
        my_mil = my_strength.get("military", 0)

        for fid, status in perception.diplomatic_status.items():
            # 计算对方实力
            target_pop = self._estimate_target_strength(fid)

            if status == "NEUTRAL":
                # 强于对手1.3倍时考虑宣战（30%概率）
                if my_pop > target_pop * 1.3 and self._rng.random() < 0.3:
                    diplo_actions.append({
                        "target_faction": fid,
                        "action": "declare_war",
                        "reasoning": "实力优势，发动掠夺战争",
                    })
                elif perception.avg_satisfaction > 0.5:
                    diplo_actions.append({
                        "target_faction": fid,
                        "action": "propose_trade",
                        "reasoning": "局势稳定，寻求贸易合作",
                    })

            elif status == "ALLIED":
                # 盟友弱小时考虑背叛（20%概率）
                trust = 0.5
                if hasattr(self.model, "diplomacy"):
                    trust = self.model.diplomacy.get_trust(
                        self.faction_id, fid,
                    )
                if trust < 0.3 and self._rng.random() < 0.2:
                    diplo_actions.append({
                        "target_faction": fid,
                        "action": "break_treaty",
                        "reasoning": "信任度低，背叛盟约以获取利益",
                    })

            # 内部满意度低时对外宣战转嫁矛盾（20%概率）
            if (
                perception.avg_satisfaction < 0.4
                and status not in ("WAR", "ALLIED")
                and self._rng.random() < 0.2
            ):
                diplo_actions.append({
                    "target_faction": fid,
                    "action": "declare_war",
                    "reasoning": "内部矛盾严重，对外转嫁矛盾",
                })

        return validate_leader_decision({
            "diplomatic_actions": diplo_actions,
            "policy_directives": directives,
            "overall_strategy": "实力扩张，机会主义外交",
            "reasoning": "规则回退策略（攻击性）",
        })

    def apply_decision(self, decision: dict) -> None:
        """将战略决策应用到阵营。"""
        self._apply_policy_directives(decision.get("policy_directives", []))
        self._apply_diplomatic_actions(
            decision.get("diplomatic_actions", []),
        )

    def _apply_policy_directives(self, directives: list[dict]) -> None:
        """应用政策指令到下属聚落。"""
        if not hasattr(self.model, "settlements"):
            return

        from civsim.politics.governance import (
            GovernanceAction,
            apply_governance_action,
        )

        for d in directives:
            sid = d.get("settlement_id")
            if sid not in self.controlled_settlements:
                continue
            settlement = self.model.settlements.get(sid)
            if settlement is None:
                continue
            action = GovernanceAction(
                tax_rate_change=d.get("tax_change", 0.0),
                security_change=d.get("security_change", 0.0),
                resource_focus=d.get("resource_focus", "balanced"),
                reasoning=f"首领{self.unique_id}指令",
            )
            apply_governance_action(settlement, action)

    def _apply_diplomatic_actions(self, actions: list[dict]) -> None:
        """应用外交行动。"""
        if not hasattr(self.model, "diplomacy"):
            return

        from civsim.politics.diplomacy import (
            DiplomaticStatus,
            Treaty,
            TreatyType,
        )

        dm: DiplomacyManager = self.model.diplomacy
        tick = self.model.clock.tick

        for action in actions:
            target = action.get("target_faction")
            act = action.get("action", "none")
            if target is None or act == "none":
                continue

            if act == "propose_alliance":
                current = dm.get_relation(self.faction_id, target)
                if current >= DiplomaticStatus.FRIENDLY:
                    treaty = Treaty(
                        treaty_type=TreatyType.MILITARY_ALLIANCE,
                        faction_a=self.faction_id,
                        faction_b=target,
                        signed_tick=tick,
                    )
                    dm.sign_treaty(treaty)
                    self.memory.add_event(
                        tick, f"与阵营{target}结盟", importance=0.9,
                    )

            elif act == "propose_trade":
                treaty = Treaty(
                    treaty_type=TreatyType.TRADE_AGREEMENT,
                    faction_a=self.faction_id,
                    faction_b=target,
                    signed_tick=tick,
                    duration_ticks=self.model.clock.ticks_per_year,
                )
                dm.sign_treaty(treaty)

            elif act == "declare_war":
                dm.set_relation(
                    self.faction_id, target,
                    DiplomaticStatus.WAR, tick,
                )
                dm.update_trust(self.faction_id, target, -0.2)
                self.memory.add_event(
                    tick, f"向阵营{target}宣战", importance=1.0,
                )

            elif act == "offer_peace":
                current = dm.get_relation(self.faction_id, target)
                if current == DiplomaticStatus.WAR:
                    dm.set_relation(
                        self.faction_id, target,
                        DiplomaticStatus.NEUTRAL, tick,
                    )
                    self.memory.add_event(
                        tick, f"与阵营{target}议和", importance=0.8,
                    )

            elif act == "break_treaty":
                treaties = dm.get_active_treaties(self.faction_id)
                for t in treaties:
                    if target in (t.faction_a, t.faction_b):
                        dm.break_treaty(t, self.faction_id, tick)
                        self.memory.add_event(
                            tick,
                            f"背叛阵营{target}，撕毁{t.treaty_type.value}",
                            importance=1.0,
                        )
                        break

            elif act == "trade_embargo":
                dm.set_relation(
                    self.faction_id, target,
                    DiplomaticStatus.HOSTILE, tick,
                )
                dm.update_trust(self.faction_id, target, -0.15)
                self.memory.add_event(
                    tick, f"对阵营{target}实施贸易禁运", importance=0.7,
                )

    def negotiate(
        self,
        other: Leader,
        topic: str,
        max_rounds: int = 2,
    ) -> dict:
        """与另一位首领进行外交谈判。

        Args:
            other: 对方首领。
            topic: 谈判议题。
            max_rounds: 最大对话轮数。

        Returns:
            谈判结果字典。
        """
        if self._gateway is None or other._gateway is None:
            return {"result": "no_llm", "outcome": "reject"}

        messages: list[str] = []
        my_strength = self._compute_strength()
        other_strength = other._compute_strength()

        for _round in range(max_rounds):
            # 己方发言
            my_prompt = build_negotiation_prompt(
                my_faction_id=self.faction_id,
                other_faction_id=other.faction_id,
                topic=topic,
                my_strength=my_strength,
                previous_messages=messages,
            )
            try:
                my_resp = self._gateway.call_json("leader", [
                    {"role": "system", "content": build_leader_system_prompt()},
                    {"role": "user", "content": my_prompt},
                ])
                my_text = my_resp.get("response", "")
                messages.append(f"阵营{self.faction_id}: {my_text}")

                if my_resp.get("decision") == "accept":
                    return {"result": "accepted", "terms": my_resp.get("terms", "")}
            except Exception:
                break

            # 对方发言
            other_prompt = build_negotiation_prompt(
                my_faction_id=other.faction_id,
                other_faction_id=self.faction_id,
                topic=topic,
                my_strength=other_strength,
                previous_messages=messages,
            )
            try:
                other_resp = other._gateway.call_json("leader", [
                    {"role": "system", "content": build_leader_system_prompt()},
                    {"role": "user", "content": other_prompt},
                ])
                other_text = other_resp.get("response", "")
                messages.append(f"阵营{other.faction_id}: {other_text}")

                if other_resp.get("decision") == "accept":
                    return {"result": "accepted", "terms": other_resp.get("terms", "")}
            except Exception:
                break

        return {"result": "no_agreement", "messages": messages}

    def _compute_strength(self) -> dict:
        """计算阵营实力。"""
        pop = 0
        gold = 0.0
        if hasattr(self.model, "settlements"):
            for sid in self.controlled_settlements:
                s = self.model.settlements.get(sid)
                if s:
                    pop += s.population
                    gold += s.stockpile.get("gold", 0)
        return {"population": pop, "military": gold * 0.5 + pop * 0.1}

    def _estimate_target_strength(self, target_faction_id: int) -> int:
        """估算目标阵营的人口实力。"""
        if not hasattr(self.model, "leaders"):
            return 0
        for leader in self.model.leaders:
            if leader.faction_id == target_faction_id:
                strength = leader._compute_strength()
                return strength.get("population", 0)
        return 0

    def _get_faction_civilians(self, settlement_id: int) -> list:
        """获取指定聚落的平民。"""
        from civsim.agents.civilian import Civilian
        return [
            a for a in self.model.agents
            if isinstance(a, Civilian)
            and a.home_settlement_id == settlement_id
        ]

    def _get_diplomatic_status(self) -> dict[int, str]:
        """获取与其他阵营的外交状态。"""
        status: dict[int, str] = {}
        if not hasattr(self.model, "diplomacy"):
            return status
        if not hasattr(self.model, "leaders"):
            return status
        for leader in self.model.leaders:
            if leader.faction_id != self.faction_id:
                rel = self.model.diplomacy.get_relation(
                    self.faction_id, leader.faction_id,
                )
                status[leader.faction_id] = rel.name
        return status

    def _get_active_treaties_desc(self) -> list[str]:
        """获取活跃条约描述列表。"""
        if not hasattr(self.model, "diplomacy"):
            return []
        treaties = self.model.diplomacy.get_active_treaties(self.faction_id)
        return [
            f"{t.treaty_type.value}: 阵营{t.faction_a}↔阵营{t.faction_b}"
            for t in treaties
        ]

    async def decide_async(
        self, perception: LeaderPerception,
    ) -> dict | None:
        """异步调用 LLM 生成战略决策。"""
        if self._gateway is None:
            return self._fallback_decision(perception)

        memory_context = self.memory.build_context(max_entries=5)
        system_msg = build_leader_system_prompt()
        user_msg = build_leader_perception_prompt(
            faction_id=perception.faction_id,
            year=perception.year,
            season=perception.season,
            settlements_info=perception.settlements_info,
            total_population=perception.total_population,
            total_resources=perception.total_resources,
            avg_satisfaction=perception.avg_satisfaction,
            diplomatic_status=perception.diplomatic_status,
            active_treaties=perception.active_treaties,
            memory_context=memory_context,
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        try:
            raw = await self._gateway.acall_json("leader", messages)
            return validate_leader_decision(raw)
        except Exception as e:
            logger.warning(
                "首领 %d 异步LLM决策失败: %s，使用回退策略",
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

        if decision is None:
            decision = await self.decide_async(perception)

        if decision is None:
            return

        if self.cache is not None and not cache_hit:
            self.cache.store(perception.to_features(), decision)

        self.apply_decision(decision)
        self.memory.add_decision(
            tick=self.model.clock.tick, decision=decision,
        )
        self.last_decision = decision
        self.decision_count += 1
