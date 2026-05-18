"""SKEW — CBOE SKEW 指数（黑天鹅 / tail risk 定价）。

数据源：CBOE:SKEW_History.csv（CBOE Skew Index）
- 日值
- 衡量 OTM put 相对 ATM put 的额外溢价 → 黑天鹅事件被定价的程度
- 数学形式：100 + 10 × log[risk-neutral skew]

方向：up（SKEW 越高 = 市场为左尾事件付的钱越多）

阈值（基于历史水平）：
  GREEN  < 130    (正常 tail risk 定价，2018-2019 多数时间)
  YELLOW 130 – 145 (升高，市场担心黑天鹅)
  RED    > 145    (极度紧张，2008/2017 都见过）

历史背景：
  - 历史均值 ~119
  - 长尾低位 105-115（2009 救市后)
  - 2017 年中曾 154（拥挤的看跌定价）
  - 2008 雷曼前 130-140

注意：SKEW 与 VIX 不一定同向。SKEW 高 + VIX 低 = "lull before storm"。

写库 schema：
  name="skew", date=YYYY-MM-DD, value=指数, source="CBOE:SKEW_History.csv"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import cboe_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "skew"
SYMBOL = "SKEW"
SOURCE = "CBOE:SKEW_History.csv"
DIRECTION = "up"

THRESHOLD_LOW = 130.0
THRESHOLD_HIGH = 145.0


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    series = cboe_client.fetch_index_history(SYMBOL, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
