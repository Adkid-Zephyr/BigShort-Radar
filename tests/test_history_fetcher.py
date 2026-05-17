"""tests for src/fetch/history_fetcher.py — 路由 + 异常处理。

mock 底层 fred_client / yf_client，不打真实网络。
"""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from src.fetch import history_fetcher as hf


# ── 正常路由 ─────────────────────────────────────────────────

def test_fred_routes_to_fred_client():
    fake_series = pd.Series([1.0, 2.0])
    with patch("src.fetch.history_fetcher.fred_client.fetch_series", return_value=fake_series) as m:
        out = hf.fetch_history("FRED:T10Y2Y", start="2020-01-01", end="2020-12-31")
    assert out is fake_series
    m.assert_called_once_with("T10Y2Y", start="2020-01-01", end="2020-12-31")


def test_yf_routes_to_yf_client():
    fake = pd.Series([13.4])
    with patch("src.fetch.history_fetcher.yf_client.fetch_close", return_value=fake) as m:
        out = hf.fetch_history("YF:^VIX", start="2020-01-01")
    assert out is fake
    m.assert_called_once_with("^VIX", start="2020-01-01", end=None)


def test_yahoo_alias_routes_same():
    fake = pd.Series([13.4])
    with patch("src.fetch.history_fetcher.yf_client.fetch_close", return_value=fake) as m:
        out = hf.fetch_history("YAHOO:^VIX", start="2020-01-01")
    assert out is fake
    m.assert_called_once_with("^VIX", start="2020-01-01", end=None)


def test_prefix_case_insensitive():
    """FRED:/fred:/FRed: 都应路由到 FRED."""
    with patch("src.fetch.history_fetcher.fred_client.fetch_series", return_value=pd.Series([1.0])) as m:
        hf.fetch_history("fred:T10Y2Y", start="2020-01-01")
        hf.fetch_history("FRed:T10Y2Y", start="2020-01-01")
    assert m.call_count == 2


def test_prefix_strips_whitespace():
    with patch("src.fetch.history_fetcher.fred_client.fetch_series", return_value=pd.Series([1.0])) as m:
        hf.fetch_history("  FRED  :  T10Y2Y  ", start="2020-01-01")
    m.assert_called_once_with("T10Y2Y", start="2020-01-01", end=None)


# ── 不支持 / 边界 ─────────────────────────────────────────────

def test_unknown_prefix_returns_none(caplog):
    """OECD/CBOE 等无 client 路由的前缀应返 None 不抛."""
    out = hf.fetch_history("OECD:M01", start="2020-01-01")
    assert out is None


def test_no_colon_returns_none():
    assert hf.fetch_history("T10Y2Y", start="2020-01-01") is None


def test_empty_ident_returns_none():
    assert hf.fetch_history("FRED:", start="2020-01-01") is None
    assert hf.fetch_history("FRED:   ", start="2020-01-01") is None


def test_none_source_returns_none():
    assert hf.fetch_history(None, start="2020-01-01") is None  # type: ignore[arg-type]


def test_empty_string_returns_none():
    assert hf.fetch_history("", start="2020-01-01") is None


def test_multi_source_with_comma_returns_none():
    """派生指标含逗号 → 路由层拒绝（让上层处理）."""
    out = hf.fetch_history("YF:^VIX,YF:^VIX3M", start="2020-01-01")
    assert out is None


def test_non_string_source_returns_none():
    assert hf.fetch_history(123, start="2020-01-01") is None  # type: ignore[arg-type]


# ── 底层 client 失败传透 ─────────────────────────────────────

def test_fred_client_returns_none_propagates():
    with patch("src.fetch.history_fetcher.fred_client.fetch_series", return_value=None):
        assert hf.fetch_history("FRED:NONEXIST", start="2020-01-01") is None


def test_yf_client_returns_none_propagates():
    with patch("src.fetch.history_fetcher.yf_client.fetch_close", return_value=None):
        assert hf.fetch_history("YF:NONEXIST", start="2020-01-01") is None
