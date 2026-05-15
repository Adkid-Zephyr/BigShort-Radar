"""IG OAS 指标（投资级公司债期权调整利差，信用市场系统性紧张度）。

数据源：FRED 序列 BAMLC0A0CM（ICE BofA US Corporate Index Option-Adjusted Spread）
方向：up（值越高越紧张：投资级公司融资压力上升、信用紧缩蔓延）

阈值（DECISIONS.md 2026-05-15 ADR）：
  GREEN  < 1.5    平静期
  YELLOW 1.5 – 3  紧张
  RED    > 3      系统性紧张（2008=6.5 / 2020 春=4.0 / 2022 末≈1.6）

写库 schema：
  name="ig_oas", date=YYYY-MM-DD, value=百分点, source="FRED:BAMLC0A0CM"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "ig_oas"
SERIES_ID = "BAMLC0A0CM"
SOURCE = "FRED:BAMLC0A0CM"
DIRECTION = "up"

# 阈值常量（与 INDICATORS.md 一致；改阈值需走 ADR 流程）
THRESHOLD_LOW = 1.5
THRESHOLD_HIGH = 3.0


def classify_value(value: float) -> Level:
    """对单个 IG OAS 数值分类（百分点）。"""
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    """从 FRED 拉取 BAMLC0A0CM 历史日值并 upsert 入库。

    入参：
        conn: 已开 schema 的 SQLite 连接
        start: 拉取起始日期（ISO YYYY-MM-DD）
        end: 拉取结束日期；缺省到当前
    返回：
        实际写入条数
    异常：
        不抛；fetch 失败返回 0
    """
    series = fred_client.fetch_series(SERIES_ID, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
