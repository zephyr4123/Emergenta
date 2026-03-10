"""DuckDB 读写封装。

提供世界快照的持久化存储和查询接口。
"""

from pathlib import Path

import duckdb
import pandas as pd


class Database:
    """DuckDB 数据库管理器。

    Attributes:
        path: 数据库文件路径。
    """

    def __init__(self, path: str = "data/simulations/civsim.duckdb") -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = duckdb.connect(path)
        self._init_tables()

    def _init_tables(self) -> None:
        """初始化数据库表结构。"""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS world_state (
                tick            INTEGER NOT NULL,
                settlement_id   INTEGER NOT NULL,
                population      INTEGER,
                food            DOUBLE,
                wood            DOUBLE,
                ore             DOUBLE,
                gold            DOUBLE,
                tax_rate        DOUBLE,
                security_level  DOUBLE,
                satisfaction_avg DOUBLE,
                protest_ratio   DOUBLE,
                PRIMARY KEY (tick, settlement_id)
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_events (
                id              INTEGER PRIMARY KEY,
                tick            INTEGER NOT NULL,
                agent_id        INTEGER NOT NULL,
                agent_type      VARCHAR,
                event_type      VARCHAR,
                detail          JSON
            )
        """)
        self._conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS agent_events_seq START 1
        """)

    def write_world_state(
        self,
        tick: int,
        settlement_id: int,
        population: int,
        food: float,
        wood: float,
        ore: float,
        gold: float,
        tax_rate: float,
        security_level: float,
        satisfaction_avg: float,
        protest_ratio: float,
    ) -> None:
        """写入一条世界状态快照。"""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO world_state VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                tick, settlement_id, population,
                food, wood, ore, gold,
                tax_rate, security_level, satisfaction_avg, protest_ratio,
            ],
        )

    def write_event(
        self,
        tick: int,
        agent_id: int,
        agent_type: str,
        event_type: str,
        detail: str,
    ) -> None:
        """写入一条事件日志。"""
        self._conn.execute(
            """
            INSERT INTO agent_events VALUES (nextval('agent_events_seq'), ?, ?, ?, ?, ?)
            """,
            [tick, agent_id, agent_type, event_type, detail],
        )

    def query_world_state(
        self,
        tick: int | None = None,
    ) -> pd.DataFrame:
        """查询世界状态。

        Args:
            tick: 指定 tick，为 None 时返回全部。

        Returns:
            查询结果 DataFrame。
        """
        if tick is not None:
            return self._conn.execute(
                "SELECT * FROM world_state WHERE tick = ? ORDER BY settlement_id",
                [tick],
            ).fetchdf()
        return self._conn.execute(
            "SELECT * FROM world_state ORDER BY tick, settlement_id"
        ).fetchdf()

    def get_latest_tick(self) -> int:
        """获取数据库中最新的 tick。"""
        result = self._conn.execute(
            "SELECT MAX(tick) FROM world_state"
        ).fetchone()
        if result and result[0] is not None:
            return result[0]
        return -1

    def batch_insert_world_states(self, records: list[dict]) -> int:
        """批量插入世界状态快照。

        Args:
            records: 字典列表，每个字典包含 world_state 表的各字段。

        Returns:
            插入的记录数。
        """
        if not records:
            return 0

        values = []
        for r in records:
            values.append([
                r["tick"], r["settlement_id"], r.get("population", 0),
                r.get("food", 0.0), r.get("wood", 0.0),
                r.get("ore", 0.0), r.get("gold", 0.0),
                r.get("tax_rate", 0.0), r.get("security_level", 0.0),
                r.get("satisfaction_avg", 0.0), r.get("protest_ratio", 0.0),
            ])

        self._conn.executemany(
            "INSERT OR REPLACE INTO world_state VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            values,
        )
        return len(values)

    def archive_old_data(self, before_tick: int) -> int:
        """归档指定 tick 之前的历史数据。

        将旧数据删除以控制数据库大小。

        Args:
            before_tick: 在此 tick 之前的数据将被删除。

        Returns:
            删除的记录数。
        """
        result = self._conn.execute(
            "SELECT COUNT(*) FROM world_state WHERE tick < ?",
            [before_tick],
        ).fetchone()
        count = result[0] if result else 0

        if count > 0:
            self._conn.execute(
                "DELETE FROM world_state WHERE tick < ?",
                [before_tick],
            )
        return count

    def get_table_stats(self) -> dict[str, int]:
        """获取各表的记录数统计。

        Returns:
            表名→记录数字典。
        """
        stats = {}
        for table in ["world_state", "agent_events"]:
            result = self._conn.execute(
                f"SELECT COUNT(*) FROM {table}"  # noqa: S608
            ).fetchone()
            stats[table] = result[0] if result else 0
        return stats

    def close(self) -> None:
        """关闭数据库连接。"""
        self._conn.close()
