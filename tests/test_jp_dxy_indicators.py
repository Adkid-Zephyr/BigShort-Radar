"""日本/全球美元 3 指标测试：USDJPY、DXY、JP 10Y。

mock fred_client，覆盖分类 + fetch+store。结构同其他 FRED 指标。
"""
from __future__ import annotations

import pytest

from src.compute.indicators import dxy as dxymod
from src.compute.indicators import jp_10y as jpmod
from src.compute.indicators import usdjpy as fxmod
from src.compute.thresholds import Level
from src.store import db as dbmod


@pytest.fixture()
def conn(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as c:
        yield c


def _series(monkeypatch, dates_values):
    pd = pytest.importorskip("pandas")
    idx = pd.to_datetime([d for d, _ in dates_values])
    return pd.Series([v for _, v in dates_values], index=idx, name="value")


# ── usdjpy ───────────────────────────────────────────────────
def test_usdjpy_classify():
    assert fxmod.classify_value(140.0) == Level.GREEN
    assert fxmod.classify_value(145.0) == Level.GREEN  # at low
    assert fxmod.classify_value(150.0) == Level.YELLOW
    assert fxmod.classify_value(160.0) == Level.YELLOW  # at high
    assert fxmod.classify_value(165.0) == Level.RED


def test_usdjpy_fetch_and_store(conn, monkeypatch):
    s = _series(monkeypatch, [("2026-05-13", 156.5), ("2026-05-14", 158.2)])
    monkeypatch.setattr(
        fxmod.fred_client, "fetch_series",
        lambda series_id, start, end=None, settings=None: s if series_id == "DEXJPUS" else None,
    )
    n = fxmod.fetch_and_store(conn, start="2026-05-13")
    assert n == 2
    rows = dbmod.get_series(conn, "usdjpy")
    assert len(rows) == 2
    assert rows[0]["source"] == "FRED:DEXJPUS"


# ── dxy ─────────────────────────────────────────────────────
def test_dxy_classify():
    assert dxymod.classify_value(105.0) == Level.GREEN
    assert dxymod.classify_value(110.0) == Level.GREEN  # at low
    assert dxymod.classify_value(118.0) == Level.YELLOW
    assert dxymod.classify_value(125.0) == Level.YELLOW  # at high
    assert dxymod.classify_value(127.0) == Level.RED


def test_dxy_fetch_and_store(conn, monkeypatch):
    s = _series(monkeypatch, [("2026-05-13", 117.0), ("2026-05-14", 118.0)])
    monkeypatch.setattr(
        dxymod.fred_client, "fetch_series",
        lambda series_id, start, end=None, settings=None: s if series_id == "DTWEXBGS" else None,
    )
    n = dxymod.fetch_and_store(conn, start="2026-05-13")
    assert n == 2
    rows = dbmod.get_series(conn, "dxy_broad")
    assert rows[0]["source"] == "FRED:DTWEXBGS"


# ── jp_10y ──────────────────────────────────────────────────
def test_jp10y_classify():
    assert jpmod.classify_value(0.5) == Level.GREEN
    assert jpmod.classify_value(1.0) == Level.GREEN  # at low
    assert jpmod.classify_value(1.5) == Level.YELLOW
    assert jpmod.classify_value(2.0) == Level.YELLOW  # at high
    assert jpmod.classify_value(2.5) == Level.RED


def test_jp10y_fetch_and_store(conn, monkeypatch):
    s = _series(monkeypatch, [("2026-04-01", 1.45), ("2026-05-01", 1.55)])
    monkeypatch.setattr(
        jpmod.fred_client, "fetch_series",
        lambda series_id, start, end=None, settings=None: s if series_id == "IRLTLT01JPM156N" else None,
    )
    n = jpmod.fetch_and_store(conn, start="2026-04-01")
    assert n == 2
    rows = dbmod.get_series(conn, "jp_10y")
    assert rows[0]["source"] == "FRED:IRLTLT01JPM156N"
