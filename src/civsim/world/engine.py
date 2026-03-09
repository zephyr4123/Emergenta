"""主世界引擎。

Mesa Model 子类，实现每 tick 的核心循环：
环境更新 → Agent 行动 → 聚落结算 → 数据采集。
"""

from __future__ import annotations

import logging

import mesa
import numpy as np

from civsim.agents.behaviors.markov import Personality
from civsim.agents.civilian import Civilian, Profession
from civsim.agents.governor import Governor
from civsim.config import CivSimConfig, load_config
from civsim.data.collector import (
    avg_satisfaction,
    create_datacollector,
    protest_ratio,
)
from civsim.data.database import Database
from civsim.economy.settlement import Settlement
from civsim.llm.gateway import LLMGateway
from civsim.world.clock import Clock
from civsim.world.map_generator import (
    generate_elevation_moisture,
    generate_tile_grid,
    place_settlements,
)
from civsim.world.tiles import TileType

logger = logging.getLogger(__name__)

# 随机事件定义
RANDOM_EVENTS = [
    {"name": "旱灾", "prob": 0.002, "scope": "settlement"},
    {"name": "瘟疫", "prob": 0.001, "scope": "settlement"},
    {"name": "矿脉发现", "prob": 0.003, "scope": "tile"},
    {"name": "丰收", "prob": 0.005, "scope": "settlement"},
    {"name": "流寇", "prob": 0.002, "scope": "settlement"},
]


