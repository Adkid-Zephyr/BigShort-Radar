"""通用历史拉取路由器。

按 source 字符串前缀分发到 fred_client / yf_client / cboe_client：
  - "FRED:T10Y2Y"             → fred_client.fetch_series("T10Y2Y", start, end)
  - "YF:^VIX"                 → yf_client.fetch_close("^VIX", start, end)
  - "CBOE:VIX9D_History.csv"  → cboe_client.fetch_index_history("VIX9D", start, end)
  - 其他前缀（OECD/派生）目前无可拉源，返回 None

iter 38 决策方案 B：不引 akshare（DECISIONS.md 2026-05-17）。
中国维度走 FRED 系列前缀（FRED:DEXCHUS / FRED:TRESEGCNM052N / FRED:IRLTLT01CNM156N）。

设计意图：sparkline / Z-score / 历史回测都需要"按 source 拉过去 N 年"的统一接口；
本模块是这个接口的薄路由层，不做缓存（缓存逻辑放 history_db.py）。

参考：src/fetch/fred_client.py、src/fetch/yf_client.py（同 docstring + 异常处理风格）。
"""
from __future__ import annotations

from typing import Any, Optional

from src.fetch import cboe_client, fred_client, yf_client
from src.utils.logger import get_logger

log = get_logger(__name__)


def fetch_history(
    source: str,
    start: str,
    end: Optional[str] = None,
) -> Optional[Any]:
    """按 source 字符串路由到对应 client，返回历史 series。

    入参：
        source: 数据源字符串，前缀决定路由：
                - "FRED:<series_id>" → fred_client.fetch_series
                - "YF:<ticker>" / "YAHOO:<ticker>" → yf_client.fetch_close
                - "CBOE:<SYMBOL>_History.csv" → cboe_client.fetch_index_history
                - 其他（OECD:/派生/格式不对）→ None + warning
        start: ISO YYYY-MM-DD
        end: ISO YYYY-MM-DD，缺省到当前
    返回：
        pandas.Series（升序），底层 client 失败 / 不支持的前缀 → None
    异常：
        不抛；底层 client 已捕获网络/鉴权/解析异常，路由层只追加格式校验
    """
    if not source or not isinstance(source, str):
        log.warning("history_fetcher: source 不合法 (%r)", source)
        return None

    if ":" not in source:
        log.warning("history_fetcher: source 缺前缀 (%s)", source)
        return None

    prefix, _, ident = source.partition(":")
    prefix = prefix.strip().upper()
    ident = ident.strip()

    if not ident:
        log.warning("history_fetcher: source ident 空 (%s)", source)
        return None

    # 派生指标 / 多源（含逗号）暂不支持自动拉取
    if "," in ident:
        log.info("history_fetcher: 派生/多源 source 不自动支持 (%s)，调用方自行处理", source)
        return None

    if prefix == "FRED":
        log.info("history_fetcher: FRED %s [%s -> %s]", ident, start, end or "now")
        return fred_client.fetch_series(ident, start=start, end=end)

    if prefix in ("YF", "YAHOO"):
        log.info("history_fetcher: YF %s [%s -> %s]", ident, start, end or "now")
        return yf_client.fetch_close(ident, start=start, end=end)

    if prefix == "CBOE" and ident.endswith("_History.csv"):
        symbol = ident.removesuffix("_History.csv")
        log.info("history_fetcher: CBOE %s [%s -> %s]", symbol, start, end or "now")
        return cboe_client.fetch_index_history(symbol, start=start, end=end)

    # 未知前缀（OECD/akshare 等）：iter 38 方案 B 不引外部 client
    log.warning(
        "history_fetcher: 不支持的 source 前缀 %s（仅支持 FRED:/YF:/YAHOO:/CBOE:），跳过 %s",
        prefix, source,
    )
    return None
