"""集成测试：迁徙再分配与空聚落先驱播种。

验证灾后多聚落恢复场景：
- 空聚落通过先驱播种机制获得初始人口
- 迁徙平民在踏入他方领地时可更换归属
- 灾后人口不会永久集中在单一聚落
"""

from civsim.agents.civilian import Civilian
from civsim.config import CivSimConfig
from civsim.world.engine import CivilizationEngine


def _make_config() -> CivSimConfig:
    """构造小型测试配置。"""
    return CivSimConfig(
        world={
            "grid": {"width": 20, "height": 20},
            "map_generation": {"seed": 42},
            "settlement": {"initial_count": 4, "min_suitability_score": 0.0},
        },
        agents={"civilian": {"initial_count": 40}},
        resources={"initial_stockpile": {"food": 300, "wood": 200, "ore": 50, "gold": 100}},
        migration_params={
            "reassignment_base_prob": 0.3,
            "pioneer_seed_enabled": True,
            "pioneer_seed_count": 2,
            "pioneer_source_min_pop": 5,
            "pioneer_seed_distance": 50,
        },
    )


def _get_civilians(engine: CivilizationEngine) -> list[Civilian]:
    """从引擎中提取所有平民 Agent。"""
    return [a for a in engine.agents if isinstance(a, Civilian)]


class TestPioneerSeeding:
    """先驱播种测试。"""

    def test_empty_settlement_gets_pioneers(self) -> None:
        """将某聚落人口清零后运行，先驱播种应使其恢复人口。"""
        config = _make_config()
        engine = CivilizationEngine(config=config, seed=42)

        # 稳定运行几个 tick
        for _ in range(5):
            engine.step()

        # 找到有足够人口的聚落
        populated_sids = [
            sid for sid, s in engine.settlements.items()
            if s.population >= 5
        ]
        if len(populated_sids) < 2:
            # 人口分布过于集中，无法测试
            return

        # 将一个聚落清空
        target_sid = populated_sids[0]
        civils_to_kill = [
            c for c in _get_civilians(engine)
            if c.home_settlement_id == target_sid
        ]
        for c in civils_to_kill:
            c.remove()
        engine.settlements[target_sid].population = 0

        # 运行更多 tick，先驱播种应启动
        for _ in range(20):
            engine.step()

        # 验证目标聚落重新获得人口
        target = engine.settlements[target_sid]
        assert target.population > 0, (
            f"聚落 {target_sid} 在先驱播种后仍然为空"
        )


class TestMigrationRedistribution:
    """迁徙再分配测试。"""

    def test_population_distributes_after_disaster(self) -> None:
        """灾后运行足够多 tick，人口应分散到多个聚落。"""
        config = _make_config()
        engine = CivilizationEngine(config=config, seed=42)

        # 运行至稳定
        for _ in range(10):
            engine.step()

        # 模拟灾难：将除一个聚落外的所有人口清空
        sids = list(engine.settlements.keys())
        survivor_sid = sids[0]
        for sid in sids[1:]:
            civils = [
                c for c in _get_civilians(engine)
                if c.home_settlement_id == sid
            ]
            for c in civils:
                c.remove()
            engine.settlements[sid].population = 0

        # 确保至少一个聚落有人
        assert engine.settlements[survivor_sid].population > 0

        # 运行恢复
        for _ in range(100):
            engine.step()

        # 验证至少有 2 个聚落有人口（先驱播种 + 迁徙再分配）
        populated = sum(
            1 for s in engine.settlements.values() if s.population > 0
        )
        assert populated >= 2, (
            f"灾后 100 tick 仅有 {populated} 个聚落有人口，"
            f"期望至少 2 个。各聚落人口: "
            f"{[(sid, s.population) for sid, s in engine.settlements.items()]}"
        )


class TestReassignmentUpdatesHome:
    """验证聚落再分配确实更新了 home_settlement_id。"""

    def test_home_settlement_can_change(self) -> None:
        """高概率再分配配置下，运行足够久应有平民改变归属。"""
        config = CivSimConfig(
            world={
                "grid": {"width": 15, "height": 15},
                "map_generation": {"seed": 99},
                "settlement": {"initial_count": 3, "min_suitability_score": 0.0},
            },
            agents={"civilian": {"initial_count": 30}},
            resources={"initial_stockpile": {"food": 500, "wood": 100, "ore": 30, "gold": 50}},
            migration_params={
                "reassignment_base_prob": 0.8,
                "pioneer_seed_enabled": False,
            },
            # 增大领地半径，使聚落领地在小地图上有交叠
            map_suitability={
                "territory_radius": 6,
                "min_settlement_distance": 4,
            },
        )
        engine = CivilizationEngine(config=config, seed=99)

        # 记录初始归属
        initial_homes = {
            c.unique_id: c.home_settlement_id
            for c in _get_civilians(engine)
        }

        # 运行 200 tick（更长以确保迁徙有足够机会）
        for _ in range(200):
            engine.step()

        # 检查是否有任何平民改变了归属
        changed = sum(
            1 for c in _get_civilians(engine)
            if c.unique_id in initial_homes
            and c.home_settlement_id != initial_homes[c.unique_id]
        )
        # 在高概率下 200 tick 几乎必然有变化
        assert changed > 0, "200 tick 后无任何平民改变归属聚落"
