"""CBOE Equity Put/Call Ratio — 个股期权看跌/看涨成交比。

数据源:CBOE US Options Daily Market Statistics 页面(当前快照)
方向:up(越高代表个股层面保护/恐慌需求越强)

意义:
  Equity Put/Call 更容易混入散户追涨/财报交易噪声。和 Index Put/Call 对比看，
  可以区分"机构指数保护"和"个股期权情绪"。

阈值:
  GREEN  < 0.55
  YELLOW 0.55-0.85
  RED    > 0.85

写库 schema:
  name="put_call_equity", date=YYYY-MM-DD, value=ratio, source="CBOE:US_OPTIONS_DAILY_MARKET_STATISTICS"
"""
from __future__ import annotations

import sqlite3
from datetime import date

from src.compute.thresholds import Level, classify
from src.fetch import cboe_client
from src.store import db as dbmod

NAME = "put_call_equity"
SOURCE = "CBOE:US_OPTIONS_DAILY_MARKET_STATISTICS"
DIRECTION = "up"

THRESHOLD_LOW = 0.55
THRESHOLD_HIGH = 0.85


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(conn: sqlite3.Connection, start: str = "", end: str = "") -> int:
    ratios = cboe_client.fetch_put_call_ratios()
    value = ratios.get("equity")
    if value is None:
        return 0
    dbmod.upsert_indicator(conn, name=NAME, date=date.today().isoformat(), value=value, source=SOURCE)
    return 1
