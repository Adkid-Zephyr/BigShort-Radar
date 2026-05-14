"""fetch 层测试：用 mock 替换外部库，不打真实网络。

本轮只覆盖 yf_client；fred_client 部分 ⏸ 待 API key 后补。
"""
from __future__ import annotations

import sys
import types

import pytest

from src.fetch import yf_client


def _install_fake_yfinance(monkeypatch, df):
    """注入一个伪 yfinance 模块到 sys.modules，让 yf_client 懒导入到它。"""
    fake = types.ModuleType("yfinance")

    def download(ticker, start=None, end=None, **kw):
        return df

    fake.download = download  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "yfinance", fake)


def _make_df(close_values, index_dates):
    """构造一个最小 DataFrame-like，避免依赖 pandas。

    yf_client 只用 df["Close"]、df.empty、df.iloc[:, 0]、.dropna()、.sort_index()、.name
    用 pandas（如果可用）；不可用则跳过该测试。
    """
    pd = pytest.importorskip("pandas")
    return pd.DataFrame({"Close": close_values}, index=pd.to_datetime(index_dates))


def test_fetch_close_returns_series_on_success(monkeypatch):
    df = _make_df([18.0, 19.5, 17.2], ["2026-05-13", "2026-05-14", "2026-05-15"])
    _install_fake_yfinance(monkeypatch, df)

    s = yf_client.fetch_close("^VIX", start="2026-05-13")
    assert s is not None
    assert s.name == "close"
    assert len(s) == 3
    # 升序
    assert list(s.index) == sorted(list(s.index))


def test_fetch_close_returns_none_when_yfinance_missing(monkeypatch):
    # 让 import yfinance 抛 ImportError
    monkeypatch.setitem(sys.modules, "yfinance", None)
    s = yf_client.fetch_close("^VIX", start="2026-05-13")
    assert s is None


def test_fetch_close_returns_none_on_empty(monkeypatch):
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"Close": []})
    _install_fake_yfinance(monkeypatch, df)
    s = yf_client.fetch_close("^VIX", start="2026-05-13")
    assert s is None


def test_fetch_close_returns_none_on_exception(monkeypatch):
    fake = types.ModuleType("yfinance")

    def boom(*a, **kw):
        raise RuntimeError("network down")

    fake.download = boom  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "yfinance", fake)

    s = yf_client.fetch_close("^VIX", start="2026-05-13")
    assert s is None
