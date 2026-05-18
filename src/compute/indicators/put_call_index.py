"""CBOE Index Put/Call Ratio — 指数期权保护需求。

数据源:CBOE US Options Daily Market Statistics 页面(当前快照)
方向:up(越高代表指数保护/对冲需求越强)

意义:
  Index Put/Call 更接近机构/组合层面的尾部保护需求，通常比 equity put/call 更适合
  监控系统性风险。

阈值:
  GREEN  < 0.90
  YELLOW 0.90-1.30
  RED    > 1.30

写库 schema:
  name="put_call_index", date=YYYY-MM-DD, value=ratio, source="CBOE:US_OPTIONS_DAILY_MARKET_STATISTICS"
"""
from __future__ import annotations

import sqlite3
from datetime import date

from src.compute.thresholds import Level, classify
from src.fetch import cboe_client
from src.store import db as dbmod

NAME = "put_call_index"
SOURCE = "CBOE:US_OPTIONS_DAILY_MARKET_STATISTICS"
DIRECTION = "up"

THRESHOLD_LOW = 0.90
THRESHOLD_HIGH = 1.30


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(conn: sqlite3.Connection, start: str = "", end: str = "") -> int:
    ratios = cboe_client.fetch_put_call_ratios()
    value = ratios.get("index")
    if value is None:
        return 0
    dbmod.upsert_indicator(conn, name=NAME, date=date.today().isoformat(), value=value, source=SOURCE)
    return 1
