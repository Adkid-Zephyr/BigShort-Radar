"""VIX 指标（CBOE 波动率指数，恐慌指数）。

数据源：yfinance ticker ^VIX
方向：up（值越高越恐慌、越危险）

阈值（默认值，存代码常量；校准后写 INDICATORS.md）：
  GREEN  ≤ 20   平静
  YELLOW 20–30  紧张
  RED    > 30   恐慌

写库 schema：
  name="vix", date=YYYY-MM-DD, value=收盘点位, source="YF:^VIX"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import yf_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "vix"
TICKER = "^VIX"
SOURCE = "YF:^VIX"
DIRECTION = "up"

# 阈值默认值（DECISIONS.md：阈值默认值放代码常量）
THRESHOLD_LOW = 20.0
THRESHOLD_HIGH = 30.0


def classify_value(value: float) -> Level:
    """对单个 VIX 数值分类。"""
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    """从 yfinance 拉取 VIX 历史收盘价并 upsert 入库。

    入参：
        conn: 已开 schema 的 SQLite 连接
        start: 拉取起始日期（ISO YYYY-MM-DD）
        end: 拉取结束日期；缺省到当前
    返回：
        实际写入条数
    异常：
        不抛；fetch 失败返回 0
    """
    series = yf_client.fetch_close(TICKER, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
