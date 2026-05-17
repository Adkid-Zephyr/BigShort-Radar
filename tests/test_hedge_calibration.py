"""tests for hedge_calibration.py + /hedge /calibration 路由."""
from __future__ import annotations

import pytest

from src.web.hedge_calibration import calibrate_threshold, split_risk_vs_hedge


# ── split_risk_vs_hedge ──────────────────────────────────────

def test_split_risk_only():
    rows = [
        {"name": "vix", "group": "波动率"},
        {"name": "yc", "group": "曲线"},
    ]
    out = split_risk_vs_hedge(rows)
    assert len(out["risk"]) == 2
    assert len(out["hedge"]) == 0


def test_split_with_policy():
    rows = [
        {"name": "vix", "group": "波动率"},
        {"name": "walcl", "group": "政策"},
        {"name": "tga", "group": "政策"},
    ]
    out = split_risk_vs_hedge(rows)
    assert len(out["risk"]) == 1
    assert len(out["hedge"]) == 2


def test_split_unknown_group_skipped():
    """未知 group 不进任何一边。"""
    rows = [{"name": "x", "group": "其他"}]
    out = split_risk_vs_hedge(rows)
    assert len(out["risk"]) == 0
    assert len(out["hedge"]) == 0


def test_split_china_in_risk():
    rows = [{"name": "usdcny", "group": "中国"}]
    out = split_risk_vs_hedge(rows)
    assert len(out["risk"]) == 1


# ── calibrate_threshold ──────────────────────────────────────

def test_calibrate_no_data():
    out = calibrate_threshold(values=[], threshold_low=1, threshold_high=2)
    assert out["verdict"] == "no_data"


def test_calibrate_too_few_samples():
    out = calibrate_threshold(values=[1.0] * 10, threshold_low=1, threshold_high=2)
    assert out["verdict"] == "no_data"


def test_calibrate_no_thresholds():
    out = calibrate_threshold(values=[1.0] * 50, threshold_low=None, threshold_high=2)
    assert out["verdict"] == "no_data"


def test_calibrate_ok_distribution():
    """全 GREEN: 50 个值 < threshold_low（up方向），大量 GREEN，0% RED → ok。"""
    out = calibrate_threshold(
        values=[1.0] * 100, threshold_low=10, threshold_high=20, direction="up"
    )
    assert out["pct_green"] == pytest.approx(100.0)
    assert out["pct_red"] == pytest.approx(0.0)
    # n=100 < 365 不触发 too_dull
    assert out["verdict"] == "ok"


def test_calibrate_too_sensitive():
    """过敏感：>20% RED。"""
    # 100 个值大部分 > threshold_high
    values = [50.0] * 50 + [5.0] * 50
    out = calibrate_threshold(
        values=values, threshold_low=10, threshold_high=20, direction="up"
    )
    assert out["pct_red"] == 50.0
    assert out["verdict"] == "too_sensitive"


def test_calibrate_too_dull():
    """过迟钝：n>=365 且 RED <1%。"""
    # 全 GREEN 365+ 天
    values = [1.0] * 400
    out = calibrate_threshold(
        values=values, threshold_low=10, threshold_high=20, direction="up"
    )
    assert out["verdict"] == "too_dull"


def test_calibrate_filters_nan():
    values = [float("nan")] * 30 + [1.0] * 50
    out = calibrate_threshold(values=values, threshold_low=10, threshold_high=20)
    assert out["n_total"] == 50


# ── 路由 e2e ─────────────────────────────────────────────────

@pytest.fixture()
def db_path(tmp_path):
    from src.compute.indicators import vix as vix_ind
    from src.compute.indicators import walcl as walcl_ind
    from src.store import db as dbmod
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as conn:
        dbmod.upsert_indicator(conn, vix_ind.NAME, "2026-05-15", 25.0, "YF:^VIX")
        dbmod.upsert_indicator(conn, walcl_ind.NAME, "2026-05-15", 7_500_000, "FRED:WALCL")
    return p


@pytest.fixture()
def history_db_path(tmp_path):
    return tmp_path / "history_cache.sqlite"


@pytest.fixture()
def client(db_path, history_db_path):
    from src.web.app import create_app
    app = create_app(db_path=db_path, history_db_path=history_db_path)
    with app.test_client() as c:
        yield c


def test_hedge_route_200(client):
    resp = client.get("/hedge")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "对冲" in body or "风险面" in body
    assert "page-nav" in body


def test_hedge_separates_groups(client):
    resp = client.get("/hedge")
    body = resp.get_data(as_text=True)
    # 风险面应含 VIX 标签
    assert "VIX" in body
    # 对冲面应含 WALCL 或 政策
    assert "WALCL" in body or "政策" in body


def test_calibration_route_200(client):
    resp = client.get("/calibration")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "校准" in body or "阈值" in body


def test_dashboard_nav_includes_new_pages(client):
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert 'href="/hedge"' in body
    assert 'href="/calibration"' in body
