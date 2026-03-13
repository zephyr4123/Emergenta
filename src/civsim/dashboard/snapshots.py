"""世界快照序列化与回放系统。

支持将完整仿真状态保存为文件，以及从快照恢复仿真。
快照使用 pickle 序列化引擎核心状态。
"""

from __future__ import annotations

import json
import logging
import pickle
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 默认快照存储目录
_DEFAULT_SNAPSHOT_DIR = Path("data/snapshots")


@dataclass
class SnapshotMeta:
    """快照元数据。

    Attributes:
        snapshot_id: 快照唯一标识（文件名去后缀）。
        tick: 快照时的 tick 编号。
        year: 快照时的年份。
        season: 快照时的季节。
        population: 快照时的总人口。
        settlement_count: 聚落数量。
        timestamp: 保存时间戳（ISO 格式）。
        description: 用户描述。
    """

    snapshot_id: str = ""
    tick: int = 0
    year: int = 0
    season: str = ""
    population: int = 0
    settlement_count: int = 0
    timestamp: str = ""
    description: str = ""


@dataclass
class EngineSnapshot:
    """引擎核心状态快照。

    存储恢复仿真所需的最小状态集合。

    Attributes:
        meta: 快照元数据。
        engine_state: pickle 序列化的引擎状态字节。
    """

    meta: SnapshotMeta = field(default_factory=SnapshotMeta)
    engine_state: bytes = b""


def capture_snapshot(
    engine: Any,
    description: str = "",
) -> EngineSnapshot:
    """从引擎捕获完整状态快照。

    Args:
        engine: CivilizationEngine 实例。
        description: 用户描述。

    Returns:
        包含完整引擎状态的快照对象。
    """
    from civsim.agents.civilian import Civilian

    civilians = [a for a in engine.agents if isinstance(a, Civilian)]
    season_val = engine.clock.current_season
    season_name = (
        season_val.name
        if hasattr(season_val, "name") else str(season_val)
    )

    meta = SnapshotMeta(
        snapshot_id=f"snap_{engine.clock.tick}_{_timestamp_id()}",
        tick=engine.clock.tick,
        year=engine.clock.current_year,
        season=season_name,
        population=len(civilians),
        settlement_count=len(engine.settlements),
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        description=description,
    )

    # 序列化引擎关键状态
    state_dict = _extract_engine_state(engine)
    engine_bytes = pickle.dumps(state_dict)

    return EngineSnapshot(meta=meta, engine_state=engine_bytes)


def save_snapshot(
    snapshot: EngineSnapshot,
    directory: str | Path | None = None,
) -> Path:
    """将快照保存到磁盘。

    Args:
        snapshot: 快照对象。
        directory: 保存目录，默认 data/snapshots/。

    Returns:
        保存的文件路径。
    """
    save_dir = Path(directory) if directory else _DEFAULT_SNAPSHOT_DIR
    save_dir.mkdir(parents=True, exist_ok=True)

    snap_path = save_dir / f"{snapshot.meta.snapshot_id}.pkl"
    meta_path = save_dir / f"{snapshot.meta.snapshot_id}.meta.json"

    # 保存快照二进制
    with open(snap_path, "wb") as f:
        pickle.dump(snapshot, f)

    # 保存元数据 JSON（便于浏览）
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(asdict(snapshot.meta), f, ensure_ascii=False, indent=2)

    logger.info("快照已保存: %s", snap_path)
    return snap_path


def load_snapshot(path: str | Path) -> EngineSnapshot:
    """从磁盘加载快照。

    Args:
        path: 快照 .pkl 文件路径。

    Returns:
        快照对象。
    """
    with open(path, "rb") as f:
        snapshot: EngineSnapshot = pickle.load(f)  # noqa: S301
    logger.info("快照已加载: %s (tick=%d)", path, snapshot.meta.tick)
    return snapshot


def list_snapshots(
    directory: str | Path | None = None,
) -> list[SnapshotMeta]:
    """列出目录下所有快照的元数据。

    Args:
        directory: 快照目录。

    Returns:
        按 tick 排序的元数据列表。
    """
    snap_dir = Path(directory) if directory else _DEFAULT_SNAPSHOT_DIR
    if not snap_dir.exists():
        return []

    metas = []
    for meta_file in sorted(snap_dir.glob("*.meta.json")):
        try:
            with open(meta_file, encoding="utf-8") as f:
                data = json.load(f)
            metas.append(SnapshotMeta(**data))
        except Exception:
            logger.warning("无法读取元数据: %s", meta_file)
    return sorted(metas, key=lambda m: m.tick)


def _extract_engine_state(engine: Any) -> dict[str, Any]:
    """提取引擎核心状态为可序列化字典。"""
    state: dict[str, Any] = {
        "clock_tick": engine.clock.tick,
        "settlements": {},
        "config_dict": engine.config.model_dump(),
    }

    # 聚落状态
    for sid, s in engine.settlements.items():
        state["settlements"][sid] = {
            "population": s.population,
            "stockpile": dict(s.stockpile),
            "tax_rate": s.tax_rate,
            "security_level": s.security_level,
            "faction_id": s.faction_id,
            "infrastructure": s.infrastructure,
        }

    # 外交状态
    if engine.diplomacy:
        state["diplomacy_relations"] = {
            f"{a}-{b}": int(status)
            for (a, b), status in engine.diplomacy._relations.items()
        }
        state["diplomacy_trust"] = {
            f"{a}-{b}": trust
            for (a, b), trust in engine.diplomacy._trust.items()
        }

    # 革命状态
    if engine.revolution_tracker:
        state["revolution_count"] = (
            engine.revolution_tracker.revolution_count
        )

    # 贸易状态
    if engine.trade_manager:
        state["trade_volume"] = engine.trade_manager.total_volume

    return state


def _timestamp_id() -> str:
    """生成时间戳 ID 片段。"""
    return datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
