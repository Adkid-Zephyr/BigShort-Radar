"""tests for src/web/zscore.py — z-score 与历史分位。"""
from __future__ import annotations

import math

import pytest

from src.web.zscore import (
    EXTREME_Z_THRESHOLD,
    MIN_POINTS_FOR_ZSCORE,
    _filter_finite,
    compute_zscore,
)


# ── _filter_finite ───────────────────────────────────────────

def test_filter_finite_drops_nan_inf_none():
    out = _filter_finite([1.0, float("nan"), float("inf"), None, 2.0, "abc"])
    assert out == [1.0, 2.0]


def test_filter_finite_empty():
    assert _filter_finite([]) == []


def test_filter_finite_none_input():
    assert _filter_finite(None) == []  # type: ignore[arg-type]


# ── compute_zscore: 不足样本 ────────────────────────────────

def test_zscore_too_few_samples():
    """少于 MIN_POINTS_FOR_ZSCORE 应返 None。"""
    out = compute_zscore(history_values=[1.0] * 10, current_value=1.5)
    assert out["z"] is None
    assert out["percentile"] is None
    assert out["extreme"] is None
    assert out["n"] == 10


def test_zscore_no_current_value():
    out = compute_zscore(history_values=[1.0] * 50, current_value=None)
    assert out["z"] is None


def test_zscore_nan_current():
    out = compute_zscore(history_values=[1.0] * 50, current_value=float("nan"))
    assert out["z"] is None


# ── compute_zscore: 正常 ─────────────────────────────────────

def test_zscore_zero_when_at_mean():
    """全 1，当前 1，z=0 percentile=50%。"""
    out = compute_zscore(history_values=[1.0] * 50, current_value=1.0)
    # std=0 → z 应返 None（避免除零）
    assert out["z"] is None
    assert out["n"] == 50


def test_zscore_normal_distribution():
    """标准化数据 0,1,2,...,99，当前 50 → z=0 (mean=49.5 std=~28.86)."""
    history = list(range(100))
    out = compute_zscore(history_values=history, current_value=49.5)
    assert out["z"] == pytest.approx(0.0, abs=0.01)
    assert 49 <= out["percentile"] <= 51


def test_zscore_extreme_high():
    """对称分布 + 当前值是 +3σ → z>2 极端。"""
    history = list(range(100))
    # 99 是远端
    out = compute_zscore(history_values=history, current_value=110.0, direction="up")
    assert out["z"] > EXTREME_Z_THRESHOLD
    assert out["extreme"] is True
    assert out["percentile"] > 99


def test_zscore_extreme_low_up_direction_not_危险():
    """z<-2 时 up 方向不应标 extreme（极低值对 up 方向不危险）。"""
    history = list(range(100))
    out = compute_zscore(history_values=history, current_value=-100.0, direction="up")
    assert out["z"] < -EXTREME_Z_THRESHOLD
    # extreme 只看危险方向，up 方向 z<<0 不是危险
    assert out["extreme"] is False


def test_zscore_extreme_low_down_direction():
    """down 方向（如收益率曲线）：值低 = 危险。"""
    history = list(range(100))
    out = compute_zscore(history_values=history, current_value=-100.0, direction="down")
    assert out["z"] < -EXTREME_Z_THRESHOLD
    assert out["extreme"] is True


def test_zscore_percentile_at_50_mean():
    history = list(range(100))
    out = compute_zscore(history_values=history, current_value=49.5)
    assert 45 <= out["percentile"] <= 55


def test_zscore_percentile_at_top():
    history = list(range(100))
    out = compute_zscore(history_values=history, current_value=99.0)
    assert out["percentile"] >= 99


def test_zscore_filters_nan_in_history():
    """NaN/Inf 在 history 中应被过滤。"""
    history = [float("nan")] * 30 + list(range(50))
    out = compute_zscore(history_values=history, current_value=24.5)
    # 有效样本 50（足够）
    assert out["n"] == 50
    assert out["z"] is not None


def test_zscore_min_points_threshold():
    """正好 30 个点应能算（边界）。"""
    history = list(range(30))
    out = compute_zscore(history_values=history, current_value=15.0)
    assert out["z"] is not None
    assert out["n"] == 30


def test_zscore_constant_history_zero_std():
    """全相同值 std=0 应返 None 不抛。"""
    history = [5.0] * 50
    out = compute_zscore(history_values=history, current_value=5.0)
    assert out["z"] is None


def test_zscore_unknown_direction():
    """未知 direction 走 abs(z) > 2 的简化判断。"""
    history = list(range(100))
    out = compute_zscore(history_values=history, current_value=110.0, direction="weird")
    assert out["z"] > 2
    assert out["extreme"] is True
