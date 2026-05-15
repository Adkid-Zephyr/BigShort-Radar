"""日本 10 年国债收益率（YCC 退出后的真正爆点）。

数据源：FRED:IRLTLT01JPM156N（OECD：Japan, Long-Term Government Bond Yield: 10-year, Monthly）
- 月值（不是日值），用于结构性趋势监控
- 注意：FRED 日值 JGB 没有公开免费源；月值已足够看趋势

方向：up（收益率越高 = 日银 YCC 防线被击穿 = 日资回流冲击美债）

阈值（DECISIONS.md ADR）：
  GREEN  < 1.0    YCC 时代水平（2016-2022 长期 0% 锚）
  YELLOW 1.0 – 2.0  YCC 已退出但仍受控（2024 触及 1.5）
  RED    > 2.0    日银失去定价权，全球套利套息逻辑彻底反转

历史参考：
  2016-2022：0%（YCC 锚定）
  2023/3：0.4%（YCC 第一次松绑）
  2024/3：0.7%（YCC 退出）
  2024/9：0.85%（加息 0.25）
  2025-2026：未披露（系统跑后填）

写库 schema：
  name="jp_10y", date=YYYY-MM-DD（月初）, value=%, source="FRED:IRLTLT01JPM156N"
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from src.compute.thresholds import Level, classify
from src.fetch import fred_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "jp_10y"
SERIES_ID = "IRLTLT01JPM156N"
SOURCE = "FRED:IRLTLT01JPM156N"
DIRECTION = "up"

THRESHOLD_LOW = 1.0
THRESHOLD_HIGH = 2.0


def classify_value(value: float) -> Level:
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    series = fred_client.fetch_series(SERIES_ID, start=start, end=end)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=series)
