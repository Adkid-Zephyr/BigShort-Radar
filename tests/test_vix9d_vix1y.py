"""tests for VIX9D / VIX1Y CBOE indicators."""
from __future__ import annotations

import pytest

from src.compute.indicators import vix1y, vix9d
from src.compute.thresholds import Level
from src.store import db as dbmod


@pytest.fixture()
def conn(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as c:
        yield c


def _series(dates_values):
    pd = pytest.importorskip("pandas")
    idx = pd.to_datetime([d for d, _ in dates_values])
    return pd.Series([v for _, v in dates_values], index=idx, name="value")


@pytest.mark.parametrize("mod,green,yellow,red", [
    (vix9d, 18.0, 25.0, 40.0),
    (vix1y, 18.0, 25.0, 35.0),
])
def test_classify_boundaries(mod, green, yellow, red):
    assert mod.classify_value(green) == Level.GREEN
    assert mod.classify_value(yellow) == Level.YELLOW
    assert mod.classify_value(red) == Level.RED


@pytest.mark.parametrize("mod,symbol,source", [
    (vix9d, "VIX9D", "CBOE:VIX9D_History.csv"),
    (vix1y, "VIX1Y", "CBOE:VIX1Y_History.csv"),
])
def test_fetch_and_store(conn, monkeypatch, mod, symbol, source):
    s = _series([("2026-05-13", 18.0), ("2026-05-14", 22.0)])

    def fake_fetch_index_history(sym, start, end=None):
        assert sym == symbol
        return s

    monkeypatch.setattr(mod.cboe_client, "fetch_index_history", fake_fetch_index_history)
    n = mod.fetch_and_store(conn, start="2026-05-13")
    assert n == 2
    rows = dbmod.get_series(conn, mod.NAME)
    assert len(rows) == 2
    assert rows[0]["source"] == source


def test_fetch_and_store_empty_returns_zero(conn, monkeypatch):
    monkeypatch.setattr(vix9d.cboe_client, "fetch_index_history", lambda *a, **k: None)
    assert vix9d.fetch_and_store(conn, start="2026-05-13") == 0
