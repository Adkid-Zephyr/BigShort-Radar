"""tests for src/store/history_db.py — 独立 cache DB schema/CRUD/批量 upsert."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pandas as pd
import pytest

from src.store import history_db as hdb


@pytest.fixture()
def conn(tmp_path):
    """临时文件 cache DB，自动建表。"""
    path = tmp_path / "hist.sqlite"
    with hdb.open_history_db(path) as c:
        yield c


# ── schema ────────────────────────────────────────────────────

def test_open_creates_table_and_index(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','index')"
    ).fetchall()
    names = {r["name"] for r in rows}
    assert "history_points" in names
    assert "idx_hist_name_date" in names


def test_open_is_idempotent(tmp_path):
    """连续打开同一个 cache 文件不应报错。"""
    p = tmp_path / "h.sqlite"
    with hdb.open_history_db(p):
        pass
    with hdb.open_history_db(p):
        pass


def test_default_path_under_data_dir():
    """HISTORY_DB_PATH 应该在主 DB 同目录但文件名不同（不污染主库）。"""
    assert hdb.HISTORY_DB_PATH.name == "historical_cache.sqlite"
    # 与主 DB 不是同一文件
    from src.store.db import DB_PATH as MAIN_DB
    assert hdb.HISTORY_DB_PATH != MAIN_DB


# ── upsert_point ──────────────────────────────────────────────

def test_upsert_point_inserts(conn):
    hdb.upsert_point(conn, "vix", "2024-01-02", 13.4, "YF:^VIX")
    row = conn.execute("SELECT * FROM history_points WHERE name='vix'").fetchone()
    assert row["date"] == "2024-01-02"
    assert row["value"] == pytest.approx(13.4)
    assert row["source"] == "YF:^VIX"
    assert row["fetched_at"]  # 非空


def test_upsert_point_updates_on_conflict(conn):
    hdb.upsert_point(conn, "vix", "2024-01-02", 13.4, "YF:^VIX")
    hdb.upsert_point(conn, "vix", "2024-01-02", 14.7, "YF:^VIX")
    rows = conn.execute("SELECT * FROM history_points WHERE name='vix'").fetchall()
    assert len(rows) == 1
    assert rows[0]["value"] == pytest.approx(14.7)


def test_upsert_point_explicit_fetched_at(conn):
    ts = "2026-01-01T00:00:00Z"
    hdb.upsert_point(conn, "vix", "2024-01-02", 13.4, "YF:^VIX", fetched_at=ts)
    row = conn.execute("SELECT fetched_at FROM history_points").fetchone()
    assert row["fetched_at"] == ts


# ── bulk_upsert ───────────────────────────────────────────────

def test_bulk_upsert_pandas_series(conn):
    idx = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
    s = pd.Series([13.4, 14.0, 13.7], index=idx)
    n = hdb.bulk_upsert(conn, name="vix", source="YF:^VIX", series=s)
    assert n == 3
    rows = conn.execute("SELECT date, value FROM history_points ORDER BY date").fetchall()
    assert [r["date"] for r in rows] == ["2024-01-02", "2024-01-03", "2024-01-04"]
    assert [r["value"] for r in rows] == [pytest.approx(x) for x in [13.4, 14.0, 13.7]]


def test_bulk_upsert_skips_nan_inf(conn):
    idx = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
    s = pd.Series([13.4, float("nan"), float("inf")], index=idx)
    n = hdb.bulk_upsert(conn, name="vix", source="YF:^VIX", series=s)
    assert n == 1
    rows = conn.execute("SELECT date FROM history_points").fetchall()
    assert [r["date"] for r in rows] == ["2024-01-02"]


def test_bulk_upsert_none(conn):
    n = hdb.bulk_upsert(conn, name="x", source="FRED:X", series=None)
    assert n == 0


def test_bulk_upsert_empty_series(conn):
    n = hdb.bulk_upsert(conn, name="x", source="FRED:X", series=pd.Series([], dtype=float))
    assert n == 0


def test_bulk_upsert_idempotent(conn):
    idx = pd.to_datetime(["2024-01-02", "2024-01-03"])
    s = pd.Series([13.4, 14.0], index=idx)
    hdb.bulk_upsert(conn, name="vix", source="YF:^VIX", series=s)
    n = hdb.bulk_upsert(conn, name="vix", source="YF:^VIX", series=s)
    assert n == 2  # 仍然算入库 2 条（覆盖式 upsert）
    assert hdb.count_points(conn, name="vix") == 2  # 实际只 2 行


def test_bulk_upsert_shared_fetched_at(conn):
    idx = pd.to_datetime(["2024-01-02", "2024-01-03"])
    s = pd.Series([1.0, 2.0], index=idx)
    ts = "2026-01-01T00:00:00Z"
    hdb.bulk_upsert(conn, name="x", source="FRED:X", series=s, fetched_at=ts)
    rows = conn.execute("SELECT fetched_at FROM history_points").fetchall()
    assert all(r["fetched_at"] == ts for r in rows)


# ── get_series_range ──────────────────────────────────────────

def test_get_series_range_all(conn):
    for d, v in [("2024-01-02", 1.0), ("2024-01-03", 2.0), ("2024-01-04", 3.0)]:
        hdb.upsert_point(conn, "x", d, v, "FRED:X")
    rows = hdb.get_series_range(conn, "x")
    assert [r["value"] for r in rows] == [1.0, 2.0, 3.0]


def test_get_series_range_with_start(conn):
    for d, v in [("2024-01-02", 1.0), ("2024-01-03", 2.0), ("2024-01-04", 3.0)]:
        hdb.upsert_point(conn, "x", d, v, "FRED:X")
    rows = hdb.get_series_range(conn, "x", start="2024-01-03")
    assert [r["date"] for r in rows] == ["2024-01-03", "2024-01-04"]


def test_get_series_range_with_end(conn):
    for d, v in [("2024-01-02", 1.0), ("2024-01-03", 2.0), ("2024-01-04", 3.0)]:
        hdb.upsert_point(conn, "x", d, v, "FRED:X")
    rows = hdb.get_series_range(conn, "x", end="2024-01-03")
    assert [r["date"] for r in rows] == ["2024-01-02", "2024-01-03"]


def test_get_series_range_with_start_and_end(conn):
    for d, v in [("2024-01-02", 1.0), ("2024-01-03", 2.0), ("2024-01-04", 3.0), ("2024-01-05", 4.0)]:
        hdb.upsert_point(conn, "x", d, v, "FRED:X")
    rows = hdb.get_series_range(conn, "x", start="2024-01-03", end="2024-01-04")
    assert [r["date"] for r in rows] == ["2024-01-03", "2024-01-04"]


def test_get_series_range_filters_other_indicators(conn):
    hdb.upsert_point(conn, "x", "2024-01-02", 1.0, "FRED:X")
    hdb.upsert_point(conn, "y", "2024-01-02", 99.0, "FRED:Y")
    rows = hdb.get_series_range(conn, "x")
    assert len(rows) == 1
    assert rows[0]["value"] == 1.0


def test_get_series_range_empty(conn):
    assert hdb.get_series_range(conn, "nonexistent") == []


# ── count_points ──────────────────────────────────────────────

def test_count_points_global(conn):
    hdb.upsert_point(conn, "a", "2024-01-01", 1.0, "FRED:A")
    hdb.upsert_point(conn, "b", "2024-01-01", 2.0, "FRED:B")
    assert hdb.count_points(conn) == 2


def test_count_points_by_name(conn):
    hdb.upsert_point(conn, "a", "2024-01-01", 1.0, "FRED:A")
    hdb.upsert_point(conn, "a", "2024-01-02", 2.0, "FRED:A")
    hdb.upsert_point(conn, "b", "2024-01-01", 9.0, "FRED:B")
    assert hdb.count_points(conn, name="a") == 2
    assert hdb.count_points(conn, name="b") == 1
    assert hdb.count_points(conn, name="c") == 0
