"""USDJPY 汇率（日元 carry trade 解除信号）。

数据源：FRED:DEXJPUS（联储官方日值 USD/JPY 收盘价）
- 不用 yfinance 避开 rate limit；FRED 提供日值且权威

方向：up（USDJPY 越高 = 日元越弱 = carry 拥挤但稳定；急速回落=carry 解除全球抛售）

关于阈值的特殊性：
  USDJPY 不像 VIX/HY OAS 那样"高=危险"。日元贬值本身不是危险，关键是：
    1) 绝对水平很高（超过 160 = 历史性偏弱，干预/政策反转风险大）
    2) 短期波动性（一周内 ¥161 → ¥141 触发 2024/8 全球抛售）

本指标先用绝对水平做一阶近似（DECISIONS.md ADR）：
  GREEN  < 145    日元相对正常
  YELLOW 145 – 160  弱日元，干预可能性升
  RED    > 160    历史极值，政策反转/解除风险高（2024/7 触及 161 后崩 ¥141）

后续若需用波动率版（5 日变化率）再拆 usdjpy_volatility 单独指标。

写库 schema：
  name="usdjpy", date=YYYY-MM-DD, value=¥/$, source="FRED:DEXJPUS"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "usdjpy"
SERIES_ID = "DEXJPUS"
SOURCE = "FRED:DEXJPUS"
DIRECTION = "up"

THRESHOLD_LOW = 145.0
THRESHOLD_HIGH = 160.0


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    series = fred_client.fetch_series(SERIES_ID, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
