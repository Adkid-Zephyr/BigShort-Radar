"""SQLite 存储层。

唯一真相源。其他模块只通过本模块读写库，不直连 sqlite3。
schema 见 ARCHITECTURE.md，改动需 ADR。
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

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
