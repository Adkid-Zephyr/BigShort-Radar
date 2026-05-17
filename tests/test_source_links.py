"""tests for src/web/source_links.py"""
from __future__ import annotations

import pytest

from src.web.source_links import source_url


class TestFRED:
    def test_simple_series(self) -> None:
        assert source_url("FRED:T10Y2Y") == "https://fred.stlouisfed.org/series/T10Y2Y"

    def test_long_id(self) -> None:
        assert (
            source_url("FRED:BAMLH0A0HYM2")
            == "https://fred.stlouisfed.org/series/BAMLH0A0HYM2"
        )

    def test_oecd_via_fred_id(self) -> None:
        # 日本 10Y FRED 那条用 OECD-derived series
        assert (
            source_url("FRED:IRLTLT01JPM156N")
            == "https://fred.stlouisfed.org/series/IRLTLT01JPM156N"
        )


class TestYahoo:
    def test_caret_ticker_encoded(self) -> None:
        # ^VIX 必须 url-encode 成 %5EVIX
        assert source_url("YF:^VIX") == "https://finance.yahoo.com/quote/%5EVIX"

    def test_yahoo_alias(self) -> None:
        assert source_url("YAHOO:^VIX") == "https://finance.yahoo.com/quote/%5EVIX"

    def test_plain_ticker(self) -> None:
        assert source_url("YF:JPY=X") == "https://finance.yahoo.com/quote/JPY%3DX"


class TestOther:
    def test_oecd(self) -> None:
        assert (
            source_url("OECD:M01")
            == "https://data.oecd.org/searchresults/?q=M01"
        )

    def test_cboe_lowercases(self) -> None:
        assert (
            source_url("CBOE:VIX")
            == "https://www.cboe.com/tradable_products/vix/"
        )


class TestEdgeCases:
    def test_none(self) -> None:
        assert source_url(None) is None

    def test_empty_string(self) -> None:
        assert source_url("") is None

    def test_no_colon(self) -> None:
        assert source_url("FREDT10Y2Y") is None

    def test_unknown_prefix(self) -> None:
        assert source_url("BLOOMBERG:USGG10YR") is None

    def test_empty_ident(self) -> None:
        assert source_url("FRED:") is None

    def test_multi_source_returns_none(self) -> None:
        # 派生指标如 "YF:^VIX,YF:^VIX3M" 应交给 registry 手填，本模块拒绝猜测
        assert source_url("YF:^VIX,YF:^VIX3M") is None

    def test_non_string(self) -> None:
        assert source_url(123) is None  # type: ignore[arg-type]

    def test_whitespace_around_prefix(self) -> None:
        assert source_url("  FRED  :  T10Y2Y  ") == "https://fred.stlouisfed.org/series/T10Y2Y"

    def test_case_insensitive_prefix(self) -> None:
        assert source_url("fred:T10Y2Y") == "https://fred.stlouisfed.org/series/T10Y2Y"
