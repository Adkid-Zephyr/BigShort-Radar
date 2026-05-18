"""把指标 source 字符串映射成官方页面 URL。

设计原则：
- 单一职责：纯函数，无 IO，无副作用。
- 不知道的前缀返回 None，由调用方决定是否渲染链接。
- registry 里手填的 source_url 优先级高于本模块（在 app.py 里 or 兜底）。

支持的前缀：
- FRED:<series_id>     → https://fred.stlouisfed.org/series/<series_id>
- YF:<ticker>          → https://finance.yahoo.com/quote/<url-encoded-ticker>
- YAHOO:<ticker>       → 同 YF（别名）
- OECD:<series_id>     → https://data.oecd.org/searchresults/?q=<series_id>（OECD 没有稳定的 series 直链）
- CBOE:<ticker>        → https://www.cboe.com/tradable_products/<lowercase>/

派生指标（如 VIX/VIX3M 比值）通常 source 是 "DERIVED:..." 或 "YF:^VIX,YF:^VIX3M"，
这种本模块也返回 None，由 registry 手填 source_url 处理。
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import quote


def source_url(source: Optional[str]) -> Optional[str]:
    """根据指标来源字符串返回官方页 URL。

    入参：
        source: 数据源字符串，形如 "FRED:T10Y2Y" / "YF:^VIX"。可为 None。
    返回：
        官方页 URL；未知前缀或 None 入参返回 None。
    异常：
        不抛。所有意外输入返回 None。
    """
    if not source or not isinstance(source, str):
        return None

    if ":" not in source:
        return None

    prefix, _, ident = source.partition(":")
    prefix = prefix.strip().upper()
    ident = ident.strip()
    if not ident:
        return None

    # 派生 / 多源指标：source 含逗号 → 不能给单链，由 registry 处理
    if "," in ident:
        return None

    if prefix == "FRED":
        return f"https://fred.stlouisfed.org/series/{quote(ident, safe='')}"

    if prefix in ("YF", "YAHOO"):
        # ^VIX 这种 caret 必须 url-encode 成 %5E
        return f"https://finance.yahoo.com/quote/{quote(ident, safe='')}"

    if prefix == "OECD":
        # OECD data portal 没有稳定的 series 直链，用搜索页托底
        return f"https://data.oecd.org/searchresults/?q={quote(ident, safe='')}"

    if prefix == "CBOE":
        if ident.endswith("_History.csv"):
            symbol = ident.removesuffix("_History.csv")
            return f"https://www.cboe.com/us/indices/dashboard/{quote(symbol.upper(), safe='')}/"
        if ident == "US_OPTIONS_DAILY_MARKET_STATISTICS":
            return "https://www.cboe.com/markets/us/options/market-statistics/daily/"
        return f"https://www.cboe.com/tradable_products/{quote(ident.lower(), safe='')}/"

    return None
