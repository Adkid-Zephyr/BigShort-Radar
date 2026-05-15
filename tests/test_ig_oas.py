"""ig_oas 指标测试：mock fred_client，覆盖分类 + fetch+store 全流程。

阈值（up 方向，DECISIONS.md 2026-05-15 ADR）：
  GREEN  v ≤ 1.5
  YELLOW 1.5 < v ≤ 3
  RED    v > 3
"""
from __future__ import annotations

import pytest

from src.compute.indicators import ig_oas as igmod
from src.compute.thresholds import Level
from src.store import db as dbmod


# ── classify_value ───────────────────────────────────────────
def test_classify_below_low_is_green():
    assert igmod.classify_value(1.0) == Level.GREEN


def test_classify_at_low_is_green():
    assert igmod.classify_value(1.5) == Level.GREEN


def test_classify_mid_is_yellow():
    assert igmod.classify_value(2.2) == Level.YELLOW


def test_classify_at_high_is_yellow():
    assert igmod.classify_value(3.0) == Level.YELLOW


def test_classify_above_high_is_red():
    assert igmod.classify_value(4.0) == Level.RED  # 2020 春级别


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
        assert series_id == "BAMLC0A0CM"
        return s

    monkeypatch.setattr(igmod.fred_client, "fetch_series", fake_fetch_series)


def test_fetch_and_store_writes_rows(conn, monkeypatch):
    _mock_series(monkeypatch, [
        ("2026-05-13", 1.2),
        ("2026-05-14", 2.5),
        ("2026-05-15", 3.5),
    ])
    n = igmod.fetch_and_store(conn, start="2026-05-13")
    assert n == 3

    rows = dbmod.get_series(conn, "ig_oas")
    assert len(rows) == 3
    by_date = {r["date"]: r for r in rows}
    assert by_date["2026-05-13"]["value"] == pytest.approx(1.2)
    assert by_date["2026-05-15"]["value"] == pytest.approx(3.5)
    assert by_date["2026-05-15"]["source"] == "FRED:BAMLC0A0CM"


def test_fetch_and_store_returns_zero_on_empty(conn, monkeypatch):
    monkeypatch.setattr(
        igmod.fred_client, "fetch_series",
        lambda series_id, start, end=None, settings=None: None,
    )
    n = igmod.fetch_and_store(conn, start="2026-05-13")
    assert n == 0
    assert dbmod.get_series(conn, "ig_oas") == []


def test_fetch_and_store_is_idempotent(conn, monkeypatch):
    _mock_series(monkeypatch, [("2026-05-15", 1.8)])
    igmod.fetch_and_store(conn, start="2026-05-15")
    _mock_series(monkeypatch, [("2026-05-15", 2.4)])
    igmod.fetch_and_store(conn, start="2026-05-15")

    rows = dbmod.get_series(conn, "ig_oas")
    assert len(rows) == 1
    assert rows[0]["value"] == pytest.approx(2.4)


def test_fetch_and_store_skips_nan(conn, monkeypatch):
    pd = pytest.importorskip("pandas")
    idx = pd.to_datetime(["2026-05-14", "2026-05-15"])
    s = pd.Series([float("nan"), 1.3], index=idx, name="value")

    monkeypatch.setattr(
        igmod.fred_client, "fetch_series",
        lambda series_id, start, end=None, settings=None: s,
    )
    n = igmod.fetch_and_store(conn, start="2026-05-14")
    rows = dbmod.get_series(conn, "ig_oas")
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-05-15"
    assert rows[0]["value"] == pytest.approx(1.3)
    assert n == 1
