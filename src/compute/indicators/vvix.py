"""VVIX — VIX 指数自身的隐含波动率（"恐慌之恐慌"）。

数据源：CBOE:VVIX_History.csv（CBOE VIX of VIX）
- 日值
- 衡量市场对 VIX 未来波动的预期
- 高 VVIX = 市场预计 VIX 自身要大幅波动（极端情绪可能切换）

方向：up（VVIX 越高 = 越多 tail risk 预期）

阈值（基于 2007-2026 历史水平）：
  GREEN  < 90       (正常稳态，2017-2019 多数时间在 80-95)
  YELLOW 90 – 120   (紧张，反身性可能启动)
  RED    > 120      (恐慌之恐慌，2008/2020 春多次穿越)

历史峰值：
  - 2008 雷曼周 ~210
  - 2018Q1 volmageddon ~180
  - 2020/3 ~210

写库 schema：
  name="vvix", date=YYYY-MM-DD, value=指数, source="CBOE:VVIX_History.csv"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import cboe_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "vvix"
SYMBOL = "VVIX"
SOURCE = "CBOE:VVIX_History.csv"
DIRECTION = "up"

THRESHOLD_LOW = 90.0
THRESHOLD_HIGH = 120.0


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    series = cboe_client.fetch_index_history(SYMBOL, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
