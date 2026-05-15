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

import math
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
        实际写入条数（去重前的行数；upsert 不区分新增/更新）
    异常：
        不抛；fetch 失败返回 0
    """
    series = yf_client.fetch_close(TICKER, start=start, end=end)
    if series is None or len(series) == 0:
        log.warning("VIX fetch 返回空，未入库")
        return 0

    count = 0
    for ts, value in series.items():
        # ts 是 pandas Timestamp，转 ISO 日期串
        date_str = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
        try:
            v = float(value)
        except (TypeError, ValueError):
            log.warning("VIX 值无法转 float，跳过 %s=%r", date_str, value)
            continue
        if math.isnan(v) or math.isinf(v):
            log.warning("VIX 值是 NaN/Inf，跳过 %s=%r", date_str, value)
            continue
        dbmod.upsert_indicator(conn, name=NAME, date=date_str, value=v, source=SOURCE)
        count += 1

    log.info("VIX 入库 %d 条（%s ~ %s）", count, start, end or "now")
    return count
