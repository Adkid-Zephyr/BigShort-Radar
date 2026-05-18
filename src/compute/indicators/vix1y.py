"""VIX1Y — CBOE 1-Year Volatility Index。

数据源:CBOE 官方历史 CSV(VIX1Y_History.csv)
方向:up(越高越恐慌)

意义:
  长端波动率。VIX9D/VIX/VIX3M 都高但 VIX1Y 也抬升时,说明市场不是只怕短期事件,
  而是在定价更长周期的不确定性,对大空头/长期保护更有意义。

阈值:
  GREEN  <= 20
  YELLOW 20-30
  RED    > 30

写库 schema:
  name="vix1y", date=YYYY-MM-DD, value=指数, source="CBOE:VIX1Y_History.csv"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import cboe_client
from src.store import db as dbmod

NAME = "vix1y"
SYMBOL = "VIX1Y"
SOURCE = "CBOE:VIX1Y_History.csv"
DIRECTION = "up"

THRESHOLD_LOW = 20.0
THRESHOLD_HIGH = 30.0


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    series = cboe_client.fetch_index_history(SYMBOL, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
