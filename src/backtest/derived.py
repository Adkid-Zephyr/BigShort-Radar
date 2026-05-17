"""回测派生指标的成分注册表 + 现场计算。

设计:
  - 主流程指标 vix_term_structure / sofr_iorb / fra_ois 是派生(基于其他底层 series 算出),
    daily_fetch 已经把"算好的派生值"以 name=派生指标名 写进主 DB,主 DB 累积。
  - 但回测用的 history cache DB 没有这些派生值(scripts/backfill_history.py::_is_derived 跳过)。
  - 本模块在 cache DB 缺派生值时,从底层成分(vix3m / sofr / iorb / dgs3mo)现场计算。

不动 cache schema(暂停清单)。底层成分通过 backfill_history --backtest 入 cache。

iter 57(2026-05-17 ADR):本模块解决三窗口回测中三条派生指标 100% missing 的稀释问题。
"""
from __future__ import annotations

import sqlite3
from typing import Any, Callable, Dict, Optional

from src.store import history_db as hdbmod


# ── 派生指标注册表 ─────────────────────────────────────────────
# 每条派生指标:
#   components: dict[本地 component name → cache DB 里存的 name]
#               (component name 是 lambda 形参名,cache name 是 hdb 查询用的)
#   compute:    lambda(**components) → float
DERIVED: Dict[str, Dict[str, Any]] = {
    "vix_term_structure": {
        "components": {"vix": "vix_fred", "vix3m": "vix3m"},
        "compute": lambda vix, vix3m: vix / vix3m if vix3m else None,
    },
    "sofr_iorb": {
        # |SOFR - IORB| × 100 = bp(FRED 原值是 %)
        "components": {"sofr": "sofr_raw", "iorb": "iorb_raw"},
        "compute": lambda sofr, iorb: abs(sofr - iorb) * 100.0,
    },
    "fra_ois": {
        # DGS3MO - SOFR(单位 %)
        "components": {"dgs3mo": "dgs3mo", "sofr": "sofr_raw"},
        "compute": lambda dgs3mo, sofr: dgs3mo - sofr,
    },
}


def is_derived(name: str) -> bool:
    """name 是否注册为派生指标。"""
    return name in DERIVED


def fetch_derived_value(
    conn: sqlite3.Connection,
    name: str,
    target_date: str,
    forward_fill_days: int = 10,
    fetcher: Optional[Callable[[sqlite3.Connection, str, str, int], Optional[float]]] = None,
) -> Optional[float]:
    """从 cache DB 拉派生指标的成分,现场算出派生值。

    入参:
        conn: history cache DB 连接
        name: 派生指标 name(必须在 DERIVED)
        target_date: ISO YYYY-MM-DD
        forward_fill_days: 单成分回看天数
        fetcher: 可注入的成分取值函数(默认用 history_db.get_series_range);
                 签名 (conn, component_cache_name, target_date, forward_fill_days) → float | None
    返回:
        派生值或 None(任一成分缺 / 计算异常 → None)

    若 name 不在 DERIVED → 抛 KeyError(调用方应先 is_derived 判断)
    """
    if name not in DERIVED:
        raise KeyError(f"{name} 不是派生指标")

    spec = DERIVED[name]
    fetcher_fn = fetcher or _default_component_fetcher

    kwargs: Dict[str, float] = {}
    for arg_name, cache_name in spec["components"].items():
        v = fetcher_fn(conn, cache_name, target_date, forward_fill_days)
        if v is None:
            return None
        kwargs[arg_name] = v

    try:
        result = spec["compute"](**kwargs)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    if result is None:
        return None
    try:
        return float(result)
    except (TypeError, ValueError):
        return None


def _default_component_fetcher(
    conn: sqlite3.Connection,
    cache_name: str,
    target_date: str,
    forward_fill_days: int,
) -> Optional[float]:
    """默认成分取值:从 history_points 取 ≤target_date 最近 forward_fill 天内的最末值。

    本质和 backtest.score.fetch_latest_value_on_or_before 同语义,这里独立写一份
    避免循环 import(score.py 会 import 本模块)。
    """
    from datetime import datetime, timedelta

    dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    start = (dt - timedelta(days=forward_fill_days)).strftime("%Y-%m-%d")
    rows = hdbmod.get_series_range(conn, cache_name, start=start, end=target_date)
    if not rows:
        return None
    last = rows[-1]
    try:
        return float(last["value"])
    except (TypeError, ValueError, KeyError):
        return None
