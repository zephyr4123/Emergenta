"""全系统性能基准测试 — 测量全层级联动下的模拟性能极限。

包含平民 + 镇长（规则回退） + 首领（规则回退） + 贸易 + 外交 + 革命。
按比例缩放所有层级：聚落数 = agents // 80, 首领数 = settlements // 3。
"""

import gc
import sys
import time
from pathlib import Path

import numpy as np
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from civsim.agents.civilian import Civilian
from civsim.agents.governor import Governor
from civsim.config import load_config
from civsim.world.engine import CivilizationEngine


def get_memory_mb() -> float:
    """获取当前进程 RSS 内存 (MB)。"""
    return psutil.Process().memory_info().rss / 1024 / 1024


def compute_scaling(n_agents: int) -> dict:
    """根据平民数量计算各层级规模。"""
    settlements = max(4, n_agents // 80)
    leaders = max(2, settlements // 3)
    grid = max(30, int(np.sqrt(n_agents) * 2.5))
    grid = min(grid, 200)  # 上限 200x200
    return {
        "settlements": settlements,
        "leaders": leaders,
        "grid": grid,
    }


def benchmark_full_system(
    n_agents: int,
    n_ticks: int,
    seed: int = 42,
) -> dict:
    """运行全系统联动基准测试。"""
    gc.collect()
    mem_before = get_memory_mb()

    scaling = compute_scaling(n_agents)
    grid_size = scaling["grid"]
    n_settlements = scaling["settlements"]
    n_leaders = scaling["leaders"]

    config = load_config()
    config.world.grid.width = grid_size
    config.world.grid.height = grid_size
    config.agents.civilian.initial_count = n_agents
    config.world.settlement.initial_count = n_settlements
    config.agents.governor.initial_count = 1  # 启用镇长（1=开关）
    config.agents.leader.initial_count = n_leaders
    config.ray.enabled = False

    # 创建引擎（全系统：镇长 + 首领 + 贸易 + 外交 + 革命）
    t0 = time.perf_counter()
    engine = CivilizationEngine(
        config=config, seed=seed,
        enable_governors=True, enable_leaders=True,
    )
    init_time = time.perf_counter() - t0

    # 强制使用规则回退，避免真实 LLM 调用
    for a in engine.agents:
        if hasattr(a, "_gateway"):
            a._gateway = None
    for leader in engine.leaders:
        leader._gateway = None

    mem_after_init = get_memory_mb()

    actual_civilians = sum(1 for a in engine.agents if isinstance(a, Civilian))
    actual_governors = sum(1 for a in engine.agents if isinstance(a, Governor))
    actual_leaders = len(engine.leaders)
    actual_settlements = len(engine.settlements)

    # 各阶段计时
    tick_times = []
    phase_times = {
        "env": [], "agents": [], "trade": [],
        "settle": [], "revolution": [], "collect": [],
    }

    for _tick_i in range(n_ticks):
        t_start = time.perf_counter()

        # 1. 环境更新
        t1 = time.perf_counter()
        engine.clock.advance()
        engine._environment_update()
        phase_times["env"].append(time.perf_counter() - t1)

        # 2. Agent 行动（含平民 + 镇长 + 首领）
        t2 = time.perf_counter()
        engine._agents_act()
        phase_times["agents"].append(time.perf_counter() - t2)

        # 3. 贸易结算
        t3 = time.perf_counter()
        if engine.trade_manager:
            engine._trade_update()
        phase_times["trade"].append(time.perf_counter() - t3)

        # 4. 聚落结算
        t4 = time.perf_counter()
        engine._settlement_reconcile()
        phase_times["settle"].append(time.perf_counter() - t4)

        # 5. 革命检测
        t5 = time.perf_counter()
        if engine.revolution_tracker:
            engine._check_revolutions()
        phase_times["revolution"].append(time.perf_counter() - t5)

        # 6. 数据采集
        t6 = time.perf_counter()
        engine.datacollector.collect(engine)
        phase_times["collect"].append(time.perf_counter() - t6)

        tick_times.append(time.perf_counter() - t_start)

    mem_peak = get_memory_mb()
    total_time = sum(tick_times)

    # 统计涌现事件
    rev_count = (
        engine.revolution_tracker.revolution_count
        if engine.revolution_tracker else 0
    )
    trade_count = (
        engine.trade_manager.trade_count
        if engine.trade_manager else 0
    )
    gov_decisions = sum(
        g.decision_count
        for g in engine.agents if isinstance(g, Governor)
    )
    leader_decisions = sum(
        l.decision_count for l in engine.leaders
    )

    result = {
        "n_agents_config": n_agents,
        "n_civilians": actual_civilians,
        "n_governors": actual_governors,
        "n_leaders": actual_leaders,
        "n_settlements": actual_settlements,
        "grid_size": f"{grid_size}x{grid_size}",
        "n_ticks": n_ticks,
        "init_time_s": round(init_time, 3),
        "total_time_s": round(total_time, 3),
        "avg_tick_ms": round(np.mean(tick_times) * 1000, 2),
        "p50_tick_ms": round(np.percentile(tick_times, 50) * 1000, 2),
        "p95_tick_ms": round(np.percentile(tick_times, 95) * 1000, 2),
        "max_tick_ms": round(max(tick_times) * 1000, 2),
        "ticks_per_second": round(n_ticks / total_time, 1) if total_time > 0 else 0,
        "mem_before_mb": round(mem_before, 1),
        "mem_after_init_mb": round(mem_after_init, 1),
        "mem_peak_mb": round(mem_peak, 1),
        "mem_delta_mb": round(mem_peak - mem_before, 1),
        "phase_avg_ms": {
            phase: round(np.mean(times) * 1000, 2)
            for phase, times in phase_times.items()
        },
        "phase_pct": {},
        "emergent_events": {
            "revolutions": rev_count,
            "trades": trade_count,
            "governor_decisions": gov_decisions,
            "leader_decisions": leader_decisions,
        },
    }

    total_phase = sum(np.mean(t) for t in phase_times.values())
    for phase, times in phase_times.items():
        pct = (np.mean(times) / total_phase * 100) if total_phase > 0 else 0
        result["phase_pct"][phase] = round(pct, 1)

    del engine
    gc.collect()
    return result


def print_result(r: dict) -> None:
    """打印单次测试结果。"""
    print(f"\n{'='*70}")
    print(f"  全系统联动: {r['n_civilians']}平民 + {r['n_governors']}镇长 + "
          f"{r['n_leaders']}首领 | {r['n_settlements']}聚落 | {r['grid_size']}")
    print(f"{'='*70}")
    print(f"  初始化:    {r['init_time_s']:.3f}s")
    print(f"  总运行:    {r['total_time_s']:.3f}s ({r['n_ticks']} ticks)")
    print(f"  Tick 速率: {r['ticks_per_second']:.1f} ticks/s")
    print(f"  Avg tick:  {r['avg_tick_ms']:.2f}ms")
    print(f"  P50/P95:   {r['p50_tick_ms']:.2f} / {r['p95_tick_ms']:.2f} ms")
    print(f"  Max tick:  {r['max_tick_ms']:.2f}ms")
    print(f"  内存增量:  {r['mem_delta_mb']:.1f} MB")
    print(f"  涌现事件:  革命={r['emergent_events']['revolutions']}, "
          f"贸易={r['emergent_events']['trades']}, "
          f"镇长决策={r['emergent_events']['governor_decisions']}, "
          f"首领决策={r['emergent_events']['leader_decisions']}")
    print(f"  各阶段耗时占比:")
    for phase, pct in r['phase_pct'].items():
        avg = r['phase_avg_ms'][phase]
        bar = "█" * int(pct / 2)
        print(f"    {phase:12s}  {avg:8.2f}ms  {pct:5.1f}%  {bar}")


def main() -> None:
    """运行全系统基准测试。"""
    print("=" * 70)
    print("  AI 文明模拟器 - 全系统联动性能基准测试")
    print("  (平民 + 镇长回退 + 首领回退 + 贸易 + 外交 + 革命)")
    print("=" * 70)

    # (agents, ticks) — 足够触发镇长决策 (120 ticks/季)
    scenarios = [
        (100,   200),
        (500,   200),
        (1000,  150),
        (2000,  150),
        (5000,  130),
        (10000, 130),
        (20000, 50),
    ]

    results = []
    for n_agents, ticks in scenarios:
        scaling = compute_scaling(n_agents)
        print(f"\n>>> 测试中: {n_agents}平民 + "
              f"{scaling['settlements']}聚落 + "
              f"{scaling['leaders']}首领, "
              f"{scaling['grid']}x{scaling['grid']}格, "
              f"{ticks} ticks...")
        try:
            r = benchmark_full_system(n_agents, ticks)
            print_result(r)
            results.append(r)

            # 如果 avg tick > 5s，跳过更大规模
            if r["avg_tick_ms"] > 5000:
                print(f"\n  >>> 单 tick 超过 5 秒，跳过更大规模")
                break
        except Exception as e:
            print(f"  !!! 失败: {e}")
            import traceback
            traceback.print_exc()
            break

    if not results:
        return

    print(f"\n{'='*70}")
    print("  全系统联动 — 汇总表")
    print(f"{'='*70}")
    header = (
        f"{'平民':>6} {'镇长':>4} {'首领':>4} {'聚落':>4} "
        f"{'格子':>8} {'Ticks':>5} {'Avg(ms)':>10} "
        f"{'TPS':>8} {'Mem(MB)':>8} {'革命':>4} {'贸易':>6} {'瓶颈':>12}"
    )
    print(header)
    print("-" * len(header) + "----")
    for r in results:
        bottleneck = max(r['phase_pct'], key=r['phase_pct'].get)
        ev = r['emergent_events']
        print(
            f"{r['n_civilians']:>6} {r['n_governors']:>4} "
            f"{r['n_leaders']:>4} {r['n_settlements']:>4} "
            f"{r['grid_size']:>8} {r['n_ticks']:>5} "
            f"{r['avg_tick_ms']:>10.2f} "
            f"{r['ticks_per_second']:>8.1f} "
            f"{r['mem_delta_mb']:>8.1f} "
            f"{ev['revolutions']:>4} {ev['trades']:>6} "
            f"{bottleneck:>12}"
        )


if __name__ == "__main__":
    main()
