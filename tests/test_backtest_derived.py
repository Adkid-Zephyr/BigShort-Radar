"""tests for src/backtest/derived.py(派生指标现场计算)。"""
from __future__ import annotations

import pytest

from src.backtest import derived as dmod
from src.store import history_db as hdbmod


# ── helpers ──────────────────────────────────────────────────


@pytest.fixture()
def hist_conn(tmp_path):
    p = tmp_path / "h.sqlite"
    with hdbmod.open_history_db(p) as c:
        # vts 成分:vix_fred + vix3m
        hdbmod.upsert_point(c, "vix_fred", "2024-01-08", 20.0, "FRED:VIXCLS")
        hdbmod.upsert_point(c, "vix3m", "2024-01-08", 25.0, "YF:^VIX3M")
        # sofr_iorb 成分:sofr_raw + iorb_raw(单位 %)
        hdbmod.upsert_point(c, "sofr_raw", "2024-02-01", 5.30, "FRED:SOFR")
        hdbmod.upsert_point(c, "iorb_raw", "2024-02-01", 5.40, "FRED:IORB")
        # fra_ois 成分:dgs3mo + sofr_raw
        hdbmod.upsert_point(c, "dgs3mo", "2024-03-01", 5.50, "FRED:DGS3MO")
        hdbmod.upsert_point(c, "sofr_raw", "2024-03-01", 5.30, "FRED:SOFR")
        yield c


# ── 注册表 + is_derived ──────────────────────────────────────


def test_is_derived_recognizes_three():
    assert dmod.is_derived("vix_term_structure")
    assert dmod.is_derived("sofr_iorb")
    assert dmod.is_derived("fra_ois")


def test_is_derived_rejects_unknown():
    assert not dmod.is_derived("vix")
    assert not dmod.is_derived("foo")


def test_derived_registry_has_three_entries():
    assert set(dmod.DERIVED.keys()) == {"vix_term_structure", "sofr_iorb", "fra_ois"}


# ── fetch_derived_value 核心计算 ────────────────────────────


def test_fetch_vts_basic(hist_conn):
    """vts = vix / vix3m = 20 / 25 = 0.8(contango 状态)"""
    v = dmod.fetch_derived_value(hist_conn, "vix_term_structure", "2024-01-08")
    assert v == pytest.approx(0.8)


def test_fetch_sofr_iorb_basic(hist_conn):
    """sofr_iorb = |5.30 - 5.40| × 100 = 10 bp"""
    v = dmod.fetch_derived_value(hist_conn, "sofr_iorb", "2024-02-01")
    assert v == pytest.approx(10.0)


def test_fetch_fra_ois_basic(hist_conn):
    """fra_ois = 5.50 - 5.30 = 0.20 %"""
    v = dmod.fetch_derived_value(hist_conn, "fra_ois", "2024-03-01")
    assert v == pytest.approx(0.20)


def test_fetch_missing_component_returns_none(tmp_path):
    """vix_fred 没写,vts 不可计算 → None"""
    p = tmp_path / "h2.sqlite"
    with hdbmod.open_history_db(p) as conn:
        hdbmod.upsert_point(conn, "vix3m", "2024-01-08", 25.0, "YF:^VIX3M")
        v = dmod.fetch_derived_value(conn, "vix_term_structure", "2024-01-08")
        assert v is None


def test_fetch_forward_fill_works(hist_conn):
    """target=01-12,vix_fred/vix3m 在 01-08,forward_fill=10 应能拿到。"""
    v = dmod.fetch_derived_value(
        hist_conn, "vix_term_structure", "2024-01-12", forward_fill_days=10
    )
    assert v == pytest.approx(0.8)


def test_fetch_forward_fill_too_old_returns_none(hist_conn):
    """forward_fill=2 不够覆盖 4 天 gap → None"""
    v = dmod.fetch_derived_value(
        hist_conn, "vix_term_structure", "2024-01-12", forward_fill_days=2
    )
    assert v is None


def test_fetch_unknown_name_raises(hist_conn):
    with pytest.raises(KeyError):
        dmod.fetch_derived_value(hist_conn, "not_a_derived", "2024-01-08")


def test_fetch_zero_division_safe(tmp_path):
    """vix3m=0 应当返回 None,而非抛 ZeroDivisionError"""
    p = tmp_path / "h3.sqlite"
    with hdbmod.open_history_db(p) as conn:
        hdbmod.upsert_point(conn, "vix_fred", "2024-01-08", 20.0, "FRED:VIXCLS")
        hdbmod.upsert_point(conn, "vix3m", "2024-01-08", 0.0, "YF:^VIX3M")
        v = dmod.fetch_derived_value(conn, "vix_term_structure", "2024-01-08")
        assert v is None
