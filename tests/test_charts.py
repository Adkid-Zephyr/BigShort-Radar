"""tests for src/web/charts.py — Plotly 大图渲染。"""
from __future__ import annotations

import pytest

from src.web.charts import build_indicator_chart_html


# ── 占位（数据不足）─────────────────────────────────────────

def test_empty_dates_returns_placeholder():
    out = build_indicator_chart_html("vix", "VIX", dates=[], values=[])
    assert "chart-placeholder" in out
    assert "暂无足够" in out


def test_mismatched_lengths_returns_placeholder():
    out = build_indicator_chart_html("vix", "VIX", dates=["2024-01-01"], values=[])
    assert "chart-placeholder" in out


def test_single_point_returns_placeholder():
    """1 个点画不出折线。"""
    out = build_indicator_chart_html("vix", "VIX", dates=["2024-01-01"], values=[18.0])
    assert "chart-placeholder" in out
    assert "不足 2 个点" in out


# ── 正常渲染 ─────────────────────────────────────────────────

def test_normal_renders_plotly_div():
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    values = [18.0, 19.5, 20.1]
    out = build_indicator_chart_html(
        "vix", "VIX 恐慌指数", dates=dates, values=values,
        threshold_low=20.0, threshold_high=30.0, direction="up",
    )
    # 应该是 plotly div
    assert "plotly" in out.lower()
    # 含 div_id 后缀
    assert "chart_vix" in out
    # 不嵌入 plotly.js（CDN 引用）
    assert "cdn.plot.ly" in out or "cdn.plotly" in out or 'src="https://cdn' in out
    # 包含数据点
    assert "18.0" in out or "18" in out


def test_threshold_lines_present_when_complete():
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    values = [18.0, 19.5, 20.1]
    out = build_indicator_chart_html(
        "vix", "VIX", dates=dates, values=values,
        threshold_low=20.0, threshold_high=30.0, direction="up",
    )
    # 阈值标签
    assert "low=20" in out
    assert "high=30" in out


def test_no_threshold_no_hrect():
    """阈值缺失不画三档填色 hrect。"""
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    values = [18.0, 19.5, 20.1]
    out = build_indicator_chart_html(
        "vix", "VIX", dates=dates, values=values,
        threshold_low=None, threshold_high=None,
    )
    # plotly hrect 在 HTML 里通常是 layout.shapes，没阈值就没这些
    assert "low=" not in out
    assert "high=" not in out


def test_label_appears_in_title():
    dates = ["2024-01-01", "2024-01-02"]
    values = [18.0, 19.5]
    out = build_indicator_chart_html(
        "vix", "VIX 恐慌指数", dates=dates, values=values,
    )
    # plotly to_html 会把中文 escape 成 unicode，所以查 unicode 转义或原文都接受
    assert "VIX 恐慌指数" in out or "\\u6050\\u614c" in out or "VIX " in out


def test_up_direction_renders():
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    values = [18.0, 19.5, 20.1]
    out = build_indicator_chart_html(
        "vix", "VIX", dates=dates, values=values,
        threshold_low=20.0, threshold_high=30.0, direction="up",
    )
    assert "plotly" in out.lower()


def test_down_direction_renders():
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    values = [0.5, 0.3, -0.1]
    out = build_indicator_chart_html(
        "yc", "10Y-2Y", dates=dates, values=values,
        threshold_low=0.5, threshold_high=0.0, direction="down",
    )
    assert "plotly" in out.lower()


def test_custom_height():
    dates = ["2024-01-01", "2024-01-02"]
    values = [1.0, 2.0]
    out = build_indicator_chart_html("x", "X", dates=dates, values=values, height=600)
    assert "600" in out  # height 应该出现在 layout
