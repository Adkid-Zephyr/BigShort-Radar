"""加速度（短期斜率 vs 长期斜率）— 异常监测视角 C。

设计原则：
  - 纯函数无副作用
  - 用最小二乘拟合算"每日变化率"
  - 比较短窗（5 天）vs 长窗（20 天）斜率：短期 > 长期 = 加速
  - "加速恶化"判定：短斜率方向与 direction 一致（up: 上升=危险，down: 下降=危险），且短斜率比长斜率更陡

调用方：src/web/app.py 的 _build_rows 行级注入 acceleration 字段
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence


def _filter_finite(values: Sequence[float]) -> List[float]:
    out: List[float] = []
    for v in values or []:
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if math.isnan(f) or math.isinf(f):
            continue
        out.append(f)
    return out


def linear_slope(values: Sequence[float]) -> Optional[float]:
    """对 values（时间均匀分布的最后 N 天）做最小二乘拟合，返单位时间斜率。

    入参：
        values: 长度 ≥ 2 的等距序列；少于 2 返 None；NaN/Inf 自动过滤
    返回：
        每"步"斜率（即每个 index 的变化量），无效时 None
    """
    clean = _filter_finite(values)
    n = len(clean)
    if n < 2:
        return None

    # 最小二乘：x = 0..n-1, y = clean
    # slope = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
    sum_x = n * (n - 1) / 2.0
    sum_x2 = sum(i * i for i in range(n))
    sum_y = sum(clean)
    sum_xy = sum(i * v for i, v in enumerate(clean))
    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return None
    return (n * sum_xy - sum_x * sum_y) / denom


def compute_acceleration(
    values: Sequence[float],
    direction: str = "up",
    short_window: int = 5,
    long_window: int = 20,
) -> Dict[str, Any]:
    """算短窗与长窗斜率，并判断是否加速恶化。

    入参：
        values: 历史值升序，越靠后越新；至少 long_window+1 个点
        direction: "up" / "down"
        short_window: 短窗天数（默认 5）
        long_window: 长窗天数（默认 20）
    返回：
        {
          "short_slope": float | None,
          "long_slope": float | None,
          "ratio": float | None,        # short_slope / long_slope，符号相同时；否则 None
          "accelerating": bool | None,  # 短斜率与 direction 同向，且 |short| > |long|
        }
    """
    out: Dict[str, Any] = {
        "short_slope": None,
        "long_slope": None,
        "ratio": None,
        "accelerating": None,
    }

    clean = _filter_finite(values)
    if len(clean) < long_window + 1:
        return out

    short_segment = clean[-short_window - 1:]  # 含起点共 short_window+1 个点
    long_segment = clean[-long_window - 1:]

    s_short = linear_slope(short_segment)
    s_long = linear_slope(long_segment)
    out["short_slope"] = s_short
    out["long_slope"] = s_long

    if s_short is None or s_long is None:
        return out

    # 短斜率方向匹配 direction = 危险方向？
    if direction == "up":
        is_dangerous_direction = s_short > 0
    elif direction == "down":
        is_dangerous_direction = s_short < 0
    else:
        is_dangerous_direction = False

    # 短斜率 |.| > 长斜率 |.|
    accel_magnitude = abs(s_short) > abs(s_long)
    out["accelerating"] = bool(is_dangerous_direction and accel_magnitude)

    if s_long != 0:
        out["ratio"] = s_short / s_long
    return out
