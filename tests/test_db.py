"""db.py CRUD 测试：upsert / get_latest / get_series / 重复插入。"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.store import db as dbmod


@pytest.fixture()
def conn(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as c:
        yield c


def test_upsert_inserts_new_row(conn):
    dbmod.upsert_indicator(conn, "vix", "2026-05-15", 18.5, "YF:^VIX")
    row = dbmod.get_latest(conn, "vix")
    assert row is not None
    assert row["name"] == "vix"
    assert row["date"] == "2026-05-15"
    assert row["value"] == 18.5
    assert row["source"] == "YF:^VIX"
    assert row["ingested_at"]  # 非空


def test_upsert_updates_on_conflict(conn):
    dbmod.upsert_indicator(conn, "vix", "2026-05-15", 18.5, "YF:^VIX",
                           ingested_at="2026-05-15T00:00:00Z")
    dbmod.upsert_indicator(conn, "vix", "2026-05-15", 22.1, "YF:^VIX",
                           ingested_at="2026-05-15T12:00:00Z")
    row = dbmod.get_latest(conn, "vix")
    assert row["value"] == 22.1
    assert row["ingested_at"] == "2026-05-15T12:00:00Z"
    # 仍只有一行
    rows = dbmod.get_series(conn, "vix")
    assert len(rows) == 1


def test_get_latest_returns_none_when_empty(conn):
    assert dbmod.get_latest(conn, "nonexistent") is None


def test_get_latest_picks_newest_date(conn):
    dbmod.upsert_indicator(conn, "vix", "2026-05-13", 17.0, "YF:^VIX")
    dbmod.upsert_indicator(conn, "vix", "2026-05-15", 19.0, "YF:^VIX")
    dbmod.upsert_indicator(conn, "vix", "2026-05-14", 18.0, "YF:^VIX")
    row = dbmod.get_latest(conn, "vix")
    assert row["date"] == "2026-05-15"
    assert row["value"] == 19.0


def test_get_series_returns_ascending(conn):
    for d, v in [("2026-05-15", 19.0), ("2026-05-13", 17.0), ("2026-05-14", 18.0)]:
        dbmod.upsert_indicator(conn, "vix", d, v, "YF:^VIX")
    series = dbmod.get_series(conn, "vix")
    dates = [r["date"] for r in series]
    assert dates == sorted(dates)
    assert len(series) == 3


def test_get_series_filters_by_days(conn):
    today = date.today()
    # 插入 10 天前、3 天前、今天
    for delta, v in [(10, 1.0), (3, 2.0), (0, 3.0)]:
        d = (today - timedelta(days=delta)).isoformat()
        dbmod.upsert_indicator(conn, "vix", d, v, "YF:^VIX")
    s7 = dbmod.get_series(conn, "vix", days=7)
    assert {r["value"] for r in s7} == {2.0, 3.0}  # 10 天前被过滤掉
    s_all = dbmod.get_series(conn, "vix")
    assert len(s_all) == 3


def test_get_series_empty_for_unknown_name(conn):
    assert dbmod.get_series(conn, "nope") == []


def test_indicators_isolated_by_name(conn):
    dbmod.upsert_indicator(conn, "vix", "2026-05-15", 19.0, "YF:^VIX")
    dbmod.upsert_indicator(conn, "yield_curve_10y2y", "2026-05-15", 0.3, "FRED:T10Y2Y")
    assert dbmod.get_latest(conn, "vix")["value"] == 19.0
    assert dbmod.get_latest(conn, "yield_curve_10y2y")["value"] == 0.3


# ── upsert_series_from_pandas（iter 21 抽象） ────────────────
def _series(monkeypatch, dates_values):
    pd = pytest.importorskip("pandas")
    idx = pd.to_datetime([d for d, _ in dates_values])
    vals = [v for _, v in dates_values]
    return pd.Series(vals, index=idx, name="value")


def test_upsert_series_writes_all(conn, monkeypatch):
    s = _series(monkeypatch, [
        ("2026-05-13", 1.0),
        ("2026-05-14", 2.0),
        ("2026-05-15", 3.0),
    ])
    n = dbmod.upsert_series_from_pandas(conn, name="x", source="FRED:X", series=s)
    assert n == 3
    rows = dbmod.get_series(conn, "x")
    assert len(rows) == 3
    assert {r["source"] for r in rows} == {"FRED:X"}


def test_upsert_series_returns_zero_on_none(conn):
    assert dbmod.upsert_series_from_pandas(conn, name="x", source="s", series=None) == 0
    assert dbmod.get_series(conn, "x") == []


def test_upsert_series_returns_zero_on_empty(conn, monkeypatch):
    pd = pytest.importorskip("pandas")
    s = pd.Series([], dtype=float, name="value")
    assert dbmod.upsert_series_from_pandas(conn, name="x", source="s", series=s) == 0


def test_upsert_series_skips_nan_inf(conn, monkeypatch):
    s = _series(monkeypatch, [
        ("2026-05-13", float("nan")),
        ("2026-05-14", float("inf")),
        ("2026-05-15", 5.0),
    ])
    n = dbmod.upsert_series_from_pandas(conn, name="x", source="s", series=s)
    assert n == 1
    rows = dbmod.get_series(conn, "x")
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-05-15"
    assert rows[0]["value"] == 5.0


def test_upsert_series_idempotent(conn, monkeypatch):
    s1 = _series(monkeypatch, [("2026-05-15", 1.0)])
    dbmod.upsert_series_from_pandas(conn, name="x", source="s", series=s1)
    s2 = _series(monkeypatch, [("2026-05-15", 9.0)])
    dbmod.upsert_series_from_pandas(conn, name="x", source="s", series=s2)
    rows = dbmod.get_series(conn, "x")
    assert len(rows) == 1
    assert rows[0]["value"] == 9.0
