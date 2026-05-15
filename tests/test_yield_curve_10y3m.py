"""yield_curve_10y3m 指标测试：mock fred_client，覆盖分类 + fetch+store 全流程。

阈值 A 案（与 10Y-2Y 同口径）：
  GREEN  ≥ 0.5
  YELLOW 0.0 ≤ v < 0.5
  RED    v < 0
"""
from __future__ import annotations

import pytest

from src.compute.indicators import yield_curve_10y3m as ycmod
from src.compute.thresholds import Level
from src.store import db as dbmod


# ── classify_value ───────────────────────────────────────────
def test_classify_above_high_is_green():
    assert ycmod.classify_value(1.50) == Level.GREEN


def test_classify_at_high_is_green():
    assert ycmod.classify_value(0.5) == Level.GREEN


def test_classify_mid_is_yellow():
    assert ycmod.classify_value(0.20) == Level.YELLOW


def test_classify_at_low_is_yellow():
    assert ycmod.classify_value(0.0) == Level.YELLOW


def test_classify_below_low_is_red():
    assert ycmod.classify_value(-0.50) == Level.RED


# ── fetch_and_store ──────────────────────────────────────────
@pytest.fixture()
def conn(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as c:
        yield c


def _mock_series(monkeypatch, dates_values):
    pd = pytest.importorskip("pandas")
    idx = pd.to_datetime([d for d, _ in dates_values])
    vals = [v for _, v in dates_values]
    s = pd.Series(vals, index=idx, name="value")

    def fake_fetch_series(series_id, start, end=None, settings=None):
        assert series_id == "T10Y3M"
        return s

    monkeypatch.setattr(ycmod.fred_client, "fetch_series", fake_fetch_series)


def test_fetch_and_store_writes_rows(conn, monkeypatch):
    _mock_series(monkeypatch, [
        ("2026-05-13", 1.20),
        ("2026-05-14", 0.30),
        ("2026-05-15", -0.05),
    ])
    n = ycmod.fetch_and_store(conn, start="2026-05-13")
    assert n == 3

    rows = dbmod.get_series(conn, "yield_curve_10y3m")
    assert len(rows) == 3
    by_date = {r["date"]: r for r in rows}
    assert by_date["2026-05-13"]["value"] == pytest.approx(1.20)
    assert by_date["2026-05-15"]["value"] == pytest.approx(-0.05)
    assert by_date["2026-05-15"]["source"] == "FRED:T10Y3M"


def test_fetch_and_store_returns_zero_on_empty(conn, monkeypatch):
    monkeypatch.setattr(
        ycmod.fred_client, "fetch_series",
        lambda series_id, start, end=None, settings=None: None,
    )
    n = ycmod.fetch_and_store(conn, start="2026-05-13")
    assert n == 0
    assert dbmod.get_series(conn, "yield_curve_10y3m") == []


def test_fetch_and_store_is_idempotent(conn, monkeypatch):
    _mock_series(monkeypatch, [("2026-05-15", 0.40)])
    ycmod.fetch_and_store(conn, start="2026-05-15")
    _mock_series(monkeypatch, [("2026-05-15", 0.65)])
    ycmod.fetch_and_store(conn, start="2026-05-15")

    rows = dbmod.get_series(conn, "yield_curve_10y3m")
    assert len(rows) == 1
    assert rows[0]["value"] == pytest.approx(0.65)


def test_fetch_and_store_skips_nan(conn, monkeypatch):
    pd = pytest.importorskip("pandas")
    idx = pd.to_datetime(["2026-05-14", "2026-05-15"])
    s = pd.Series([float("nan"), 0.85], index=idx, name="value")

    monkeypatch.setattr(
        ycmod.fred_client, "fetch_series",
        lambda series_id, start, end=None, settings=None: s,
    )
    n = ycmod.fetch_and_store(conn, start="2026-05-14")
    rows = dbmod.get_series(conn, "yield_curve_10y3m")
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-05-15"
    assert rows[0]["value"] == pytest.approx(0.85)
    assert n == 1
