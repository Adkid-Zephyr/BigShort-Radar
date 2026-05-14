"""yfinance 封装。

- 不需要 API key
- 懒导入 yfinance：只在 fetch_close 调用时才 import，便于测试 mock
- 任何外部异常都捕获并写日志，返回 None，不让程序崩
"""
from __future__ import annotations

from typing import Any, Optional

from src.utils.logger import get_logger

log = get_logger(__name__)


def fetch_close(
    ticker: str,
    start: str,
    end: Optional[str] = None,
) -> Optional[Any]:
    """获取某 ticker 在 [start, end] 区间的日收盘价序列。

    入参：
        ticker: yfinance 代码（如 "^VIX" / "JPY=X"）
        start: ISO YYYY-MM-DD
        end: ISO YYYY-MM-DD，缺省到当前
    返回：
        pandas.Series（index=DatetimeIndex 升序，name="close"），失败返回 None
    异常：
        不抛；网络/解析失败一律转为 log.error 并返回 None
    """
    try:
        import yfinance as yf  # 懒导入
    except ImportError as e:
        log.error("yfinance 未安装：%s", e)
        return None

    try:
        df = yf.download(
            ticker,
            start=start,
            end=end,
            progress=False,
            auto_adjust=False,
            threads=False,
        )
    except Exception as e:  # 网络/服务异常
        log.error("yfinance 下载 %s 失败: %s", ticker, e)
        return None

    if df is None or df.empty:
        log.warning("yfinance 返回空数据: ticker=%s start=%s end=%s", ticker, start, end)
        return None

    # 取 Close 列。yfinance 多 ticker 时是 MultiIndex，单 ticker 一般直接拿 "Close"
    try:
        close = df["Close"]
        # 多 ticker 情况下 close 仍是 DataFrame，单 ticker 通常是 Series
        if hasattr(close, "columns"):
            # MultiIndex 取首列
            close = close.iloc[:, 0]
        close = close.dropna()
        close.name = "close"
        return close.sort_index()
    except Exception as e:
        log.error("解析 yfinance 返回结构失败: %s", e)
        return None
