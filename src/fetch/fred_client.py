"""FRED (Federal Reserve Economic Data) 封装。

- API key 从 Settings 读（.env: FRED_API_KEY）
- 懒导入 fredapi：只在 fetch_series 调用时才 import，便于测试 mock
- 任何外部异常都捕获并写日志，返回 None，不让程序崩

数据来源署名（FRED 服务条款要求）：
  Source: FRED, Federal Reserve Bank of St. Louis
"""
from __future__ import annotations

from typing import Any, Optional

from src.utils.config import Settings, load_settings
from src.utils.logger import get_logger

log = get_logger(__name__)


def fetch_series(
    series_id: str,
    start: str,
    end: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> Optional[Any]:
    """获取某 FRED 序列在 [start, end] 区间的日频值。

    入参：
        series_id: FRED 序列代码（如 "T10Y2Y"、"BAMLH0A0HYM2"）
        start: ISO YYYY-MM-DD
        end: ISO YYYY-MM-DD，缺省到当前
        settings: 可选，注入测试用 Settings；缺省 load_settings()
    返回：
        pandas.Series（index=DatetimeIndex 升序，name="value"），失败返回 None
    异常：
        不抛；缺 key、ImportError、网络/解析异常一律转为 log + None
    """
    s = settings if settings is not None else load_settings()
    if not s.fred_api_key:
        log.error("FRED_API_KEY 未配置（.env），无法拉取 %s", series_id)
        return None

    try:
        from fredapi import Fred  # 懒导入
    except ImportError as e:
        log.error("fredapi 未安装：%s", e)
        return None

    try:
        fred = Fred(api_key=s.fred_api_key)
        series = fred.get_series(
            series_id,
            observation_start=start,
            observation_end=end,
        )
    except Exception as e:  # 网络 / 鉴权 / 序列不存在
        log.error("FRED 拉取 %s 失败: %s", series_id, e)
        return None

    if series is None or len(series) == 0:
        log.warning("FRED 返回空数据: series=%s start=%s end=%s", series_id, start, end)
        return None

    try:
        # FRED 缺数会用 "." 字符或 NaN，dropna 处理
        cleaned = series.dropna()
        cleaned.name = "value"
        return cleaned.sort_index()
    except Exception as e:
        log.error("解析 FRED 返回结构失败: %s", e)
        return None
