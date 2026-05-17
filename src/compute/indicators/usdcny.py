"""USDCNY 在岸人民币汇率。

数据源：FRED:DEXCHUS - China / U.S. Foreign Exchange Rate（中间价 RMB per USD）
- 日值

方向：up（CNY 贬值 = USDCNY 上升 = 资本外流压力 / 全球美元强势）

阈值（基于近 5 年中间价水平）：
  GREEN  < 7.10    人民币正常区间
  YELLOW 7.10 – 7.30   贬值压力升高
  RED    > 7.30    显著贬值压力（2022/10 一度触及 7.32 创历史新低）

THESIS §4.4 中-日-美三角：USDCNY 与 USDJPY、DXY 共振 = 全球美元紧缩传导

写库 schema：
  name="usdcny", date=YYYY-MM-DD, value=RMB/USD, source="FRED:DEXCHUS"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "usdcny"
SERIES_ID = "DEXCHUS"
SOURCE = "FRED:DEXCHUS"
DIRECTION = "up"

THRESHOLD_LOW = 7.10
THRESHOLD_HIGH = 7.30


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    series = fred_client.fetch_series(SERIES_ID, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
