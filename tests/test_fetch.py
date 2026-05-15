"""fetch 层测试：用 mock 替换外部库，不打真实网络。

覆盖 yf_client 与 fred_client。
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from src.fetch import fred_client, yf_client
from src.utils.config import Settings


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


# ── fred_client ──────────────────────────────────────────────
def _fake_settings(key="testkey"):
    return Settings(
        fred_api_key=key,
        tz="Asia/Shanghai",
        flask_port=5050,
        flask_debug=False,
        db_path=Path("/tmp/x.sqlite"),
        logs_dir=Path("/tmp"),
        project_root=Path("/tmp"),
    )


def _install_fake_fredapi(monkeypatch, series_or_exc):
    """注入伪 fredapi 模块，Fred(api_key=...).get_series(...) 返回指定值或抛异常。"""
    fake = types.ModuleType("fredapi")

    class FakeFred:
        def __init__(self, api_key=None):
            assert api_key, "Fred should receive an api_key"

        def get_series(self, series_id, observation_start=None, observation_end=None):
            if isinstance(series_or_exc, Exception):
                raise series_or_exc
            return series_or_exc

    fake.Fred = FakeFred  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "fredapi", fake)


def test_fetch_series_returns_series_on_success(monkeypatch):
    pd = pytest.importorskip("pandas")
    s = pd.Series(
        [0.45, 0.30, -0.10],
        index=pd.to_datetime(["2026-05-13", "2026-05-14", "2026-05-15"]),
    )
    _install_fake_fredapi(monkeypatch, s)

    out = fred_client.fetch_series("T10Y2Y", start="2026-05-13", settings=_fake_settings())
    assert out is not None
    assert out.name == "value"
    assert len(out) == 3
    assert list(out.index) == sorted(list(out.index))


def test_fetch_series_returns_none_when_no_key():
    out = fred_client.fetch_series("T10Y2Y", start="2026-05-13", settings=_fake_settings(key=None))
    assert out is None


def test_fetch_series_returns_none_when_fredapi_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "fredapi", None)
    out = fred_client.fetch_series("T10Y2Y", start="2026-05-13", settings=_fake_settings())
    assert out is None


def test_fetch_series_returns_none_on_exception(monkeypatch):
    _install_fake_fredapi(monkeypatch, RuntimeError("403 Forbidden"))
    out = fred_client.fetch_series("T10Y2Y", start="2026-05-13", settings=_fake_settings())
    assert out is None


def test_fetch_series_drops_nan(monkeypatch):
    pd = pytest.importorskip("pandas")
    s = pd.Series(
        [0.45, float("nan"), 0.30],
        index=pd.to_datetime(["2026-05-13", "2026-05-14", "2026-05-15"]),
    )
    _install_fake_fredapi(monkeypatch, s)

    out = fred_client.fetch_series("T10Y2Y", start="2026-05-13", settings=_fake_settings())
    assert out is not None
    assert len(out) == 2  # NaN 被 dropna 去掉
