"""ON RRP — 隔夜逆回购协议余额（流动性下限框架）。

数据源：FRED:RRPONTSYD（Overnight Reverse Repurchase Agreements: Treasury Securities Sold by the Federal Reserve in the Temporary Open Market Operations，单位 millions of dollars）
- 日值
- 当资金紧张/赚不到 IORB 时，机构将多余现金放 ON RRP；反之撤出

方向：down（余额降低 = 缓冲耗尽 = 流动性紧张接近极限）

阈值：
  GREEN  > 500,000     ($500B+，缓冲充裕)
  YELLOW 100,000 – 500,000  ($100B-500B，缓冲消耗中)
  RED    < 100,000     (<$100B，缓冲将耗尽，流动性临界)

历史背景：
  - 2023 年峰值 $2.5T（疫情 QE 后大量过剩流动性）
  - 2024-25 持续下降（QT + T-Bill 发行吸资金）
  - 2025 中跌破 $200B 后市场紧张升温

写库 schema：
  name="on_rrp", date=YYYY-MM-DD, value=百万美元, source="FRED:RRPONTSYD"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "on_rrp"
SERIES_ID = "RRPONTSYD"
SOURCE = "FRED:RRPONTSYD"
DIRECTION = "down"

# 注意 down 方向：阈值 GREEN > THRESHOLD_HIGH（高=安全）
# 与 yield_curve 同样 down direction：high=THRESHOLD_HIGH 是 GREEN/YELLOW 切点，low=THRESHOLD_LOW 是 YELLOW/RED 切点
THRESHOLD_LOW = 100_000.0   # < 100B = RED
THRESHOLD_HIGH = 500_000.0  # > 500B = GREEN


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    series = fred_client.fetch_series(SERIES_ID, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
