"""hy_oas 指标测试：mock fred_client，覆盖分类 + fetch+store 全流程。

阈值（up 方向，DECISIONS.md 2026-05-15 ADR）：
  GREEN  v ≤ 4
  YELLOW 4 < v ≤ 8
  RED    v > 8
"""
from __future__ import annotations

import pytest

from src.compute.indicators import hy_oas as hymod
from src.compute.thresholds import Level
from src.store import db as dbmod


# ── classify_value ───────────────────────────────────────────
def test_classify_below_low_is_green():
    assert hymod.classify_value(3.2) == Level.GREEN


def test_classify_at_low_is_green():
    # up 方向 value == low → GREEN
    assert hymod.classify_value(4.0) == Level.GREEN


def test_classify_mid_is_yellow():
    assert hymod.classify_value(6.0) == Level.YELLOW


def test_classify_at_high_is_yellow():
    # up 方向 value == high → YELLOW
    assert hymod.classify_value(8.0) == Level.YELLOW


def test_classify_above_high_is_red():
    assert hymod.classify_value(11.5) == Level.RED  # 2020 春级别


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
        assert series_id == "BAMLH0A0HYM2"
        return s

    monkeypatch.setattr(hymod.fred_client, "fetch_series", fake_fetch_series)


def test_fetch_and_store_writes_rows(conn, monkeypatch):
    _mock_series(monkeypatch, [
        ("2026-05-13", 3.5),
        ("2026-05-14", 6.0),
        ("2026-05-15", 9.2),
    ])
    n = hymod.fetch_and_store(conn, start="2026-05-13")
    assert n == 3

    rows = dbmod.get_series(conn, "hy_oas")
    assert len(rows) == 3
    by_date = {r["date"]: r for r in rows}
    assert by_date["2026-05-13"]["value"] == pytest.approx(3.5)
    assert by_date["2026-05-15"]["value"] == pytest.approx(9.2)
    assert by_date["2026-05-15"]["source"] == "FRED:BAMLH0A0HYM2"


def test_fetch_and_store_returns_zero_on_empty(conn, monkeypatch):
    monkeypatch.setattr(
        hymod.fred_client, "fetch_series",
        lambda series_id, start, end=None, settings=None: None,
    )
    n = hymod.fetch_and_store(conn, start="2026-05-13")
    assert n == 0
    assert dbmod.get_series(conn, "hy_oas") == []


def test_fetch_and_store_is_idempotent(conn, monkeypatch):
    _mock_series(monkeypatch, [("2026-05-15", 5.0)])
    hymod.fetch_and_store(conn, start="2026-05-15")
    _mock_series(monkeypatch, [("2026-05-15", 7.5)])
    hymod.fetch_and_store(conn, start="2026-05-15")

    rows = dbmod.get_series(conn, "hy_oas")
    assert len(rows) == 1
    assert rows[0]["value"] == pytest.approx(7.5)


def test_fetch_and_store_skips_nan(conn, monkeypatch):
    pd = pytest.importorskip("pandas")
    idx = pd.to_datetime(["2026-05-14", "2026-05-15"])
    s = pd.Series([float("nan"), 4.2], index=idx, name="value")

    monkeypatch.setattr(
        hymod.fred_client, "fetch_series",
        lambda series_id, start, end=None, settings=None: s,
    )
    n = hymod.fetch_and_store(conn, start="2026-05-14")
    rows = dbmod.get_series(conn, "hy_oas")
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-05-15"
    assert rows[0]["value"] == pytest.approx(4.2)
    assert n == 1
