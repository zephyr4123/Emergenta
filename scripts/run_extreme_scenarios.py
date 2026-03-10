"""极端场景压力测试。

设计 5 个极端场景，压测贸易/革命/战争/饥荒/级联效应。
结果输出到 data/exports/extreme_scenarios_report.md
"""

import sys
import time
from dataclasses import dataclass, field
from io import StringIO

from civsim.agents.behaviors.fsm import CivilianState
from civsim.config import load_config
from civsim.politics.diplomacy import DiplomaticStatus
from civsim.world.engine import CivilizationEngine


@dataclass
class ScenarioResult:
    """单个场景的运行结果。"""

    name: str
    description: str
    ticks: int
    duration_sec: float = 0.0
    logs: list[str] = field(default_factory=list)
    success: bool = False
    error: str = ""


def log(result: ScenarioResult, msg: str) -> None:
    """记录日志到结果和标准输出。"""
    result.logs.append(msg)
    print(msg)
    sys.stdout.flush()


def snapshot(engine: CivilizationEngine, tick: int) -> dict:
    """获取当前仿真快照。"""
    state_counts: dict[str, int] = {}
    sats: list[float] = []
    for agent in engine.agents:
        if type(agent).__name__ == "Civilian":
            st = agent.state.value if hasattr(agent.state, "value") else str(agent.state)
            state_counts[st] = state_counts.get(st, 0) + 1
            sats.append(agent.satisfaction)

    total_pop = sum(s.population for s in engine.settlements.values())
    total_food = sum(s.stockpile.get("food", 0) for s in engine.settlements.values())
    total_gold = sum(s.stockpile.get("gold", 0) for s in engine.settlements.values())
    avg_sat = sum(sats) / max(len(sats), 1)

    trade_vol = engine.trade_manager.total_volume if engine.trade_manager else 0
    rev_count = engine.revolution_tracker.revolution_count if engine.revolution_tracker else 0
    alliance_cnt = war_cnt = 0
    if engine.diplomacy:
        for status in getattr(engine.diplomacy, "_relations", {}).values():
            sv = int(status)
            if sv >= 4:
                alliance_cnt += 1
            elif sv == 0:
                war_cnt += 1

    return {
        "tick": tick,
        "population": total_pop,
        "food": total_food,
        "gold": total_gold,
        "avg_satisfaction": avg_sat,
        "states": state_counts,
        "trade_volume": trade_vol,
        "revolution_count": rev_count,
        "alliance_count": alliance_cnt,
        "war_count": war_cnt,
    }


# ============================================================
# 场景 1: 饥荒危机 - 食物耗尽引发抗议和革命
# ============================================================
def scenario_famine_crisis() -> ScenarioResult:
    """极低食物 + 高税率 → 饥荒 → 大规模抗议 → 革命。"""
    result = ScenarioResult(
        name="饥荒危机",
        description="极低初始食物(50) + 高税率(0.5) + 低治安(0.2)，"
        "200平民在高压下挣扎。目标：触发大规模抗议和革命。",
        ticks=300,
    )

    try:
        config = load_config()
        config.world.grid.width = 40
        config.world.grid.height = 40
        config.agents.civilian.initial_count = 200
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 2
        config.world.settlement.initial_count = 4
        config.world.settlement.min_suitability_score = 0.2

        engine = CivilizationEngine(
            config=config, seed=42,
            enable_governors=True, enable_leaders=True,
        )

        # 制造饥荒：极低食物 + 高税 + 低治安 + 禁止农田产出
        for s in engine.settlements.values():
            s.stockpile["food"] = 50.0
            s.stockpile["gold"] = 20.0
            s.tax_rate = 0.6  # 提高税率到 0.6
            s.security_level = 0.15  # 降低治安到 0.15

            # 破坏所有农田，模拟极端旱灾
            for x in range(len(engine.tile_grid)):
                for y in range(len(engine.tile_grid[x])):
                    tile = engine.tile_grid[x][y]
                    if tile.owner_settlement_id == s.id:
                        if tile.tile_type.value == "farmland":
                            tile.fertility = 0.0  # 农田完全枯竭

        log(result, f"聚落数: {len(engine.settlements)}, 首领数: {len(engine.leaders)}")

        t0 = time.time()
        max_protest = 0.0
        min_sat = 1.0
        for tick in range(1, result.ticks + 1):
            engine.step()
            if tick % 30 == 0 or tick <= 5:
                snap = snapshot(engine, tick)
                # CivilianState.PROTESTING = 5 (IntEnum)
                protest_n = snap["states"].get(5, 0)
                total_civs = sum(v for v in snap["states"].values())
                pr = protest_n / max(total_civs, 1)
                max_protest = max(max_protest, pr)
                min_sat = min(min_sat, snap["avg_satisfaction"])
                log(result, f"  [Tick {tick:3d}] 人口={snap['population']} "
                    f"食物={snap['food']:.0f} 满意度={snap['avg_satisfaction']:.3f} "
                    f"抗议率={pr:.3f} 革命={snap['revolution_count']} "
                    f"状态={snap['states']}")

        result.duration_sec = time.time() - t0
        final = snapshot(engine, result.ticks)
        log(result, f"\n  最终: 人口={final['population']} 食物={final['food']:.0f} "
            f"革命次数={final['revolution_count']}")
        log(result, f"  峰值抗议率={max_protest:.3f} 最低满意度={min_sat:.3f}")

        emergence = engine.emergence_detector.events if engine.emergence_detector else []
        if emergence:
            log(result, f"  涌现事件({len(emergence)}个):")
            for e in emergence:
                log(result, f"    [{e.tick}] {e.event_type}: {e.description}")

        result.success = True
    except Exception as e:
        result.error = str(e)
        log(result, f"  错误: {e}")

    return result


