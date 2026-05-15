"""sofr_iorb 测试：mock fred_client 两次调用，覆盖对齐 + bp 转换 + 入库。"""
from __future__ import annotations

import pytest

from src.compute.indicators import sofr_iorb as smod
from src.compute.thresholds import Level
from src.store import db as dbmod


# ── classify_value ───────────────────────────────────────────
def test_classify_below_low_is_green():
    assert smod.classify_value(2.0) == Level.GREEN


def test_classify_at_low_is_green():
    assert smod.classify_value(5.0) == Level.GREEN


def test_classify_mid_is_yellow():
    assert smod.classify_value(10.0) == Level.YELLOW


def test_classify_at_high_is_yellow():
    assert smod.classify_value(15.0) == Level.YELLOW


def test_classify_above_high_is_red():
    assert smod.classify_value(50.0) == Level.RED  # 远低于 2019 回购危机的 300bp 但仍 RED


# ── _compute_spread_bp ───────────────────────────────────────
def _series(dates_values, name="x"):
    pd = pytest.importorskip("pandas")
    idx = pd.to_datetime([d for d, _ in dates_values])
    return pd.Series([v for _, v in dates_values], index=idx, name=name)


def test_compute_spread_basic_bp_conversion():
    # SOFR / IORB 都是 %，差 0.05% = 5bp
    sofr = _series([("2026-05-13", 5.30), ("2026-05-14", 5.40)])
    iorb = _series([("2026-05-13", 5.25), ("2026-05-14", 5.25)])
    sp = smod._compute_spread_bp(sofr, iorb)
    assert pytest.approx(sp.iloc[0]) == 5.0   # 0.05% × 100 = 5bp
    assert pytest.approx(sp.iloc[1]) == 15.0


def test_compute_spread_uses_abs():
    # SOFR 低于 IORB 也是异常
    sofr = _series([("2026-05-13", 5.20)])
    iorb = _series([("2026-05-13", 5.25)])
    sp = smod._compute_spread_bp(sofr, iorb)
    assert pytest.approx(sp.iloc[0]) == 5.0  # |5.20 - 5.25| = 0.05% = 5bp


def test_compute_spread_intersect_only():
    sofr = _series([("2026-05-13", 5.30), ("2026-05-14", 5.40)])
    iorb = _series([("2026-05-14", 5.25), ("2026-05-15", 5.25)])
    sp = smod._compute_spread_bp(sofr, iorb)
    assert len(sp) == 1


def test_compute_spread_returns_none_on_no_overlap():
    sofr = _series([("2026-05-13", 5.30)])
    iorb = _series([("2026-05-14", 5.25)])
    assert smod._compute_spread_bp(sofr, iorb) is None


def test_compute_spread_returns_none_on_none():
    assert smod._compute_spread_bp(None, _series([("2026-05-13", 5.0)])) is None
    assert smod._compute_spread_bp(_series([("2026-05-13", 5.0)]), None) is None


# ── fetch_and_store ──────────────────────────────────────────
@pytest.fixture()
def conn(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as c:
        yield c


def test_fetch_and_store_writes_bp_rows(conn, monkeypatch):
    sofr = _series([("2026-05-13", 5.30), ("2026-05-14", 5.45)])
    iorb = _series([("2026-05-13", 5.25), ("2026-05-14", 5.25)])

    def fake_fetch_series(series_id, start, end=None, settings=None):
        return {"SOFR": sofr, "IORB": iorb}[series_id]

    monkeypatch.setattr(smod.fred_client, "fetch_series", fake_fetch_series)
    n = smod.fetch_and_store(conn, start="2026-05-13")
    assert n == 2
    rows = dbmod.get_series(conn, "sofr_iorb")
    assert pytest.approx(rows[0]["value"]) == 5.0
    assert pytest.approx(rows[1]["value"]) == 20.0
    assert rows[0]["source"] == "FRED:SOFR-IORB"


def test_fetch_and_store_returns_zero_when_either_fail(conn, monkeypatch):
    monkeypatch.setattr(
        smod.fred_client, "fetch_series",
        lambda series_id, start, end=None, settings=None: None,
    )
    n = smod.fetch_and_store(conn, start="2026-05-13")
    assert n == 0
