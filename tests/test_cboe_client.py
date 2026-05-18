"""tests for src/fetch/cboe_client.py."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.fetch import cboe_client


class _Resp:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_fetch_index_history_parses_close(monkeypatch):
    csv = "DATE,OPEN,HIGH,LOW,CLOSE\n01/02/2024,10,11,9,10.5\n01/03/2024,12,13,11,12.5\n"
    monkeypatch.setattr(cboe_client.requests, "get", lambda *a, **k: _Resp(csv))
    s = cboe_client.fetch_index_history("VIX9D", start="2024-01-03")
    assert s is not None
    assert len(s) == 1
    assert s.iloc[0] == pytest.approx(12.5)
    assert s.name == "value"


def test_fetch_index_history_bad_http_returns_none(monkeypatch):
    monkeypatch.setattr(cboe_client.requests, "get", lambda *a, **k: _Resp("x", status_code=404))
    assert cboe_client.fetch_index_history("BAD", start="2024-01-01") is None


def test_fetch_index_history_bad_columns_returns_none(monkeypatch):
    monkeypatch.setattr(cboe_client.requests, "get", lambda *a, **k: _Resp("A,B\n1,2\n"))
    assert cboe_client.fetch_index_history("BAD", start="2024-01-01") is None


def test_fetch_put_call_ratios_parses_embedded_json(monkeypatch):
    ratios = (
        '"ratios":[{"name":"TOTAL PUT/CALL RATIO","value":"0.93"},'
        '{"name":"INDEX PUT/CALL RATIO","value":"1.03"},'
        '{"name":"EXCHANGE TRADED PRODUCTS PUT/CALL RATIO","value":"1.35"},'
        '{"name":"EQUITY PUT/CALL RATIO","value":"0.59"},'
        '{"name":"CBOE VOLATILITY INDEX (VIX) PUT/CALL RATIO","value":"0.44"}],"volumeAndOi"'
    )
    monkeypatch.setattr(cboe_client.requests, "get", lambda *a, **k: _Resp(ratios))
    out = cboe_client.fetch_put_call_ratios()
    assert out["total"] == pytest.approx(0.93)
    assert out["index"] == pytest.approx(1.03)
    assert out["etp"] == pytest.approx(1.35)
    assert out["equity"] == pytest.approx(0.59)
    assert out["vix"] == pytest.approx(0.44)


def test_fetch_put_call_ratios_no_match_returns_empty(monkeypatch):
    monkeypatch.setattr(cboe_client.requests, "get", lambda *a, **k: _Resp("no ratios here"))
    assert cboe_client.fetch_put_call_ratios() == {}


def test_fetch_put_call_ratios_http_error_returns_empty(monkeypatch):
    monkeypatch.setattr(cboe_client.requests, "get", lambda *a, **k: _Resp("x", status_code=500))
    assert cboe_client.fetch_put_call_ratios() == {}
