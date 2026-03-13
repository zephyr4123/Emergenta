"""报告与数据导出系统。

支持将仿真数据导出为 CSV/Parquet/PNG/Markdown 格式。
"""

from __future__ import annotations

import json
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from civsim.dashboard.shared_state import SharedState, TickSnapshot

logger = logging.getLogger(__name__)

# 默认导出目录
_DEFAULT_EXPORT_DIR = Path("data/exports")


def export_history_csv(
    history: list[TickSnapshot],
    output_path: str | Path | None = None,
) -> Path:
    """将历史快照导出为 CSV 文件。

    Args:
        history: TickSnapshot 列表。
        output_path: 输出路径，默认自动生成。

    Returns:
        导出文件路径。
    """
    if not history:
        msg = "无历史数据可导出"
        raise ValueError(msg)

    rows = []
    for snap in history:
        row: dict[str, Any] = {
            "tick": snap.tick,
            "year": snap.year,
            "season": snap.season,
            "population": snap.population,
            "avg_satisfaction": snap.avg_satisfaction,
            "avg_hunger": snap.avg_hunger,
            "protest_ratio": snap.protest_ratio,
            "revolution_count": snap.revolution_count,
            "trade_volume": snap.trade_volume,
            "alliance_count": snap.alliance_count,
            "war_count": snap.war_count,
        }
        for res in ("food", "wood", "ore", "gold"):
            row[f"total_{res}"] = snap.resources.get(res, 0)
        for state_name, count in snap.state_counts.items():
            row[f"state_{state_name.lower()}"] = count
        rows.append(row)

    df = pd.DataFrame(rows)
    path = _resolve_path(output_path, "history", "csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    logger.info("CSV 导出完成: %s (%d 行)", path, len(df))
    return path


def export_history_parquet(
    history: list[TickSnapshot],
    output_path: str | Path | None = None,
) -> Path:
    """将历史快照导出为 Parquet 文件。

    Args:
        history: TickSnapshot 列表。
        output_path: 输出路径。

    Returns:
        导出文件路径。
    """
    if not history:
        msg = "无历史数据可导出"
        raise ValueError(msg)

    rows = []
    for snap in history:
        row: dict[str, Any] = {
            "tick": snap.tick,
            "year": snap.year,
            "population": snap.population,
            "avg_satisfaction": snap.avg_satisfaction,
            "protest_ratio": snap.protest_ratio,
            "revolution_count": snap.revolution_count,
            "trade_volume": snap.trade_volume,
        }
        for res in ("food", "wood", "ore", "gold"):
            row[f"total_{res}"] = snap.resources.get(res, 0)
        rows.append(row)

    df = pd.DataFrame(rows)
    path = _resolve_path(output_path, "history", "parquet")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    logger.info("Parquet 导出完成: %s (%d 行)", path, len(df))
    return path


def export_charts_png(
    shared_state: SharedState,
    output_dir: str | Path | None = None,
) -> list[Path]:
    """将所有图表导出为 PNG 文件。

    Args:
        shared_state: 共享状态对象。
        output_dir: 输出目录。

    Returns:
        导出的文件路径列表。
    """
    from civsim.dashboard import charts

    directory = Path(output_dir) if output_dir else _DEFAULT_EXPORT_DIR / "charts"
    directory.mkdir(parents=True, exist_ok=True)

    history = shared_state.get_history()
    snap = shared_state.get_latest()

    chart_builders = {
        "population": lambda: charts.build_population_chart(history),
        "resources": lambda: charts.build_resource_chart(history),
        "satisfaction": lambda: charts.build_satisfaction_chart(history),
        "revolution": lambda: charts.build_revolution_timeline(history),
        "adaptive": lambda: charts.build_adaptive_chart(history),
        "settlements": lambda: charts.build_settlement_table(snap),
    }

    paths = []
    for name, builder in chart_builders.items():
        try:
            fig = builder()
            path = directory / f"{name}.png"
            fig.write_image(str(path), width=1200, height=600)
            paths.append(path)
            logger.info("图表导出: %s", path)
        except Exception:
            logger.exception("图表导出失败: %s", name)

    return paths


def export_markdown_report(
    shared_state: SharedState,
    output_path: str | Path | None = None,
) -> Path:
    """生成 Markdown 格式的仿真报告。

    Args:
        shared_state: 共享状态对象。
        output_path: 输出路径。

    Returns:
        报告文件路径。
    """
    snap = shared_state.get_latest()
    history = shared_state.get_history()

    path = _resolve_path(output_path, "report", "md")
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# CivSim 仿真报告",
        "",
        f"**生成时间**: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**总 Tick 数**: {snap.tick}",
        f"**模拟时间**: 第{snap.year}年 {snap.season}",
        "",
        "## 总览",
        "",
        f"- 总人口: {snap.population}",
        f"- 平均满意度: {snap.avg_satisfaction:.3f}",
        f"- 抗议率: {snap.protest_ratio:.1%}",
        f"- 累计革命: {snap.revolution_count}",
        f"- 贸易总量: {snap.trade_volume:.0f}",
        f"- 联盟数: {snap.alliance_count}",
        f"- 战争数: {snap.war_count}",
        "",
        "## 资源总量",
        "",
        f"| 资源 | 数量 |",
        f"|------|------|",
    ]
    for res in ("food", "wood", "ore", "gold"):
        lines.append(f"| {res} | {snap.resources.get(res, 0):.0f} |")

    lines.extend([
        "",
        "## 聚落详情",
        "",
        "| 聚落 | 人口 | 食物 | 金币 | 税率 | 满意度 |",
        "|------|------|------|------|------|--------|",
    ])
    for s in sorted(snap.settlements, key=lambda x: x.get("population", 0), reverse=True):
        lines.append(
            f"| {s.get('name', '')} | {s.get('population', 0)} "
            f"| {s.get('food', 0):.0f} | {s.get('gold', 0):.0f} "
            f"| {s.get('tax_rate', 0):.0%} | {s.get('satisfaction', 0):.2f} |"
        )

    lines.extend([
        "",
        "## 状态分布",
        "",
        "| 状态 | 人数 |",
        "|------|------|",
    ])
    for state_name, count in snap.state_counts.items():
        lines.append(f"| {state_name} | {count} |")

    # 关键事件
    events = shared_state.get_event_log(30)
    if events:
        lines.extend([
            "",
            "## 最近事件",
            "",
        ])
        for ev in events:
            lines.append(f"- {ev}")

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("报告导出完成: %s", path)
    return path


def export_full_archive(
    shared_state: SharedState,
    output_path: str | Path | None = None,
) -> Path:
    """导出完整仿真存档（数据 + 图表 + 报告 → zip）。

    Args:
        shared_state: 共享状态对象。
        output_path: zip 文件输出路径。

    Returns:
        zip 文件路径。
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # 导出各组件
        csv_path = export_history_csv(
            shared_state.get_history(),
            tmp / "history.csv",
        )
        report_path = export_markdown_report(
            shared_state,
            tmp / "report.md",
        )

        # 打包
        zip_path = _resolve_path(output_path, "archive", "zip")
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(csv_path, "history.csv")
            zf.write(report_path, "report.md")

    logger.info("存档导出完成: %s", zip_path)
    return zip_path


def _resolve_path(
    path: str | Path | None,
    default_name: str,
    ext: str,
) -> Path:
    """解析输出路径，无路径时自动生成。"""
    if path is not None:
        return Path(path)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    return _DEFAULT_EXPORT_DIR / f"{default_name}_{ts}.{ext}"
