"""动态马尔可夫转移矩阵与 FSM 的单元测试。

覆盖 NUM_STATES 常量、基础矩阵行和验证、normalize_rows 工具函数、
compute_transition_matrix 的饥饿/税率/安全/Granovetter 传染效应，
以及 sample_next_state 的有效性。
"""

import numpy as np
import pytest

from civsim.agents.behaviors.fsm import NUM_STATES, STATE_NAMES, CivilianState
from civsim.agents.behaviors.markov import (
    PERSONALITY_MATRICES,
    Personality,
    compute_transition_matrix,
    normalize_rows,
    sample_next_state,
)


class TestFSMConstants:
    """FSM 常量与枚举测试。"""

    def test_num_states_is_seven(self) -> None:
        """NUM_STATES 应为 7。"""
        assert NUM_STATES == 7

    def test_civilian_state_count(self) -> None:
        """CivilianState 枚举应有 7 个成员。"""
        assert len(CivilianState) == 7

    def test_civilian_state_values_contiguous(self) -> None:
        """CivilianState 的整数值应为 0-6 连续。"""
        values = sorted(s.value for s in CivilianState)
        assert values == list(range(7))

    def test_state_names_covers_all_states(self) -> None:
        """STATE_NAMES 应覆盖所有状态。"""
        for state in CivilianState:
            assert state in STATE_NAMES

    def test_state_names_are_chinese(self) -> None:
        """状态名称应为中文。"""
        expected = {"劳作", "休息", "交易", "社交", "迁徙", "抗议", "战斗"}
        actual = set(STATE_NAMES.values())
        assert actual == expected


class TestPersonality:
    """Personality 枚举测试。"""

    def test_three_personalities(self) -> None:
        """应有 3 种性格类型。"""
        assert len(Personality) == 3

    def test_personality_values(self) -> None:
        """性格枚举值应正确。"""
        assert Personality.COMPLIANT.value == "compliant"
        assert Personality.NEUTRAL.value == "neutral"
        assert Personality.REBELLIOUS.value == "rebellious"


class TestBaseMatrices:
    """基础转移矩阵验证测试。"""

    @pytest.mark.parametrize("personality", list(Personality))
    def test_matrix_shape(self, personality: Personality) -> None:
        """每种性格的基础矩阵形状应为 (7, 7)。"""
        matrix = PERSONALITY_MATRICES[personality]
        assert matrix.shape == (NUM_STATES, NUM_STATES)

    @pytest.mark.parametrize("personality", list(Personality))
    def test_row_sums_are_one(self, personality: Personality) -> None:
        """基础矩阵每行之和应为 1.0。"""
        matrix = PERSONALITY_MATRICES[personality]
        row_sums = matrix.sum(axis=1)
        np.testing.assert_allclose(row_sums, 1.0, atol=1e-10)

    @pytest.mark.parametrize("personality", list(Personality))
    def test_all_probabilities_non_negative(
        self, personality: Personality
    ) -> None:
        """基础矩阵所有元素应非负。"""
        matrix = PERSONALITY_MATRICES[personality]
        assert np.all(matrix >= 0.0)

    @pytest.mark.parametrize("personality", list(Personality))
    def test_all_probabilities_at_most_one(
        self, personality: Personality
    ) -> None:
        """基础矩阵所有元素应不超过 1.0。"""
        matrix = PERSONALITY_MATRICES[personality]
        assert np.all(matrix <= 1.0)

    def test_all_three_personalities_present(self) -> None:
        """PERSONALITY_MATRICES 应包含全部 3 种性格。"""
        for p in Personality:
            assert p in PERSONALITY_MATRICES

    def test_compliant_has_low_protest_from_working(self) -> None:
        """顺从型从劳作到抗议的基础概率应较低。"""
        m = PERSONALITY_MATRICES[Personality.COMPLIANT]
        assert m[CivilianState.WORKING][CivilianState.PROTESTING] < 0.05

    def test_rebellious_has_high_protest_from_working(self) -> None:
        """叛逆型从劳作到抗议的基础概率应较高。"""
        m = PERSONALITY_MATRICES[Personality.REBELLIOUS]
        assert m[CivilianState.WORKING][CivilianState.PROTESTING] > 0.10

    def test_rebellious_protest_higher_than_compliant(self) -> None:
        """叛逆型的抗议倾向应高于顺从型。"""
        mc = PERSONALITY_MATRICES[Personality.COMPLIANT]
        mr = PERSONALITY_MATRICES[Personality.REBELLIOUS]
        # 从劳作到抗议
        assert (
            mr[CivilianState.WORKING][CivilianState.PROTESTING]
            > mc[CivilianState.WORKING][CivilianState.PROTESTING]
        )
        # 从社交到抗议
        assert (
            mr[CivilianState.SOCIALIZING][CivilianState.PROTESTING]
            > mc[CivilianState.SOCIALIZING][CivilianState.PROTESTING]
        )


