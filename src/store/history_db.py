"""历史数据 cache DB（独立于主 DB）。

设计意图：
  - 主 DB（data/radar.sqlite）只存"每日最新一条 per 指标"，结构稳定
  - 本模块管理 data/historical_cache.sqlite，存每条指标过去 N 年的全量序列
  - 用于 sparkline / Z-score / 加速度 / 历史回测等"需要历史窗口"的场景
  - **不动主 DB schema**，与主 DB 完全隔离

schema：与主 DB indicators 表结构一致（便于复用 upsert/get_series 心智模型），
但新增 fetched_at 字段用于追踪批量回填的运行时间。

参考：src/store/db.py（同模式实现 + 同 docstring 风格）。
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

# 默认放在主 DB 同目录下，文件名 historical_cache.sqlite
HISTORY_DB_PATH = DB_PATH.parent / "historical_cache.sqlite"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS history_points (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    value       REAL    NOT NULL,
    source      TEXT    NOT NULL,
    fetched_at  TEXT    NOT NULL,
    UNIQUE(name, date)
);
CREATE INDEX IF NOT EXISTS idx_hist_name_date ON history_points(name, date);
"""


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """打开历史 cache DB 连接（自动建库目录）。

    入参：
        db_path: 可选自定义路径；默认 HISTORY_DB_PATH
    返回：
        sqlite3.Connection（row_factory=Row）
    异常：
        OSError 创建目录失败时抛
        sqlite3.Error 打开数据库失败时抛
    """
    target = Path(db_path) if db_path is not None else HISTORY_DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """创建 history_points 表 + 索引（幂等）。

    入参：
        conn: 已打开的连接
    返回：无
    异常：
        sqlite3.Error
    """
    with conn:
        conn.executescript(_SCHEMA_SQL)
    log.info("history cache schema 初始化完成")


@contextmanager
def open_history_db(db_path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    """连接 + 自动建表 + 上下文管理器。

    用法：
        with open_history_db() as conn:
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
    """当前 UTC 时间 ISO 字符串。"""
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def upsert_point(
    conn: sqlite3.Connection,
    name: str,
    date: str,
    value: float,
    source: str,
    fetched_at: Optional[str] = None,
) -> None:
    """写入或更新一条历史点（按 (name, date) 唯一）。

    入参：
        conn: 已开 schema 的连接
        name: 指标 name
        date: 日期 ISO YYYY-MM-DD
        value: 数值
        source: 数据源（如 FRED:T10Y2Y）
        fetched_at: 入库 UTC 时间戳；缺省取当前
    返回：无
    异常：
        sqlite3.Error
    """
    ts = fetched_at or _utc_now_iso()
    with conn:
        conn.execute(
            """
            INSERT INTO history_points (name, date, value, source, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name, date) DO UPDATE SET
                value=excluded.value,
                source=excluded.source,
                fetched_at=excluded.fetched_at
            """,
            (name, date, float(value), source, ts),
        )


def bulk_upsert(
    conn: sqlite3.Connection,
    name: str,
    source: str,
    series: Any,
    fetched_at: Optional[str] = None,
) -> int:
    """批量 upsert 一条指标的历史序列（pandas.Series 或 (date,value) 可迭代）。

    与 src/store/db.py::upsert_series_from_pandas 同心智，但写入 history_points 表。

    行为约定：
      - index 是日期型 → strftime；否则 str(ts)[:10]
      - NaN / Inf / 不能转 float → 跳过 + warning
      - 单行错不抛，整体不抛

    入参：
        conn: 已开 schema 的连接
        name: 指标 name
        source: 数据源
        series: pandas.Series 或 (timestamp, value) 可迭代；None / 空 → 0
        fetched_at: 共享一个时间戳给整批；缺省每条取当前 UTC
    返回：
        实际入库行数
    """
    if series is None:
        return 0
    try:
        if len(series) == 0:
            return 0
    except TypeError:
        pass

    ts_shared = fetched_at or _utc_now_iso()
    count = 0
    iterator = series.items() if hasattr(series, "items") else iter(series)
    for ts, value in iterator:
        date_str = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
        try:
            v = float(value)
        except (TypeError, ValueError):
            log.warning("[%s] 值无法转 float，跳过 %s=%r", name, date_str, value)
            continue
        if v != v or v in (float("inf"), float("-inf")):
            log.warning("[%s] 值 NaN/Inf，跳过 %s=%r", name, date_str, value)
            continue
        upsert_point(conn, name=name, date=date_str, value=v, source=source, fetched_at=ts_shared)
        count += 1

    log.info("[%s] history bulk_upsert %d 条", name, count)
    return count


def get_series_range(
    conn: sqlite3.Connection,
    name: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """按 [start, end] 闭区间取某指标历史序列（按 date 升序）。

    入参：
        conn: 连接
        name: 指标 name
        start: 起始日期 YYYY-MM-DD（含），None 不限
        end:   结束日期 YYYY-MM-DD（含），None 不限
    返回：
        list[dict]，每个含 name/date/value/source/fetched_at
    异常：
        sqlite3.Error
    """
    sql = "SELECT name, date, value, source, fetched_at FROM history_points WHERE name = ?"
    params: List[Any] = [name]
    if start is not None:
        sql += " AND date >= ?"
        params.append(start)
    if end is not None:
        sql += " AND date <= ?"
        params.append(end)
    sql += " ORDER BY date ASC"
    cur = conn.execute(sql, params)
    return [dict(r) for r in cur.fetchall()]


def count_points(conn: sqlite3.Connection, name: Optional[str] = None) -> int:
    """统计 history_points 行数；name 给定则按指标过滤。

    入参：
        conn: 连接
        name: 可选指标过滤
    返回：
        行数（int）
    """
    if name is None:
        cur = conn.execute("SELECT COUNT(*) AS c FROM history_points")
    else:
        cur = conn.execute("SELECT COUNT(*) AS c FROM history_points WHERE name = ?", (name,))
    return int(cur.fetchone()["c"])
