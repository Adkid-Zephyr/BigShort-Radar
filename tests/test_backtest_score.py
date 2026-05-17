"""tests for src/backtest/score.py 与 risk_score.score_from_indicator_values."""
from __future__ import annotations

import pytest

from src.backtest.score import (
    _date_minus_days,
    compute_score_for_date,
    fetch_latest_value_on_or_before,
)
from src.compute.risk_score import score_from_indicator_values
from src.compute.thresholds import Level
from src.store import history_db as hdbmod


# ── helpers ──────────────────────────────────────────────────

def test_date_minus_days():
    assert _date_minus_days("2024-01-15", 7) == "2024-01-08"
    assert _date_minus_days("2024-03-01", 1) == "2024-02-29"  # 闰年


# ── score_from_indicator_values（共用 helper）──────────────

def _fake_classify_up(low, high):
    """生成一个 up 方向的 classify 函数。"""
    from src.compute.thresholds import classify
    return lambda v: classify(v, low=low, high=high, direction="up")


def test_score_from_values_normal():
    registry = [
        {"name": "a", "label": "A", "classify": _fake_classify_up(20, 30), "group": "波动率"},
        {"name": "b", "label": "B", "classify": _fake_classify_up(20, 30), "group": "信用"},
    ]
    out = score_from_indicator_values({"a": 25, "b": 35}, registry)
    # a=YELLOW=50, b=RED=100；曲线/信用各占权重
    assert out["score"] > 0
    assert "波动率" in out["breakdown"]
    assert out["missing"] == []


def test_score_from_values_missing():
    registry = [
        {"name": "a", "label": "A", "classify": _fake_classify_up(20, 30), "group": "波动率"},
        {"name": "b", "label": "B", "classify": _fake_classify_up(20, 30), "group": "信用"},
    ]
    out = score_from_indicator_values({"a": 25}, registry)
    assert "b" in out["missing"]


def test_score_from_values_empty():
    out = score_from_indicator_values({}, [])
    assert out["score"] == 0.0
    assert out["level"] == "GREEN"


# ── fetch_latest_value_on_or_before ──────────────────────────

@pytest.fixture()
def hist_conn(tmp_path):
    p = tmp_path / "h.sqlite"
    with hdbmod.open_history_db(p) as c:
        # 写一系列数据
        hdbmod.upsert_point(c, "vix", "2024-01-05", 18.0, "YF:^VIX")
        hdbmod.upsert_point(c, "vix", "2024-01-08", 19.0, "YF:^VIX")
        hdbmod.upsert_point(c, "vix", "2024-01-12", 22.0, "YF:^VIX")
        hdbmod.upsert_point(c, "jp_10y", "2024-01-01", 1.0, "FRED:JP")  # 月值
        yield c


def test_fetch_exact_match(hist_conn):
    """target 当天有数据。"""
    v = fetch_latest_value_on_or_before(hist_conn, "vix", "2024-01-08", forward_fill_days=10)
    assert v == 19.0


def test_fetch_forward_fill(hist_conn):
    """target=01-10 没数据，回看 10 天 → 拿 01-08 的 19.0。"""
    v = fetch_latest_value_on_or_before(hist_conn, "vix", "2024-01-10", forward_fill_days=10)
    assert v == 19.0


def test_fetch_too_old_returns_none(hist_conn):
    """target=01-25，回看 10 天到 01-15，最新一条是 01-12 早于 01-15 → None。"""
    v = fetch_latest_value_on_or_before(hist_conn, "vix", "2024-01-25", forward_fill_days=10)
    assert v is None


def test_fetch_no_data_returns_none(hist_conn):
    v = fetch_latest_value_on_or_before(hist_conn, "nonexistent", "2024-01-08", forward_fill_days=10)
    assert v is None


def test_fetch_monthly_indicator(hist_conn):
    """月值 jp_10y 在 01-01 写一条，target=01-15 + ff=20 应能拿到。"""
    v = fetch_latest_value_on_or_before(hist_conn, "jp_10y", "2024-01-15", forward_fill_days=20)
    assert v == 1.0


# ── compute_score_for_date ───────────────────────────────────

def test_compute_score_for_date_basic(hist_conn):
    registry = [
        {
            "name": "vix", "label": "VIX",
            "classify": _fake_classify_up(20, 30),
            "group": "波动率",
        },
    ]
    out = compute_score_for_date(hist_conn, "2024-01-08", registry)
    assert out["date"] == "2024-01-08"
    # vix=19.0 < 20 → GREEN，score=0
    assert out["score"] == 0.0
    assert out["level"] == "GREEN"


def test_compute_score_for_date_missing(hist_conn):
    """target 在数据范围外，应进 missing。"""
    registry = [
        {
            "name": "vix", "label": "VIX",
            "classify": _fake_classify_up(20, 30),
            "group": "波动率",
        },
    ]
    out = compute_score_for_date(hist_conn, "2024-12-25", registry, forward_fill_days=5)
    assert "vix" in out["missing"]


def test_compute_score_for_date_red(hist_conn):
    registry = [
        {
            "name": "vix", "label": "VIX",
            "classify": _fake_classify_up(20, 30),
            "group": "波动率",
        },
    ]
    # 写一条更高的值
    hdbmod.upsert_point(hist_conn, "vix", "2024-02-01", 50.0, "YF:^VIX")
    out = compute_score_for_date(hist_conn, "2024-02-01", registry)
    assert out["level"] == "RED"
    assert out["score"] == 100.0