class TestNormalizeRows:
    """normalize_rows() 工具函数测试。"""

    def test_already_normalized(self) -> None:
        """已归一化矩阵应保持不变。"""
        m = np.array([[0.5, 0.3, 0.2], [0.1, 0.8, 0.1]])
        result = normalize_rows(m)
        np.testing.assert_allclose(result, m, atol=1e-10)

    def test_unnormalized_rows(self) -> None:
        """未归一化矩阵应被正确归一化。"""
        m = np.array([[2.0, 3.0, 5.0], [1.0, 1.0, 1.0]])
        result = normalize_rows(m)
        np.testing.assert_allclose(result.sum(axis=1), 1.0, atol=1e-10)
        np.testing.assert_allclose(result[0], [0.2, 0.3, 0.5], atol=1e-10)
        np.testing.assert_allclose(
            result[1], [1 / 3, 1 / 3, 1 / 3], atol=1e-10
        )

    def test_negative_values_clipped(self) -> None:
        """负值应被裁剪为 0 再归一化。"""
        m = np.array([[-1.0, 2.0, 3.0]])
        result = normalize_rows(m)
        assert result[0][0] == pytest.approx(0.0)
        np.testing.assert_allclose(result.sum(axis=1), 1.0, atol=1e-10)

    def test_zero_row_handled(self) -> None:
        """全零行不应导致除零错误。"""
        m = np.array([[0.0, 0.0, 0.0]])
        result = normalize_rows(m)
        # 全零行按实现逻辑除以 1.0，结果全为 0
        np.testing.assert_allclose(result[0], [0.0, 0.0, 0.0], atol=1e-10)

    def test_preserves_shape(self) -> None:
        """归一化不应改变矩阵形状。"""
        m = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
        result = normalize_rows(m)
        assert result.shape == m.shape

    def test_7x7_matrix(self) -> None:
        """7x7 矩阵应正确归一化。"""
        rng = np.random.default_rng(42)
        m = rng.random((7, 7))
        result = normalize_rows(m)
        np.testing.assert_allclose(result.sum(axis=1), 1.0, atol=1e-10)
        assert np.all(result >= 0.0)


