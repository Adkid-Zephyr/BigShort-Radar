"""SQLite 存储层。

唯一真相源。其他模块只通过本模块读写库，不直连 sqlite3。
schema 见 ARCHITECTURE.md，改动需 ADR。
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from src.utils.config import DB_PATH
from src.utils.logger import get_logger

log = get_logger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS indicators (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    value       REAL    NOT NULL,
    source      TEXT    NOT NULL,
    ingested_at TEXT    NOT NULL,
    UNIQUE(name, date)
);
CREATE INDEX IF NOT EXISTS idx_name_date ON indicators(name, date);
"""


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """打开 SQLite 连接（自动建库目录），并启用外键。

    入参：
        db_path: 可选自定义路径；默认 config.DB_PATH
    返回：
        sqlite3.Connection（row_factory=Row）
    异常：
        OSError 创建目录失败时抛
        sqlite3.Error 打开数据库失败时抛
    """
    target = Path(db_path) if db_path is not None else DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """创建 indicators 表及索引（幂等）。

    入参：
        conn: 已打开的 SQLite 连接
    返回：无
    异常：
        sqlite3.Error 执行失败时抛
    """
    with conn:  # 事务：成功 commit，失败 rollback
        conn.executescript(_SCHEMA_SQL)
    log.info("schema 初始化完成（indicators 表 + idx_name_date 索引）")


@contextmanager
def open_db(db_path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    """连接 + 自动建表 + 上下文管理器，使用方便。

    用法：
        with open_db() as conn:
            ...
    """
    conn = connect(db_path)
    try:
        init_schema(conn)
        yield conn
    finally:
        conn.close()


# ── CRUD ─────────────────────────────────────────────────────

def _utc_now_iso() -> str:
    """当前 UTC 时间 ISO 字符串（秒级，带 Z）。"""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def upsert_indicator(
    conn: sqlite3.Connection,
    name: str,
    date: str,
    value: float,
    source: str,
    ingested_at: Optional[str] = None,
) -> None:
    """写入或更新一条指标值（按 (name, date) 唯一）。

    入参：
        conn: 已开 schema 的连接
        name: 指标 name（如 yield_curve_10y2y）
        date: 指标日期，ISO YYYY-MM-DD
        value: 数值
        source: 数据源（如 FRED:T10Y2Y / YF:^VIX）
        ingested_at: 入库 UTC 时间戳；缺省取当前 UTC
    返回：无
    异常：
        sqlite3.Error 写入失败时抛
    """
    ts = ingested_at or _utc_now_iso()
    with conn:
        conn.execute(
            """
            INSERT INTO indicators (name, date, value, source, ingested_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name, date) DO UPDATE SET
                value=excluded.value,
                source=excluded.source,
                ingested_at=excluded.ingested_at
            """,
            (name, date, float(value), source, ts),
        )


def get_latest(conn: sqlite3.Connection, name: str) -> Optional[Dict[str, Any]]:
    """返回某指标最新一条记录（按 date 倒序），无则 None。

    入参：
        conn: 连接
        name: 指标 name
    返回：
        dict 或 None
    异常：
        sqlite3.Error
    """
    cur = conn.execute(
        "SELECT name, date, value, source, ingested_at FROM indicators "
        "WHERE name = ? ORDER BY date DESC LIMIT 1",
        (name,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_series(
    conn: sqlite3.Connection, name: str, days: Optional[int] = None
) -> List[Dict[str, Any]]:
    """返回某指标的历史序列（按 date 升序）。

    入参：
        conn: 连接
        name: 指标 name
        days: 仅取最近 N 天；缺省返回全部
    返回：
        list[dict]，可能为空
    异常：
        sqlite3.Error
    """
    if days is not None and days > 0:
        cur = conn.execute(
            """
            SELECT name, date, value, source, ingested_at FROM indicators
            WHERE name = ?
              AND date >= date('now', ?)
            ORDER BY date ASC
            """,
            (name, f"-{int(days)} days"),
        )
    else:
        cur = conn.execute(
            "SELECT name, date, value, source, ingested_at FROM indicators "
            "WHERE name = ? ORDER BY date ASC",
            (name,),
        )
    return [dict(r) for r in cur.fetchall()]
