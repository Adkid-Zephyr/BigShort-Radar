"""VIX 期限结构指标（VIX / VIX3M 比值）。

衡量市场对"近月波动 vs 中期波动"的相对定价：
- 比值 < 1（contango）：远月波动率溢价 → 市场平静
- 比值 ≈ 1（flat）：紧张
- 比值 > 1（backwardation）：近月恐慌定价 > 远月 → 危机临近

数据源：
  yfinance ^VIX（CBOE Volatility Index，30 天预期波动率）
  yfinance ^VIX3M（CBOE 3-Month Volatility Index）
计算：value = VIX_close / VIX3M_close（按交易日对齐）
方向：up（值越高越危险）

阈值（DECISIONS.md 2026-05-15 ADR）：
  GREEN  < 0.95   contango，平静
  YELLOW 0.95 – 1.0  紧张
  RED    > 1.0    倒挂，危机临近（2008、2020 春、2022 多次）

写库 schema：
  name="vix_term_structure", date=YYYY-MM-DD, value=比值, source="YF:^VIX/^VIX3M"
"""
from __future__ import annotations

import sqlite3
from typing import Any, Optional

from src.compute.thresholds import Level, classify
from src.fetch import yf_client
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger(__name__)

NAME = "vix_term_structure"
TICKER_FRONT = "^VIX"
TICKER_BACK = "^VIX3M"
SOURCE = "YF:^VIX/^VIX3M"
DIRECTION = "up"

# 阈值常量（与 INDICATORS.md 一致）
THRESHOLD_LOW = 0.95
THRESHOLD_HIGH = 1.0


def classify_value(value: float) -> Level:
    """对单个 VIX/VIX3M 比值分类。"""
    return classify(value, low=THRESHOLD_LOW, high=THRESHOLD_HIGH, direction=DIRECTION)


def _compute_ratio(front: Any, back: Any) -> Any:
    """对齐两条 pandas.Series，返回 ratio = front / back（去 NaN，去 back==0）。

    入参：
        front, back: pandas.Series，index=日期
    返回：
        pandas.Series，name="value"；空对齐返回 None
    """
    if front is None or back is None:
        return None
    try:
        # 用 index 交集对齐（pandas 会自动对齐，但显式更清晰）
        common = front.index.intersection(back.index)
        if len(common) == 0:
            return None
        f = front.loc[common]
        b = back.loc[common]
        # 防 0 除：把 b==0 的位置 mask 掉
        mask = (b != 0) & b.notna() & f.notna()
        if not mask.any():
            return None
        ratio = (f[mask] / b[mask])
        ratio.name = "value"
        return ratio.sort_index()
    except Exception as e:  # pragma: no cover
        log.error("VIX 期限结构对齐失败: %s", e)
        return None


def fetch_and_store(
    conn: sqlite3.Connection,
    start: str = "2020-01-01",
    end: Optional[str] = None,
) -> int:
    """拉 VIX 与 VIX3M、计算比值并入库。

    入参：
        conn: 已开 schema 的 SQLite 连接
        start: 拉取起始日期 YYYY-MM-DD
        end: 拉取结束日期；缺省到当前
    返回：
        实际写入条数
    异常：
        不抛；任一条 fetch 失败 → 返回 0
    """
    front = yf_client.fetch_close(TICKER_FRONT, start=start, end=end)
    back = yf_client.fetch_close(TICKER_BACK, start=start, end=end)
    ratio = _compute_ratio(front, back)
    return dbmod.upsert_series_from_pandas(conn, name=NAME, source=SOURCE, series=ratio)