class TestComputeTransitionMatrix:
    """compute_transition_matrix() 动态调节测试。"""

    def test_output_shape(self) -> None:
        """输出矩阵形状应为 (7, 7)。"""
        m = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 0.0, 1.0, 0.0, 0.5
        )
        assert m.shape == (NUM_STATES, NUM_STATES)

    def test_output_rows_sum_to_one(self) -> None:
        """输出矩阵每行和应为 1.0。"""
        m = compute_transition_matrix(
            Personality.NEUTRAL, 0.5, 0.3, 0.7, 0.2, 0.4
        )
        np.testing.assert_allclose(m.sum(axis=1), 1.0, atol=1e-10)

    def test_output_non_negative(self) -> None:
        """输出矩阵所有元素应非负。"""
        m = compute_transition_matrix(
            Personality.REBELLIOUS, 1.0, 1.0, 0.0, 1.0, 0.0
        )
        assert np.all(m >= 0.0)

    def test_zero_adjustments_match_base(self) -> None:
        """无调节因子时结果应接近基础矩阵。"""
        m = compute_transition_matrix(
            Personality.NEUTRAL,
            hunger=0.0,
            tax_rate=0.0,
            security=1.0,  # safety = 0
            protest_ratio=0.0,
            revolt_threshold=0.5,
        )
        base = PERSONALITY_MATRICES[Personality.NEUTRAL]
        np.testing.assert_allclose(m, base, atol=1e-10)

    def test_hunger_increases_protest_from_working(self) -> None:
        """高饥饿度应增加从劳作到抗议的转移概率。"""
        m_low = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 0.0, 1.0, 0.0, 0.5
        )
        m_high = compute_transition_matrix(
            Personality.NEUTRAL, 1.0, 0.0, 1.0, 0.0, 0.5
        )
        assert (
            m_high[CivilianState.WORKING][CivilianState.PROTESTING]
            > m_low[CivilianState.WORKING][CivilianState.PROTESTING]
        )

    def test_hunger_increases_migration_from_working(self) -> None:
        """高饥饿度应增加从劳作到迁徙的转移概率。"""
        m_low = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 0.0, 1.0, 0.0, 0.5
        )
        m_high = compute_transition_matrix(
            Personality.NEUTRAL, 1.0, 0.0, 1.0, 0.0, 0.5
        )
        assert (
            m_high[CivilianState.WORKING][CivilianState.MIGRATING]
            > m_low[CivilianState.WORKING][CivilianState.MIGRATING]
        )

    def test_hunger_increases_working_from_resting(self) -> None:
        """高饥饿度应增加从休息到劳作的转移概率。"""
        m_low = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 0.0, 1.0, 0.0, 0.5
        )
        m_high = compute_transition_matrix(
            Personality.NEUTRAL, 1.0, 0.0, 1.0, 0.0, 0.5
        )
        assert (
            m_high[CivilianState.RESTING][CivilianState.WORKING]
            > m_low[CivilianState.RESTING][CivilianState.WORKING]
        )

    def test_tax_increases_protest_from_working(self) -> None:
        """高税率应增加从劳作到抗议的转移概率。"""
        m_low = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 0.0, 1.0, 0.0, 0.5
        )
        m_high = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 1.0, 1.0, 0.0, 0.5
        )
        assert (
            m_high[CivilianState.WORKING][CivilianState.PROTESTING]
            > m_low[CivilianState.WORKING][CivilianState.PROTESTING]
        )

    def test_tax_increases_protest_from_trading(self) -> None:
        """高税率应增加从交易到抗议的转移概率。"""
        m_low = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 0.0, 1.0, 0.0, 0.5
        )
        m_high = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 1.0, 1.0, 0.0, 0.5
        )
        assert (
            m_high[CivilianState.TRADING][CivilianState.PROTESTING]
            > m_low[CivilianState.TRADING][CivilianState.PROTESTING]
        )

    def test_low_security_increases_fighting(self) -> None:
        """低治安应增加从社交/抗议到战斗的转移概率。"""
        m_safe = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 0.0, 1.0, 0.0, 0.5
        )
        m_unsafe = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 0.0, 0.0, 0.0, 0.5
        )
        assert (
            m_unsafe[CivilianState.SOCIALIZING][CivilianState.FIGHTING]
            > m_safe[CivilianState.SOCIALIZING][CivilianState.FIGHTING]
        )
        assert (
            m_unsafe[CivilianState.PROTESTING][CivilianState.FIGHTING]
            > m_safe[CivilianState.PROTESTING][CivilianState.FIGHTING]
        )

    def test_granovetter_contagion_below_threshold(self) -> None:
        """抗议比例低于阈值时不应触发传染。"""
        m = compute_transition_matrix(
            Personality.NEUTRAL,
            hunger=0.0,
            tax_rate=0.0,
            security=1.0,
            protest_ratio=0.3,
            revolt_threshold=0.5,
        )
        base = PERSONALITY_MATRICES[Personality.NEUTRAL]
        # 应等于基础矩阵（因为其他因子都为 0）
        np.testing.assert_allclose(m, base, atol=1e-10)

    def test_granovetter_contagion_above_threshold(self) -> None:
        """抗议比例超过阈值时应大幅增加抗议转移概率。"""
        m_no = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 0.0, 1.0, 0.0, 0.5
        )
        m_yes = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 0.0, 1.0, 0.6, 0.5
        )
        # 劳作→抗议 应大幅增加
        assert (
            m_yes[CivilianState.WORKING][CivilianState.PROTESTING]
            > m_no[CivilianState.WORKING][CivilianState.PROTESTING] * 2
        )
        # 休息→抗议
        assert (
            m_yes[CivilianState.RESTING][CivilianState.PROTESTING]
            > m_no[CivilianState.RESTING][CivilianState.PROTESTING] * 2
        )
        # 社交→抗议
        assert (
            m_yes[CivilianState.SOCIALIZING][CivilianState.PROTESTING]
            > m_no[CivilianState.SOCIALIZING][CivilianState.PROTESTING] * 2
        )
        # 交易→抗议
        assert (
            m_yes[CivilianState.TRADING][CivilianState.PROTESTING]
            > m_no[CivilianState.TRADING][CivilianState.PROTESTING] * 2
        )

    def test_granovetter_at_exact_threshold(self) -> None:
        """抗议比例恰好等于阈值时应触发传染。"""
        m_below = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 0.0, 1.0, 0.49, 0.5
        )
        m_exact = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 0.0, 1.0, 0.5, 0.5
        )
        assert (
            m_exact[CivilianState.WORKING][CivilianState.PROTESTING]
            > m_below[CivilianState.WORKING][CivilianState.PROTESTING]
        )

    @pytest.mark.parametrize("personality", list(Personality))
    def test_all_personalities_produce_valid_matrix(
        self, personality: Personality
    ) -> None:
        """所有性格类型应产生有效的转移矩阵。"""
        m = compute_transition_matrix(
            personality, 0.5, 0.3, 0.6, 0.2, 0.4
        )
        assert m.shape == (NUM_STATES, NUM_STATES)
        np.testing.assert_allclose(m.sum(axis=1), 1.0, atol=1e-10)
        assert np.all(m >= 0.0)

    def test_extreme_values_still_valid(self) -> None:
        """极端参数（全满）仍应产生有效矩阵。"""
        m = compute_transition_matrix(
            Personality.REBELLIOUS,
            hunger=1.0,
            tax_rate=1.0,
            security=0.0,
            protest_ratio=1.0,
            revolt_threshold=0.0,
        )
        np.testing.assert_allclose(m.sum(axis=1), 1.0, atol=1e-10)
        assert np.all(m >= 0.0)
        assert np.all(m <= 1.0)


