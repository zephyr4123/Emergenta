"""diplomacy.py 单元测试。

验证外交关系管理器的状态机、条约签署/违反/过期、信任度更新。
"""

import pytest

from civsim.config_params_ext import DiplomacyParamsConfig
from civsim.politics.diplomacy import (
    DiplomacyManager,
    DiplomaticStatus,
    Treaty,
    TreatyType,
)


class TestDiplomaticStatus:
    """测试外交状态枚举。"""

    def test_status_ordering(self) -> None:
        """验证状态枚举的数值顺序。"""
        assert DiplomaticStatus.WAR < DiplomaticStatus.HOSTILE
        assert DiplomaticStatus.HOSTILE < DiplomaticStatus.NEUTRAL
        assert DiplomaticStatus.NEUTRAL < DiplomaticStatus.FRIENDLY
        assert DiplomaticStatus.FRIENDLY < DiplomaticStatus.ALLIED

    def test_status_int_values(self) -> None:
        """验证状态枚举的整数值。"""
        assert int(DiplomaticStatus.WAR) == 0
        assert int(DiplomaticStatus.ALLIED) == 4


class TestDiplomacyManagerRelations:
    """测试外交关系管理。"""

    def test_default_relation_is_neutral(self) -> None:
        """验证未设置的关系默认为中立。"""
        dm = DiplomacyManager()
        assert dm.get_relation(1, 2) == DiplomaticStatus.NEUTRAL

    def test_set_and_get_relation(self) -> None:
        """验证设置和获取关系。"""
        dm = DiplomacyManager()
        dm.set_relation(1, 2, DiplomaticStatus.FRIENDLY, tick=10)
        assert dm.get_relation(1, 2) == DiplomaticStatus.FRIENDLY

    def test_relation_key_is_ordered(self) -> None:
        """验证关系键是有序的（无论参数顺序）。"""
        dm = DiplomacyManager()
        dm.set_relation(3, 1, DiplomaticStatus.WAR, tick=5)
        assert dm.get_relation(1, 3) == DiplomaticStatus.WAR
        assert dm.get_relation(3, 1) == DiplomaticStatus.WAR

    def test_set_relation_logs_event(self) -> None:
        """验证状态变更记录到日志。"""
        dm = DiplomacyManager()
        dm.set_relation(1, 2, DiplomaticStatus.WAR, tick=100)
        assert len(dm.event_log) == 1
        assert dm.event_log[0]["new_status"] == "WAR"

    def test_same_status_no_log(self) -> None:
        """验证相同状态不重复记录。"""
        dm = DiplomacyManager()
        dm.set_relation(1, 2, DiplomaticStatus.NEUTRAL, tick=1)
        assert len(dm.event_log) == 0  # NEUTRAL→NEUTRAL 无变化


class TestDiplomacyManagerTrust:
    """测试信任度系统。"""

    def test_default_trust(self) -> None:
        """验证默认信任度（随机化在 0.3-0.7 范围内）。"""
        dm = DiplomacyManager()
        trust = dm.get_trust(1, 2)
        assert 0.3 <= trust <= 0.7

    def test_update_trust_positive(self) -> None:
        """验证信任度增加。"""
        params = DiplomacyParamsConfig(initial_trust=0.5, randomize_trust=False)
        dm = DiplomacyManager(params=params)
        result = dm.update_trust(1, 2, 0.2)
        assert result == pytest.approx(0.7)
        assert dm.get_trust(1, 2) == pytest.approx(0.7)

    def test_trust_clamped_to_zero_one(self) -> None:
        """验证信任度被截断到 [0, 1]。"""
        dm = DiplomacyManager(initial_trust=0.5)
        dm.update_trust(1, 2, 0.8)
        assert dm.get_trust(1, 2) == 1.0

        dm.update_trust(1, 2, -1.5)
        assert dm.get_trust(1, 2) == 0.0


class TestTreaty:
    """测试条约。"""

    def test_permanent_treaty_never_expires(self) -> None:
        """验证永久条约不过期。"""
        treaty = Treaty(
            treaty_type=TreatyType.MILITARY_ALLIANCE,
            faction_a=1, faction_b=2, signed_tick=0,
        )
        assert not treaty.is_expired(99999)

    def test_timed_treaty_expires(self) -> None:
        """验证定时条约过期。"""
        treaty = Treaty(
            treaty_type=TreatyType.TRADE_AGREEMENT,
            faction_a=1, faction_b=2,
            signed_tick=100, duration_ticks=50,
        )
        assert not treaty.is_expired(149)
        assert treaty.is_expired(150)
        assert treaty.is_expired(200)


