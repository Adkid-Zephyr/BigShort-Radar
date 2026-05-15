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


# ── 批量写入 helper ──────────────────────────────────────────

def upsert_series_from_pandas(
    conn: sqlite3.Connection,
    name: str,
    source: str,
    series: Any,
) -> int:
    """从一个 pandas.Series 批量 upsert 进 indicators 表。

    抽象自 vix.py / yield_curve.py / yield_curve_10y3m.py 三处共用的循环
    （DECISIONS.md "重复三次再抽象"原则触发，2026-05-15 iter 21）。

    行为约定：
      - index 必须是日期型（pandas.Timestamp 或可 strftime("%Y-%m-%d")），其他降级到 str(ts)[:10]
      - 值无法转 float / 是 NaN / 是 Inf → 跳过该行并写 warning
      - 全程 try/except 单行错误，整体不抛
      - 调用方法：upsert_indicator 单行复用，事务由其内部 with conn 管理

    入参：
        conn: 已开 schema 的连接
        name: 指标 name（如 "vix"）
        source: 数据源（如 "YF:^VIX"）
        series: pandas.Series 或类似 .items() 的可迭代（(timestamp, value)）；
                None 或 len==0 直接返回 0
    返回：
        实际入库行数（跳过的不计）
    异常：
        不抛；底层 sqlite3.Error 由 upsert_indicator 抛出（极少见）
    """
    if series is None:
        return 0
    try:
        if len(series) == 0:
            return 0
    except TypeError:
        # 没有 __len__ 也尝试继续（迭代器场景）
        pass

    count = 0
    for ts, value in series.items():
        date_str = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
        try:
            v = float(value)
        except (TypeError, ValueError):
            log.warning("[%s] 值无法转 float，跳过 %s=%r", name, date_str, value)
            continue
        # 用 != 自身判断 NaN，避免依赖 math（保持 db.py 零外部库）
        if v != v or v in (float("inf"), float("-inf")):
            log.warning("[%s] 值是 NaN/Inf，跳过 %s=%r", name, date_str, value)
            continue
        upsert_indicator(conn, name=name, date=date_str, value=v, source=source)
        count += 1

    log.info("[%s] 批量入库 %d 条（来自 series 长度 %d）", name, count, len(series) if hasattr(series, "__len__") else -1)
    return count
