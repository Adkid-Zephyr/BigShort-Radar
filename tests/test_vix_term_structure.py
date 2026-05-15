"""vix_term_structure 测试：mock yf_client 的两次调用，覆盖对齐 + 比值计算 + 入库。"""
from __future__ import annotations

import pytest

from src.compute.indicators import vix_term_structure as vtsmod
from src.compute.thresholds import Level
from src.store import db as dbmod


# ── classify_value ───────────────────────────────────────────
def test_classify_strong_contango_is_green():
    assert vtsmod.classify_value(0.85) == Level.GREEN


def test_classify_at_low_is_green():
    # up 方向 value == low → GREEN
    assert vtsmod.classify_value(0.95) == Level.GREEN


def test_classify_flat_is_yellow():
    assert vtsmod.classify_value(0.98) == Level.YELLOW


def test_classify_at_high_is_yellow():
    assert vtsmod.classify_value(1.0) == Level.YELLOW


def test_classify_backwardation_is_red():
    assert vtsmod.classify_value(1.15) == Level.RED


# ── _compute_ratio ───────────────────────────────────────────
def _series(dates_values, name="x"):
    pd = pytest.importorskip("pandas")
    idx = pd.to_datetime([d for d, _ in dates_values])
    s = pd.Series([v for _, v in dates_values], index=idx, name=name)
    return s


def test_compute_ratio_basic():
    front = _series([("2026-05-13", 18.0), ("2026-05-14", 20.0), ("2026-05-15", 25.0)])
    back = _series([("2026-05-13", 20.0), ("2026-05-14", 22.0), ("2026-05-15", 22.0)])
    r = vtsmod._compute_ratio(front, back)
    assert r is not None
    assert len(r) == 3
    assert pytest.approx(r.iloc[0]) == 0.9
    assert pytest.approx(r.iloc[2]) == 25.0 / 22.0


def test_compute_ratio_intersect_only():
    # 只有 5/14 重叠
    front = _series([("2026-05-13", 18.0), ("2026-05-14", 20.0)])
    back = _series([("2026-05-14", 22.0), ("2026-05-15", 23.0)])
    r = vtsmod._compute_ratio(front, back)
    assert len(r) == 1
    assert pytest.approx(r.iloc[0]) == 20.0 / 22.0


def test_compute_ratio_returns_none_on_no_overlap():
    front = _series([("2026-05-13", 18.0)])
    back = _series([("2026-05-14", 20.0)])
    assert vtsmod._compute_ratio(front, back) is None


def test_compute_ratio_returns_none_on_none_input():
    assert vtsmod._compute_ratio(None, _series([("2026-05-13", 1.0)])) is None
    assert vtsmod._compute_ratio(_series([("2026-05-13", 1.0)]), None) is None


def test_compute_ratio_filters_zero_back():
    front = _series([("2026-05-14", 20.0), ("2026-05-15", 22.0)])
    back = _series([("2026-05-14", 0.0), ("2026-05-15", 22.0)])
    r = vtsmod._compute_ratio(front, back)
    assert len(r) == 1


# ── fetch_and_store ──────────────────────────────────────────
@pytest.fixture()
def conn(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as c:
        yield c


def test_fetch_and_store_writes_ratio_rows(conn, monkeypatch):
    front = _series([("2026-05-13", 18.0), ("2026-05-14", 21.0)])
    back = _series([("2026-05-13", 20.0), ("2026-05-14", 21.0)])

    def fake_fetch_close(ticker, start, end=None):
        return {"^VIX": front, "^VIX3M": back}[ticker]

    monkeypatch.setattr(vtsmod.yf_client, "fetch_close", fake_fetch_close)
    n = vtsmod.fetch_and_store(conn, start="2026-05-13")
    assert n == 2
    rows = dbmod.get_series(conn, "vix_term_structure")
    assert len(rows) == 2
    assert pytest.approx(rows[0]["value"]) == 0.9
    assert pytest.approx(rows[1]["value"]) == 1.0
    assert rows[0]["source"] == "YF:^VIX/^VIX3M"


def test_fetch_and_store_returns_zero_when_either_fail(conn, monkeypatch):
    def fake_fetch_close(ticker, start, end=None):
        return None  # 模拟 ^VIX3M 拉不到

    monkeypatch.setattr(vtsmod.yf_client, "fetch_close", fake_fetch_close)
    n = vtsmod.fetch_and_store(conn, start="2026-05-13")
    assert n == 0
    assert dbmod.get_series(conn, "vix_term_structure") == []
