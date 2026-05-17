"""中国 10 年期国债收益率（China 10Y Government Bond Yield）。

数据源：FRED:IRLTLT01CNM156N - Long-Term Government Bond Yields: 10-year: Main (Including Benchmark) for China，月值，单位 % 年化
- 月度（OECD 数据，FRED 转载）

方向：down（中国国债收益率下降 = 经济动能弱 / 通缩压力 / 资本流入避险 / 增长担忧）

阈值（基于 2018-2026 历史水平）：
  GREEN  > 2.5    经济动能稳健，正常水平
  YELLOW 2.0 – 2.5  增长疲弱信号
  RED    < 2.0    显著通缩 / 经济失速信号（2024-25 触及 1.7-1.8）

THESIS §4.4 中-日-美三角：CNY 10Y 跟 JP 10Y 同步走低 = 亚洲资本通缩共振

写库 schema：
  name="china_10y", date=YYYY-MM-DD, value=百分点, source="FRED:IRLTLT01CNM156N"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "china_10y"
SERIES_ID = "IRLTLT01CNM156N"
SOURCE = "FRED:IRLTLT01CNM156N"
DIRECTION = "down"

THRESHOLD_LOW = 2.0
THRESHOLD_HIGH = 2.5


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    series = fred_client.fetch_series(SERIES_ID, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