class TestSampleNextState:
    """sample_next_state() 采样测试。"""

    def test_returns_valid_state(self) -> None:
        """采样结果应为有效的 CivilianState。"""
        rng = np.random.default_rng(42)
        m = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 0.0, 1.0, 0.0, 0.5
        )
        state = sample_next_state(CivilianState.WORKING, m, rng)
        assert isinstance(state, CivilianState)
        assert 0 <= state.value < NUM_STATES

    def test_deterministic_with_seed(self) -> None:
        """相同种子应产生相同结果。"""
        m = compute_transition_matrix(
            Personality.NEUTRAL, 0.0, 0.0, 1.0, 0.0, 0.5
        )
        results_a = []
        results_b = []
        for _ in range(20):
            rng_a = np.random.default_rng(123)
            rng_b = np.random.default_rng(123)
            results_a.append(
                sample_next_state(CivilianState.WORKING, m, rng_a)
            )
            results_b.append(
                sample_next_state(CivilianState.WORKING, m, rng_b)
            )
        assert results_a == results_b

    def test_samples_from_correct_row(self) -> None:
        """应按当前状态对应的行采样。"""
        # 构造一个确定性矩阵：从 WORKING 必定转到 RESTING
        m = np.zeros((NUM_STATES, NUM_STATES))
        m[CivilianState.WORKING][CivilianState.RESTING] = 1.0
        # 其他行也给合法概率
        for i in range(NUM_STATES):
            if i != CivilianState.WORKING:
                m[i][i] = 1.0

        rng = np.random.default_rng(0)
        state = sample_next_state(CivilianState.WORKING, m, rng)
        assert state == CivilianState.RESTING

    @pytest.mark.parametrize("current", list(CivilianState))
    def test_all_starting_states(self, current: CivilianState) -> None:
        """从任意起始状态采样都应返回有效状态。"""
        rng = np.random.default_rng(42)
        m = compute_transition_matrix(
            Personality.NEUTRAL, 0.3, 0.2, 0.8, 0.1, 0.5
        )
        state = sample_next_state(current, m, rng)
        assert isinstance(state, CivilianState)

    def test_statistical_distribution(self) -> None:
        """大量采样的分布应近似矩阵概率。"""
        rng = np.random.default_rng(42)
        m = PERSONALITY_MATRICES[Personality.NEUTRAL].copy()
        n_samples = 50000
        counts = np.zeros(NUM_STATES)
        for _ in range(n_samples):
            state = sample_next_state(CivilianState.WORKING, m, rng)
            counts[state] += 1
        empirical = counts / n_samples
        expected = m[CivilianState.WORKING]
        np.testing.assert_allclose(empirical, expected, atol=0.02)