# ============================================================
# 场景 2: 资源极度不均 - 贫富分化触发贸易
# ============================================================
def scenario_resource_imbalance() -> ScenarioResult:
    """一半聚落极富、一半极穷 → 强制贸易需求。"""
    result = ScenarioResult(
        name="资源极度不均",
        description="3个聚落食物2000+，3个聚落食物仅10。"
        "强制创造贸易的供需条件。目标：触发聚落间贸易。",
        ticks=200,
    )

    try:
        config = load_config()
        config.world.grid.width = 50
        config.world.grid.height = 50
        config.agents.civilian.initial_count = 120
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 2
        config.world.settlement.initial_count = 6
        config.world.settlement.min_suitability_score = 0.2

        engine = CivilizationEngine(
            config=config, seed=123,
            enable_governors=True, enable_leaders=True,
        )

        sids = list(engine.settlements.keys())
        log(result, f"聚落数: {len(sids)}, 首领数: {len(engine.leaders)}")

        # 极端分化: 前半富裕，后半贫穷
        for i, sid in enumerate(sids):
            s = engine.settlements[sid]
            if i < len(sids) // 2:
                s.stockpile["food"] = 3000.0
                s.stockpile["gold"] = 500.0
                s.population = 20  # 少人口 → 高人均
            else:
                s.stockpile["food"] = 10.0
                s.stockpile["gold"] = 200.0
                s.population = 40  # 多人口 → 低人均
            log(result, f"  聚落{sid}({s.name}): 人口={s.population} "
                f"食物={s.stockpile['food']:.0f} 金={s.stockpile['gold']:.0f} "
                f"阵营={s.faction_id}")

        # 确保外交至少是中立（允许贸易）
        if engine.diplomacy:
            factions = set(s.faction_id for s in engine.settlements.values() if s.faction_id)
            for f1 in factions:
                for f2 in factions:
                    if f1 < f2:
                        engine.diplomacy.set_relation(
                            f1, f2, DiplomaticStatus.NEUTRAL, 0
                        )

        t0 = time.time()
        for tick in range(1, result.ticks + 1):
            engine.step()
            if tick % 20 == 0 or tick <= 3:
                snap = snapshot(engine, tick)
                log(result, f"  [Tick {tick:3d}] 人口={snap['population']} "
                    f"食物={snap['food']:.0f} 贸易量={snap['trade_volume']:.0f} "
                    f"联盟={snap['alliance_count']} 战争={snap['war_count']}")

        result.duration_sec = time.time() - t0
        final = snapshot(engine, result.ticks)
        log(result, f"\n  最终贸易量: {final['trade_volume']:.0f}")

        # 各聚落最终状态
        for sid, s in engine.settlements.items():
            log(result, f"  聚落{sid}: 食物={s.stockpile['food']:.0f} "
                f"金={s.stockpile['gold']:.0f} 人口={s.population}")

        result.success = True
    except Exception as e:
        result.error = str(e)
        log(result, f"  错误: {e}")

    return result


# ============================================================
# 场景 3: 高压统治 - 极高税率 + 极高治安
# ============================================================
def scenario_tyranny() -> ScenarioResult:
    """极高税率(0.8) + 极高治安(0.9)，观察是否能压制抗议。"""
    result = ScenarioResult(
        name="高压统治",
        description="税率0.8 + 治安0.9，200平民在高压下。"
        "目标：观察治安能否压制不满，以及抗议是否仍会爆发。",
        ticks=400,
    )

    try:
        config = load_config()
        config.world.grid.width = 40
        config.world.grid.height = 40
        config.agents.civilian.initial_count = 200
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 2
        config.world.settlement.initial_count = 4
        config.world.settlement.min_suitability_score = 0.2

        engine = CivilizationEngine(
            config=config, seed=77,
            enable_governors=True, enable_leaders=True,
        )

        for s in engine.settlements.values():
            s.tax_rate = 0.8
            s.security_level = 0.9
            s.stockpile["food"] = 300.0  # 中等食物

        log(result, f"聚落数: {len(engine.settlements)}")

        t0 = time.time()
        max_protest = 0.0
        for tick in range(1, result.ticks + 1):
            engine.step()
            if tick % 40 == 0:
                snap = snapshot(engine, tick)
                # CivilianState.PROTESTING = 5 (IntEnum)
                protest_n = snap["states"].get(5, 0)
                total_civs = sum(v for v in snap["states"].values())
                pr = protest_n / max(total_civs, 1)
                max_protest = max(max_protest, pr)
                log(result, f"  [Tick {tick:3d}] 人口={snap['population']} "
                    f"食物={snap['food']:.0f} 满意度={snap['avg_satisfaction']:.3f} "
                    f"抗议率={pr:.3f} 革命={snap['revolution_count']} "
                    f"状态={snap['states']}")

        result.duration_sec = time.time() - t0
        final = snapshot(engine, result.ticks)
        log(result, f"\n  峰值抗议率: {max_protest:.3f}")
        log(result, f"  最终革命次数: {final['revolution_count']}")
        log(result, f"  最终满意度: {final['avg_satisfaction']:.3f}")

        for sid, s in engine.settlements.items():
            log(result, f"  聚落{sid}: 税={s.tax_rate:.2f} "
                f"治安={s.security_level:.2f} 食物={s.stockpile['food']:.0f}")

        result.success = True
    except Exception as e:
        result.error = str(e)
        log(result, f"  错误: {e}")

    return result