class TestDiplomacyManagerTreaties:
    """测试条约管理。"""

    def test_sign_military_alliance_sets_allied(self) -> None:
        """验证签署军事同盟设置 ALLIED 状态。"""
        dm = DiplomacyManager()
        treaty = Treaty(
            treaty_type=TreatyType.MILITARY_ALLIANCE,
            faction_a=1, faction_b=2, signed_tick=10,
        )
        dm.sign_treaty(treaty)
        assert dm.get_relation(1, 2) == DiplomaticStatus.ALLIED

    def test_sign_trade_agreement_upgrades_to_friendly(self) -> None:
        """验证签署贸易协议升级到 FRIENDLY。"""
        dm = DiplomacyManager()
        treaty = Treaty(
            treaty_type=TreatyType.TRADE_AGREEMENT,
            faction_a=1, faction_b=2, signed_tick=10,
        )
        dm.sign_treaty(treaty)
        assert dm.get_relation(1, 2) == DiplomaticStatus.FRIENDLY

    def test_sign_treaty_increases_trust(self) -> None:
        """验证签署条约增加信任度。"""
        params = DiplomacyParamsConfig(initial_trust=0.5, randomize_trust=False)
        dm = DiplomacyManager(params=params)
        treaty = Treaty(
            treaty_type=TreatyType.TRADE_AGREEMENT,
            faction_a=1, faction_b=2, signed_tick=10,
        )
        dm.sign_treaty(treaty)
        assert dm.get_trust(1, 2) == pytest.approx(0.6)

    def test_break_treaty_decreases_trust(self) -> None:
        """验证违反条约降低信任度。"""
        dm = DiplomacyManager(initial_trust=0.5)
        treaty = Treaty(
            treaty_type=TreatyType.TRADE_AGREEMENT,
            faction_a=1, faction_b=2, signed_tick=10,
        )
        dm.sign_treaty(treaty)
        dm.break_treaty(treaty, breaker_id=1, tick=20)
        assert not treaty.active
        assert dm.get_trust(1, 2) < 0.5

    def test_break_treaty_sets_hostile(self) -> None:
        """验证违反条约后关系降为 WAR。"""
        dm = DiplomacyManager()
        treaty = Treaty(
            treaty_type=TreatyType.MILITARY_ALLIANCE,
            faction_a=1, faction_b=2, signed_tick=10,
        )
        dm.sign_treaty(treaty)
        dm.break_treaty(treaty, breaker_id=1, tick=20)
        assert dm.get_relation(1, 2) == DiplomaticStatus.WAR

    def test_expire_treaties(self) -> None:
        """验证条约过期清理。"""
        dm = DiplomacyManager()
        treaty = Treaty(
            treaty_type=TreatyType.TRADE_AGREEMENT,
            faction_a=1, faction_b=2,
            signed_tick=0, duration_ticks=100,
        )
        dm.sign_treaty(treaty)
        expired = dm.expire_treaties(50)
        assert len(expired) == 0
        expired = dm.expire_treaties(100)
        assert len(expired) == 1
        assert not treaty.active

    def test_get_active_treaties(self) -> None:
        """验证获取活跃条约。"""
        dm = DiplomacyManager()
        t1 = Treaty(
            treaty_type=TreatyType.TRADE_AGREEMENT,
            faction_a=1, faction_b=2, signed_tick=0,
        )
        t2 = Treaty(
            treaty_type=TreatyType.NON_AGGRESSION,
            faction_a=1, faction_b=3, signed_tick=0,
        )
        dm.sign_treaty(t1)
        dm.sign_treaty(t2)
        all_active = dm.get_active_treaties()
        assert len(all_active) == 2
        faction1 = dm.get_active_treaties(faction_id=1)
        assert len(faction1) == 2
        faction3 = dm.get_active_treaties(faction_id=3)
        assert len(faction3) == 1


class TestDiplomacyManagerQueries:
    """测试查询方法。"""

    def test_get_allies(self) -> None:
        """验证获取盟友列表。"""
        dm = DiplomacyManager()
        dm.set_relation(1, 2, DiplomaticStatus.ALLIED, tick=0)
        dm.set_relation(1, 3, DiplomaticStatus.FRIENDLY, tick=0)
        allies = dm.get_allies(1)
        assert 2 in allies
        assert 3 not in allies

    def test_get_enemies(self) -> None:
        """验证获取敌对阵营。"""
        dm = DiplomacyManager()
        dm.set_relation(1, 2, DiplomaticStatus.WAR, tick=0)
        dm.set_relation(1, 3, DiplomaticStatus.HOSTILE, tick=0)
        enemies = dm.get_enemies(1)
        assert 2 in enemies
        assert 3 not in enemies

    def test_get_relations_dict(self) -> None:
        """验证整数值字典导出。"""
        dm = DiplomacyManager()
        dm.set_relation(1, 2, DiplomaticStatus.FRIENDLY, tick=0)
        d = dm.get_relations_dict()
        assert d[(1, 2)] == 3
