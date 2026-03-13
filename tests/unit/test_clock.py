"""时间系统的单元测试。

覆盖 Clock 的 tick 递增、day/season/year 计算、
季节边界判断、产出倍率映射，以及决策时刻检测。
"""

import pytest

from civsim.world.clock import (
    SEASON_FARM_MULTIPLIER,
    SEASON_FOOD_CONSUMPTION_MULTIPLIER,
    SEASON_FOREST_MULTIPLIER,
    Clock,
    Season,
)


class TestSeason:
    """Season 枚举测试。"""

    def test_four_seasons(self) -> None:
        """应包含 4 个季节。"""
        assert len(Season) == 4

    def test_season_ordering(self) -> None:
        """季节按 春→夏→秋→冬 排列。"""
        assert Season.SPRING < Season.SUMMER < Season.AUTUMN < Season.WINTER

    def test_season_int_values(self) -> None:
        """季节整数值应为 0-3。"""
        assert Season.SPRING == 0
        assert Season.SUMMER == 1
        assert Season.AUTUMN == 2
        assert Season.WINTER == 3


class TestClockAdvance:
    """Clock.advance() 测试。"""

    def test_initial_tick_is_zero(self) -> None:
        """初始 tick 应为 0。"""
        clock = Clock()
        assert clock.tick == 0

    def test_advance_increments_tick(self) -> None:
        """advance() 应将 tick 加 1。"""
        clock = Clock()
        clock.advance()
        assert clock.tick == 1

    def test_multiple_advances(self) -> None:
        """多次 advance 应累计。"""
        clock = Clock()
        for _ in range(10):
            clock.advance()
        assert clock.tick == 10


class TestClockTimeCalculation:
    """当前 day/season/year 计算测试。"""

    def test_current_day_at_start(self) -> None:
        """初始状态当前天数应为 0。"""
        clock = Clock(ticks_per_day=4)
        assert clock.current_day == 0

    def test_current_day_within_first_day(self) -> None:
        """一天内多个 tick 应属于同一天。"""
        clock = Clock(ticks_per_day=4)
        for _ in range(3):
            clock.advance()
        assert clock.current_day == 0

    def test_current_day_after_one_day(self) -> None:
        """过了一天的 tick 数后应进入第 1 天。"""
        clock = Clock(ticks_per_day=4)
        for _ in range(4):
            clock.advance()
        assert clock.current_day == 1

    def test_current_season_at_start(self) -> None:
        """初始季节应为春。"""
        clock = Clock()
        assert clock.current_season == Season.SPRING

    def test_current_season_changes(self) -> None:
        """经过一个季度的 tick 数后季节应变化。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        ticks_per_season = 4 * 30  # 120
        for _ in range(ticks_per_season):
            clock.advance()
        assert clock.current_season == Season.SUMMER

    def test_season_cycle(self) -> None:
        """季节应按顺序循环。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        tps = clock.ticks_per_season
        expected_seasons = [
            Season.SPRING,
            Season.SUMMER,
            Season.AUTUMN,
            Season.WINTER,
            Season.SPRING,  # 循环回春
        ]
        for i, expected in enumerate(expected_seasons):
            clock.tick = i * tps
            assert clock.current_season == expected, (
                f"tick={clock.tick} 应为 {expected}"
            )

    def test_current_year_at_start(self) -> None:
        """初始年份应为 0。"""
        clock = Clock()
        assert clock.current_year == 0

    def test_current_year_after_one_year(self) -> None:
        """经过一年的 tick 数后年份应增加。"""
        clock = Clock(ticks_per_day=4, days_per_season=30, seasons_per_year=4)
        ticks_per_year = 4 * 30 * 4  # 480
        clock.tick = ticks_per_year
        assert clock.current_year == 1

    def test_ticks_per_season(self) -> None:
        """ticks_per_season 应等于 ticks_per_day * days_per_season。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        assert clock.ticks_per_season == 120

    def test_ticks_per_year(self) -> None:
        """ticks_per_year 应等于 ticks_per_season * seasons_per_year。"""
        clock = Clock(ticks_per_day=4, days_per_season=30, seasons_per_year=4)
        assert clock.ticks_per_year == 480


class TestClockBoundaryChecks:
    """is_new_day/is_new_season/is_new_year 边界检测测试。"""

    def test_is_new_day_at_tick_zero(self) -> None:
        """tick=0 应为新一天的开始。"""
        clock = Clock(ticks_per_day=4)
        assert clock.is_new_day() is True

    def test_is_new_day_mid_day(self) -> None:
        """一天中间的 tick 不应为新一天。"""
        clock = Clock(ticks_per_day=4)
        clock.tick = 1
        assert clock.is_new_day() is False
        clock.tick = 2
        assert clock.is_new_day() is False
        clock.tick = 3
        assert clock.is_new_day() is False

    def test_is_new_day_at_day_boundary(self) -> None:
        """恰好在天数边界应为新一天。"""
        clock = Clock(ticks_per_day=4)
        clock.tick = 4
        assert clock.is_new_day() is True
        clock.tick = 8
        assert clock.is_new_day() is True

    def test_is_new_season_at_tick_zero(self) -> None:
        """tick=0 应为新季度的开始。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        assert clock.is_new_season() is True

    def test_is_new_season_mid_season(self) -> None:
        """季度中间不应为新季度。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        clock.tick = 60
        assert clock.is_new_season() is False

    def test_is_new_season_at_boundary(self) -> None:
        """恰好在季度边界应为新季度。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        clock.tick = 120  # 4 * 30
        assert clock.is_new_season() is True

    def test_is_new_year_at_tick_zero(self) -> None:
        """tick=0 应为新一年的开始。"""
        clock = Clock(ticks_per_day=4, days_per_season=30, seasons_per_year=4)
        assert clock.is_new_year() is True

    def test_is_new_year_mid_year(self) -> None:
        """年中间不应为新一年。"""
        clock = Clock(ticks_per_day=4, days_per_season=30, seasons_per_year=4)
        clock.tick = 240
        assert clock.is_new_year() is False

    def test_is_new_year_at_boundary(self) -> None:
        """恰好在年度边界应为新一年。"""
        clock = Clock(ticks_per_day=4, days_per_season=30, seasons_per_year=4)
        clock.tick = 480  # 4 * 30 * 4
        assert clock.is_new_year() is True