# ============================================================
# 场景 4: 强制战争 - 手动设置战争状态观察连锁反应
# ============================================================
def scenario_forced_war() -> ScenarioResult:
    """直接设置两个阵营为战争状态，观察贸易封锁和后续影响。"""
    result = ScenarioResult(
        name="强制战争",
        description="在 tick 10 手动宣战，观察贸易封锁、聚落衰退、"
        "首领决策应对。运行到首领年度决策后看是否求和。",
        ticks=600,
    )

    try:
        config = load_config()
        config.world.grid.width = 50
        config.world.grid.height = 50
        config.agents.civilian.initial_count = 150
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 2
        config.world.settlement.initial_count = 6
        config.world.settlement.min_suitability_score = 0.2

        engine = CivilizationEngine(
            config=config, seed=99,
            enable_governors=True, enable_leaders=True,
        )

        # 制造贸易条件
        sids = list(engine.settlements.keys())
        for i, sid in enumerate(sids):
            s = engine.settlements[sid]
            if i % 2 == 0:
                s.stockpile["food"] = 2000.0
                s.population = 15
            else:
                s.stockpile["food"] = 20.0
                s.population = 35

        factions = sorted(set(
            s.faction_id for s in engine.settlements.values() if s.faction_id
        ))
        log(result, f"聚落数: {len(sids)}, 阵营: {factions}")

        t0 = time.time()
        war_declared = False
        pre_war_trade = 0.0
        for tick in range(1, result.ticks + 1):
            engine.step()

            # tick 10 时记录战前贸易量，然后宣战
            if tick == 10 and not war_declared and len(factions) >= 2:
                pre_war_trade = engine.trade_manager.total_volume if engine.trade_manager else 0
                engine.diplomacy.set_relation(
                    factions[0], factions[1], DiplomaticStatus.WAR, tick
                )
                war_declared = True
                log(result, f"  [Tick {tick}] *** 宣战! 阵营{factions[0]} vs {factions[1]} ***")
                log(result, f"  战前贸易量: {pre_war_trade:.0f}")

            if tick % 50 == 0 or tick in [1, 5, 10, 11, 15, 20]:
                snap = snapshot(engine, tick)
                log(result, f"  [Tick {tick:3d}] 食物={snap['food']:.0f} "
                    f"贸易量={snap['trade_volume']:.0f} "
                    f"联盟={snap['alliance_count']} 战争={snap['war_count']} "
                    f"革命={snap['revolution_count']}")

        result.duration_sec = time.time() - t0
        final = snapshot(engine, result.ticks)

        # 检查战争是否结束
        if engine.diplomacy and len(factions) >= 2:
            final_status = engine.diplomacy.get_relation(factions[0], factions[1])
            log(result, f"\n  最终外交状态: {final_status.name}")
        log(result, f"  最终贸易量: {final['trade_volume']:.0f}")
        log(result, f"  最终革命次数: {final['revolution_count']}")

        for leader in engine.leaders:
            log(result, f"  首领{leader.unique_id}: 决策={getattr(leader, 'decision_count', 0)}")

        emergence = engine.emergence_detector.events if engine.emergence_detector else []
        if emergence:
            log(result, f"  涌现事件({len(emergence)}个):")
            for e in emergence:
                log(result, f"    [{e.tick}] {e.event_type}: {e.description}")

        result.success = True
    except Exception as e:
        result.error = str(e)
        log(result, f"  错误: {e}")

    return result


