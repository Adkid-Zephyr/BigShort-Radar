"""CBOE public data helpers.

目前只用公开、无需 key 的 CBOE/CDN 页面：
- 指数历史日线 CSV: https://cdn.cboe.com/api/global/us_indices/daily_prices/{SYMBOL}_History.csv
- US options daily market statistics 页面(内嵌 Put/Call ratios)

不引入新依赖：requests / pandas 已在 requirements.txt。
"""
from __future__ import annotations

import json
import re
from io import StringIO
from typing import Dict, Optional

import pandas as pd
import requests

from src.utils.logger import get_logger

log = get_logger(__name__)

_INDEX_HISTORY_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{symbol}_History.csv"
_DAILY_STATS_URL = "https://www.cboe.com/markets/us/options/market-statistics/daily/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (BigShort-Radar; contact=local)"}


def fetch_index_history(symbol: str, start: str, end: Optional[str] = None) -> Optional[pd.Series]:
    """拉 CBOE 指数历史日线 CSV,返回 close 序列。

    CSV 格式通常为 DATE,OPEN,HIGH,LOW,CLOSE，日期是 mm/dd/YYYY。
    返回 index 为 pandas.Timestamp, name="value"。
    任意网络/格式错误返回 None，不抛给上层。
    """
    url = _INDEX_HISTORY_URL.format(symbol=symbol.upper())
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text))
    except Exception as e:  # noqa: BLE001
        log.error("CBOE 指数历史拉取失败 symbol=%s: %s", symbol, e)
        return None

    if df.empty or "DATE" not in df.columns:
        log.warning("CBOE 指数历史格式异常 symbol=%s columns=%s", symbol, list(df.columns))
        return None
    value_col = "CLOSE" if "CLOSE" in df.columns else symbol.upper()
    if value_col not in df.columns:
        log.warning("CBOE 指数历史缺少值列 symbol=%s columns=%s", symbol, list(df.columns))
        return None

    try:
        df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        df = df.dropna(subset=["DATE", value_col]).sort_values("DATE")
        start_ts = pd.to_datetime(start)
        df = df[df["DATE"] >= start_ts]
        if end is not None:
            df = df[df["DATE"] <= pd.to_datetime(end)]
        if df.empty:
            return None
        s = pd.Series(df[value_col].to_numpy(), index=df["DATE"], name="value")
        return s
    except Exception as e:  # noqa: BLE001
        log.error("CBOE 指数历史解析失败 symbol=%s: %s", symbol, e)
        return None


def fetch_put_call_ratios() -> Dict[str, float]:
    """从 CBOE daily market statistics 页面解析当前 Put/Call ratios。

    返回 key:
      - total
      - index
      - etp
      - equity
      - vix

    页面是 Next.js 内嵌 JSON，当前未发现稳定公开历史 CSV/API。
    解析失败返回空 dict，不抛。
    """
    try:
        resp = requests.get(_DAILY_STATS_URL, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        text = resp.text
    except Exception as e:  # noqa: BLE001
        log.error("CBOE Put/Call 页面拉取失败: %s", e)
        return {}

    # 页面中可见片段有两种形态：
    # 1) 普通 JSON: "ratios":[{"name":"TOTAL PUT/CALL RATIO","value":"0.93"},...]
    # 2) Next.js flight 字符串里转义 JSON: \"ratios\":[{\"name\":\"TOTAL PUT/CALL RATIO\",...}]
    match = re.search(r'"ratios"\s*:\s*(\[.*?\])', text)
    escaped = False
    if not match:
        match = re.search(r'\\"ratios\\"\s*:\s*(\[.*?\])', text)
        escaped = True
    if not match:
        log.warning("CBOE Put/Call 页面未找到 ratios JSON")
        return {}

    raw_text = match.group(1).replace('\\"', '"') if escaped else match.group(1)
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as e:
        log.error("CBOE Put/Call ratios JSON 解析失败: %s", e)
        return {}

    out: Dict[str, float] = {}
    for item in raw:
        name = str(item.get("name", "")).upper()
        try:
            value = float(item.get("value"))
        except (TypeError, ValueError):
            continue
        if name == "TOTAL PUT/CALL RATIO":
            out["total"] = value
        elif name == "INDEX PUT/CALL RATIO":
            out["index"] = value
        elif name == "EXCHANGE TRADED PRODUCTS PUT/CALL RATIO":
            out["etp"] = value
        elif name == "EQUITY PUT/CALL RATIO":
            out["equity"] = value
        elif name == "CBOE VOLATILITY INDEX (VIX) PUT/CALL RATIO":
            out["vix"] = value
    return out
