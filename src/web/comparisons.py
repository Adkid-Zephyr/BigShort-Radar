"""同比 / 环比对比工具（行内异常监测视角 H）。

设计原则：
  - 纯函数无副作用
  - 给定 (date_iso → value) 历史字典 + 今天 + 回看天数 → 返回该回看点的值与变化率
  - "恶化"判断：方向 up 时上升 = 恶化；方向 down 时下降 = 恶化

调用方：src/web/app.py 的 _build_rows，行级注入 comparisons 字段
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Mapping, Optional


def _parse_iso(s: str) -> Optional[date]:
    """容错解析 YYYY-MM-DD。"""
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _nearest_value_on_or_before(
    history: Mapping[str, float], target: date
) -> Optional[float]:
    """在 history 里找 target 当天或之前最近的非空值。

    入参：
        history: dict[date_iso → value]，未排序
        target: 目标日期
    返回：
        最近一个 ≤ target 的值；找不到返 None
    """
    target_iso = target.strftime("%Y-%m-%d")
    candidates = [
        (d_iso, v)
        for d_iso, v in history.items()
        if d_iso <= target_iso
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    # 取最近一个非 None / 非 NaN 的值
    for _, v in candidates:
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f != f:  # NaN
            continue
        return f
    return None


def lookback_summary(
    history: Mapping[str, float],
    today_value: Optional[float],
    today_date: Optional[date],
    lookback_days: int,
    direction: str = "up",
) -> Dict[str, Any]:
    """对比"今天"与"N 天前"，返回值 + 变化百分比 + 是否恶化。

    入参：
        history: dict[date_iso → value]，至少要含 lookback 那天附近
        today_value: 今日值；None 时所有字段为 None
        today_date: 今日日期 date 对象；None 时使用 history 最新 key
        lookback_days: 回看 N 天前
        direction: "up" 值大=危险 / "down" 值小=危险
    返回：
        {
          "lookback_value": float | None,
          "pct_change": float | None,    # (today - past) / past * 100
          "abs_change": float | None,    # today - past
          "deteriorate": bool | None,    # True=恶化，False=改善，None=无法判断
        }
    """
    out: Dict[str, Any] = {
        "lookback_value": None,
        "pct_change": None,
        "abs_change": None,
        "deteriorate": None,
    }

    if today_value is None:
        return out
    try:
        today_v = float(today_value)
        if today_v != today_v:
            return out
    except (TypeError, ValueError):
        return out

    if today_date is None:
        # 兜底：用 history 最大 key 作为今天
        if not history:
            return out
        today_iso = max(history.keys())
        td = _parse_iso(today_iso)
        if td is None:
            return out
        today_date = td

    target = today_date - timedelta(days=int(lookback_days))
    past = _nearest_value_on_or_before(history, target)
    if past is None:
        return out

    out["lookback_value"] = past
    out["abs_change"] = today_v - past
    if past != 0:
        out["pct_change"] = (today_v - past) / abs(past) * 100.0
    else:
        # past=0 时百分比无意义
        out["pct_change"] = None

    # 恶化判断
    delta = today_v - past
    if delta > 0:
        out["deteriorate"] = (direction == "up")
    elif delta < 0:
        out["deteriorate"] = (direction == "down")
    else:
        out["deteriorate"] = False  # 持平 = 不算恶化

    return out


def build_comparisons(
    dates: List[str],
    values: List[float],
    today_value: Optional[float],
    today_date: Optional[date],
    direction: str = "up",
    lookbacks: tuple = (7, 30, 90),
) -> Dict[int, Dict[str, Any]]:
    """同时算多个 lookback 的对比，组装成 {7: {...}, 30: {...}, 90: {...}}。

    入参：
        dates: 历史 date_iso 列表
        values: 同长度 values
        today_value, today_date, direction: 同 lookback_summary
        lookbacks: 想算的回看天数 tuple
    返回：
        {lookback_days: lookback_summary 输出 dict}
    """
    if len(dates) != len(values):
        raise ValueError("dates and values must be same length")
    history = {d: v for d, v in zip(dates, values)}
    return {
        d: lookback_summary(
            history=history,
            today_value=today_value,
            today_date=today_date,
            lookback_days=d,
            direction=direction,
        )
        for d in lookbacks
    }
