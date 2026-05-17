"""tests for iter 45 波动率结构 2 条：VVIX / SKEW."""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from src.compute.indicators import skew as skew_ind
from src.compute.indicators import vvix as vvix_ind
from src.compute.thresholds import Level
from src.store import db as dbmod


class TestVvix:
    def test_classify_green(self):
        assert vvix_ind.classify_value(80) == Level.GREEN

    def test_classify_yellow(self):
        assert vvix_ind.classify_value(100) == Level.YELLOW

    def test_classify_red(self):
        assert vvix_ind.classify_value(150) == Level.RED

    def test_constants(self):
        assert vvix_ind.NAME == "vvix"
        assert vvix_ind.SOURCE == "YF:^VVIX"
        assert vvix_ind.DIRECTION == "up"

    def test_fetch_and_store(self, tmp_path):
        idx = pd.to_datetime(["2024-01-03"])
        s = pd.Series([85.0], index=idx)
        with dbmod.open_db(tmp_path / "t.sqlite") as conn:
            with patch("src.compute.indicators.vvix.yf_client.fetch_close", return_value=s):
                n = vvix_ind.fetch_and_store(conn, start="2024-01-01")
        assert n == 1


class TestSkew:
    def test_classify_green(self):
        assert skew_ind.classify_value(120) == Level.GREEN

    def test_classify_yellow(self):
        assert skew_ind.classify_value(140) == Level.YELLOW

    def test_classify_red(self):
        assert skew_ind.classify_value(150) == Level.RED

    def test_constants(self):
        assert skew_ind.NAME == "skew"
        assert skew_ind.SOURCE == "YF:^SKEW"
        assert skew_ind.DIRECTION == "up"

    def test_fetch_and_store(self, tmp_path):
        idx = pd.to_datetime(["2024-01-03"])
        s = pd.Series([130.0], index=idx)
        with dbmod.open_db(tmp_path / "t.sqlite") as conn:
            with patch("src.compute.indicators.skew.yf_client.fetch_close", return_value=s):
                n = skew_ind.fetch_and_store(conn, start="2024-01-01")
        assert n == 1


def test_indicators_in_web_registry():
    from src.web.app import _REGISTRY_BY_NAME
    assert "vvix" in _REGISTRY_BY_NAME
    assert "skew" in _REGISTRY_BY_NAME
    assert _REGISTRY_BY_NAME["vvix"]["group"] == "波动率"
    assert _REGISTRY_BY_NAME["skew"]["group"] == "波动率"


def test_indicators_in_daily_fetch():
    from scripts.daily_fetch import FETCHERS
    names = {f.name for f in FETCHERS}
    assert "vvix" in names
    assert "skew" in names


def test_indicators_in_backfill():
    from scripts.backfill_history import TARGETS
    names = {t.name for t in TARGETS}
    assert "vvix" in names
    assert "skew" in names