class CivilizationEngine(mesa.Model):
    """AI 文明模拟器的核心世界引擎。

    Attributes:
        config: 全局配置。
        clock: 时间系统。
        tile_grid: 地块网格。
        settlements: 聚落字典 {id: Settlement}。
        db: 数据库实例（可选）。
    """

    def __init__(
        self,
        config: CivSimConfig | None = None,
        config_path: str | None = None,
        enable_db: bool = False,
        seed: int | None = None,
        enable_governors: bool | None = None,
    ) -> None:
        super().__init__(seed=seed)
        self.config = config or load_config(config_path)
        self._rng = np.random.default_rng(seed)

        # 初始化时间系统
        self.clock = Clock(
            ticks_per_day=self.config.clock.ticks_per_day,
            days_per_season=self.config.clock.days_per_season,
            seasons_per_year=self.config.clock.seasons_per_year,
        )

        # 生成地图
        w = self.config.world.grid.width
        h = self.config.world.grid.height
        map_cfg = self.config.world.map_generation

        self.elevation, self.moisture = generate_elevation_moisture(
            width=w, height=h,
            elevation_scale=map_cfg.elevation_scale,
            moisture_scale=map_cfg.moisture_scale,
            octaves=map_cfg.octaves,
            persistence=map_cfg.persistence,
            seed=map_cfg.seed or (seed if seed else None),
        )

        thresholds = self.config.world.tile_thresholds.model_dump()
        self.tile_grid = generate_tile_grid(w, h, self.elevation, self.moisture, thresholds)

        # 创建 Mesa Grid
        self.grid = mesa.space.MultiGrid(w, h, torus=False)

        # 放置聚落
        settlement_cfg = self.config.world.settlement
        settlement_list = place_settlements(
            self.tile_grid, self.elevation, w, h,
            count=settlement_cfg.initial_count,
            min_score=settlement_cfg.min_suitability_score,
        )
        self.settlements: dict[int, Settlement] = {s.id: s for s in settlement_list}

        # 初始化聚落资源
        initial = self.config.resources.initial_stockpile
        for s in self.settlements.values():
            s.stockpile = {
                "food": initial.food,
                "wood": initial.wood,
                "ore": initial.ore,
                "gold": initial.gold,
            }

        # 创建平民 Agent
        self._spawn_civilians()

        # LLM 网关（Phase 2+）
        self.llm_gateway: LLMGateway | None = None

        # 创建镇长 Agent（Phase 2+）
        should_enable = enable_governors
        if should_enable is None:
            should_enable = self.config.agents.governor.initial_count > 0
        if should_enable:
            self._init_llm_gateway()
            self._spawn_governors()

        # 数据采集器
        self.datacollector = create_datacollector()

        # 数据库（可选）
        self.db: Database | None = None
        if enable_db:
            self.db = Database(self.config.database.path)

        # 活跃事件追踪
        self._active_events: list[dict] = []

    def _spawn_civilians(self) -> None:
        """生成初始平民 Agent 并放置到聚落附近。"""
        n = self.config.agents.civilian.initial_count
        dist = self.config.agents.civilian.personality_distribution
        threshold_cfg = self.config.agents.civilian.revolt_threshold

        # 性格分布采样
        personalities = (
            [Personality.COMPLIANT] * int(n * dist.compliant)
            + [Personality.NEUTRAL] * int(n * dist.neutral)
            + [Personality.REBELLIOUS] * int(n * (1 - dist.compliant - dist.neutral))
        )
        # 补齐到 n
        while len(personalities) < n:
            personalities.append(Personality.NEUTRAL)
        self._rng.shuffle(personalities)

        # 职业分布（农民占 40%，其余各 20%）
        professions_weighted = (
            [Profession.FARMER] * 4
            + [Profession.WOODCUTTER] * 2
            + [Profession.MINER] * 2
            + [Profession.MERCHANT] * 2
        )

        if not self.settlements:
            return

        settlement_ids = list(self.settlements.keys())

        for i in range(n):
            sid = settlement_ids[i % len(settlement_ids)]
            settlement = self.settlements[sid]

            # Granovetter 阈值正态采样
            threshold = float(np.clip(
                self._rng.normal(threshold_cfg.mean, threshold_cfg.std),
                threshold_cfg.min,
                threshold_cfg.max,
            ))

            agent = Civilian(
                model=self,
                home_settlement_id=sid,
                personality=personalities[i],
                profession=professions_weighted[i % len(professions_weighted)],
                revolt_threshold=threshold,
            )

            # 放置到聚落附近
            pos = settlement.position
            self.grid.place_agent(agent, pos)

            # 更新聚落人口
            settlement.population += 1

    def _init_llm_gateway(self) -> None:
        """初始化 LLM 网关并注册模型配置。"""
        self.llm_gateway = LLMGateway(max_retries=2, timeout=30)
        llm_cfg = self.config.llm

        # 注册所有配置的角色模型
        for role in llm_cfg.models:
            try:
                model_config = llm_cfg.get_model_config(role)
                self.llm_gateway.register_model(role, model_config)
                logger.info("注册 LLM 模型: %s → %s", role, model_config.model)
            except KeyError:
                logger.warning("角色 '%s' 的 LLM 模型配置缺失", role)

    def _spawn_governors(self) -> None:
        """为每个聚落创建镇长 Agent。"""
        if not self.settlements:
            return

        cache_enabled = self.config.llm.cache.enabled
        memory_limit = self.config.agents.governor.decision_context_window // 10

        for sid, settlement in self.settlements.items():
            governor = Governor(
                model=self,
                settlement_id=sid,
                gateway=self.llm_gateway,
                memory_limit=max(5, memory_limit),
                cache_enabled=cache_enabled,
            )
            settlement.governor_id = governor.unique_id

            # 放置到聚落中心
            self.grid.place_agent(governor, settlement.position)

        logger.info("已创建 %d 个镇长 Agent", len(self.settlements))

    def get_governors(self) -> list[Governor]:
        """获取所有镇长 Agent。

        Returns:
            镇长 Agent 列表。
        """
        return [a for a in self.agents if isinstance(a, Governor)]

    def step(self) -> None:
        """执行一个 tick 的核心循环。"""
        # 1. 时间推进
        self.clock.advance()

        # 2. 环境更新
        self._environment_update()

        # 3. Agent 行动
        self.agents.shuffle_do("step")

        # 4. 聚落结算
        self._settlement_reconcile()

        # 5. 数据采集
        self.datacollector.collect(self)

        # 6. 数据库快照
        if (
            self.db is not None
            and self.clock.tick % self.config.database.snapshot_interval == 0
        ):
            self._write_snapshot()

    def _environment_update(self) -> None:
        """环境更新：资源再生 + 随机事件处理。"""
        regen = self.config.resources.regeneration
        w = self.config.world.grid.width
        h = self.config.world.grid.height

        # 资源再生
        for x in range(w):
            for y in range(h):
                self.tile_grid[x][y].regenerate(
                    regen.farmland_per_tick, regen.forest_per_tick
                )

        # 处理活跃事件
        self._process_active_events()

        # 触发新随机事件
        self._trigger_random_events()

    def _trigger_random_events(self) -> None:
        """按概率触发随机事件。"""
        if not self.settlements:
            return

        for event_def in RANDOM_EVENTS:
            if self._rng.random() < event_def["prob"]:
                sid = self._rng.choice(list(self.settlements.keys()))
                settlement = self.settlements[sid]
                self._apply_event(event_def["name"], settlement)

    def _apply_event(self, event_name: str, settlement: Settlement) -> None:
        """应用随机事件效果。"""
        if event_name == "旱灾":
            for tx, ty in settlement.territory_tiles:
                tile = self.tile_grid[tx][ty]
                if tile.tile_type == TileType.FARMLAND:
                    tile.fertility *= 0.3
            self._active_events.append({
                "name": "旱灾", "settlement_id": settlement.id,
                "remaining_ticks": 30,
            })
        elif event_name == "瘟疫":
            deaths = max(1, int(settlement.population * 0.10))
            settlement.population = max(0, settlement.population - deaths)
        elif event_name == "丰收":
            self._active_events.append({
                "name": "丰收", "settlement_id": settlement.id,
                "remaining_ticks": 15,
            })
        elif event_name == "流寇":
            settlement.stockpile["gold"] *= 0.7
            settlement.security_level = max(0.0, settlement.security_level - 0.2)

    def _process_active_events(self) -> None:
        """处理持续中的事件。"""
        remaining = []
        for event in self._active_events:
            event["remaining_ticks"] -= 1
            if event["remaining_ticks"] > 0:
                if event["name"] == "丰收":
                    sid = event["settlement_id"]
                    settlement = self.settlements.get(sid)
                    if settlement:
                        settlement.deposit({"food": 5.0})
                remaining.append(event)
        self._active_events = remaining

    def _settlement_reconcile(self) -> None:
        """聚落结算：饥荒减员、人口增长。

        注意：食物消耗已在 Civilian._update_needs() 中按个体扣除，
        此处仅处理饥荒导致的人口死亡和自然增长。
        """
        from civsim.world.clock import Season

        for settlement in self.settlements.values():
            # 饥荒减员：scarcity_index 高时人口减少
            if settlement.scarcity_index > 0.7 and settlement.population > 0:
                death_rate = (settlement.scarcity_index - 0.7) * 0.1
                deaths = max(1, int(settlement.population * death_rate))
                settlement.population = max(0, settlement.population - deaths)

            # 自然增长（春季加成）
            growth_rate = 0.002
            if self.clock.current_season == Season.SPRING:
                growth_rate *= 1.5
            settlement.natural_growth(growth_rate)

    def _write_snapshot(self) -> None:
        """将当前状态写入数据库。"""
        if self.db is None:
            return
        pr = protest_ratio(self)
        avg_sat = avg_satisfaction(self)
        for sid, s in self.settlements.items():
            self.db.write_world_state(
                tick=self.clock.tick,
                settlement_id=sid,
                population=s.population,
                food=s.stockpile.get("food", 0),
                wood=s.stockpile.get("wood", 0),
                ore=s.stockpile.get("ore", 0),
                gold=s.stockpile.get("gold", 0),
                tax_rate=s.tax_rate,
                security_level=s.security_level,
                satisfaction_avg=avg_sat,
                protest_ratio=pr,
            )
