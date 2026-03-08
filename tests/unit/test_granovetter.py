"""granovetter.py 单元测试。

验证 Granovetter 阈值传染模型的比例计算与阈值突破判定。
"""

import pytest

from civsim.agents.behaviors.fsm import CivilianState
from civsim.agents.behaviors.granovetter import (
    compute_fighting_ratio,
    compute_protest_ratio,
    granovetter_check,
)


class TestComputeProtestRatio:
    """测试 compute_protest_ratio 抗议比例计算。"""

    def test_empty_neighbors_returns_zero(self) -> None:
        """验证无邻居时返回 0。"""
        assert compute_protest_ratio([]) == 0.0

    def test_all_protesting_returns_one(self) -> None:
        """验证全部抗议时返回 1。"""
        states = [CivilianState.PROTESTING] * 5
        assert compute_protest_ratio(states) == 1.0

    def test_no_protesting_returns_zero(self) -> None:
        """验证无人抗议时返回 0。"""
        states = [CivilianState.WORKING, CivilianState.RESTING]
        assert compute_protest_ratio(states) == 0.0

    def test_partial_protesting(self) -> None:
        """验证部分抗议时返回正确比例。"""
        states = [
            CivilianState.PROTESTING,
            CivilianState.WORKING,
            CivilianState.RESTING,
            CivilianState.PROTESTING,
        ]
        assert compute_protest_ratio(states) == pytest.approx(0.5)

    def test_single_protesting_neighbor(self) -> None:
        """验证仅一个邻居且为抗议时返回 1。"""
        states = [CivilianState.PROTESTING]
        assert compute_protest_ratio(states) == 1.0

    def test_single_non_protesting_neighbor(self) -> None:
        """验证仅一个邻居且非抗议时返回 0。"""
        states = [CivilianState.FIGHTING]
        assert compute_protest_ratio(states) == 0.0


class TestGranovetterCheck:
    """测试 granovetter_check 阈值突破判定。"""

    def test_ratio_above_threshold_triggers(self) -> None:
        """验证抗议比例超过阈值时触发传染。"""
        states = [CivilianState.PROTESTING] * 3 + [CivilianState.WORKING] * 2
        # 比例 = 0.6, 阈值 = 0.5
        assert granovetter_check(0.5, states) is True

    def test_ratio_below_threshold_does_not_trigger(self) -> None:
        """验证抗议比例低于阈值时不触发传染。"""
        states = [CivilianState.PROTESTING] + [CivilianState.WORKING] * 4
        # 比例 = 0.2, 阈值 = 0.5
        assert granovetter_check(0.5, states) is False

    def test_ratio_equals_threshold_triggers(self) -> None:
        """验证抗议比例恰好等于阈值时触发传染。"""
        states = [CivilianState.PROTESTING] * 2 + [CivilianState.WORKING] * 2
        # 比例 = 0.5, 阈值 = 0.5
        assert granovetter_check(0.5, states) is True

    def test_zero_threshold_always_triggers_with_neighbors(self) -> None:
        """验证阈值为 0 时只要有邻居即触发。"""
        states = [CivilianState.WORKING] * 3
        # 比例 = 0.0, 阈值 = 0.0 => 0.0 >= 0.0
        assert granovetter_check(0.0, states) is True

    def test_zero_threshold_no_neighbors(self) -> None:
        """验证阈值为 0 且无邻居时不触发（比例为 0）。"""
        assert granovetter_check(0.0, []) is True

    def test_threshold_one_requires_all_protesting(self) -> None:
        """验证阈值为 1.0 时需要全部邻居抗议才触发。"""
        mixed = [CivilianState.PROTESTING] * 4 + [CivilianState.WORKING]
        assert granovetter_check(1.0, mixed) is False

        all_protest = [CivilianState.PROTESTING] * 5
        assert granovetter_check(1.0, all_protest) is True

    def test_empty_neighbors_returns_false_for_high_threshold(self) -> None:
        """验证无邻居时高阈值不触发。"""
        assert granovetter_check(0.5, []) is False


class TestComputeFightingRatio:
    """测试 compute_fighting_ratio 战斗比例计算。"""

    def test_empty_neighbors_returns_zero(self) -> None:
        """验证无邻居时返回 0。"""
        assert compute_fighting_ratio([]) == 0.0

    def test_all_fighting_returns_one(self) -> None:
        """验证全部战斗时返回 1。"""
        states = [CivilianState.FIGHTING] * 4
        assert compute_fighting_ratio(states) == 1.0

    def test_no_fighting_returns_zero(self) -> None:
        """验证无人战斗时返回 0。"""
        states = [CivilianState.PROTESTING, CivilianState.WORKING]
        assert compute_fighting_ratio(states) == 0.0

    def test_partial_fighting(self) -> None:
        """验证部分战斗时返回正确比例。"""
        states = [
            CivilianState.FIGHTING,
            CivilianState.WORKING,
            CivilianState.FIGHTING,
            CivilianState.PROTESTING,
        ]
        assert compute_fighting_ratio(states) == pytest.approx(0.5)

    def test_protesting_not_counted_as_fighting(self) -> None:
        """验证抗议状态不被计入战斗比例。"""
        states = [CivilianState.PROTESTING] * 3
        assert compute_fighting_ratio(states) == 0.0
