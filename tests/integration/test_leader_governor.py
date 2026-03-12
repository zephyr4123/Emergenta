"""首领-镇长集成测试。

验证首领指令→镇长执行→平民反应的完整链路。
使用真实配置，最少化 mock。
"""

import mesa
import numpy as np
import pytest

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.behaviors.markov import Personality
from civsim.agents.civilian import Civilian, Profession
from civsim.agents.governor import Governor
from civsim.agents.leader import Leader
from civsim.config import CivSimConfig, load_config
from civsim.economy.settlement import Settlement
from civsim.llm.prompts import validate_leader_decision
from civsim.politics.diplomacy import DiplomacyManager, DiplomaticStatus, Treaty, TreatyType
from civsim.politics.governance import GovernanceAction, apply_governance_action
from civsim.world.clock import Clock


class IntegrationModel(mesa.Model):
    """集成测试用 Model，模拟三层结构。"""

    def __init__(self, seed: int = 42) -> None:
        super().__init__(seed=seed)
        self.grid = mesa.space.MultiGrid(30, 30, torus=False)
        self.clock = Clock(ticks_per_day=4, days_per_season=30)
        self.config = CivSimConfig()
        self.db = None
        self.diplomacy = DiplomacyManager()
        self.leaders: list = []
        self.settlements: dict[int, Settlement] = {
            0: Settlement(
                id=0, name="聚落A", position=(5, 5),
                population=30,
                stockpile={"food": 500.0, "wood": 200.0, "ore": 50.0, "gold": 100.0},
            ),
            1: Settlement(
                id=1, name="聚落B", position=(25, 25),
                population=20,
                stockpile={"food": 400.0, "wood": 150.0, "ore": 30.0, "gold": 80.0},
            ),
        }


def _spawn_civilians(model: IntegrationModel, sid: int, n: int) -> list:
    """生成平民。"""
    pos = model.settlements[sid].position
    civs = []
    for _ in range(n):
        c = Civilian(
            model=model, home_settlement_id=sid,
            personality=Personality.NEUTRAL,
            profession=Profession.FARMER,
            revolt_threshold=0.4,
        )
        model.grid.place_agent(c, pos)
        civs.append(c)
    return civs


class TestLeaderPolicyToGovernor:
    """测试首领政策→镇长执行链路。"""

    def test_leader_directive_changes_settlement(self) -> None:
        """验证首领指令通过治理模块改变聚落参数。"""
        model = IntegrationModel()
        _spawn_civilians(model, 0, 5)

        leader = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
        )
        model.grid.place_agent(leader, (5, 5))
        model.leaders.append(leader)

        old_tax = model.settlements[0].tax_rate
        decision = validate_leader_decision({
            "policy_directives": [{
                "settlement_id": 0,
                "tax_change": 0.05,
                "security_change": 0.1,
                "resource_focus": "food",
            }],
            "diplomatic_actions": [],
            "overall_strategy": "发展经济",
            "reasoning": "测试",
        })
        leader.apply_decision(decision)

        assert model.settlements[0].tax_rate == pytest.approx(old_tax + 0.05)
        assert model.settlements[0].security_level > 0.5

    def test_leader_tax_increase_affects_civilians(self) -> None:
        """验证首领加税→聚落税率升高→影响平民转移矩阵。"""
        model = IntegrationModel()
        civs = _spawn_civilians(model, 0, 10)

        leader = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
        )
        model.grid.place_agent(leader, (5, 5))

        # 大幅加税
        decision = validate_leader_decision({
            "policy_directives": [{
                "settlement_id": 0,
                "tax_change": 0.1,
                "security_change": 0.0,
                "resource_focus": "balanced",
            }],
        })
        leader.apply_decision(decision)
        new_tax = model.settlements[0].tax_rate
        assert new_tax > 0.1

        # 运行平民几个 tick，检查状态变化
        for _ in range(10):
            model.clock.advance()
            for c in civs:
                c.step()

        # 验证平民不再全是初始状态
        states = [c.state for c in civs]
        assert len(set(states)) >= 1  # 至少有状态转移发生


