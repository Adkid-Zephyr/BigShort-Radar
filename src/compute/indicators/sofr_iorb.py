"""SOFR-IORB 指标（货币市场流动性温度计）。

衡量回购市场利率（SOFR）与法定准备金利率（IORB）的偏离度。
联储靠 IORB 当上限 + ON RRP 当下限把 SOFR 框在窄区间内。偏离 = 货币市场异常。

数据源：
  FRED:SOFR  - 担保隔夜融资利率（替代 LIBOR 的回购市场基准）
  FRED:IORB  - 法定准备金利率（联储付给商业银行的隔夜利率）

计算：value = |SOFR - IORB| × 100  （单位 bp，FRED 原值是 %）

方向：up（偏离越大越危险）

阈值（DECISIONS.md 2026-05-15 ADR）：
  GREEN  < 5 bp     紧贴上限，正常
  YELLOW 5 – 15 bp  异常信号
  RED    > 15 bp    货币市场失灵（2019/9 回购危机 SOFR 偏离 +300bp）

写库 schema：
  name="sofr_iorb", date=YYYY-MM-DD, value=bp（绝对值）, source="FRED:SOFR-IORB"
"""
from __future__ import annotations

import sqlite3
from typing import Any, Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "sofr_iorb"
SERIES_SOFR = "SOFR"
SERIES_IORB = "IORB"
SOURCE = "FRED:SOFR-IORB"
DIRECTION = "up"

# 阈值（与 INDICATORS.md 一致；改阈值需走 ADR）
THRESHOLD_LOW = 5.0
THRESHOLD_HIGH = 15.0


def classify_value(value: float) -> Level:
    """对单个 |SOFR - IORB| 数值（bp）分类。"""
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def _compute_spread_bp(sofr: Any, iorb: Any) -> Any:
    """对齐 SOFR 与 IORB，返回 |SOFR - IORB| × 100（bp 单位）。

    入参：
        sofr, iorb: pandas.Series（FRED 原值是 %）
    返回：
        pandas.Series，name="value"；空对齐返回 None
    """
    if sofr is None or iorb is None:
        return None
    try:
        common = sofr.index.intersection(iorb.index)
        if len(common) == 0:
            return None
        s = sofr.loc[common]
        i = iorb.loc[common]
        spread = (s - i).abs() * 100.0
        spread = spread.dropna()
        if len(spread) == 0:
            return None
        spread.name = "value"
        return spread.sort_index()
    except Exception as e:  # pragma: no cover
        log.error("SOFR-IORB 对齐失败: %s", e)
        return None


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    """拉 SOFR + IORB、计算 |SOFR-IORB| bp 并入库。

    入参：
        conn: 已开 schema 的 SQLite 连接
        start: 拉取起始日期 YYYY-MM-DD
        end: 拉取结束日期；缺省到当前
    返回：
        实际写入条数
    异常：
        不抛；任一条 fetch 失败 → 返回 0
    """
    sofr = fred_client.fetch_series(SERIES_SOFR, start=start, end=end)
    iorb = fred_client.fetch_series(SERIES_IORB, start=start, end=end)
    spread = _compute_spread_bp(sofr, iorb)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=spread)
