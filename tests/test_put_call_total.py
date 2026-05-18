"""tests for CBOE total Put/Call Ratio indicator."""
from __future__ import annotations

import pytest

from src.compute.indicators import put_call_equity as pce
from src.compute.indicators import put_call_index as pci
from src.compute.indicators import put_call_total as pc
from src.compute.thresholds import Level
from src.store import db as dbmod


@pytest.fixture()
def conn(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as c:
        yield c


def test_classify_boundaries():
    assert pc.classify_value(0.70) == Level.GREEN
    assert pc.classify_value(0.95) == Level.YELLOW
    assert pc.classify_value(1.30) == Level.RED


def test_fetch_and_store(conn, monkeypatch):
    monkeypatch.setattr(pc.cboe_client, "fetch_put_call_ratios", lambda: {"total": 0.93})
    n = pc.fetch_and_store(conn)
    assert n == 1
    rows = dbmod.get_series(conn, pc.NAME)
    assert len(rows) == 1
    assert rows[0]["value"] == pytest.approx(0.93)
    assert rows[0]["source"] == pc.SOURCE


def test_fetch_and_store_missing_total_returns_zero(conn, monkeypatch):
    monkeypatch.setattr(pc.cboe_client, "fetch_put_call_ratios", lambda: {"equity": 0.59})
    assert pc.fetch_and_store(conn) == 0
    assert dbmod.get_series(conn, pc.NAME) == []


def test_index_and_equity_modules_write_own_names(conn, monkeypatch):
    ratios = {"index": 1.03, "equity": 0.59}
    monkeypatch.setattr(pci.cboe_client, "fetch_put_call_ratios", lambda: ratios)
    monkeypatch.setattr(pce.cboe_client, "fetch_put_call_ratios", lambda: ratios)
    assert pci.fetch_and_store(conn) == 1
    assert pce.fetch_and_store(conn) == 1
    idx_rows = dbmod.get_series(conn, pci.NAME)
    eq_rows = dbmod.get_series(conn, pce.NAME)
    assert idx_rows[0]["value"] == pytest.approx(1.03)
    assert eq_rows[0]["value"] == pytest.approx(0.59)


def test_index_and_equity_classify():
    assert pci.classify_value(0.80) == Level.GREEN
    assert pci.classify_value(1.00) == Level.YELLOW
    assert pci.classify_value(1.40) == Level.RED
    assert pce.classify_value(0.40) == Level.GREEN
    assert pce.classify_value(0.70) == Level.YELLOW
    assert pce.classify_value(1.00) == Level.RED
