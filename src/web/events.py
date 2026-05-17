"""异常事件检测（视角 F：30 天倒序事件流）。

设计原则：
  - 纯函数，不查 DB（DB 查询逻辑在 app.py，本模块只接受 (dates, values)）
  - 三类事件：翻档（level 切换） / 突破阈值（首次跨切点） / 显著变化（单日 ≥5%）
  - 输出按 date 倒序

调用方：app.py 的 /events 路由
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from src.compute.thresholds import Level, classify


def _fmt_value(v: float) -> str:
    """格式化数值显示（千分位 / 自适应小数）。"""
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"{v:,.1f}"
    return f"{v:.4f}"


def detect_indicator_events(
    name: str,
    label: str,
    group: str,
    dates: Sequence[str],
    values: Sequence[float],
    threshold_low: Optional[float],
    threshold_high: Optional[float],
    direction: str = "up",
    lookback_days: int = 30,
) -> List[Dict[str, Any]]:
    """对单条指标的 (dates, values) 找近 N 天的事件。

    入参：
        name: 指标 name
        label: 中文显示名
        group: 维度
        dates: 升序 ISO 日期
        values: 同长度
        threshold_low / threshold_high: 阈值
        direction: up / down
        lookback_days: 仅看最近 N 天（基于 dates 末日往前）
    返回：
        list of dicts: {date, name, label, group, kind, severity, message}
        kind ∈ {"flip_up", "flip_down", "cross_low", "cross_high", "spike"}
        severity ∈ {"info", "warn", "alert"}
    """
    events: List[Dict[str, Any]] = []
    if len(dates) != len(values) or len(values) < 2:
        return events
    if threshold_low is None or threshold_high is None:
        return events

    # 限制窗口
    try:
        end_d = datetime.strptime(dates[-1][:10], "%Y-%m-%d").date()
        start_d = end_d - timedelta(days=lookback_days)
    except ValueError:
        return events

    # level 序列
    levels: List[Level] = []
    for v in values:
        if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
            levels.append(None)  # type: ignore
            continue
        levels.append(classify(float(v), low=threshold_low, high=threshold_high, direction=direction))

    # 翻档检测：相邻两天 level 不同
    for i in range(1, len(dates)):
        prev_lv, curr_lv = levels[i - 1], levels[i]
        if prev_lv is None or curr_lv is None:
            continue
        if prev_lv == curr_lv:
            continue
        # 看是否在窗口内
        try:
            d = datetime.strptime(str(dates[i])[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if d < start_d:
            continue
        # 恶化方向：从 GREEN→YELLOW / YELLOW→RED 是 flip_up；反之 flip_down
        severity_map = {Level.GREEN: 0, Level.YELLOW: 1, Level.RED: 2}
        prev_s = severity_map[prev_lv]
        curr_s = severity_map[curr_lv]
        delta = curr_s - prev_s
        kind = "flip_up" if delta > 0 else "flip_down"
        sev = "alert" if (delta > 0 and curr_lv == Level.RED) else ("warn" if delta > 0 else "info")
        events.append({
            "date": str(dates[i])[:10],
            "name": name,
            "label": label,
            "group": group,
            "kind": kind,
            "severity": sev,
            "message": f"{label} {prev_lv.value} → {curr_lv.value}（{_fmt_value(values[i-1])} → {_fmt_value(values[i])}）",
        })

    # 突破阈值检测（首次穿越 low/high；只看上穿 / 下穿 1 次以避免重复）
    crossed_low = False
    crossed_high = False
    for i in range(1, len(dates)):
        v_prev = values[i - 1]
        v_curr = values[i]
        if v_prev is None or v_curr is None:
            continue
        try:
            d = datetime.strptime(str(dates[i])[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if d < start_d:
            continue
        # 上穿 low
        if not crossed_low and v_prev < threshold_low <= v_curr:
            events.append({
                "date": str(dates[i])[:10],
                "name": name,
                "label": label,
                "group": group,
                "kind": "cross_low",
                "severity": "warn",
                "message": f"{label} 跨过 LOW 阈值 {threshold_low}（{_fmt_value(v_prev)} → {_fmt_value(v_curr)}）",
            })
            crossed_low = True
        # 上穿 high
        if not crossed_high and v_prev < threshold_high <= v_curr:
            events.append({
                "date": str(dates[i])[:10],
                "name": name,
                "label": label,
                "group": group,
                "kind": "cross_high",
                "severity": "alert",
                "message": f"{label} 跨过 HIGH 阈值 {threshold_high}（{_fmt_value(v_prev)} → {_fmt_value(v_curr)}）",
            })
            crossed_high = True

    # 单日突变（>5%）
    for i in range(1, len(dates)):
        v_prev = values[i - 1]
        v_curr = values[i]
        if v_prev is None or v_curr is None or v_prev == 0:
            continue
        try:
            d = datetime.strptime(str(dates[i])[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if d < start_d:
            continue
        pct = (v_curr - v_prev) / abs(v_prev) * 100.0
        if abs(pct) < 5.0:
            continue
        # 是否朝 direction = 危险方向？
        is_dangerous = (pct > 0 and direction == "up") or (pct < 0 and direction == "down")
        events.append({
            "date": str(dates[i])[:10],
            "name": name,
            "label": label,
            "group": group,
            "kind": "spike",
            "severity": "warn" if is_dangerous else "info",
            "message": f"{label} 单日变动 {pct:+.1f}%（{_fmt_value(v_prev)} → {_fmt_value(v_curr)}）",
        })

    return events


def merge_events(per_indicator: Sequence[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """合并多个指标的事件 list 并按日期倒序。"""
    flat: List[Dict[str, Any]] = []
    for evs in per_indicator:
        flat.extend(evs)
    # 同一日同一指标可能产生多个事件（翻档+突破阈值），保留全部
    flat.sort(key=lambda e: (e["date"], e["name"]), reverse=True)
    return flat
