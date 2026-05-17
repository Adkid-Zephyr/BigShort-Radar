"""tests for iter 46 中国维度 + FRA-OIS 代理 4 条新指标."""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from src.compute.indicators import china_10y as china_10y_ind
from src.compute.indicators import china_fx_reserves as china_fx_ind
from src.compute.indicators import fra_ois as fra_ois_ind
from src.compute.indicators import usdcny as usdcny_ind
from src.compute.thresholds import Level
from src.store import db as dbmod


# ── FRA-OIS 代理 ─────────────────────────────────────────────

class TestFraOis:
    def test_classify_green(self):
        assert fra_ois_ind.classify_value(0.05) == Level.GREEN

    def test_classify_yellow(self):
        assert fra_ois_ind.classify_value(0.20) == Level.YELLOW

    def test_classify_red(self):
        assert fra_ois_ind.classify_value(0.50) == Level.RED

    def test_constants(self):
        assert fra_ois_ind.NAME == "fra_ois"
        assert fra_ois_ind.SOURCE == "FRED:DGS3MO-SOFR"

    def test_compute_spread(self):
        idx = pd.to_datetime(["2024-01-01", "2024-01-02"])
        tbill = pd.Series([5.30, 5.32], index=idx)
        sofr = pd.Series([5.20, 5.21], index=idx)
        spread = fra_ois_ind._compute_spread(tbill, sofr)
        assert spread is not None
        assert len(spread) == 2
        assert spread.iloc[0] == pytest.approx(0.10)

    def test_compute_spread_none_input(self):
        assert fra_ois_ind._compute_spread(None, None) is None
        assert fra_ois_ind._compute_spread(pd.Series([1]), None) is None

    def test_fetch_and_store(self, tmp_path):
        idx = pd.to_datetime(["2024-01-03"])
        tbill = pd.Series([5.30], index=idx)
        sofr = pd.Series([5.20], index=idx)
        with dbmod.open_db(tmp_path / "t.sqlite") as conn:
            with patch("src.compute.indicators.fra_ois.fred_client.fetch_series", side_effect=[tbill, sofr]):
                n = fra_ois_ind.fetch_and_store(conn, start="2024-01-01")
        assert n == 1


# ── 中国 3 条 ────────────────────────────────────────────────

class TestChinaFxReserves:
    def test_direction_down(self):
        assert china_fx_ind.DIRECTION == "down"

    def test_classify_green(self):
        """高储备 = 安全。"""
        assert china_fx_ind.classify_value(3_300_000_000_000) == Level.GREEN

    def test_classify_yellow(self):
        assert china_fx_ind.classify_value(3_050_000_000_000) == Level.YELLOW

    def test_classify_red(self):
        """< 3T 显著资本外流。"""
        assert china_fx_ind.classify_value(2_900_000_000_000) == Level.RED


class TestUsdCny:
    def test_direction_up(self):
        assert usdcny_ind.DIRECTION == "up"

    def test_classify_green(self):
        assert usdcny_ind.classify_value(7.05) == Level.GREEN

    def test_classify_yellow(self):
        assert usdcny_ind.classify_value(7.20) == Level.YELLOW

    def test_classify_red(self):
        assert usdcny_ind.classify_value(7.40) == Level.RED


class TestChina10y:
    def test_direction_down(self):
        assert china_10y_ind.DIRECTION == "down"

    def test_classify_green(self):
        """高利率 = 经济稳健。"""
        assert china_10y_ind.classify_value(2.7) == Level.GREEN

    def test_classify_yellow(self):
        assert china_10y_ind.classify_value(2.2) == Level.YELLOW

    def test_classify_red(self):
        """< 2% 通缩信号。"""
        assert china_10y_ind.classify_value(1.7) == Level.RED


# ── 注册到 web/daily_fetch/backfill ─────────────────────────

def test_indicators_in_web_registry():
    from src.web.app import _REGISTRY_BY_NAME
    for name in ("fra_ois", "china_fx_reserves", "usdcny", "china_10y"):
        assert name in _REGISTRY_BY_NAME, f"{name} 应该在 _REGISTRY_BY_NAME"
    assert _REGISTRY_BY_NAME["fra_ois"]["group"] == "流动性"
    assert _REGISTRY_BY_NAME["china_fx_reserves"]["group"] == "中国"
    assert _REGISTRY_BY_NAME["usdcny"]["group"] == "中国"
    assert _REGISTRY_BY_NAME["china_10y"]["group"] == "中国"


def test_china_group_in_order():
    from src.web.app import _GROUP_ORDER
    assert "中国" in _GROUP_ORDER


def test_indicators_in_daily_fetch():
    from scripts.daily_fetch import FETCHERS
    names = {f.name for f in FETCHERS}
    for n in ("fra_ois", "china_fx_reserves", "usdcny", "china_10y"):
        assert n in names, f"{n} 应该在 daily_fetch FETCHERS"


def test_indicators_in_backfill():
    from scripts.backfill_history import TARGETS
    names = {t.name for t in TARGETS}
    for n in ("fra_ois", "china_fx_reserves", "usdcny", "china_10y"):
        assert n in names


def test_china_in_risk_score_weights():
    from src.compute.risk_score import _GROUP_WEIGHTS
    assert "中国" in _GROUP_WEIGHTS
    assert _GROUP_WEIGHTS["中国"] > 0
    # 总和归一化到 100
    assert abs(sum(_GROUP_WEIGHTS.values()) - 100.0) < 0.01


def test_fra_ois_is_derived_for_backfill():
    """FRA-OIS 是 FRED:DGS3MO-SOFR 派生（含 -），backfill 应跳过。"""
    from scripts.backfill_history import _is_derived
    assert _is_derived("FRED:DGS3MO-SOFR") is True