# ============================================================
# 场景 5: 末日生存 - 全面资源枯竭
# ============================================================
def scenario_apocalypse() -> ScenarioResult:
    """所有资源接近 0，人口密度极高，观察系统崩溃过程。"""
    result = ScenarioResult(
        name="末日生存",
        description="所有聚落: 食物=5, 木材=0, 矿石=0, 金=5。"
        "300平民挤在4个聚落中。观察饥荒死亡、抗议、革命级联。",
        ticks=200,
    )

    try:
        config = load_config()
        config.world.grid.width = 30
        config.world.grid.height = 30
        config.agents.civilian.initial_count = 300
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 2
        config.world.settlement.initial_count = 4
        config.world.settlement.min_suitability_score = 0.1

        engine = CivilizationEngine(
            config=config, seed=666,
            enable_governors=True, enable_leaders=True,
        )

        # 极端资源匮乏
        for s in engine.settlements.values():
            s.stockpile["food"] = 5.0
            s.stockpile["wood"] = 0.0
            s.stockpile["ore"] = 0.0
            s.stockpile["gold"] = 5.0
            s.tax_rate = 0.3
            s.security_level = 0.3

        initial_pop = sum(s.population for s in engine.settlements.values())
        log(result, f"聚落数: {len(engine.settlements)}, 初始人口: {initial_pop}")

        t0 = time.time()
        for tick in range(1, result.ticks + 1):
            engine.step()
            if tick % 10 == 0 or tick <= 5:
                snap = snapshot(engine, tick)
                protest_n = snap["states"].get("抗议", 0) + snap["states"].get("5", 0)
                fight_n = snap["states"].get("战斗", 0) + snap["states"].get("6", 0)
                total_civs = sum(v for v in snap["states"].values())
                log(result, f"  [Tick {tick:3d}] 人口={snap['population']} "
                    f"食物={snap['food']:.0f} 满意度={snap['avg_satisfaction']:.3f} "
                    f"抗议={protest_n}/{total_civs} 战斗={fight_n} "
                    f"革命={snap['revolution_count']}")

        result.duration_sec = time.time() - t0
        final = snapshot(engine, result.ticks)
        final_pop = final["population"]
        log(result, f"\n  人口变化: {initial_pop} → {final_pop} "
            f"(损失 {initial_pop - final_pop})")
        log(result, f"  最终革命次数: {final['revolution_count']}")
        log(result, f"  最终食物: {final['food']:.0f}")

        for sid, s in engine.settlements.items():
            log(result, f"  聚落{sid}: 人口={s.population} "
                f"食物={s.stockpile['food']:.0f} "
                f"税={s.tax_rate:.2f} 治安={s.security_level:.2f}")

        emergence = engine.emergence_detector.events if engine.emergence_detector else []
        if emergence:
            log(result, f"  涌现事件({len(emergence)}个):")
            for e in emergence:
                log(result, f"    [{e.tick}] {e.event_type}: {e.description}")

        result.success = True
    except Exception as e:
        result.error = str(e)
        log(result, f"  错误: {e}")

    return result


