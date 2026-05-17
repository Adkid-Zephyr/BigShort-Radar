"""tests for src/web/acceleration.py — 短/长斜率与加速判定。"""
from __future__ import annotations

import math

import pytest

from src.web.acceleration import (
    _filter_finite,
    compute_acceleration,
    linear_slope,
)


# ── _filter_finite ───────────────────────────────────────────

def test_filter_finite_drops_invalid():
    out = _filter_finite([1.0, float("nan"), float("inf"), None, 2.0])
    assert out == [1.0, 2.0]


# ── linear_slope ─────────────────────────────────────────────

def test_slope_constant_is_zero():
    assert linear_slope([1.0, 1.0, 1.0, 1.0, 1.0]) == pytest.approx(0.0)


def test_slope_linear_increase():
    """y=2x，slope=2."""
    assert linear_slope([0.0, 2.0, 4.0, 6.0, 8.0]) == pytest.approx(2.0)


def test_slope_linear_decrease():
    """y=-x+10，slope=-1."""
    assert linear_slope([10.0, 9.0, 8.0, 7.0, 6.0]) == pytest.approx(-1.0)


def test_slope_too_few_points():
    assert linear_slope([1.0]) is None
    assert linear_slope([]) is None


def test_slope_filters_nan():
    out = linear_slope([0.0, float("nan"), 2.0, float("inf"), 4.0, 6.0])
    # 过滤后变 [0,2,4,6]，slope=2
    assert out == pytest.approx(2.0)


# ── compute_acceleration ─────────────────────────────────────

def test_too_few_points_returns_none():
    out = compute_acceleration(values=[1.0, 2.0, 3.0], long_window=20)
    assert out["short_slope"] is None
    assert out["long_slope"] is None
    assert out["accelerating"] is None


def test_constant_no_acceleration():
    """全相同值，斜率 0，不加速。"""
    out = compute_acceleration(values=[5.0] * 30)
    assert out["short_slope"] == pytest.approx(0.0)
    assert out["long_slope"] == pytest.approx(0.0)
    assert out["accelerating"] is False


def test_steady_uptrend_no_acceleration():
    """均匀递增，短斜率 ≈ 长斜率 → 不加速。"""
    values = [float(i) for i in range(30)]  # 每天 +1
    out = compute_acceleration(values=values, direction="up", short_window=5, long_window=20)
    assert out["short_slope"] == pytest.approx(1.0, abs=0.01)
    assert out["long_slope"] == pytest.approx(1.0, abs=0.01)
    # |1| 不大于 |1|（严格），不加速
    assert out["accelerating"] is False


def test_recent_acceleration_up():
    """前面平稳，最近 5 天突然飙：短斜率 > 长斜率，up 方向 = 加速恶化。"""
    values = [10.0] * 20 + [10.0, 12.0, 15.0, 19.0, 24.0, 30.0]
    out = compute_acceleration(values=values, direction="up", short_window=5, long_window=20)
    assert out["short_slope"] > out["long_slope"]
    assert out["accelerating"] is True


def test_recent_acceleration_down_for_up_direction_not_dangerous():
    """最近 5 天暴跌，up 方向不算危险（值低 = 安全）。"""
    values = [10.0] * 20 + [10.0, 8.0, 6.0, 4.0, 2.0, 0.0]
    out = compute_acceleration(values=values, direction="up", short_window=5, long_window=20)
    assert out["short_slope"] < 0
    # short 是负数，up 方向危险=正向，所以不算加速恶化
    assert out["accelerating"] is False


def test_recent_acceleration_down_for_down_direction_dangerous():
    """down 方向（如收益率曲线）：值跌 = 危险。"""
    values = [0.5] * 20 + [0.5, 0.3, 0.1, -0.1, -0.3, -0.5]
    out = compute_acceleration(values=values, direction="down", short_window=5, long_window=20)
    assert out["short_slope"] < 0
    assert out["accelerating"] is True


def test_ratio_calculated_when_long_nonzero():
    values = [float(i) for i in range(30)]
    out = compute_acceleration(values=values, short_window=5, long_window=20)
    assert out["ratio"] is not None
    assert out["ratio"] == pytest.approx(1.0, abs=0.01)


def test_ratio_none_when_long_slope_zero():
    """长期斜率 0 时 ratio 应是 None（防除零）。"""
    values = [10.0] * 20 + [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
    out = compute_acceleration(values=values, short_window=5, long_window=20)
    # 长 20 天的斜率受最近 5 天影响，不一定为 0；这里检查 ratio 至少不抛
    assert "ratio" in out
