"""tests for src/web/sparkline.py — SVG 渲染纯函数。"""
from __future__ import annotations

import math
import re

import pytest

from src.web.sparkline import (
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    MIN_POINTS,
    _is_finite,
    build_sparkline_svg,
)


# ── _is_finite ────────────────────────────────────────────────

def test_is_finite_normal():
    assert _is_finite(0.0)
    assert _is_finite(-3.5)
    assert _is_finite(100)


def test_is_finite_rejects_none():
    assert not _is_finite(None)


def test_is_finite_rejects_nan():
    assert not _is_finite(float("nan"))


def test_is_finite_rejects_inf():
    assert not _is_finite(float("inf"))
    assert not _is_finite(float("-inf"))


def test_is_finite_rejects_non_numeric():
    assert not _is_finite("abc")
    assert not _is_finite([1, 2])


# ── 占位（数据不足）─────────────────────────────────────────

def test_empty_values_returns_placeholder():
    out = build_sparkline_svg([])
    assert "积累中" in out
    assert "0/10" in out
    assert "<svg" in out
    assert "</svg>" in out


def test_few_values_returns_placeholder():
    out = build_sparkline_svg([1.0, 2.0, 3.0])
    assert "积累中" in out
    assert "3/10" in out


def test_all_nan_returns_placeholder():
    """全 NaN 过滤后 0 点，应出占位。"""
    nan = float("nan")
    out = build_sparkline_svg([nan] * 20)
    assert "积累中" in out


def test_min_points_param_respected():
    """自定义 min_points=5 时，5 个值足够。"""
    out = build_sparkline_svg([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], min_points=5)
    assert "积累中" not in out
    assert "<path" in out


# ── 正常折线 ─────────────────────────────────────────────────

def test_normal_series_generates_path():
    values = list(range(15))  # 0..14，单调递增
    out = build_sparkline_svg(values, threshold_low=5.0, threshold_high=10.0, direction="up")
    assert "<svg" in out
    assert "<path" in out
    # 末点高亮 circle
    assert "<circle" in out
    # 三档背景带（up 方向）
    assert out.count("<rect") == 3


def test_default_dimensions():
    values = list(range(15))
    out = build_sparkline_svg(values)
    assert f'width="{DEFAULT_WIDTH}"' in out
    assert f'height="{DEFAULT_HEIGHT}"' in out


def test_custom_dimensions():
    values = list(range(15))
    out = build_sparkline_svg(values, width=200, height=40)
    assert 'width="200"' in out
    assert 'height="40"' in out


def test_path_starts_with_M():
    values = list(range(15))
    out = build_sparkline_svg(values, threshold_low=5.0, threshold_high=10.0)
    # 折线第一个点用 M 命令
    m = re.search(r'd="M[\d.]+,[\d.]+', out)
    assert m is not None


def test_no_threshold_no_bands():
    """阈值 None 不画背景带（rect）。"""
    values = list(range(15))
    out = build_sparkline_svg(values)
    assert out.count("<rect") == 0


def test_partial_threshold_no_bands():
    """只给 low 不给 high，也不画带（要齐全才画）。"""
    values = list(range(15))
    out = build_sparkline_svg(values, threshold_low=5.0)
    assert out.count("<rect") == 0


# ── 方向决定颜色顺序 ────────────────────────────────────────

def test_up_direction_red_on_top():
    """up 方向，值大=危险=RED 在顶部（小 y）。"""
    values = list(range(15))
    out = build_sparkline_svg(values, threshold_low=5.0, threshold_high=10.0, direction="up")
    # 第一个 rect（顶部）应该是 RED 色
    first_rect = re.search(r'<rect[^>]*fill="([^"]+)"', out)
    assert first_rect is not None
    assert "239,68,68" in first_rect.group(1)  # RED rgba


def test_down_direction_green_on_top():
    """down 方向（如收益率曲线倒挂），值大=安全=GREEN 在顶部。"""
    values = [3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0, -0.5, -1.0, -1.5, -2.0]
    out = build_sparkline_svg(values, threshold_low=0.0, threshold_high=0.5, direction="down")
    first_rect = re.search(r'<rect[^>]*fill="([^"]+)"', out)
    assert first_rect is not None
    assert "34,197,94" in first_rect.group(1)  # GREEN rgba


# ── 鲁棒性 ────────────────────────────────────────────────────

def test_filters_nan_inf_keeps_valid():
    """混入 NaN/Inf 应被滤掉，只用合法点画线。"""
    values = [1.0, float("nan"), 2.0, float("inf"), 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
    out = build_sparkline_svg(values, threshold_low=3.0, threshold_high=7.0)
    # 9 个有效点 ≥ MIN_POINTS=10？只有 9 → 占位
    # 这里 9 个有效 < 10 → 占位
    assert "积累中" in out


def test_constant_values_does_not_zero_div():
    """全部值相同时不应除零。"""
    values = [5.0] * 20
    out = build_sparkline_svg(values, threshold_low=4.0, threshold_high=6.0)
    assert "<path" in out  # 仍能渲染（人为扩展 ±1 防 zero-div）


def test_circle_at_last_point():
    """末点高亮 circle 的 cx 应该接近右边缘（width - padding）。"""
    values = list(range(15))
    out = build_sparkline_svg(values, width=120, height=28)
    cm = re.search(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="2"', out)
    assert cm is not None
    cx = float(cm.group(1))
    # 末点 x 应接近 120 - padding = 119
    assert cx > 110


def test_sparkline_is_self_contained_svg():
    """输出应是合法 inline SVG（一个根 <svg>，闭合）。"""
    out = build_sparkline_svg(list(range(15)))
    assert out.startswith("<svg")
    assert out.endswith("</svg>")
    assert out.count("<svg") == 1
    assert out.count("</svg>") == 1
