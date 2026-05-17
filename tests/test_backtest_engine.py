"""tests for src/backtest/engine.py 与 src/backtest/registry.py."""
from __future__ import annotations

import csv

import pytest

from src.backtest.engine import _iter_dates, backtest_window, write_csv
from src.backtest.registry import (
    BACKTEST_INDICATORS,
    backtest_only_indicators,
    main_only_indicators,
)
from src.store import history_db as hdbmod


# ── _iter_dates ──────────────────────────────────────────────

def test_iter_dates_simple():
    out = _iter_dates("2024-01-01", "2024-01-03")
    assert out == ["2024-01-01", "2024-01-02", "2024-01-03"]


def test_iter_dates_step():
    out = _iter_dates("2024-01-01", "2024-01-10", step_days=3)
    assert out == ["2024-01-01", "2024-01-04", "2024-01-07", "2024-01-10"]


def test_iter_dates_reverse_returns_empty():
    assert _iter_dates("2024-01-10", "2024-01-01") == []


# ── BACKTEST_INDICATORS ──────────────────────────────────────

def test_backtest_registry_includes_main():
    """主流程 19 条都应在 BACKTEST_INDICATORS。"""
    names = {ind["name"] for ind in BACKTEST_INDICATORS}
    assert "vix" in names
    assert "yield_curve_10y2y" in names
    assert "walcl" in names
    assert "china_fx_reserves" in names


def test_backtest_registry_extras_present():
    names = {ind["name"] for ind in BACKTEST_INDICATORS}
    assert "vix_fred" in names
    assert "ted_spread" in names


def test_main_only_excludes_backtest():
    main = main_only_indicators()
    names = {ind["name"] for ind in main}
    assert "vix" in names
    assert "vix_fred" not in names
    assert "ted_spread" not in names


def test_backtest_only_subset():
    extras = backtest_only_indicators()
    names = {ind["name"] for ind in extras}
    assert names == {"vix_fred", "ted_spread"}


def test_vix_fred_thresholds_reuse_main():
    """vix_fred 阈值应等于主 VIX。"""
    vf = next(i for i in BACKTEST_INDICATORS if i["name"] == "vix_fred")
    assert vf["threshold_low"] == 20.0
    assert vf["threshold_high"] == 30.0


def test_ted_spread_thresholds():
    ts = next(i for i in BACKTEST_INDICATORS if i["name"] == "ted_spread")
    assert ts["threshold_low"] == 0.50
    assert ts["threshold_high"] == 1.00
    assert ts["direction"] == "up"


# ── backtest_window e2e ──────────────────────────────────────

@pytest.fixture()
def hist_path(tmp_path):
    p = tmp_path / "h.sqlite"
    with hdbmod.open_history_db(p) as c:
        # 简化：只准备 vix 几天数据
        hdbmod.upsert_point(c, "vix", "2024-01-01", 18.0, "YF:^VIX")
        hdbmod.upsert_point(c, "vix", "2024-01-02", 22.0, "YF:^VIX")
        hdbmod.upsert_point(c, "vix", "2024-01-03", 35.0, "YF:^VIX")
    return p


def _minimal_registry():
    """只含 vix 的最小 registry，用于测试。"""
    from src.compute.indicators import vix as vix_ind
    return [{
        "name": vix_ind.NAME,
        "label": "VIX",
        "classify": vix_ind.classify_value,
        "group": "波动率",
        "threshold_low": vix_ind.THRESHOLD_LOW,
        "threshold_high": vix_ind.THRESHOLD_HIGH,
        "direction": vix_ind.DIRECTION,
    }]


def test_backtest_window_runs(hist_path):
    out = backtest_window(
        "2024-01-01", "2024-01-03",
        registry=_minimal_registry(),
        history_db_path=hist_path,
    )
    assert len(out) == 3
    assert out[0]["date"] == "2024-01-01"
    assert out[0]["level"] == "GREEN"  # 18 < 20
    assert out[1]["level"] == "YELLOW"  # 22 在 20-30
    assert out[2]["level"] == "RED"  # 35 > 30


def test_backtest_window_step(hist_path):
    out = backtest_window(
        "2024-01-01", "2024-01-03",
        registry=_minimal_registry(),
        history_db_path=hist_path,
        step_days=2,
    )
    # step=2 → [01, 03]
    assert len(out) == 2


def test_backtest_window_empty_dates(hist_path):
    out = backtest_window(
        "2024-01-10", "2024-01-01",
        registry=_minimal_registry(),
        history_db_path=hist_path,
    )
    assert out == []


# ── write_csv ────────────────────────────────────────────────

def test_write_csv_creates_file(tmp_path, hist_path):
    out = backtest_window(
        "2024-01-01", "2024-01-03",
        registry=_minimal_registry(),
        history_db_path=hist_path,
    )
    csv_path = tmp_path / "result.csv"
    write_csv(out, csv_path, registry=_minimal_registry())
    assert csv_path.exists()

    with csv_path.open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3
    assert rows[0]["date"] == "2024-01-01"
    assert rows[2]["level"] == "RED"
    assert rows[0]["vix"] == "18.0"


def test_write_csv_creates_parent(tmp_path, hist_path):
    out = backtest_window(
        "2024-01-01", "2024-01-01",
        registry=_minimal_registry(),
        history_db_path=hist_path,
    )
    csv_path = tmp_path / "subdir" / "nested" / "out.csv"
    write_csv(out, csv_path, registry=_minimal_registry())
    assert csv_path.exists()
