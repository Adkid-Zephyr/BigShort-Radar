"""VIX 指标测试：mock fred_client，覆盖分类 + fetch+store 全流程。

iter 58 起 VIX 主流程切 FRED:VIXCLS（绕开 yahoo 限速），mock 目标从 yf_client 改 fred_client。
"""
from __future__ import annotations

import pytest

from src.compute.indicators import vix as vixmod
from src.compute.thresholds import Level
from src.store import db as dbmod


# ── classify_value ───────────────────────────────────────────
def test_classify_low_is_green():
    assert vixmod.classify_value(15.0) == Level.GREEN


def test_classify_at_low_is_green():
    # 边界规则：up 方向 value == low → GREEN
    assert vixmod.classify_value(20.0) == Level.GREEN


def test_classify_mid_is_yellow():
    assert vixmod.classify_value(25.0) == Level.YELLOW


def test_classify_at_high_is_yellow():
    # value == high → YELLOW
    assert vixmod.classify_value(30.0) == Level.YELLOW


def test_classify_high_is_red():
    assert vixmod.classify_value(45.0) == Level.RED


# ── 模块常量校验（防回退到 yahoo）─────────────────────────────
def test_source_is_fred():
    """iter 58：VIX 主流程已切 FRED:VIXCLS，不再走 yahoo。"""
    assert vixmod.SOURCE == "FRED:VIXCLS"
    assert vixmod.SERIES_ID == "VIXCLS"


# ── fetch_and_store ──────────────────────────────────────────
@pytest.fixture()
def conn(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as c:
        yield c


def _mock_series(monkeypatch, dates_values):
    """构造 pandas.Series 替代 fred_client.fetch_series 的返回。"""
    pd = pytest.importorskip("pandas")
    idx = pd.to_datetime([d for d, _ in dates_values])
    vals = [v for _, v in dates_values]
    s = pd.Series(vals, index=idx, name="value")

    def fake_fetch_series(series_id, start, end=None, settings=None):
        assert series_id == "VIXCLS"
        return s

    monkeypatch.setattr(vixmod.fred_client, "fetch_series", fake_fetch_series)


def test_fetch_and_store_writes_rows(conn, monkeypatch):
    _mock_series(monkeypatch, [
        ("2026-05-13", 17.5),
        ("2026-05-14", 22.1),
        ("2026-05-15", 33.0),
    ])
    n = vixmod.fetch_and_store(conn, start="2026-05-13")
    assert n == 3

    rows = dbmod.get_series(conn, "vix")
    assert len(rows) == 3
    by_date = {r["date"]: r for r in rows}
    assert by_date["2026-05-13"]["value"] == pytest.approx(17.5)
    assert by_date["2026-05-15"]["value"] == pytest.approx(33.0)
    assert by_date["2026-05-15"]["source"] == "FRED:VIXCLS"


def test_fetch_and_store_returns_zero_on_empty(conn, monkeypatch):
    monkeypatch.setattr(vixmod.fred_client, "fetch_series",
                        lambda series_id, start, end=None, settings=None: None)
    n = vixmod.fetch_and_store(conn, start="2026-05-13")
    assert n == 0
    assert dbmod.get_series(conn, "vix") == []


def test_fetch_and_store_is_idempotent(conn, monkeypatch):
    _mock_series(monkeypatch, [("2026-05-15", 19.0)])
    vixmod.fetch_and_store(conn, start="2026-05-15")
    # 再跑一次，值变了
    _mock_series(monkeypatch, [("2026-05-15", 21.5)])
    vixmod.fetch_and_store(conn, start="2026-05-15")

    rows = dbmod.get_series(conn, "vix")
    assert len(rows) == 1  # 仍只有一行
    assert rows[0]["value"] == pytest.approx(21.5)


def test_fetch_and_store_skips_non_numeric(conn, monkeypatch):
    pd = pytest.importorskip("pandas")
    idx = pd.to_datetime(["2026-05-14", "2026-05-15"])
    s = pd.Series([float("nan"), 18.0], index=idx, name="close")

    monkeypatch.setattr(vixmod.fred_client, "fetch_series",
                        lambda series_id, start, end=None, settings=None: s)
    n = vixmod.fetch_and_store(conn, start="2026-05-14")
    # NaN 被跳过；18.0 入库
    rows = dbmod.get_series(conn, "vix")
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-05-15"
    assert rows[0]["value"] == 18.0
    assert n == 1
