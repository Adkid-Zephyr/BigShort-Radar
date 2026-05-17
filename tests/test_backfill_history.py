"""tests for scripts/backfill_history.py — mock fetcher + cache DB."""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from scripts import backfill_history as bf
from src.store import history_db as hdb


# ── 派生指标识别 ─────────────────────────────────────────────

def test_is_derived_with_slash():
    assert bf._is_derived("YF:^VIX/^VIX3M") is True


def test_is_derived_with_comma():
    assert bf._is_derived("YF:^VIX,YF:^VIX3M") is True


def test_is_derived_fred_with_dash():
    """FRED:SOFR-IORB 是减法派生，应识别为派生（FRED 真实 series id 不含 -）。"""
    assert bf._is_derived("FRED:SOFR-IORB") is True


def test_is_derived_yf_dash_not_treated_as_derived():
    """YF ticker 偶尔含 -（如 BRK-B），不算派生。规则只对 FRED 前缀生效。"""
    assert bf._is_derived("YF:BRK-B") is False


def test_not_derived_normal():
    assert bf._is_derived("FRED:T10Y2Y") is False
    assert bf._is_derived("YF:^VIX") is False


# ── _default_start ────────────────────────────────────────────

def test_default_start_5_years_ago():
    out = bf._default_start(years=5)
    # ISO YYYY-MM-DD，10 字符
    assert len(out) == 10
    assert out[4] == "-" and out[7] == "-"


# ── run_one ───────────────────────────────────────────────────

@pytest.fixture()
def conn(tmp_path):
    p = tmp_path / "h.sqlite"
    with hdb.open_history_db(p) as c:
        yield c


def test_run_one_skips_derived(conn):
    """派生指标（含 /）应跳过且返 0，不调底层 fetcher."""
    target = bf.Target(name="vix_term_structure", source="YF:^VIX/^VIX3M")
    with patch("scripts.backfill_history.hf.fetch_history") as m:
        n = bf.run_one(target, start="2020-01-01", end=None, conn=conn)
    assert n == 0
    m.assert_not_called()
    assert hdb.count_points(conn) == 0


def test_run_one_inserts_normal_series(conn):
    idx = pd.to_datetime(["2024-01-02", "2024-01-03"])
    fake = pd.Series([13.4, 14.0], index=idx)
    target = bf.Target(name="vix", source="YF:^VIX")
    with patch("scripts.backfill_history.hf.fetch_history", return_value=fake):
        n = bf.run_one(target, start="2024-01-01", end=None, conn=conn)
    assert n == 2
    assert hdb.count_points(conn, name="vix") == 2


def test_run_one_handles_none_series(conn):
    """fetcher 返 None 时应返 0，不写入也不抛."""
    target = bf.Target(name="vix", source="YF:^VIX")
    with patch("scripts.backfill_history.hf.fetch_history", return_value=None):
        n = bf.run_one(target, start="2020-01-01", end=None, conn=conn)
    assert n == 0


def test_run_one_handles_fetcher_exception(conn):
    """底层抛异常也应返 0，不让脚本崩."""
    target = bf.Target(name="vix", source="YF:^VIX")
    with patch("scripts.backfill_history.hf.fetch_history", side_effect=RuntimeError("boom")):
        n = bf.run_one(target, start="2020-01-01", end=None, conn=conn)
    assert n == 0


# ── main ──────────────────────────────────────────────────────

def test_main_only_filter_no_match():
    """--only 给个不存在的 name 应返 2."""
    rc = bf.main(["--only", "nonexistent_indicator"])
    assert rc == 2


def test_main_only_filter_runs_one(tmp_path, monkeypatch):
    """--only 给一条存在的 name 应只跑那条."""
    # 用临时 cache 路径避免污染默认 path
    p = tmp_path / "h.sqlite"
    monkeypatch.setattr(bf.hdb, "HISTORY_DB_PATH", p)
    idx = pd.to_datetime(["2024-01-02"])
    fake = pd.Series([13.4], index=idx)
    with patch("scripts.backfill_history.hf.fetch_history", return_value=fake) as m:
        rc = bf.main(["--only", "vix", "--start", "2024-01-01"])
    assert rc == 0
    # 只调用一次（仅 vix）
    assert m.call_count == 1
    # cache 里只有 vix
    with hdb.open_history_db(p) as conn:
        assert hdb.count_points(conn, name="vix") == 1


def test_main_runs_all_targets(tmp_path, monkeypatch):
    """无 --only 应跑所有 target，派生跳过。"""
    p = tmp_path / "h.sqlite"
    monkeypatch.setattr(bf.hdb, "HISTORY_DB_PATH", p)
    idx = pd.to_datetime(["2024-01-02"])
    fake = pd.Series([1.0], index=idx)
    with patch("scripts.backfill_history.hf.fetch_history", return_value=fake) as m:
        rc = bf.main(["--start", "2024-01-01"])
    assert rc == 0
    # TARGETS 里 15 条（含 walcl/on_rrp/tga + vvix/skew），2 条派生（vix_term_structure, sofr_iorb），fetcher 应被调 13 次
    assert m.call_count == 13
