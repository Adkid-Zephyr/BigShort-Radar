"""thresholds 单元测试：覆盖正向 / 反向 / 边界 / 异常输入。"""
from __future__ import annotations

import pytest

from src.compute.thresholds import Level, classify


# ── 正向（up：值越高越危险，如 VIX）─────────────────────────
def test_up_above_high_is_red():
    assert classify(35.0, low=20.0, high=30.0, direction="up") == Level.RED


def test_up_between_is_yellow():
    assert classify(25.0, low=20.0, high=30.0, direction="up") == Level.YELLOW


def test_up_below_low_is_green():
    assert classify(15.0, low=20.0, high=30.0, direction="up") == Level.GREEN


def test_up_at_low_is_green():
    # value == low 走 GREEN（边界规则见 docstring）
    assert classify(20.0, low=20.0, high=30.0, direction="up") == Level.GREEN


def test_up_at_high_is_yellow():
    # value == high 仍是 YELLOW，要严格大于 high 才 RED
    assert classify(30.0, low=20.0, high=30.0, direction="up") == Level.YELLOW


# ── 反向（down：值越低越危险，如 10Y-2Y 倒挂）─────────────
def test_down_below_low_is_red():
    # 10Y-2Y < 0 → RED（倒挂）
    assert classify(-0.2, low=0.0, high=0.5, direction="down") == Level.RED


def test_down_between_is_yellow():
    assert classify(0.3, low=0.0, high=0.5, direction="down") == Level.YELLOW


def test_down_above_high_is_green():
    assert classify(0.8, low=0.0, high=0.5, direction="down") == Level.GREEN


def test_down_at_high_is_green():
    assert classify(0.5, low=0.0, high=0.5, direction="down") == Level.GREEN


def test_down_at_low_is_yellow():
    # value == low 仍是 YELLOW，要严格小于 low 才 RED
    assert classify(0.0, low=0.0, high=0.5, direction="down") == Level.YELLOW


# ── 异常输入 ─────────────────────────────────────────────
def test_invalid_direction_raises():
    with pytest.raises(ValueError):
        classify(1.0, low=0.0, high=1.0, direction="sideways")  # type: ignore[arg-type]


def test_low_greater_than_high_raises():
    with pytest.raises(ValueError):
        classify(1.0, low=10.0, high=5.0, direction="up")


def test_int_value_accepted():
    assert classify(25, low=20, high=30, direction="up") == Level.YELLOW


def test_level_enum_str_value():
    assert Level.RED.value == "RED"
    assert str(Level.GREEN.value) == "GREEN"