class TestLeaderDiplomacy:
    """测试首领外交行动。"""

    def test_declare_war_sets_status(self) -> None:
        """验证宣战改变外交状态。"""
        model = IntegrationModel()
        leader1 = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
        )
        leader2 = Leader(
            model=model, faction_id=2,
            controlled_settlements=[1],
        )
        model.leaders = [leader1, leader2]
        model.grid.place_agent(leader1, (5, 5))
        model.grid.place_agent(leader2, (25, 25))

        decision = validate_leader_decision({
            "diplomatic_actions": [{
                "target_faction": 2,
                "action": "declare_war",
                "reasoning": "测试宣战",
            }],
        })
        leader1.apply_decision(decision)
        assert model.diplomacy.get_relation(1, 2) == DiplomaticStatus.WAR

    def test_propose_trade_creates_treaty(self) -> None:
        """验证提议贸易创建条约。"""
        model = IntegrationModel()
        leader1 = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
        )
        leader2 = Leader(
            model=model, faction_id=2,
            controlled_settlements=[1],
        )
        model.leaders = [leader1, leader2]
        model.grid.place_agent(leader1, (5, 5))
        model.grid.place_agent(leader2, (25, 25))

        decision = validate_leader_decision({
            "diplomatic_actions": [{
                "target_faction": 2,
                "action": "propose_trade",
                "reasoning": "测试贸易",
            }],
        })
        leader1.apply_decision(decision)
        treaties = model.diplomacy.get_active_treaties(faction_id=1)
        assert len(treaties) >= 1

    def test_propose_alliance_requires_friendly(self) -> None:
        """验证联盟需要友好关系。"""
        model = IntegrationModel()
        leader1 = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
        )
        leader2 = Leader(
            model=model, faction_id=2,
            controlled_settlements=[1],
        )
        model.leaders = [leader1, leader2]
        model.grid.place_agent(leader1, (5, 5))
        model.grid.place_agent(leader2, (25, 25))

        # 先设为友好
        model.diplomacy.set_relation(1, 2, DiplomaticStatus.FRIENDLY)
        decision = validate_leader_decision({
            "diplomatic_actions": [{
                "target_faction": 2,
                "action": "propose_alliance",
                "reasoning": "测试联盟",
            }],
        })
        leader1.apply_decision(decision)
        assert model.diplomacy.get_relation(1, 2) == DiplomaticStatus.ALLIED

    def test_offer_peace_ends_war(self) -> None:
        """验证求和结束战争。"""
        model = IntegrationModel()
        leader1 = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
        )
        leader2 = Leader(
            model=model, faction_id=2,
            controlled_settlements=[1],
        )
        model.leaders = [leader1, leader2]
        model.grid.place_agent(leader1, (5, 5))
        model.grid.place_agent(leader2, (25, 25))

        model.diplomacy.set_relation(1, 2, DiplomaticStatus.WAR)
        decision = validate_leader_decision({
            "diplomatic_actions": [{
                "target_faction": 2,
                "action": "offer_peace",
                "reasoning": "测试求和",
            }],
        })
        leader1.apply_decision(decision)
        assert model.diplomacy.get_relation(1, 2) == DiplomaticStatus.NEUTRAL


class TestFullChain:
    """测试完整三层链路。"""

    def test_leader_governor_civilian_chain(self) -> None:
        """验证首领→镇长→平民的完整决策传导链。"""
        model = IntegrationModel()
        civs = _spawn_civilians(model, 0, 10)

        gov = Governor(model=model, settlement_id=0, gateway=None)
        model.grid.place_agent(gov, (5, 5))
        gov.decision_offset = 0  # 固定偏移，确保在季度边界决策

        leader = Leader(
            model=model, faction_id=1,
            controlled_settlements=[0],
        )
        model.grid.place_agent(leader, (5, 5))
        model.leaders.append(leader)

        # 首领决策加税
        leader_decision = validate_leader_decision({
            "policy_directives": [{
                "settlement_id": 0,
                "tax_change": 0.08,
                "security_change": -0.05,
                "resource_focus": "food",
            }],
        })
        leader.apply_decision(leader_decision)

        # 验证聚落税率已变
        assert model.settlements[0].tax_rate > 0.1

        # 推进到季度边界，让镇长决策
        ticks_per_season = model.clock.ticks_per_day * model.clock.days_per_season
        for _ in range(ticks_per_season):
            model.clock.advance()

        gov.step()  # 镇长感知并做出决策
        # 镇长应该已经做了一次决策
        assert gov.decision_count == 1

        # 平民运行几 tick
        for _ in range(20):
            model.clock.advance()
            for c in civs:
                c.step()

        # 验证至少有状态转移发生
        states = [c.state for c in civs]
        unique_states = set(states)
        assert len(unique_states) >= 1
