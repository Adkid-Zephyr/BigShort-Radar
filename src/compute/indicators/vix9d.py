"""VIX9D — CBOE S&P 500 9-Day Volatility Index。

数据源:CBOE 官方历史 CSV(VIX9D_History.csv)
方向:up(越高越恐慌)

意义:
  比 VIX(30D) 更敏感于短期事件风险(FOMC/NFP/财报/地缘冲击)。
  期权交易者用它判断周度/0DTE 期权是否已经把短期事件溢价打满。

阈值:
  GREEN  <= 20
  YELLOW 20-32
  RED    > 32

写库 schema:
  name="vix9d", date=YYYY-MM-DD, value=指数, source="CBOE:VIX9D_History.csv"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import cboe_client
from src.store import db as dbmod

NAME = "vix9d"
SYMBOL = "VIX9D"
SOURCE = "CBOE:VIX9D_History.csv"
DIRECTION = "up"

THRESHOLD_LOW = 20.0
THRESHOLD_HIGH = 32.0


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    series = cboe_client.fetch_index_history(SYMBOL, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
