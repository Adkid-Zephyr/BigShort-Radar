"""TGA — 财政部一般账户余额（Treasury General Account）。

数据源：FRED:WTREGEN（Treasury General Account at the Federal Reserve，单位 millions of dollars）
- 周值
- 财政部花的钱 → TGA ↓ → 流动性 ↑（钱进入私营部门）
- 财政部存的钱 → TGA ↑ → 流动性 ↓（钱被吸走）

方向：up（余额越高 = 财政部囤越多现金 = 私营流动性减少）

阈值：
  GREEN  < 600,000     (TGA <$600B，财政部正常运转)
  YELLOW 600,000 – 1,000,000  ($600B-1T，吸纳流动性中)
  RED    > 1,000,000   (>$1T，大量囤现金 = 显著吸流动性)

历史背景：
  - 疫情前正常 $300-500B
  - 2020 春疫情救助 → 一度 $1.8T 峰值（COVID 救助资金待发）
  - 2023 债务上限解决后大幅再发债 → TGA 重建到 $700-800B
  - 2024-25 维持 $700-900B 区间

写库 schema：
  name="tga", date=YYYY-MM-DD, value=百万美元, source="FRED:WTREGEN"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "tga"
SERIES_ID = "WTREGEN"
SOURCE = "FRED:WTREGEN"
DIRECTION = "up"

THRESHOLD_LOW = 600_000.0
THRESHOLD_HIGH = 1_000_000.0


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    series = fred_client.fetch_series(SERIES_ID, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
