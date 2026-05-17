"""FRA-OIS 代理（融资市场压力 / 美元荒早期信号）。

THESIS §4.3 揭示的"08 真正引爆器"维度。原 FRA-OIS（Forward Rate Agreement minus
Overnight Index Swap）是 LIBOR 时代主信号，LIBOR 退役后 FRED 无现成 series。
本指标用代理：3 个月 T-Bill 收益率 - SOFR

  proxy_fra_ois = DGS3MO - SOFR  （单位 %，FRED 原值是 %）

含义：
  - T-Bill 是无风险货币市场利率（政府背书）
  - SOFR 是有担保回购市场基准（机构间）
  - 差值放大 = 机构间融资压力升高 = 类 FRA-OIS 信号

数据源：
  FRED:DGS3MO   - 3-Month Treasury Constant Maturity Rate
  FRED:SOFR     - Secured Overnight Financing Rate

方向：up（差值越大 = 融资市场越紧张）

阈值（基于 2008/2020/2023 历史压力期）：
  GREEN  < 0.10 (10 bp)   正常稳态
  YELLOW 0.10 – 0.30      紧张
  RED    > 0.30 (30 bp)   显著压力（2020/3 一度走阔到 ~0.50）

注意：
  - 本指标是代理，不是原版 FRA-OIS。原 FRA-OIS 数据需 Bloomberg
  - 2018 年前 SOFR 历史短，前期数据有限

写库 schema：
  name="fra_ois", date=YYYY-MM-DD, value=百分点, source="FRED:DGS3MO-SOFR"
"""
from __future__ import annotations

import sqlite3
from typing import Any, Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "fra_ois"
SERIES_TBILL = "DGS3MO"
SERIES_SOFR = "SOFR"
SOURCE = "FRED:DGS3MO-SOFR"
DIRECTION = "up"

THRESHOLD_LOW = 0.10
THRESHOLD_HIGH = 0.30


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def _compute_spread(tbill: Any, sofr: Any) -> Any:
    """T-Bill - SOFR 差值（保留符号，因为代理含义为"T-Bill 高 vs SOFR 低=避险流入 T-Bill=压力升"）。

    入参：tbill, sofr 是 pandas.Series
    返回：pandas.Series 或 None
    """
    if tbill is None or sofr is None:
        return None
    try:
        common = tbill.index.intersection(sofr.index)
        if len(common) == 0:
            return None
        spread = tbill.loc[common] - sofr.loc[common]
        spread = spread.dropna()
        if len(spread) == 0:
            return None
        spread.name = "value"
        return spread.sort_index()
    except Exception as e:  # pragma: no cover
        log.error("FRA-OIS 代理计算失败: %s", e)
        return None


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    tbill = fred_client.fetch_series(SERIES_TBILL, start=start, end=end)
    sofr = fred_client.fetch_series(SERIES_SOFR, start=start, end=end)
    spread = _compute_spread(tbill, sofr)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=spread)
