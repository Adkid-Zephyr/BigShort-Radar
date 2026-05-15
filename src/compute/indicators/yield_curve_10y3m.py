"""收益率曲线 10Y-3M 指标（衰退预警，纽约联储更偏好的口径）。

数据源：FRED 序列 T10Y3M（已是 10Y - 3M 的差，单位 %）
方向：down（值越低越危险；倒挂 < 0 是历史衰退前奏）

阈值（A 案 — 与 10Y-2Y 同口径，DECISIONS.md 2026-05-15 ADR）：
  GREEN  > 0.5    曲线健康
  YELLOW 0 – 0.5  曲线偏平
  RED    < 0      倒挂

写库 schema：
  name="yield_curve_10y3m", date=YYYY-MM-DD, value=百分点, source="FRED:T10Y3M"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "yield_curve_10y3m"
SERIES_ID = "T10Y3M"
SOURCE = "FRED:T10Y3M"
DIRECTION = "down"

# 阈值常量（与 INDICATORS.md 一致，改阈值需走 ADR 流程）
THRESHOLD_LOW = 0.0
THRESHOLD_HIGH = 0.5


def classify_value(value: float) -> Level:
    """对单个 10Y-3M 数值分类（百分点）。"""
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    """从 FRED 拉取 T10Y3M 历史日值并 upsert 入库。

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
