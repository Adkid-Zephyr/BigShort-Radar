"""CBOE Total Put/Call Ratio — 全市场看跌/看涨期权成交比。

数据源:CBOE US Options Daily Market Statistics 页面(当前快照)
方向:up(越高代表保护需求/恐慌情绪越强)

注意:
  Put/Call Ratio 有反向指标属性:极高时既代表恐慌,也可能代表短期过度 hedging 后的反弹条件。
  本系统用于危机监控,先按"hedge demand 升高 = 风险升"处理。

阈值:
  GREEN  < 0.85
  YELLOW 0.85-1.15
  RED    > 1.15

写库 schema:
  name="put_call_total", date=YYYY-MM-DD, value=ratio, source="CBOE:US_OPTIONS_DAILY_MARKET_STATISTICS"
"""
from __future__ import annotations

import sqlite3
from datetime import date

from src.compute.thresholds import Level, classify
from src.fetch import cboe_client
from src.store import db as dbmod

NAME = "put_call_total"
SOURCE = "CBOE:US_OPTIONS_DAILY_MARKET_STATISTICS"
DIRECTION = "up"

THRESHOLD_LOW = 0.85
THRESHOLD_HIGH = 1.15


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(conn: sqlite3.Connection, start: str = "", end: str = "") -> int:
    ratios = cboe_client.fetch_put_call_ratios()
    value = ratios.get("total")
    if value is None:
        return 0
    dbmod.upsert_indicator(conn, name=NAME, date=date.today().isoformat(), value=value, source=SOURCE)
    return 1
