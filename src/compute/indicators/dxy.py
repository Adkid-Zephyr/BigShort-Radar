"""DXY 美元广义贸易加权指数（美元强弱 / 全球美元周期）。

数据源：FRED:DTWEXBGS（Trade Weighted U.S. Dollar Index: Broad, Goods and Services）
- 日值，覆盖更广（不只 6 货币篮子，而是全球贸易伙伴加权）

方向：up（强美元 = 全球美元荒、新兴市场承压；弱美元 = 风险偏好、宽松环境）

阈值（DECISIONS.md ADR）：
  GREEN  < 110    美元正常
  YELLOW 110 – 125  美元偏强（2022 末顶 124、2025 春 121）
  RED    > 125    极强美元，新兴市场系统性承压（2022/9 一度触及 126，DTWEXBGS 历史峰）

写库 schema：
  name="dxy_broad", date=YYYY-MM-DD, value=指数, source="FRED:DTWEXBGS"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "dxy_broad"
SERIES_ID = "DTWEXBGS"
SOURCE = "FRED:DTWEXBGS"
DIRECTION = "up"

THRESHOLD_LOW = 110.0
THRESHOLD_HIGH = 125.0


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    series = fred_client.fetch_series(SERIES_ID, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
