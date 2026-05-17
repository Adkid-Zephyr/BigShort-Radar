"""按指定日期算综合分（回测核心）。

forward-fill 思路：取 ≤target_date 最近的非空值，最多回看 N 天。
对周值 / 月值指标特别有用（jp_10y 月值会被前向填到下一发布日）。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.compute.risk_score import score_from_indicator_values
from src.store import history_db as hdbmod
from src.utils.logger import get_logger

log = get_logger(__name__)


def _date_minus_days(date_iso: str, days: int) -> str:
    """ISO 日期减 N 天。"""
    dt = datetime.strptime(date_iso, "%Y-%m-%d").date()
    return (dt - timedelta(days=days)).strftime("%Y-%m-%d")


def fetch_latest_value_on_or_before(
    conn: sqlite3.Connection,
    name: str,
    target_date: str,
    forward_fill_days: int = 10,
) -> Optional[float]:
    """从 history_points 拉 ≤target_date 最近 N 天内的最新一条非空值。

    入参：
        conn: history cache DB 连接
        name: 指标 name
        target_date: ISO YYYY-MM-DD
        forward_fill_days: 最多向前填多少天
    返回：
        浮点值或 None
    """
    start = _date_minus_days(target_date, forward_fill_days)
    rows = hdbmod.get_series_range(conn, name, start=start, end=target_date)
    if not rows:
        return None
    # rows 已按 date 升序 → 取末尾
    last = rows[-1]
    try:
        return float(last["value"])
    except (TypeError, ValueError, KeyError):
        return None


def compute_score_for_date(
    history_conn: sqlite3.Connection,
    target_date: str,
    registry: List[Dict[str, Any]],
    forward_fill_days: int = 10,
) -> Dict[str, Any]:
    """指定日期的综合风险分（forward-fill 取每条指标 ≤target 最近值）。

    入参：
        history_conn: 已开 schema 的 history cache DB 连接
        target_date: ISO YYYY-MM-DD
        registry: 指标列表（同主流程或 BACKTEST_INDICATORS）
        forward_fill_days: 单条指标向前回看天数（缺数据容忍度）
    返回：
        dict 同 risk_score.score_from_indicator_values：{score, level, breakdown, missing}
        额外含 "date": target_date
    """
    name_to_value: Dict[str, Any] = {}
    for ind in registry:
        v = fetch_latest_value_on_or_before(
            history_conn,
            name=ind["name"],
            target_date=target_date,
            forward_fill_days=forward_fill_days,
        )
        if v is not None:
            name_to_value[ind["name"]] = v

    result = score_from_indicator_values(name_to_value, registry)
    result["date"] = target_date
    return result
