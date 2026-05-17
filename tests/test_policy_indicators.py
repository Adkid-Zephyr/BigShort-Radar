"""tests for iter 44 政策反应指标：WALCL / ON RRP / TGA."""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from src.compute.indicators import on_rrp as on_rrp_ind
from src.compute.indicators import tga as tga_ind
from src.compute.indicators import walcl as walcl_ind
from src.compute.thresholds import Level
from src.store import db as dbmod


# ── walcl ────────────────────────────────────────────────────

class TestWalcl:
    def test_classify_green(self):
        assert walcl_ind.classify_value(7_000_000) == Level.GREEN

    def test_classify_yellow(self):
        assert walcl_ind.classify_value(8_500_000) == Level.YELLOW

    def test_classify_red(self):
        assert walcl_ind.classify_value(9_500_000) == Level.RED

    def test_constants(self):
        assert walcl_ind.NAME == "walcl"
        assert walcl_ind.SOURCE == "FRED:WALCL"
        assert walcl_ind.DIRECTION == "up"

    def test_fetch_and_store_calls_fred_and_db(self, tmp_path):
        idx = pd.to_datetime(["2024-01-03"])
        s = pd.Series([7_300_000.0], index=idx)
        with dbmod.open_db(tmp_path / "t.sqlite") as conn:
            with patch("src.compute.indicators.walcl.fred_client.fetch_series", return_value=s):
                n = walcl_ind.fetch_and_store(conn, start="2024-01-01")
        assert n == 1


# ── on_rrp ───────────────────────────────────────────────────

class TestOnRrp:
    def test_direction_down(self):
        assert on_rrp_ind.DIRECTION == "down"

    def test_classify_green_high_balance(self):
        """大于 500B 应该 GREEN（缓冲充裕）。"""
        assert on_rrp_ind.classify_value(800_000) == Level.GREEN

    def test_classify_yellow_mid_balance(self):
        assert on_rrp_ind.classify_value(300_000) == Level.YELLOW

    def test_classify_red_low_balance(self):
        """< 100B = RED（缓冲耗尽）。"""
        assert on_rrp_ind.classify_value(50_000) == Level.RED

    def test_constants(self):
        assert on_rrp_ind.NAME == "on_rrp"
        assert on_rrp_ind.SOURCE == "FRED:RRPONTSYD"

    def test_fetch_and_store(self, tmp_path):
        idx = pd.to_datetime(["2024-01-03"])
        s = pd.Series([200_000.0], index=idx)
        with dbmod.open_db(tmp_path / "t.sqlite") as conn:
            with patch("src.compute.indicators.on_rrp.fred_client.fetch_series", return_value=s):
                n = on_rrp_ind.fetch_and_store(conn, start="2024-01-01")
        assert n == 1


# ── tga ──────────────────────────────────────────────────────

class TestTga:
    def test_direction_up(self):
        assert tga_ind.DIRECTION == "up"

    def test_classify_green(self):
        """< 600B 正常。"""
        assert tga_ind.classify_value(400_000) == Level.GREEN

    def test_classify_yellow(self):
        assert tga_ind.classify_value(800_000) == Level.YELLOW

    def test_classify_red(self):
        """> 1T 显著吸流动性。"""
        assert tga_ind.classify_value(1_500_000) == Level.RED

    def test_constants(self):
        assert tga_ind.NAME == "tga"
        assert tga_ind.SOURCE == "FRED:WTREGEN"

    def test_fetch_and_store(self, tmp_path):
        idx = pd.to_datetime(["2024-01-03"])
        s = pd.Series([700_000.0], index=idx)
        with dbmod.open_db(tmp_path / "t.sqlite") as conn:
            with patch("src.compute.indicators.tga.fred_client.fetch_series", return_value=s):
                n = tga_ind.fetch_and_store(conn, start="2024-01-01")
        assert n == 1


# ── 注册到 web app & daily_fetch ─────────────────────────────

def test_indicators_in_web_registry():
    """新指标应进 _INDICATOR_REGISTRY 并属于 政策 group。"""
    from src.web.app import _REGISTRY_BY_NAME
    assert "walcl" in _REGISTRY_BY_NAME
    assert "on_rrp" in _REGISTRY_BY_NAME
    assert "tga" in _REGISTRY_BY_NAME
    assert _REGISTRY_BY_NAME["walcl"]["group"] == "政策"


def test_indicators_in_daily_fetch_fetchers():
    """daily_fetch FETCHERS 应包含三条新指标。"""
    from scripts.daily_fetch import FETCHERS
    names = {f.name for f in FETCHERS}
    assert "walcl" in names
    assert "on_rrp" in names
    assert "tga" in names


def test_indicators_in_backfill_targets():
    from scripts.backfill_history import TARGETS
    names = {t.name for t in TARGETS}
    assert "walcl" in names
    assert "on_rrp" in names
    assert "tga" in names


def test_policy_group_in_order():
    from src.web.app import _GROUP_ORDER
    assert "政策" in _GROUP_ORDER