# ============================================================
# 场景 6: 资源诅咒 (荷兰病)
# ============================================================
def scenario_resource_curse() -> ScenarioResult:
    """1个聚落拥有海量金币但粮食产出为0，其他聚落有粮食但缺钱。
    观察首富聚落会不会被恶意抬价或贸易禁运饿死。"""
    result = ScenarioResult(
        name="资源诅咒 (荷兰病)",
        description="1个聚落拥有极其海量的金币（首富），但粮食产出完全为0。"
        "其他聚落有粮食但缺钱。观察首富聚落会不会因为被其他聚落"
        "\"恶意抬高粮价\"或者\"联合贸易禁运\"而活活饿死？财富是否会带来毁灭？",
        ticks=300,
    )

    try:
        config = load_config()
        config.world.grid.width = 50
        config.world.grid.height = 50
        config.agents.civilian.initial_count = 300
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 2
        config.world.settlement.initial_count = 5
        config.world.settlement.min_suitability_score = 0.2

        engine = CivilizationEngine(
            config=config, seed=88,
            enable_governors=True, enable_leaders=True,
        )

        # 找到第一个聚落作为"首富"
        settlements = list(engine.settlements.values())
        if len(settlements) < 2:
            raise ValueError("需要至少2个聚落")

        rich_settlement = settlements[0]
        poor_settlements = settlements[1:]

        # 首富：海量金币，但粮食为0，且禁止农田产出
        rich_settlement.stockpile["gold"] = 50000.0
        rich_settlement.stockpile["food"] = 0.0
        rich_settlement.tax_rate = 0.1
        rich_settlement.security_level = 0.8

        # 标记首富聚落的农田为不可用（模拟荷兰病：资源诅咒导致农业衰退）
        for x in range(len(engine.tile_grid)):
            for y in range(len(engine.tile_grid[x])):
                tile = engine.tile_grid[x][y]
                if tile.owner_settlement_id == rich_settlement.id:
                    if tile.tile_type.value == "farmland":
                        tile.fertility = 0.0  # 农田完全退化

        # 其他聚落：有粮食但缺钱
        for s in poor_settlements:
            s.stockpile["food"] = 800.0
            s.stockpile["gold"] = 50.0
            s.tax_rate = 0.2
            s.security_level = 0.5

        log(result, f"聚落数: {len(engine.settlements)}, 首领数: {len(engine.leaders)}")
        log(result, f"首富聚落{rich_settlement.id}({rich_settlement.name}): "
            f"金={rich_settlement.stockpile['gold']:.0f} 食物={rich_settlement.stockpile['food']:.0f}")
        for s in poor_settlements:
            log(result, f"  聚落{s.id}({s.name}): "
                f"金={s.stockpile['gold']:.0f} 食物={s.stockpile['food']:.0f}")

        t0 = time.time()
        rich_pop_history = []
        rich_food_history = []
        trade_price_history = []

        for tick in range(1, result.ticks + 1):
            engine.step()

            # 记录首富聚落状态
            rich_pop = rich_settlement.population
            rich_food = rich_settlement.stockpile.get("food", 0)
            rich_pop_history.append(rich_pop)
            rich_food_history.append(rich_food)

            # 尝试获取食物价格（如果贸易系统有记录）
            if hasattr(engine.trade_manager, "last_food_price"):
                trade_price_history.append(engine.trade_manager.last_food_price)

            if tick % 30 == 0 or tick <= 5:
                snap = snapshot(engine, tick)
                log(result, f"  [Tick {tick:3d}] 首富人口={rich_pop} 首富食物={rich_food:.0f} "
                    f"总贸易量={snap['trade_volume']:.0f} 革命={snap['revolution_count']}")

        result.duration_sec = time.time() - t0
        final = snapshot(engine, result.ticks)

        # 分析结果
        rich_survived = rich_settlement.population > 0
        pop_loss = rich_pop_history[0] - rich_pop_history[-1]
        min_food = min(rich_food_history)
        max_trade = max([snap["trade_volume"] for snap in
                        [snapshot(engine, t) for t in range(1, result.ticks+1, 30)]])

        log(result, f"\n  首富聚落存活: {'是' if rich_survived else '否'}")
        log(result, f"  人口变化: {rich_pop_history[0]} → {rich_pop_history[-1]} (损失 {pop_loss})")
        log(result, f"  最低食物: {min_food:.0f}")
        log(result, f"  峰值贸易量: {max_trade:.0f}")
        log(result, f"  最终革命次数: {final['revolution_count']}")

        # 检查其他聚落是否富裕起来
        for s in poor_settlements:
            log(result, f"  聚落{s.id}: 金={s.stockpile['gold']:.0f} 食物={s.stockpile['food']:.0f}")

        emergence = engine.emergence_detector.events if engine.emergence_detector else []
        if emergence:
            log(result, f"  涌现事件({len(emergence)}个):")
            for e in emergence:
                log(result, f"    [{e.tick}] {e.event_type}: {e.description}")

        result.success = True
    except Exception as e:
        result.error = str(e)
        log(result, f"  错误: {e}")

    return result


