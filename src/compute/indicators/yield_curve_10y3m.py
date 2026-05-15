"""收益率曲线 10Y-3M 指标（衰退预警，纽约联储更偏好的口径）。

数据源：FRED 序列 T10Y3M（已是 10Y - 3M 的差，单位 %）
方向：down（值越低越危险；倒挂 < 0 是历史衰退前奏）

阈值（A 案 — 与 10Y-2Y 同口径，DECISIONS.md 2026-05-15 ADR）：
  GREEN  > 0.5    曲线健康
  YELLOW 0 – 0.5  曲线偏平
  RED    < 0      倒挂

写库 schema：
  name="yield_curve_10y3m", date=YYYY-MM-DD, value=百分点, source="FRED:T10Y3M"

注：本文件结构与 vix.py / yield_curve.py 一致——这是该形状的第三次出现。
按 DECISIONS.md "重复三次再抽象"，下一轮（iter 21）应将"遍历 series 写库"抽到
store 层 helper，并回填三处。
"""
from __future__ import annotations

import math
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
    if series is None or len(series) == 0:
        log.warning("yield_curve_10y3m fetch 返回空，未入库")
        return 0

    count = 0
    for ts, value in series.items():
        date_str = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
        try:
            v = float(value)
        except (TypeError, ValueError):
            log.warning("yield_curve_10y3m 值无法转 float，跳过 %s=%r", date_str, value)
            continue
        if math.isnan(v) or math.isinf(v):
            log.warning("yield_curve_10y3m 值是 NaN/Inf，跳过 %s=%r", date_str, value)
            continue
        dbmod.upsert_indicator(conn, name=NAME, date=date_str, value=v, source=SOURCE)
        count += 1

    log.info("yield_curve_10y3m 入库 %d 条（%s ~ %s）", count, start, end or "now")
    return count
