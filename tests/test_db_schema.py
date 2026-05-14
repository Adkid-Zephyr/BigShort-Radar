"""db.py schema 部分单元测试（CRUD 测试见下一轮 test_db.py）。"""
from __future__ import annotations

import sqlite3

from src.store import db as dbmod


def test_connect_creates_parent_dir(tmp_path):
    p = tmp_path / "sub" / "dir" / "radar.sqlite"
    conn = dbmod.connect(p)
    assert p.parent.exists()
    conn.close()


def test_init_schema_creates_indicators_table(tmp_path):
    p = tmp_path / "radar.sqlite"
    conn = dbmod.connect(p)
    dbmod.init_schema(conn)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='indicators'"
    )
    assert cur.fetchone() is not None
    conn.close()


def test_init_schema_creates_index(tmp_path):
    p = tmp_path / "radar.sqlite"
    conn = dbmod.connect(p)
    dbmod.init_schema(conn)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_name_date'"
    )
    assert cur.fetchone() is not None
    conn.close()


def test_init_schema_idempotent(tmp_path):
    p = tmp_path / "radar.sqlite"
    conn = dbmod.connect(p)
    dbmod.init_schema(conn)
    dbmod.init_schema(conn)  # 第二次不应抛
    conn.close()


def test_open_db_context_manager(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as conn:
        cur = conn.execute("SELECT count(*) FROM indicators")
        assert cur.fetchone()[0] == 0


def test_unique_constraint_name_date(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as conn:
        conn.execute(
            "INSERT INTO indicators (name, date, value, source, ingested_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("x", "2026-05-15", 1.0, "TEST", "2026-05-15T00:00:00Z"),
        )
        # 同 name+date 再插应触发 UNIQUE
        try:
            conn.execute(
                "INSERT INTO indicators (name, date, value, source, ingested_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ("x", "2026-05-15", 2.0, "TEST", "2026-05-15T00:00:00Z"),
            )
            raised = False
        except sqlite3.IntegrityError:
            raised = True
        assert raised
