"""阈值分类通用工具。

三档：GREEN（安全）/ YELLOW（注意）/ RED（高风险）。
方向：
  - "up"   表示"值越高越危险"（如 VIX、HY OAS、Shiller PE）
  - "down" 表示"值越低越危险"（如 收益率曲线 10Y-2Y）
"""
from __future__ import annotations

from enum import Enum
from typing import Literal


class Level(str, Enum):
    """三档风险等级。"""

    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


Direction = Literal["up", "down"]


def classify(value: float, low: float, high: float, direction: Direction) -> Level:
    """把 value 落到 GREEN/YELLOW/RED 三档。

    入参：
        value: 待分类的数值
        low: 低阈值
        high: 高阈值，必须 ≥ low
        direction:
            "up"   值 > high → RED；low < 值 ≤ high → YELLOW；值 ≤ low → GREEN
            "down" 值 < low  → RED；low ≤ 值 < high → YELLOW；值 ≥ high → GREEN

        边界：
            "up"   value == low  → GREEN；value == high → YELLOW
            "down" value == high → GREEN；value == low  → YELLOW
    返回：
        Level
    异常：
        ValueError: low > high 或 direction 非法
        TypeError: 数值类型不可比较
    """
    if direction not in ("up", "down"):
        raise ValueError(f"direction 必须是 'up' 或 'down'，收到 {direction!r}")
    if low > high:
        raise ValueError(f"low ({low}) 不能大于 high ({high})")

    v = float(value)
    if direction == "up":
        if v > high:
            return Level.RED
        if v > low:
            return Level.YELLOW
        return Level.GREEN
    # direction == "down"
    if v < low:
        return Level.RED
    if v < high:
        return Level.YELLOW
    return Level.GREEN
