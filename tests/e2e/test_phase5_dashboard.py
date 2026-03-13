"""Phase 5 仪表盘集成测试。

验证 SharedState、SimulationRunner、图表构建、快照、导出全链路。
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from civsim.config import load_config
from civsim.dashboard.shared_state import (
    GodAction,
    GodModeAction,
    SharedState,
    TickSnapshot,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture()
def small_config():
    """小规模测试配置。"""
    config = load_config()
    config.agents.civilian.initial_count = 30
    config.world.grid.width = 15
    config.world.grid.height = 15
    config.world.settlement.initial_count = 3
    config.world.settlement.min_suitability_score = 0.1
    config.agents.governor.initial_count = 0
    config.agents.leader.initial_count = 0
    return config


@pytest.fixture()
def runner(small_config):
    """创建并启动 SimulationRunner。"""
    from civsim.dashboard.sim_runner import SimulationRunner

    r = SimulationRunner(
        config=small_config,
        seed=42,
        enable_governors=False,
        enable_leaders=False,
    )
    yield r
    if r.state.is_running:
        r.stop()


# ============================================================
# SharedState 单元测试
# ============================================================

class TestSharedState:
    """SharedState 基础功能测试。"""

    def test_initial_state(self) -> None:
        """初始状态为暂停、速度1。"""
        ss = SharedState()
        assert ss.is_paused is True
        assert ss.speed == 1
        assert ss.is_running is False

    def test_action_queue(self) -> None:
        """操作队列 enqueue/drain 正确工作。"""
        ss = SharedState()
        ss.enqueue_action(GodModeAction(action=GodAction.PAUSE))
        ss.enqueue_action(GodModeAction(action=GodAction.RESUME))
        actions = ss.drain_actions()
        assert len(actions) == 2
        assert actions[0].action == GodAction.PAUSE
        assert actions[1].action == GodAction.RESUME
        # drain 后队列为空
        assert len(ss.drain_actions()) == 0

    def test_speed_clamping(self) -> None:
        """速度值被正确限制在 [1, 20]。"""
        ss = SharedState()
        ss.speed = 25
        assert ss.speed == 20
        ss.speed = 0
        assert ss.speed == 1

    def test_event_log(self) -> None:
        """事件日志追加和读取。"""
        ss = SharedState()
        ss.add_event("test event 1")
        ss.add_event("test event 2")
        logs = ss.get_event_log(10)
        assert len(logs) == 2
        assert "test event 1" in logs[0]

    def test_history_storage(self) -> None:
        """历史快照存储和检索。"""
        ss = SharedState()
        for i in range(5):
            snap = TickSnapshot(tick=i, population=100 + i)
            ss._lock.acquire()
            ss._latest = snap
            ss._history.append(snap)
            ss._lock.release()

        history = ss.get_history()
        assert len(history) == 5
        assert history[0].tick == 0
        assert history[4].tick == 4

        recent = ss.get_history(2)
        assert len(recent) == 2
        assert recent[0].tick == 3


# ============================================================
# SimulationRunner 测试
# ============================================================

class TestSimulationRunner:
    """SimulationRunner 基础功能测试。"""

    def test_init(self, runner) -> None:
        """Runner 正确初始化。"""
        assert runner.engine is not None
        assert runner.state is not None
        snap = runner.state.get_latest()
        assert snap.population > 0

    def test_manual_step(self, runner) -> None:
        """手动执行 step。"""
        tick_before = runner.engine.clock.tick
        runner.engine.step()
        runner.state.update_from_engine(runner.engine)
        snap = runner.state.get_latest()
        assert snap.tick == tick_before + 1

    def test_multiple_steps(self, runner) -> None:
        """执行多步并验证历史记录。"""
        for _ in range(10):
            runner.engine.step()
            runner.state.update_from_engine(runner.engine)

        history = runner.state.get_history()
        # 初始快照 + 10 步
        assert len(history) >= 10
        snap = runner.state.get_latest()
        assert snap.tick == 10

    def test_snapshot_data_integrity(self, runner) -> None:
        """快照数据完整性验证。"""
        runner.engine.step()
        runner.state.update_from_engine(runner.engine)
        snap = runner.state.get_latest()

        assert snap.tick > 0
        assert snap.population > 0
        assert isinstance(snap.state_counts, dict)
        assert "WORKING" in snap.state_counts
        assert isinstance(snap.resources, dict)
        assert "food" in snap.resources
        assert len(snap.settlements) > 0

    def test_god_action_inject_event(self, runner) -> None:
        """上帝模式事件注入。"""
        sid = list(runner.engine.settlements.keys())[0]
        settlement = runner.engine.settlements[sid]
        food_before = settlement.stockpile["food"]

        action = GodModeAction(
            action=GodAction.INJECT_EVENT,
            params={"event_name": "丰收", "settlement_id": sid},
        )
        runner.state.enqueue_action(action)
        runner._process_god_actions()

        assert settlement.stockpile["food"] == pytest.approx(
            food_before * 2.0,
        )

    def test_god_action_speed(self, runner) -> None:
        """上帝模式速度调整。"""
        action = GodModeAction(
            action=GodAction.SET_SPEED,
            params={"speed": 10},
        )
        runner.state.enqueue_action(action)
        runner._process_god_actions()
        assert runner.state.speed == 10

    def test_background_thread(self, runner) -> None:
        """后台线程启动/停止。"""
        runner.start()
        assert runner.state.is_running is True
        time.sleep(0.2)
        runner.stop()
        assert runner.state.is_running is False


# ============================================================
# 图表构建测试
# ============================================================

class TestCharts:
    """图表构建器基础测试。"""

    def _make_history(self, n: int = 20) -> list[TickSnapshot]:
        """生成模拟历史数据。"""
        history = []
        for i in range(n):
            history.append(TickSnapshot(
                tick=i,
                population=100 - i,
                state_counts={
                    "WORKING": 50 - i,
                    "RESTING": 20,
                    "TRADING": 10,
                    "SOCIALIZING": 5,
                    "MIGRATING": 3,
                    "PROTESTING": i,
                    "FIGHTING": max(0, i - 10),
                },
                resources={
                    "food": 500 - i * 10,
                    "wood": 200,
                    "ore": 50,
                    "gold": 100 + i * 5,
                },
                avg_satisfaction=0.6 - i * 0.01,
                avg_hunger=0.1 + i * 0.02,
                protest_ratio=i / 100,
                revolution_count=i // 10,
                settlements=[
                    {"id": 1, "name": "A", "population": 50,
                     "food": 200, "gold": 50, "tax_rate": 0.2,
                     "security_level": 0.5, "satisfaction": 0.6,
                     "protest_ratio": 0.1, "faction_id": 1,
                     "position": (5, 5)},
                ],
                adaptive_info={
                    "temperature": 0.3 + i * 0.01,
                    "markov_protest_multiplier": 1.0,
                    "satisfaction_recovery_multiplier": 1.0,
                },
            ))
        return history

    def test_population_chart(self) -> None:
        from civsim.dashboard.charts import build_population_chart
        fig = build_population_chart(self._make_history())
        assert fig is not None
        assert len(fig.data) > 0

    def test_resource_chart(self) -> None:
        from civsim.dashboard.charts import build_resource_chart
        fig = build_resource_chart(self._make_history())
        assert len(fig.data) == 4  # 4 resources

    def test_satisfaction_chart(self) -> None:
        from civsim.dashboard.charts import build_satisfaction_chart
        fig = build_satisfaction_chart(self._make_history())
        assert len(fig.data) == 3  # satisfaction, protest, hunger

    def test_settlement_table(self) -> None:
        from civsim.dashboard.charts import build_settlement_table
        snap = self._make_history()[0]
        fig = build_settlement_table(snap)
        assert fig is not None

    def test_revolution_timeline(self) -> None:
        from civsim.dashboard.charts import build_revolution_timeline
        fig = build_revolution_timeline(self._make_history())
        assert fig is not None

    def test_adaptive_chart(self) -> None:
        from civsim.dashboard.charts import build_adaptive_chart
        fig = build_adaptive_chart(self._make_history())
        assert len(fig.data) >= 2

    def test_empty_history(self) -> None:
        """空数据不崩溃。"""
        from civsim.dashboard.charts import (
            build_population_chart,
            build_resource_chart,
        )
        fig1 = build_population_chart([])
        fig2 = build_resource_chart([])
        assert fig1 is not None
        assert fig2 is not None


# ============================================================
# 快照系统测试
# ============================================================

class TestSnapshots:
    """快照系统测试。"""

    def test_capture_and_save(self, runner) -> None:
        """捕获快照并保存到磁盘。"""
        from civsim.dashboard.snapshots import (
            capture_snapshot,
            list_snapshots,
            load_snapshot,
            save_snapshot,
        )

        runner.engine.step()
        snap = capture_snapshot(runner.engine, description="测试快照")

        assert snap.meta.tick == 1
        assert snap.meta.population > 0
        assert len(snap.engine_state) > 0

        with tempfile.TemporaryDirectory() as tmpdir:
            path = save_snapshot(snap, tmpdir)
            assert path.exists()

            # 列出快照
            metas = list_snapshots(tmpdir)
            assert len(metas) == 1
            assert metas[0].tick == 1

            # 加载快照
            loaded = load_snapshot(path)
            assert loaded.meta.tick == 1


# ============================================================
# 导出系统测试
# ============================================================

class TestExport:
    """导出系统测试。"""

    def _make_state_with_history(self) -> SharedState:
        """创建包含历史数据的 SharedState。"""
        ss = SharedState()
        for i in range(10):
            snap = TickSnapshot(
                tick=i,
                population=100,
                state_counts={"WORKING": 80, "PROTESTING": 20},
                resources={"food": 500, "wood": 200, "ore": 50, "gold": 100},
                avg_satisfaction=0.6,
                protest_ratio=0.2,
                settlements=[
                    {"id": 1, "name": "A", "population": 100,
                     "food": 500, "gold": 100, "tax_rate": 0.2,
                     "security_level": 0.5, "satisfaction": 0.6,
                     "protest_ratio": 0.1},
                ],
            )
            ss._lock.acquire()
            ss._latest = snap
            ss._history.append(snap)
            ss._lock.release()
        return ss

    def test_csv_export(self) -> None:
        from civsim.dashboard.export import export_history_csv
        ss = self._make_state_with_history()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_history_csv(
                ss.get_history(),
                Path(tmpdir) / "test.csv",
            )
            assert path.exists()
            content = path.read_text()
            assert "tick" in content
            assert "population" in content

    def test_parquet_export(self) -> None:
        from civsim.dashboard.export import export_history_parquet
        ss = self._make_state_with_history()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_history_parquet(
                ss.get_history(),
                Path(tmpdir) / "test.parquet",
            )
            assert path.exists()
            assert path.stat().st_size > 0

    def test_markdown_report(self) -> None:
        from civsim.dashboard.export import export_markdown_report
        ss = self._make_state_with_history()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_markdown_report(
                ss,
                Path(tmpdir) / "report.md",
            )
            assert path.exists()
            content = path.read_text()
            assert "CivSim" in content
            assert "人口" in content

    def test_full_archive(self) -> None:
        from civsim.dashboard.export import export_full_archive
        ss = self._make_state_with_history()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = export_full_archive(
                ss,
                Path(tmpdir) / "archive.zip",
            )
            assert path.exists()
            assert path.suffix == ".zip"


# ============================================================
# Dash App 创建测试
# ============================================================

class TestDashApp:
    """Dash 应用创建测试。"""

    def test_create_app(self) -> None:
        """应用创建不报错。"""
        from civsim.dashboard.app import create_app
        from civsim.dashboard.callbacks import register_callbacks

        ss = SharedState()
        app = create_app(ss)
        register_callbacks(app)

        assert app.title == "Emergenta — AI Civilization Simulator"
        assert hasattr(app, "shared_state")

    def test_app_layout_has_tabs(self) -> None:
        """布局包含标签页。"""
        from civsim.dashboard.app import create_app

        ss = SharedState()
        app = create_app(ss)
        # 检查布局非空
        assert app.layout is not None


# ============================================================
# 场景预设测试
# ============================================================

class TestScenarios:
    """场景预设功能测试。"""

    def test_dutch_disease(self, runner) -> None:
        """荷兰病场景应用后富裕聚落金币暴增、食物为零。"""
        from civsim.dashboard.scenarios import apply_scenario

        logs = apply_scenario(runner.engine, "dutch_disease")
        assert any("荷兰病" in m for m in logs)

        settlements = list(runner.engine.settlements.values())
        # 至少有一个聚落 gold >= 50000
        gold_values = [s.stockpile["gold"] for s in settlements]
        assert max(gold_values) >= 50000
        # 该聚落食物为 0
        rich = max(settlements, key=lambda s: s.stockpile["gold"])
        assert rich.stockpile["food"] == 0.0

    def test_info_cocoon(self, runner) -> None:
        """信息茧房场景应用后部分聚落处于困境。"""
        from civsim.dashboard.scenarios import apply_scenario

        logs = apply_scenario(runner.engine, "info_cocoon")
        assert any("信息茧房" in m for m in logs)

        settlements = list(runner.engine.settlements.values())
        # 至少有一个聚落食物 <= 10
        food_values = [s.stockpile["food"] for s in settlements]
        assert min(food_values) <= 10.0
        # 至少有一个聚落食物 >= 500（正常聚落）
        assert max(food_values) >= 500.0

    def test_apocalypse(self, runner) -> None:
        """世界末日场景所有聚落资源极低。"""
        from civsim.dashboard.scenarios import apply_scenario

        logs = apply_scenario(runner.engine, "apocalypse")
        assert any("世界末日" in m for m in logs)

        settlements = list(runner.engine.settlements.values())
        for s in settlements:
            assert s.stockpile["food"] == 30.0
            assert s.stockpile["gold"] == 20.0
            assert s.tax_rate == 0.5

    def test_scenario_via_god_action(self, runner) -> None:
        """通过上帝模式队列应用场景。"""
        runner.state.enqueue_action(
            GodModeAction(
                action=GodAction.APPLY_SCENARIO,
                params={"scenario_key": "apocalypse"},
            ),
        )
        # 手动触发处理
        runner._process_god_actions()

        logs = runner.state.get_event_log(20)
        assert any("世界末日" in m for m in logs)

    def test_unknown_scenario(self, runner) -> None:
        """未知场景返回警告。"""
        from civsim.dashboard.scenarios import apply_scenario

        logs = apply_scenario(runner.engine, "nonexistent")
        assert any("未知场景" in m for m in logs)