class TestClockSeasonMultiplier:
    """季节产出倍率测试。"""

    def test_spring_farm_multiplier(self) -> None:
        """春季农田倍率应为 1.0。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        clock.tick = 0  # 春
        assert clock.farm_multiplier == pytest.approx(1.0)

    def test_summer_farm_multiplier(self) -> None:
        """夏季农田倍率应为 1.5。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        clock.tick = 120  # 夏
        assert clock.farm_multiplier == pytest.approx(1.5)

    def test_autumn_farm_multiplier(self) -> None:
        """秋季农田倍率应为 1.2。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        clock.tick = 240  # 秋
        assert clock.farm_multiplier == pytest.approx(1.2)

    def test_winter_farm_multiplier(self) -> None:
        """冬季农田倍率应为 0.3。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        clock.tick = 360  # 冬
        assert clock.farm_multiplier == pytest.approx(0.3)

    def test_forest_multiplier_all_seasons(self) -> None:
        """各季节森林倍率应正确。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        expected = {
            Season.SPRING: 1.0,
            Season.SUMMER: 1.2,
            Season.AUTUMN: 0.8,
            Season.WINTER: 0.5,
        }
        for season, multiplier in expected.items():
            clock.tick = int(season) * clock.ticks_per_season
            assert clock.forest_multiplier == pytest.approx(multiplier), (
                f"{season.name} 森林倍率应为 {multiplier}"
            )

    def test_food_consumption_multiplier_winter(self) -> None:
        """冬季食物消耗倍率应为 1.5。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        clock.tick = 360  # 冬
        assert clock.food_consumption_multiplier == pytest.approx(1.5)

    def test_food_consumption_multiplier_non_winter(self) -> None:
        """非冬季食物消耗倍率应为 1.0。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        for season in (Season.SPRING, Season.SUMMER, Season.AUTUMN):
            clock.tick = int(season) * clock.ticks_per_season
            assert clock.food_consumption_multiplier == pytest.approx(1.0), (
                f"{season.name} 食物消耗倍率应为 1.0"
            )

    def test_multiplier_constants_complete(self) -> None:
        """全局倍率字典应覆盖所有 4 个季节。"""
        for season in Season:
            assert season in SEASON_FARM_MULTIPLIER
            assert season in SEASON_FOREST_MULTIPLIER
            assert season in SEASON_FOOD_CONSUMPTION_MULTIPLIER


class TestClockDecisionTicks:
    """决策时刻检测测试。"""

    def test_governor_decision_at_season_start(self) -> None:
        """镇长决策时刻应在每季度开始。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        clock.tick = 0
        assert clock.is_governor_decision_tick() is True
        clock.tick = 120
        assert clock.is_governor_decision_tick() is True

    def test_governor_decision_not_mid_season(self) -> None:
        """季度中间不应是镇长决策时刻。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        clock.tick = 50
        assert clock.is_governor_decision_tick() is False

    def test_leader_decision_at_year_start(self) -> None:
        """首领决策时刻应在每年开始。"""
        clock = Clock(ticks_per_day=4, days_per_season=30, seasons_per_year=4)
        clock.tick = 0
        assert clock.is_leader_decision_tick() is True
        clock.tick = 480
        assert clock.is_leader_decision_tick() is True

    def test_leader_decision_not_mid_year(self) -> None:
        """年中间不应是首领决策时刻。"""
        clock = Clock(ticks_per_day=4, days_per_season=30, seasons_per_year=4)
        clock.tick = 120  # 夏季开始，非年度开始
        assert clock.is_leader_decision_tick() is False

    def test_governor_is_alias_for_new_season(self) -> None:
        """is_governor_decision_tick 应等价于 is_new_season。"""
        clock = Clock(ticks_per_day=4, days_per_season=30)
        for t in range(500):
            clock.tick = t
            assert (
                clock.is_governor_decision_tick() == clock.is_new_season()
            )

    def test_leader_is_alias_for_new_year(self) -> None:
        """is_leader_decision_tick 应在每半年触发。"""
        clock = Clock(ticks_per_day=4, days_per_season=30, seasons_per_year=4)
        half_year = clock.ticks_per_year // 2  # 240
        for t in range(1000):
            clock.tick = t
            expected = (half_year > 0 and t % half_year == 0)
            assert clock.is_leader_decision_tick() == expected