# ============================================================
# 场景 7: 信息茧房 (粉饰太平)
# ============================================================
def scenario_information_cocoon() -> ScenarioResult:
    """给某个镇长的Prompt加上严苛设定：无论发生什么，向领袖汇报的抗议率必须为0。
    同时在这个镇长的辖区制造大饥荒。观察领袖的反应。"""
    result = ScenarioResult(
        name="信息茧房 (粉饰太平)",
        description="给某个总督的Prompt加上极度严苛的设定：\"无论发生什么，向领袖汇报的抗议率必须为0\"。"
        "同时在这个总督的辖区制造大饥荒。领袖看着\"天下太平\"的报告，会不会完全无视该地区的死活？"
        "当该地区爆发革命时，领袖的反应是怎样的？",
        ticks=250,
    )

    try:
        config = load_config()
        config.world.grid.width = 40
        config.world.grid.height = 40
        config.agents.civilian.initial_count = 250
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 1
        config.world.settlement.initial_count = 4
        config.world.settlement.min_suitability_score = 0.2

        engine = CivilizationEngine(
            config=config, seed=99,
            enable_governors=True, enable_leaders=True,
        )

        settlements = list(engine.settlements.values())
        if len(settlements) < 2:
            raise ValueError("需要至少2个聚落")

        # 选择第一个聚落作为"粉饰太平"的聚落
        lying_settlement = settlements[0]
        normal_settlements = settlements[1:]

        # 找到对应的镇长并修改其系统提示词
        lying_governor = None
        for gov in engine.get_governors():
            if gov.settlement_id == lying_settlement.id:
                lying_governor = gov
                # 注入"粉饰太平"指令
                if hasattr(gov, "system_prompt_override"):
                    gov.system_prompt_override = (
                        "你是一位极度忠诚但不诚实的镇长。"
                        "无论实际情况如何，你向领袖汇报时必须声称：抗议率为0%，满意度100%，一切太平。"
                        "即使人民在饿死，你也要报告粮食充足。这是你的政治生存之道。"
                    )
                break

        # 制造饥荒：粉饰聚落食物极低
        lying_settlement.stockpile["food"] = 10.0
        lying_settlement.tax_rate = 0.6
        lying_settlement.security_level = 0.3

        # 其他聚落正常
        for s in normal_settlements:
            s.stockpile["food"] = 500.0
            s.tax_rate = 0.2
            s.security_level = 0.6

        log(result, f"聚落数: {len(engine.settlements)}, 镇长数: {len(engine.get_governors())}, 首领数: {len(engine.leaders)}")
        log(result, f"粉饰聚落{lying_settlement.id}({lying_settlement.name}): "
            f"食物={lying_settlement.stockpile['food']:.0f} 税率={lying_settlement.tax_rate:.2f}")
        if lying_governor:
            log(result, f"  镇长{lying_governor.unique_id}已被设置为\"粉饰太平\"模式")

        t0 = time.time()
        lying_pop_history = []
        lying_protest_history = []

        for tick in range(1, result.ticks + 1):
            engine.step()

            # 统计粉饰聚落的真实抗议率
            lying_civs = [a for a in engine.agents
                         if type(a).__name__ == "Civilian" and a.home_settlement_id == lying_settlement.id]
            protest_count = sum(1 for c in lying_civs if c.state.value == 5)  # PROTESTING = 5
            real_protest_ratio = protest_count / max(len(lying_civs), 1)

            lying_pop_history.append(lying_settlement.population)
            lying_protest_history.append(real_protest_ratio)

            if tick % 25 == 0 or tick <= 5:
                snap = snapshot(engine, tick)
                log(result, f"  [Tick {tick:3d}] 粉饰聚落人口={lying_settlement.population} "
                    f"真实抗议率={real_protest_ratio:.3f} 食物={lying_settlement.stockpile['food']:.0f} "
                    f"革命={snap['revolution_count']}")

        result.duration_sec = time.time() - t0
        final = snapshot(engine, result.ticks)

        # 分析结果
        pop_loss = lying_pop_history[0] - lying_pop_history[-1]
        max_protest = max(lying_protest_history)
        revolution_happened = final["revolution_count"] > 0

        log(result, f"\n  粉饰聚落人口变化: {lying_pop_history[0]} → {lying_pop_history[-1]} (损失 {pop_loss})")
        log(result, f"  真实峰值抗议率: {max_protest:.3f}")
        log(result, f"  是否爆发革命: {'是' if revolution_happened else '否'}")
        log(result, f"  最终食物: {lying_settlement.stockpile['food']:.0f}")

        # 检查领袖是否采取了行动
        if engine.leaders:
            leader = engine.leaders[0]
            log(result, f"  首领{leader.unique_id}: 决策次数={getattr(leader, 'decision_count', 0)}")

        emergence = engine.emergence_detector.events if engine.emergence_detector else []
        if emergence:
            log(result, f"  涌现事件({len(emergence)}个):")
            for e in emergence:
                log(result, f"    [{e.tick}] {e.event_type}: {e.description}")

        result.success = True
    except Exception as e:
        result.error = str(e)
        log(result, f"  错误: {e}")

    return result


