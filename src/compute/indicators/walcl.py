"""WALCL — 联储总资产（Fed Balance Sheet 总规模）。

数据源：FRED:WALCL（Assets: Total Assets, Wednesday Level，单位 millions of dollars）
- 周值（每周三发布）
- 反映美联储 QE/QT 状态

方向：up（资产负债表越大 = 越多次危机救市 = 系统性风险已显性化）

阈值（基于 2008-2026 历史水平 + 联储退出 QE 节奏，单位百万美元 = M）：
  GREEN  < 8,000,000      ($8T 以下，QE 后正常稳态)
  YELLOW 8,000,000 – 9,000,000   ($8-9T，部分救市动作如 BTFP 仍在)
  RED    > 9,000,000      ($9T+，新一轮危机救市量级)

历史峰值参考：
  - 2014 QE3 顶 $4.5T
  - 2020 春 $4.1T → 2022 春 $8.96T（COVID + Ukraine）
  - 2024 中 ~$7.3T（QT 进行中）
  - 2025-26 当前 ~$6.7-7T

写库 schema：
  name="walcl", date=YYYY-MM-DD, value=百万美元, source="FRED:WALCL"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "walcl"
SERIES_ID = "WALCL"
SOURCE = "FRED:WALCL"
DIRECTION = "up"

# 单位 millions of dollars
THRESHOLD_LOW = 8_000_000.0
THRESHOLD_HIGH = 9_000_000.0


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    series = fred_client.fetch_series(SERIES_ID, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
