"""收益率曲线 10Y-2Y 指标（衰退预警）。

数据源：FRED 序列 T10Y2Y（已是 10Y - 2Y 的差，单位 %）
方向：down（值越低越危险；倒挂 < 0 是历史衰退前奏）

阈值（INDICATORS.md 定义，本文件常量与之一致）：
  GREEN  > 0.5    曲线健康
  YELLOW 0 – 0.5  曲线偏平
  RED    < 0      倒挂

写库 schema：
  name="yield_curve_10y2y", date=YYYY-MM-DD, value=百分点, source="FRED:T10Y2Y"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "yield_curve_10y2y"
SERIES_ID = "T10Y2Y"
SOURCE = "FRED:T10Y2Y"
DIRECTION = "down"

# 阈值默认值（与 INDICATORS.md 一致；改阈值需走 ADR 流程）
THRESHOLD_LOW = 0.0
THRESHOLD_HIGH = 0.5


def classify_value(value: float) -> Level:
    """对单个 10Y-2Y 数值分类（百分点）。"""
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    """从 FRED 拉取 T10Y2Y 历史日值并 upsert 入库。

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
