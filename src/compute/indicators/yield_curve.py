"""收益率曲线 10Y-2Y 指标（衰退预警）。

数据源：FRED 序列 T10Y2Y（已是 10Y - 2Y 的差，单位 %）
方向：down（值越低越危险；倒挂 < 0 是历史衰退前奏）

阈值（INDICATORS.md 定义，本文件常量与之一致）：
  GREEN  > 0.5    曲线健康
  YELLOW 0 – 0.5  曲线偏平
  RED    < 0      倒挂

写库 schema：
  name="yield_curve_10y2y", date=YYYY-MM-DD, value=百分点, source="FRED:T10Y2Y"

注：本文件结构刻意与 src/compute/indicators/vix.py 对齐（fetch+遍历+upsert）。
DECISIONS.md "重复三次再抽象"——本指标是结构第二次出现，等到第三个 FRED 指标
（10Y-3M 或 HY OAS）再把"遍历 series 写库"这段抽到 store 层 helper。
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
        实际写入条数（去重前的行数；upsert 不区分新增/更新）
    异常：
        不抛；fetch 失败返回 0
    """
    series = fred_client.fetch_series(SERIES_ID, start=start, end=end)
    if series is None or len(series) == 0:
        log.warning("yield_curve_10y2y fetch 返回空，未入库")
        return 0

    count = 0
    for ts, value in series.items():
        # ts 是 pandas Timestamp，转 ISO 日期串
        date_str = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
        try:
            v = float(value)
        except (TypeError, ValueError):
            log.warning("yield_curve_10y2y 值无法转 float，跳过 %s=%r", date_str, value)
            continue
        if math.isnan(v) or math.isinf(v):
            log.warning("yield_curve_10y2y 值是 NaN/Inf，跳过 %s=%r", date_str, value)
            continue
        dbmod.upsert_indicator(conn, name=NAME, date=date_str, value=v, source=SOURCE)
        count += 1

    log.info("yield_curve_10y2y 入库 %d 条（%s ~ %s）", count, start, end or "now")
    return count
