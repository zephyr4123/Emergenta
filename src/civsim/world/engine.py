"""主世界引擎。

Mesa Model 子类，实现每 tick 的核心循环：
环境更新 → Agent 行动 → 贸易结算 → 聚落结算 → 革命检测 → 数据采集。
支持 LLM 异步并行决策调度。
"""

from __future__ import annotations

import asyncio
import logging

import mesa
import numpy as np

from civsim.agents.behaviors.fsm import CivilianState
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
from civsim.world.events import (
    process_active_events,
    trigger_random_events,
)
from civsim.world.tiles import TileType

logger = logging.getLogger(__name__)

# Phase 4 并行模块（延迟导入避免循环依赖）
_PARALLEL_AVAILABLE = True
try:
    from civsim.parallel.coordinator import ParallelCoordinator
except ImportError:
    _PARALLEL_AVAILABLE = False

# 自适应控制器（延迟导入）
try:
    from civsim.world.adaptive import (
        AdaptiveParameterController,
        SystemMetrics,
    )
    _ADAPTIVE_AVAILABLE = True
except ImportError:
    _ADAPTIVE_AVAILABLE = False


class CivilizationEngine(mesa.Model):
    """AI 文明模拟器的核心世界引擎。"""

    def __init__(
        self,
        config: CivSimConfig | None = None,
        config_path: str | None = None,
        enable_db: bool = False,
        seed: int | None = None,
        enable_governors: bool | None = None,
        enable_leaders: bool | None = None,
    ) -> None:
        super().__init__(seed=seed)
        self.config = config or load_config(config_path)
        self._rng = np.random.default_rng(seed)

        # 时间系统
        self.clock = Clock(
            ticks_per_day=self.config.clock.ticks_per_day,
            days_per_season=self.config.clock.days_per_season,
            seasons_per_year=self.config.clock.seasons_per_year,
            season_params=self.config.season_params,
        )

        # 生成地图
        w, h = self.config.world.grid.width, self.config.world.grid.height
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
        self.tile_grid = generate_tile_grid(
            w, h, self.elevation, self.moisture, thresholds,
        )
        self.grid = mesa.space.MultiGrid(w, h, torus=False)

        # 预构建可再生地块索引（跳过 WATER/MOUNTAIN/BARREN/MINE/SETTLEMENT）
        self._regenerable_tiles: list = []
        for x in range(w):
            for y in range(h):
                tt = self.tile_grid[x][y].tile_type
                if tt in (TileType.FARMLAND, TileType.FOREST):
                    self._regenerable_tiles.append(self.tile_grid[x][y])

        # 放置聚落
        s_cfg = self.config.world.settlement
        settlement_list = place_settlements(
            self.tile_grid, self.elevation, w, h,
            count=s_cfg.initial_count, min_score=s_cfg.min_suitability_score,
            suitability_config=self.config.map_suitability,
        )
        self.settlements: dict[int, Settlement] = {
            s.id: s for s in settlement_list
        }
        initial = self.config.resources.initial_stockpile
        for s in self.settlements.values():
            s.stockpile = {
                "food": initial.food, "wood": initial.wood,
                "ore": initial.ore, "gold": initial.gold,
            }

        # 创建平民
        self._spawn_civilians()

        self.llm_gateway: LLMGateway | None = None

        # Phase 2: 镇长
        should_gov = enable_governors
        if should_gov is None:
            should_gov = self.config.agents.governor.initial_count > 0
        if should_gov:
            self._init_llm_gateway()
            self._spawn_governors()

        # Phase 3: 首领 + 贸易 + 外交 + 革命
        self.leaders: list = []
        self.diplomacy = None
        self.trade_manager = None
        self.revolution_tracker = None
        self.emergence_detector = None
        self.mqtt_manager = None

        should_lead = enable_leaders
        if should_lead is None:
            should_lead = self.config.agents.leader.initial_count > 0
        if should_lead:
            self._init_phase3()

        # 数据采集与存储
        self.datacollector = create_datacollector()
        self.db: Database | None = None
        if enable_db:
            self.db = Database(self.config.database.path)
        self._active_events: list[dict] = []

        # Phase 4: 并行协调器
        self._coordinator: ParallelCoordinator | None = None
        self._parallel_threshold = self.config.performance.parallel_threshold
        if _PARALLEL_AVAILABLE and self.config.ray.enabled:
            ray_cfg = self.config.ray
            self._coordinator = ParallelCoordinator(
                num_workers=ray_cfg.num_workers,
                batch_size=ray_cfg.batch_size,
                enable_ray=True,
                object_store_mb=ray_cfg.object_store_memory_mb,
            )

        # 自适应参数控制器
        self.adaptive_controller: AdaptiveParameterController | None = None
        if (
            _ADAPTIVE_AVAILABLE
            and self.config.adaptive_controller.enabled
        ):
            self.adaptive_controller = AdaptiveParameterController(
                config=self.config.adaptive_controller,
            )

    def _spawn_civilians(self) -> None:
        """生成初始平民 Agent 并放置到聚落附近。"""
        n = self.config.agents.civilian.initial_count
        dist = self.config.agents.civilian.personality_distribution
        threshold_cfg = self.config.agents.civilian.revolt_threshold

        personalities = (
            [Personality.COMPLIANT] * int(n * dist.compliant)
            + [Personality.NEUTRAL] * int(n * dist.neutral)
            + [Personality.REBELLIOUS] * int(n * (1 - dist.compliant - dist.neutral))
        )
        while len(personalities) < n:
            personalities.append(Personality.NEUTRAL)
        self._rng.shuffle(personalities)

        professions = (
            [Profession.FARMER] * int(10 * self.config.engine_params.profession_farmer_ratio)
            + [Profession.WOODCUTTER] * int(10 * self.config.engine_params.profession_woodcutter_ratio)
            + [Profession.MINER] * int(10 * self.config.engine_params.profession_miner_ratio)
            + [Profession.MERCHANT] * int(10 * self.config.engine_params.profession_merchant_ratio)
        )
        if not self.settlements:
            return
        sids = list(self.settlements.keys())

        for i in range(n):
            sid = sids[i % len(sids)]
            settlement = self.settlements[sid]
            threshold = float(np.clip(
                self._rng.normal(threshold_cfg.mean, threshold_cfg.std),
                threshold_cfg.min, threshold_cfg.max,
            ))
            agent = Civilian(
                model=self, home_settlement_id=sid,
                personality=personalities[i],
                profession=professions[i % len(professions)],
                revolt_threshold=threshold,
            )
            self.grid.place_agent(agent, settlement.position)
            settlement.population += 1

    def _init_llm_gateway(self) -> None:
        """初始化 LLM 网关并注册模型配置。"""
        self.llm_gateway = LLMGateway(params=self.config.gateway_params)
        for role in self.config.llm.models:
            try:
                cfg = self.config.llm.get_model_config(role)
                self.llm_gateway.register_model(role, cfg)
                logger.info("注册 LLM 模型: %s → %s", role, cfg.model)
            except KeyError:
                logger.warning("角色 '%s' 的 LLM 模型配置缺失", role)

    def _spawn_governors(self) -> None:
        """为每个聚落创建镇长 Agent。"""
        if not self.settlements:
            return
        cache_on = self.config.llm.cache.enabled
        mem = max(5, self.config.agents.governor.decision_context_window // 10)
        for sid, settlement in self.settlements.items():
            gov = Governor(
                model=self, settlement_id=sid,
                gateway=self.llm_gateway,
                memory_limit=mem, cache_enabled=cache_on,
            )
            settlement.governor_id = gov.unique_id
            self.grid.place_agent(gov, settlement.position)
        logger.info("已创建 %d 个镇长 Agent", len(self.settlements))

    def _init_phase3(self) -> None:
        """初始化 Phase 3 系统：外交、贸易、革命、涌现检测、通信。"""
        if self.llm_gateway is None:
            self._init_llm_gateway()

        from civsim.data.analytics import EmergenceDetector
        from civsim.economy.trade import TradeManager
        from civsim.politics.diplomacy import DiplomacyManager
        from civsim.politics.revolution import RevolutionTracker

        self.diplomacy = DiplomacyManager(
            params=self.config.diplomacy_params,
        )
        self.trade_manager = TradeManager(
            params=self.config.trade_params,
        )
        self.revolution_tracker = RevolutionTracker(
            params=self.config.revolution_params,
        )
        self.emergence_detector = EmergenceDetector(
            params=self.config.analytics_params,
        )

        # 尝试连接 MQTT
        try:
            from civsim.communication.mqtt_broker import MQTTManager
            mqtt_cfg = self.config.mqtt
            self.mqtt_manager = MQTTManager(
                host=mqtt_cfg.broker_host, port=mqtt_cfg.broker_port,
            )
            self.mqtt_manager.connect()
        except Exception as e:
            logger.warning("MQTT 初始化失败: %s，使用本地消息", e)

        self._spawn_leaders()

    def _spawn_leaders(self) -> None:
        """创建首领 Agent 并分配聚落到阵营。"""
        from civsim.agents.leader import Leader

        n_leaders = min(
            self.config.agents.leader.initial_count,
            len(self.settlements),
        )
        if n_leaders <= 0:
            return

        sids = list(self.settlements.keys())
        cache_on = self.config.llm.cache.enabled
        mem = max(10, self.config.agents.leader.memory_max_entries // 10)

        for i in range(n_leaders):
            faction_id = i + 1
            # 按轮询分配聚落
            controlled = [
                sids[j] for j in range(len(sids))
                if j % n_leaders == i
            ]
            leader = Leader(
                model=self, faction_id=faction_id,
                controlled_settlements=controlled,
                gateway=self.llm_gateway,
                memory_limit=mem, cache_enabled=cache_on,
            )
            # 设置聚落 faction_id
            for sid in controlled:
                self.settlements[sid].faction_id = faction_id
            # 放置到第一个聚落
            if controlled:
                pos = self.settlements[controlled[0]].position
                self.grid.place_agent(leader, pos)
            self.leaders.append(leader)

        logger.info("已创建 %d 个首领 Agent", n_leaders)

    def get_governors(self) -> list[Governor]:
        """获取所有镇长 Agent。"""
        return [a for a in self.agents if isinstance(a, Governor)]

    def get_leaders(self) -> list:
        """获取所有首领 Agent。"""
        return list(self.leaders)

    def step(self) -> None:
        """执行一个 tick 的核心循环。"""
        self.clock.advance()
        self._environment_update()
        self._agents_act()
        if self.trade_manager:
            self._trade_update()
            self._apply_trade_trust_feedback()
        self._settlement_reconcile()
        if self.revolution_tracker:
            self._check_revolutions()
            self._update_recovery_phases()
        if self.emergence_detector:
            self._detect_emergence()
        self._update_adaptive_controller()
        self.datacollector.collect(self)
        if (
            self.db is not None
            and self.clock.tick % self.config.database.snapshot_interval == 0
        ):
            self._write_snapshot()

    def _agents_act(self) -> None:
        """执行所有 Agent 的行动。

        平民使用并行/串行执行；
        镇长和首领在决策 tick 时使用 asyncio.gather 并行 LLM 调用。
        """
        civilians = [a for a in self.agents if isinstance(a, Civilian)]
        non_civilians = [a for a in self.agents if not isinstance(a, Civilian)]

        use_parallel = (
            self._coordinator is not None
            and len(civilians) >= self._parallel_threshold
        )

        if use_parallel:
            self._parallel_civilian_step(civilians)
        else:
            # 只执行平民的 step
            for agent in civilians:
                agent.step()

        # 镇长/首领决策：尝试异步并行
        if self._should_async_llm_decisions():
            self._async_llm_decisions()
        else:
            for agent in non_civilians:
                agent.step()

    def _should_async_llm_decisions(self) -> bool:
        """判断是否应使用异步并行 LLM 决策。"""
        if self.llm_gateway is None:
            return False
        is_gov_tick = self.clock.is_governor_decision_tick() and self.clock.tick > 0
        is_leader_tick = (
            self.clock.is_leader_decision_tick()
            and self.clock.tick > 0
            and self.leaders
        )
        return is_gov_tick or is_leader_tick

    def _async_llm_decisions(self) -> None:
        """使用 asyncio 批量并行执行 LLM 决策。"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self._batch_decisions(),
                    )
                    future.result()
            else:
                loop.run_until_complete(self._batch_decisions())
        except RuntimeError:
            asyncio.run(self._batch_decisions())

    async def _batch_decisions(self) -> None:
        """批量执行镇长和首领的异步决策。"""
        tasks = []

        if (
            self.clock.is_governor_decision_tick()
            and self.clock.tick > 0
        ):
            governors = self.get_governors()
            for gov in governors:
                tasks.append(gov.decision_cycle_async())

        if (
            self.clock.is_leader_decision_tick()
            and self.clock.tick > 0
            and self.leaders
        ):
            for leader in self.leaders:
                tasks.append(leader.decision_cycle_async())

        if tasks:
            results = await asyncio.gather(
                *tasks, return_exceptions=True,
            )
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(
                        "异步决策 #%d 失败: %s", i, result,
                    )

    def _parallel_civilian_step(self, civilians: list[Civilian]) -> None:
        """使用并行协调器执行平民 step 并应用结果。"""
        from civsim.agents.behaviors.fsm import CivilianState

        results = self._coordinator.execute_parallel_step(self, civilians)

        # 构建 ID → Agent 映射
        agent_map = {c.unique_id: c for c in civilians}

        # Apply: 将结果写回
        for result in results:
            agent = agent_map.get(result.agent_id)
            if agent is None:
                continue

            old_state = agent.state
            agent.state = CivilianState(result.new_state)
            agent.hunger = result.new_hunger
            agent.satisfaction = result.new_satisfaction
            agent.tick_in_current_state = result.tick_in_current_state

            # 应用资源产出到聚落
            if result.resource_deposit:
                settlement = self.settlements.get(agent.home_settlement_id)
                if settlement:
                    settlement.deposit(result.resource_deposit)

            # 应用食物消耗
            if result.food_consumed > 0:
                settlement = self.settlements.get(agent.home_settlement_id)
                if settlement:
                    settlement.withdraw_food(result.food_consumed)

    def _build_civilian_index(self) -> dict[int, list[Civilian]]:
        """构建 settlement_id → civilians 索引。

        一次 O(N) 遍历替代多次 O(S*N) 过滤。

        Returns:
            聚落 ID 到平民列表的映射。
        """
        index: dict[int, list[Civilian]] = {sid: [] for sid in self.settlements}
        for a in self.agents:
            if isinstance(a, Civilian) and a.home_settlement_id in index:
                index[a.home_settlement_id].append(a)
        return index

    def _environment_update(self) -> None:
        """环境更新：资源再生 + 事件处理 + 信任衰减。"""
        regen = self.config.resources.regeneration
        for tile in self._regenerable_tiles:
            tile.regenerate(regen.farmland_per_tick, regen.forest_per_tick)
        self._active_events = process_active_events(
            self._active_events, self.settlements,
            event_params=self.config.event_params,
        )
        event_mult = 1.0
        if self.adaptive_controller is not None:
            event_mult = (
                self.adaptive_controller.coefficients.random_event_multiplier
            )
        trigger_random_events(
            self.settlements, self.tile_grid,
            self._active_events, self._rng,
            event_multiplier=event_mult,
            event_params=self.config.event_params,
        )
        if self.diplomacy:
            self.diplomacy.expire_treaties(self.clock.tick)
            self.diplomacy.decay_trust()
            self.diplomacy.auto_downgrade_relations(self.clock.tick)

    def _trade_update(self) -> None:
        """处理聚落间贸易。"""
        diplo_rels = None
        trust_data = None
        if self.diplomacy:
            diplo_rels = self.diplomacy.get_relations_dict()
            trust_data = self.diplomacy.get_trust_data()
        self.trade_manager.process_tick(
            self.settlements, diplo_rels, trust_data,
        )

    def _check_revolutions(self) -> None:
        """检测并处理革命。"""
        civ_index = self._build_civilian_index()
        for sid, s in self.settlements.items():
            civs = civ_index.get(sid, [])
            if not civs:
                continue
            pr = sum(1 for c in civs if c.state == CivilianState.PROTESTING) / len(civs)
            sat = float(np.mean([c.satisfaction for c in civs]))
            if self.revolution_tracker.update(sid, pr, sat):
                ev = self.revolution_tracker.trigger_revolution(
                    sid, self.clock.tick,
                    old_faction_id=s.faction_id,
                    old_governor_id=s.governor_id,
                )
                self.revolution_tracker.apply_revolution(ev, s)

    def _detect_emergence(self) -> None:
        """运行涌现行为检测器。"""
        rev = self.revolution_tracker.events if self.revolution_tracker else []
        self.emergence_detector.detect_all(
            tick=self.clock.tick, revolution_events=rev,
            diplomacy_manager=self.diplomacy, trade_manager=self.trade_manager,
        )

    def _settlement_reconcile(self) -> None:
        """聚落结算：饥荒减员、人口增长。"""
        from civsim.world.clock import Season
        ep = self.config.engine_params
        sp = self.config.season_params
        for s in self.settlements.values():
            if s.scarcity_index > ep.starvation_scarcity_threshold and s.population > 0:
                death_rate = (
                    (s.scarcity_index - ep.starvation_scarcity_threshold)
                    * ep.starvation_rate_factor
                )
                deaths = max(1, int(s.population * death_rate))
                s.population = max(0, s.population - deaths)
            growth_rate = ep.natural_growth_rate
            if self.clock.current_season == Season.SPRING:
                growth_rate *= sp.spring_growth_bonus
            s.natural_growth(growth_rate)

    def _apply_trade_trust_feedback(self) -> None:
        """将贸易产生的信任增量应用到外交系统。"""
        if self.diplomacy is None or self.trade_manager is None:
            return
        deltas = self.trade_manager.compute_trust_deltas()
        for (fid_a, fid_b), delta in deltas.items():
            self.diplomacy.adjust_trust(fid_a, fid_b, delta)

    def _update_recovery_phases(self) -> None:
        """更新革命后恢复阶段。"""
        if self.revolution_tracker is None:
            return
        self.revolution_tracker.update_recovery()

    def _update_adaptive_controller(self) -> None:
        """更新自适应参数控制器。"""
        if self.adaptive_controller is None:
            return
        if not self.adaptive_controller.should_update(self.clock.tick):
            return

        metrics = self._compute_system_metrics()
        self.adaptive_controller.update(metrics)

    def _compute_system_metrics(self) -> SystemMetrics:
        """计算系统状态指标供自适应控制器使用。

        Returns:
            系统状态快照。
        """
        civilians = [
            a for a in self.agents if isinstance(a, Civilian)
        ]

        protest_count = sum(
            1 for c in civilians
            if c.state == CivilianState.PROTESTING
        )
        total_civ = max(1, len(civilians))
        global_pr = protest_count / total_civ
        avg_sat = float(
            np.mean([c.satisfaction for c in civilians])
        ) if civilians else 0.5

        rev_count = 0
        rev_recent = 0
        if self.revolution_tracker:
            rev_count = self.revolution_tracker.revolution_count
            lookback = self.config.adaptive_controller.lookback_ticks
            rev_recent = self.revolution_tracker.recent_revolution_count(
                self.clock.tick, lookback,
            )

        active_wars = 0
        if self.diplomacy:
            active_wars = self.diplomacy.count_wars()

        collapsed = sum(
            1 for s in self.settlements.values() if s.population <= 0
        )
        total_pop = sum(s.population for s in self.settlements.values())

        trade_vol = 0.0
        if self.trade_manager:
            trade_vol = self.trade_manager.total_volume

        return SystemMetrics(
            tick=self.clock.tick,
            global_protest_ratio=global_pr,
            avg_satisfaction=avg_sat,
            revolution_count=rev_count,
            revolutions_recent=rev_recent,
            active_wars=active_wars,
            collapsed_settlements=collapsed,
            total_settlements=len(self.settlements),
            total_population=total_pop,
            trade_volume_recent=trade_vol,
        )

    def _write_snapshot(self) -> None:
        """将当前状态写入数据库。"""
        if self.db is None:
            return
        pr, avg_sat = protest_ratio(self), avg_satisfaction(self)
        for sid, s in self.settlements.items():
            self.db.write_world_state(
                tick=self.clock.tick, settlement_id=sid, population=s.population,
                food=s.stockpile.get("food", 0), wood=s.stockpile.get("wood", 0),
                ore=s.stockpile.get("ore", 0), gold=s.stockpile.get("gold", 0),
                tax_rate=s.tax_rate, security_level=s.security_level,
                satisfaction_avg=avg_sat, protest_ratio=pr,
            )
