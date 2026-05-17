"""中国外汇储备（China Foreign Exchange Reserves）。

数据源：FRED:TRESEGCNM052N - Total Reserves excluding Gold for China，月值，单位 USD
- 单位 美元 + 月度
- SAFE 国家外汇管理局发布，FRED 转载

方向：down（外储减少 = 中国卖美债 + 资本外流 + 人民币贬值压力 = 全球美元荒信号）

THESIS §4.4 揭示的"中-日-美三角"中国一脚信号。

阈值：
  GREEN  > 3.1T (3,100,000,000,000 美元)  储备稳定，无明显资本外流
  YELLOW 3.0T – 3.1T   边缘，2015-2016 中俄贬值期临界
  RED    < 3.0T        显著资本外流（2016 年中曾跌穿 3.05T 引发市场紧张）

历史背景：
  - 2014 年中峰值 ~4.0T
  - 2015-2016 资本外流期跌至 ~3.0T
  - 2018-2024 维持 3.1-3.2T 区间

写库 schema：
  name="china_fx_reserves", date=YYYY-MM-DD, value=美元（不是百万），source="FRED:TRESEGCNM052N"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "china_fx_reserves"
SERIES_ID = "TRESEGCNM052N"
SOURCE = "FRED:TRESEGCNM052N"
DIRECTION = "down"

# 单位：美元（FRED 原值单位）
THRESHOLD_LOW = 3_000_000_000_000.0   # 3.0T
THRESHOLD_HIGH = 3_100_000_000_000.0  # 3.1T


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    series = fred_client.fetch_series(SERIES_ID, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