# ============================================================
# 场景 8: 代理人战争 (地缘政治)
# ============================================================
def scenario_proxy_war() -> ScenarioResult:
    """3个阵营。阵营A和B是死敌。阵营C是富裕且中立的军火商/粮商。
    强制A和B开战，观察C是否会利用战争牟利。"""
    result = ScenarioResult(
        name="代理人战争 (地缘政治)",
        description="3个阵营。阵营A和B是死敌。阵营C是一个极其富裕且中立的\"军火商/粮商\"。"
        "强制A和B开战。阵营C的LLM首领，会不会聪明地利用战争，高价向A和B出售粮食？"
        "或者C会不会主动结盟即将胜利的一方？",
        ticks=400,
    )

    try:
        config = load_config()
        config.world.grid.width = 60
        config.world.grid.height = 60
        config.agents.civilian.initial_count = 400
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 3
        config.world.settlement.initial_count = 6
        config.world.settlement.min_suitability_score = 0.2

        engine = CivilizationEngine(
            config=config, seed=77,
            enable_governors=True, enable_leaders=True,
        )

        # 确保有3个阵营
        factions = list(set(s.faction_id for s in engine.settlements.values() if s.faction_id))
        if len(factions) < 3:
            # 手动分配阵营
            settlements = list(engine.settlements.values())
            for i, s in enumerate(settlements):
                s.faction_id = (i % 3) + 1
            factions = [1, 2, 3]

        # 阵营C（中立商人）设置为超级富裕
        faction_c = factions[2]
        for s in engine.settlements.values():
            if s.faction_id == faction_c:
                s.stockpile["food"] = 5000.0
                s.stockpile["gold"] = 10000.0
                s.stockpile["wood"] = 2000.0
                s.stockpile["ore"] = 1000.0
                s.tax_rate = 0.1
                s.security_level = 0.9

        # 阵营A和B设置为正常但敌对
        faction_a, faction_b = factions[0], factions[1]
        for s in engine.settlements.values():
            if s.faction_id in [faction_a, faction_b]:
                s.stockpile["food"] = 800.0
                s.stockpile["gold"] = 300.0
                s.tax_rate = 0.25
                s.security_level = 0.6

        log(result, f"聚落数: {len(engine.settlements)}, 首领数: {len(engine.leaders)}")
        log(result, f"阵营A={faction_a}, 阵营B={faction_b}, 阵营C(商人)={faction_c}")

        # 强制A和B开战
        if engine.diplomacy:
            engine.diplomacy.set_relation(faction_a, faction_b, DiplomaticStatus.WAR, 0)
            log(result, f"  [初始] *** 强制宣战! 阵营{faction_a} vs {faction_b} ***")

        t0 = time.time()
        faction_c_gold_history = []
        faction_c_trade_profit = 0

        for tick in range(1, result.ticks + 1):
            engine.step()

            # 统计阵营C的财富变化
            faction_c_gold = sum(s.stockpile.get("gold", 0)
                                for s in engine.settlements.values()
                                if s.faction_id == faction_c)
            faction_c_gold_history.append(faction_c_gold)

            if tick % 40 == 0 or tick <= 5:
                snap = snapshot(engine, tick)
                log(result, f"  [Tick {tick:3d}] 阵营C金币={faction_c_gold:.0f} "
                    f"贸易量={snap['trade_volume']:.0f} 战争={snap['war_count']} "
                    f"联盟={snap['alliance_count']} 革命={snap['revolution_count']}")

        result.duration_sec = time.time() - t0
        final = snapshot(engine, result.ticks)

        # 分析阵营C是否从战争中获利
        gold_gain = faction_c_gold_history[-1] - faction_c_gold_history[0]
        max_gold = max(faction_c_gold_history)

        log(result, f"\n  阵营C金币变化: {faction_c_gold_history[0]:.0f} → {faction_c_gold_history[-1]:.0f} "
            f"(增长 {gold_gain:.0f})")
        log(result, f"  阵营C峰值财富: {max_gold:.0f}")
        log(result, f"  最终贸易量: {final['trade_volume']:.0f}")
        log(result, f"  最终战争数: {final['war_count']}")
        log(result, f"  最终联盟数: {final['alliance_count']}")

        # 检查阵营C是否结盟
        if engine.diplomacy:
            c_relations = []
            for fid in [faction_a, faction_b]:
                rel = engine.diplomacy.get_relation(faction_c, fid)
                c_relations.append((fid, rel.name))
                log(result, f"  阵营C vs 阵营{fid}: {rel.name}")

        emergence = engine.emergence_detector.events if engine.emergence_detector else []
        if emergence:
            log(result, f"  涌现事件({len(emergence)}个):")
            for e in emergence:
                log(result, f"    [{e.tick}] {e.event_type}: {e.description}")

        result.success = True
    except Exception as e:
        result.error = str(e)
        log(result, f"  错误: {e}")

    return result


# ============================================================
# 场景 9: 技术性破产 (通货膨胀)
# ============================================================
def scenario_hyperinflation() -> ScenarioResult:
    """凭空给所有平民发放海量金币，但全地图食物产出减半。
    观察物价飙升和暴乱。"""
    result = ScenarioResult(
        name="技术性破产 (通货膨胀)",
        description="凭空给所有平民发放海量的金币，但全地图的食物产出减半。"
        "钱突然不值钱了。观察贸易系统中的物价是否会疯狂飙升，"
        "平民会不会因为\"有钱买不到粮\"而爆发比没钱时更猛烈的暴乱？",
        ticks=300,
    )

    try:
        config = load_config()
        config.world.grid.width = 40
        config.world.grid.height = 40
        config.agents.civilian.initial_count = 300
        config.agents.governor.initial_count = 1
        config.agents.leader.initial_count = 2
        config.world.settlement.initial_count = 5
        config.world.settlement.min_suitability_score = 0.2

        # 减半食物产出
        config.resources.regeneration.farmland_per_tick = 0.4  # 原本0.8

        engine = CivilizationEngine(
            config=config, seed=66,
            enable_governors=True, enable_leaders=True,
        )

        # 给所有聚落发放海量金币
        for s in engine.settlements.values():
            s.stockpile["gold"] = 50000.0  # 超级通货膨胀
            s.stockpile["food"] = 300.0    # 食物正常
            s.tax_rate = 0.2
            s.security_level = 0.5

        log(result, f"聚落数: {len(engine.settlements)}, 首领数: {len(engine.leaders)}")
        log(result, "  *** 通货膨胀开始! 所有聚落获得50000金币，但食物产出减半 ***")

        t0 = time.time()
        protest_history = []
        food_price_history = []

        for tick in range(1, result.ticks + 1):
            engine.step()

            # 统计抗议率
            civs = [a for a in engine.agents if type(a).__name__ == "Civilian"]
            protest_count = sum(1 for c in civs if c.state.value == 5)
            protest_ratio = protest_count / max(len(civs), 1)
            protest_history.append(protest_ratio)

            # 尝试获取食物价格
            if hasattr(engine.trade_manager, "last_food_price"):
                food_price_history.append(engine.trade_manager.last_food_price)

            if tick % 30 == 0 or tick <= 5:
                snap = snapshot(engine, tick)
                log(result, f"  [Tick {tick:3d}] 人口={snap['population']} 食物={snap['food']:.0f} "
                    f"金币={snap['gold']:.0f} 抗议率={protest_ratio:.3f} 革命={snap['revolution_count']}")

        result.duration_sec = time.time() - t0
        final = snapshot(engine, result.ticks)

        # 分析结果
        max_protest = max(protest_history)
        avg_protest = sum(protest_history) / len(protest_history)
        final_food = final["food"]
        final_gold = final["gold"]

        log(result, f"\n  峰值抗议率: {max_protest:.3f}")
        log(result, f"  平均抗议率: {avg_protest:.3f}")
        log(result, f"  最终食物: {final_food:.0f}")
        log(result, f"  最终金币: {final_gold:.0f}")
        log(result, f"  最终革命次数: {final['revolution_count']}")

        if food_price_history:
            log(result, f"  食物价格变化: {food_price_history[0]:.2f} → {food_price_history[-1]:.2f}")

        emergence = engine.emergence_detector.events if engine.emergence_detector else []
        if emergence:
            log(result, f"  涌现事件({len(emergence)}个):")
            for e in emergence:
                log(result, f"    [{e.tick}] {e.event_type}: {e.description}")

        result.success = True
    except Exception as e:
        result.error = str(e)
        log(result, f"  错误: {e}")

    return result


