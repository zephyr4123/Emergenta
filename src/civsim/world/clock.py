"""时间系统。

管理 tick / day / season / year 的时间推进，
提供季节判断与决策间隔检测。
"""

from enum import IntEnum


class Season(IntEnum):
    """季节枚举。"""

    SPRING = 0
    SUMMER = 1
    AUTUMN = 2
    WINTER = 3


# 季节对应的产出倍率
SEASON_FARM_MULTIPLIER: dict[Season, float] = {
    Season.SPRING: 1.0,
    Season.SUMMER: 1.5,
    Season.AUTUMN: 1.2,
    Season.WINTER: 0.3,
}

SEASON_FOREST_MULTIPLIER: dict[Season, float] = {
    Season.SPRING: 1.0,
    Season.SUMMER: 1.2,
    Season.AUTUMN: 0.8,
    Season.WINTER: 0.5,
}

SEASON_FOOD_CONSUMPTION_MULTIPLIER: dict[Season, float] = {
    Season.SPRING: 1.0,
    Season.SUMMER: 1.0,
    Season.AUTUMN: 1.0,
    Season.WINTER: 1.5,
}


class Clock:
    """世界时间系统。

    管理 tick → day → season → year 的时间层级。

    Attributes:
        tick: 当前总 tick 数。
        ticks_per_day: 每天的 tick 数。
        days_per_season: 每季的天数。
        seasons_per_year: 每年的季数。
    """

    def __init__(
        self,
        ticks_per_day: int = 4,
        days_per_season: int = 30,
        seasons_per_year: int = 4,
    ) -> None:
        self.tick: int = 0
        self.ticks_per_day = ticks_per_day
        self.days_per_season = days_per_season
        self.seasons_per_year = seasons_per_year

    @property
    def ticks_per_season(self) -> int:
        """每季度的 tick 数。"""
        return self.ticks_per_day * self.days_per_season

    @property
    def ticks_per_year(self) -> int:
        """每年的 tick 数。"""
        return self.ticks_per_season * self.seasons_per_year

    @property
    def current_day(self) -> int:
        """当前天数（从 0 开始）。"""
        return self.tick // self.ticks_per_day

    @property
    def current_season(self) -> Season:
        """当前季节。"""
        season_index = (self.tick // self.ticks_per_season) % self.seasons_per_year
        return Season(season_index)

    @property
    def current_year(self) -> int:
        """当前年份（从 0 开始）。"""
        return self.tick // self.ticks_per_year

    @property
    def farm_multiplier(self) -> float:
        """当前季节的农田产出倍率。"""
        return SEASON_FARM_MULTIPLIER[self.current_season]

    @property
    def forest_multiplier(self) -> float:
        """当前季节的森林产出倍率。"""
        return SEASON_FOREST_MULTIPLIER[self.current_season]

    @property
    def food_consumption_multiplier(self) -> float:
        """当前季节的食物消耗倍率。"""
        return SEASON_FOOD_CONSUMPTION_MULTIPLIER[self.current_season]

    def advance(self) -> None:
        """推进一个 tick。"""
        self.tick += 1

    def is_new_day(self) -> bool:
        """当前 tick 是否是新一天的开始。"""
        return self.tick % self.ticks_per_day == 0

    def is_new_season(self) -> bool:
        """当前 tick 是否是新季度的开始。"""
        return self.tick % self.ticks_per_season == 0

    def is_new_year(self) -> bool:
        """当前 tick 是否是新一年的开始。"""
        return self.tick % self.ticks_per_year == 0

    def is_governor_decision_tick(self) -> bool:
        """当前 tick 是否是镇长决策时刻（每季度开始）。"""
        return self.is_new_season()

    def is_leader_decision_tick(self) -> bool:
        """当前 tick 是否是首领决策时刻（每年开始）。"""
        return self.is_new_year()
