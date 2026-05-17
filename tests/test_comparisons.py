"""tests for src/web/comparisons.py — 同环比对比纯函数。"""
from __future__ import annotations

from datetime import date

import pytest

from src.web.comparisons import (
    _nearest_value_on_or_before,
    _parse_iso,
    build_comparisons,
    lookback_summary,
)


# ── helpers ───────────────────────────────────────────────────

def test_parse_iso_normal():
    assert _parse_iso("2024-05-15") == date(2024, 5, 15)


def test_parse_iso_with_time_suffix():
    """容许 YYYY-MM-DDTHH... 截前 10 字符。"""
    assert _parse_iso("2024-05-15T12:00:00Z") == date(2024, 5, 15)


def test_parse_iso_invalid():
    assert _parse_iso("not-a-date") is None
    assert _parse_iso("") is None


def test_parse_iso_none():
    assert _parse_iso(None) is None  # type: ignore[arg-type]


# ── _nearest_value_on_or_before ──────────────────────────────

def test_nearest_exact_match():
    h = {"2024-01-01": 1.0, "2024-01-08": 8.0, "2024-01-15": 15.0}
    assert _nearest_value_on_or_before(h, date(2024, 1, 8)) == 8.0


def test_nearest_falls_back_to_earlier():
    """目标日期不存在 → 取最近一个 ≤ target。"""
    h = {"2024-01-01": 1.0, "2024-01-08": 8.0, "2024-01-15": 15.0}
    assert _nearest_value_on_or_before(h, date(2024, 1, 10)) == 8.0


def test_nearest_no_data_before_target():
    h = {"2024-01-15": 15.0}
    assert _nearest_value_on_or_before(h, date(2024, 1, 1)) is None


def test_nearest_skips_nan():
    h = {"2024-01-01": 1.0, "2024-01-05": float("nan"), "2024-01-08": 8.0}
    # target=2024-01-06 → 跳过 nan → 用 2024-01-01 的 1.0
    out = _nearest_value_on_or_before(h, date(2024, 1, 6))
    assert out == 1.0


def test_nearest_empty():
    assert _nearest_value_on_or_before({}, date(2024, 1, 1)) is None


# ── lookback_summary ─────────────────────────────────────────

def test_lookback_basic_up_deteriorates_when_rises():
    """up 方向 + 值上升 = 恶化。"""
    h = {"2024-01-01": 10.0, "2024-01-08": 12.0}
    out = lookback_summary(
        history=h, today_value=12.0, today_date=date(2024, 1, 8),
        lookback_days=7, direction="up",
    )
    assert out["lookback_value"] == 10.0
    assert out["abs_change"] == pytest.approx(2.0)
    assert out["pct_change"] == pytest.approx(20.0)
    assert out["deteriorate"] is True


def test_lookback_basic_up_improves_when_falls():
    h = {"2024-01-01": 12.0, "2024-01-08": 10.0}
    out = lookback_summary(
        history=h, today_value=10.0, today_date=date(2024, 1, 8),
        lookback_days=7, direction="up",
    )
    assert out["pct_change"] == pytest.approx(-100.0 / 12.0 * 2)  # -16.67%
    assert out["deteriorate"] is False


def test_lookback_down_direction():
    """down 方向（如收益率曲线）：值下降 = 恶化。"""
    h = {"2024-01-01": 0.5, "2024-01-08": -0.1}
    out = lookback_summary(
        history=h, today_value=-0.1, today_date=date(2024, 1, 8),
        lookback_days=7, direction="down",
    )
    assert out["abs_change"] < 0
    assert out["deteriorate"] is True


def test_lookback_no_today_value():
    out = lookback_summary(
        history={"2024-01-01": 10.0}, today_value=None,
        today_date=date(2024, 1, 8), lookback_days=7,
    )
    assert out == {
        "lookback_value": None,
        "pct_change": None,
        "abs_change": None,
        "deteriorate": None,
    }


def test_lookback_no_history_at_target():
    """history 空 / 目标日期之前没数据。"""
    h = {"2024-01-08": 10.0}
    out = lookback_summary(
        history=h, today_value=10.0, today_date=date(2024, 1, 8),
        lookback_days=7, direction="up",
    )
    assert out["lookback_value"] is None


def test_lookback_zero_past_value():
    """past=0 时百分比无意义，应返 None。"""
    h = {"2024-01-01": 0.0, "2024-01-08": 5.0}
    out = lookback_summary(
        history=h, today_value=5.0, today_date=date(2024, 1, 8),
        lookback_days=7, direction="up",
    )
    assert out["pct_change"] is None
    assert out["abs_change"] == 5.0


def test_lookback_today_date_falls_back_to_history_max():
    """today_date=None 时用 history 最大 key 当今天。"""
    h = {"2024-01-01": 10.0, "2024-01-08": 12.0}
    out = lookback_summary(
        history=h, today_value=12.0, today_date=None,
        lookback_days=7, direction="up",
    )
    assert out["lookback_value"] == 10.0


def test_lookback_today_value_nan():
    h = {"2024-01-01": 10.0}
    out = lookback_summary(
        history=h, today_value=float("nan"), today_date=date(2024, 1, 8),
        lookback_days=7,
    )
    assert out["lookback_value"] is None


def test_lookback_today_value_non_numeric():
    h = {"2024-01-01": 10.0}
    out = lookback_summary(
        history=h, today_value="abc", today_date=date(2024, 1, 8),  # type: ignore[arg-type]
        lookback_days=7,
    )
    assert out["lookback_value"] is None


def test_lookback_persists_when_equal():
    h = {"2024-01-01": 10.0}
    out = lookback_summary(
        history=h, today_value=10.0, today_date=date(2024, 1, 8),
        lookback_days=7, direction="up",
    )
    assert out["pct_change"] == pytest.approx(0.0)
    assert out["deteriorate"] is False


# ── build_comparisons ─────────────────────────────────────────

def test_build_comparisons_multi_lookback():
    dates = ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01"]
    values = [10.0, 11.0, 12.0, 14.0]
    out = build_comparisons(
        dates=dates, values=values,
        today_value=14.0, today_date=date(2024, 4, 1),
        direction="up",
        lookbacks=(7, 30, 90),
    )
    assert set(out.keys()) == {7, 30, 90}
    # 90 天前 ~2024-01-02 → 取 2024-01-01 = 10.0
    assert out[90]["lookback_value"] == 10.0
    assert out[90]["pct_change"] == pytest.approx(40.0)
    assert out[90]["deteriorate"] is True


def test_build_comparisons_length_mismatch_raises():
    with pytest.raises(ValueError):
        build_comparisons(
            dates=["2024-01-01"], values=[1.0, 2.0],
            today_value=2.0, today_date=None,
        )


def test_build_comparisons_empty_history():
    out = build_comparisons(
        dates=[], values=[],
        today_value=10.0, today_date=date(2024, 1, 1),
    )
    for d in (7, 30, 90):
        assert out[d]["lookback_value"] is None