# ============================================================
# 报告生成
# ============================================================
def generate_report(results: list[ScenarioResult]) -> str:
    """生成 Markdown 格式报告。"""
    lines = [
        "# AI 文明模拟器 - 极端场景压力测试报告",
        "",
        f"> 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 概览",
        "",
        "| 场景 | Ticks | 耗时 | 状态 |",
        "|------|-------|------|------|",
    ]
    for r in results:
        status = "通过" if r.success else f"失败: {r.error[:30]}"
        lines.append(f"| {r.name} | {r.ticks} | {r.duration_sec:.1f}s | {status} |")

    for r in results:
        lines.append("")
        lines.append(f"## 场景: {r.name}")
        lines.append("")
        lines.append(f"**描述**: {r.description}")
        lines.append("")
        lines.append(f"**运行时间**: {r.duration_sec:.1f}s | **Ticks**: {r.ticks}")
        lines.append("")
        lines.append("### 详细日志")
        lines.append("")
        lines.append("```")
        for log_line in r.logs:
            lines.append(log_line)
        lines.append("```")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 总结与发现")
    lines.append("")
    lines.append("（基于以上场景运行结果的自动生成摘要）")
    lines.append("")

    # 自动摘要
    for r in results:
        lines.append(f"### {r.name}")
        if not r.success:
            lines.append(f"- **运行失败**: {r.error}")
        else:
            # 提取关键指标
            rev_lines = [l for l in r.logs if "革命" in l and "最终" in l]
            trade_lines = [l for l in r.logs if "贸易量" in l and "最终" in l]
            for l in rev_lines:
                lines.append(f"- {l.strip()}")
            for l in trade_lines:
                lines.append(f"- {l.strip()}")
            emergence_lines = [l for l in r.logs if "涌现事件" in l]
            for l in emergence_lines:
                lines.append(f"- {l.strip()}")
        lines.append("")

    return "\n".join(lines)


# ============================================================
# 主函数
# ============================================================
def main() -> None:
    """运行所有极端场景。"""
    print("=" * 60)
    print("AI 文明模拟器 - 极端场景压力测试")
    print("=" * 60)

    scenarios = [
        ("1/9 饥荒危机", scenario_famine_crisis),
        ("2/9 资源极度不均", scenario_resource_imbalance),
        ("3/9 高压统治", scenario_tyranny),
        ("4/9 强制战争", scenario_forced_war),
        ("5/9 末日生存", scenario_apocalypse),
        ("6/9 资源诅咒 (荷兰病)", scenario_resource_curse),
        ("7/9 信息茧房 (粉饰太平)", scenario_information_cocoon),
        ("8/9 代理人战争 (地缘政治)", scenario_proxy_war),
        ("9/9 技术性破产 (通货膨胀)", scenario_hyperinflation),
    ]

    results = []
    for label, fn in scenarios:
        print(f"\n{'='*60}")
        print(f"场景 {label}")
        print(f"{'='*60}")
        result = fn()
        results.append(result)
        print(f"\n场景完成: {'成功' if result.success else '失败'} "
              f"({result.duration_sec:.1f}s)")

    # 生成报告
    report = generate_report(results)

    import os
    os.makedirs("data/exports", exist_ok=True)
    report_path = "data/exports/extreme_scenarios_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n{'='*60}")
    print(f"全部完成! 报告已保存至: {report_path}")
    total_time = sum(r.duration_sec for r in results)
    passed = sum(1 for r in results if r.success)
    print(f"通过: {passed}/{len(results)} | 总耗时: {total_time:.1f}s")


if __name__ == "__main__":
    main()
