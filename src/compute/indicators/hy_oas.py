"""HY OAS 指标（高收益债期权调整利差，信用市场紧张度）。

数据源：FRED 序列 BAMLH0A0HYM2（ICE BofA US High Yield Index Option-Adjusted Spread）
方向：up（值越高越紧张：违约定价、信用收缩、流动性退潮）

阈值（DECISIONS.md 2026-05-15 ADR）：
  GREEN  < 4    平静期
  YELLOW 4 – 8  紧张
  RED    > 8    显著违约定价（2008=18 / 2020 春=11 / 2022 末≈5.8）

写库 schema：
  name="hy_oas", date=YYYY-MM-DD, value=百分点, source="FRED:BAMLH0A0HYM2"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "hy_oas"
SERIES_ID = "BAMLH0A0HYM2"
SOURCE = "FRED:BAMLH0A0HYM2"
DIRECTION = "up"

# 阈值常量（与 INDICATORS.md 一致；改阈值需走 ADR 流程）
THRESHOLD_LOW = 4.0
THRESHOLD_HIGH = 8.0


def classify_value(value: float) -> Level:
    """对单个 HY OAS 数值分类（百分点）。"""
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    """从 FRED 拉取 BAMLH0A0HYM2 历史日值并 upsert 入库。

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
