"""Z-score / 历史分位计算（异常监测视角 B）。

设计原则：
  - 纯函数，不查 DB
  - z-score = (value - mean) / std；std=0 时返 None 不抛
  - percentile = 当前值在历史值中的百分位（0-100）
  - "极端"判定：|z| > 2（默认 95% 置信区间外）

调用方：src/web/app.py 的 _build_rows，行级注入 zscore 字段
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence

# 极端 z-score 阈值（绝对值大于此判为异常）
EXTREME_Z_THRESHOLD = 2.0
MIN_POINTS_FOR_ZSCORE = 30


def _filter_finite(values: Sequence[float]) -> List[float]:
    """过滤 None / NaN / Inf 保留有限浮点。"""
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


def compute_zscore(
    history_values: Sequence[float],
    current_value: Optional[float],
    direction: str = "up",
) -> Dict[str, Any]:
    """对比当前值与历史分布，算 z-score 与百分位。

    入参：
        history_values: 历史值列表（含或不含当前点都行，函数自己用全分布算 mean/std）
        current_value: 当前值
        direction: "up" / "down"，决定"极端=危险"的方向
    返回：
        {
          "z": float | None,                # z-score，std=0 或样本不足返 None
          "percentile": float | None,       # 0-100，当前值在历史分布的百分位（小=低）
          "extreme": bool | None,           # |z| > EXTREME_Z_THRESHOLD（且方向匹配=危险）
          "n": int,                         # 实际有效样本数
        }
    """
    if current_value is None:
        return {"z": None, "percentile": None, "extreme": None, "n": 0}
    try:
        cur = float(current_value)
        if math.isnan(cur) or math.isinf(cur):
            return {"z": None, "percentile": None, "extreme": None, "n": 0}
    except (TypeError, ValueError):
        return {"z": None, "percentile": None, "extreme": None, "n": 0}

    clean = _filter_finite(history_values)
    n = len(clean)

    if n < MIN_POINTS_FOR_ZSCORE:
        return {"z": None, "percentile": None, "extreme": None, "n": n}

    mean = sum(clean) / n
    var = sum((x - mean) ** 2 for x in clean) / n
    std = math.sqrt(var)

    if std == 0:
        return {"z": None, "percentile": None, "extreme": None, "n": n}

    z = (cur - mean) / std

    # 百分位：当前值在历史中的排名 / n × 100
    below = sum(1 for x in clean if x < cur)
    equal = sum(1 for x in clean if x == cur)
    # 用中位百分位约定：(below + equal/2) / n × 100
    pct = (below + equal / 2.0) / n * 100.0

    # 极端 + 方向：z>2 & up 危险 / z<-2 & down 危险
    if direction == "up":
        extreme = z > EXTREME_Z_THRESHOLD
    elif direction == "down":
        extreme = z < -EXTREME_Z_THRESHOLD
    else:
        extreme = abs(z) > EXTREME_Z_THRESHOLD

    return {
        "z": z,
        "percentile": pct,
        "extreme": extreme,
        "n": n,
    }
