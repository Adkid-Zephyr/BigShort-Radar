"""综合风险温度计测试：compute / 入库 / get_latest。"""
from __future__ import annotations

import pytest

from src.compute import risk_score as rs
from src.compute.indicators import hy_oas as hy_ind
from src.compute.indicators import vix as vix_ind
from src.store import db as dbmod


@pytest.fixture()
def conn(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as c:
        yield c


_REGISTRY = [
    {"name": vix_ind.NAME, "label": "VIX 恐慌指数",
     "classify": vix_ind.classify_value, "group": "波动率"},
    {"name": hy_ind.NAME, "label": "HY OAS",
     "classify": hy_ind.classify_value, "group": "信用"},
]


def test_compute_score_all_green(conn):
    dbmod.upsert_indicator(conn, vix_ind.NAME, "2026-05-15", 15.0, "YF:^VIX")  # GREEN
    dbmod.upsert_indicator(conn, hy_ind.NAME, "2026-05-15", 3.0, "FRED:HY")  # GREEN
    out = rs.compute_score(conn, _REGISTRY)
    assert out["score"] == 0.0
    assert out["level"] == "GREEN"


def test_compute_score_all_red(conn):
    dbmod.upsert_indicator(conn, vix_ind.NAME, "2026-05-15", 50.0, "YF:^VIX")  # RED
    dbmod.upsert_indicator(conn, hy_ind.NAME, "2026-05-15", 12.0, "FRED:HY")  # RED
    out = rs.compute_score(conn, _REGISTRY)
    assert out["score"] == 100.0
    assert out["level"] == "RED"


def test_compute_score_mixed_yellow(conn):
    dbmod.upsert_indicator(conn, vix_ind.NAME, "2026-05-15", 25.0, "YF:^VIX")  # YELLOW
    dbmod.upsert_indicator(conn, hy_ind.NAME, "2026-05-15", 6.0, "FRED:HY")  # YELLOW
    out = rs.compute_score(conn, _REGISTRY)
    assert out["score"] == 50.0
    assert out["level"] == "YELLOW"


def test_compute_score_skips_missing(conn):
    dbmod.upsert_indicator(conn, vix_ind.NAME, "2026-05-15", 15.0, "YF:^VIX")  # 仅 VIX 有数据
    out = rs.compute_score(conn, _REGISTRY)
    assert hy_ind.NAME in out["missing"]
    assert out["score"] == 0.0  # 仅 VIX GREEN


def test_compute_score_breakdown_structure(conn):
    dbmod.upsert_indicator(conn, vix_ind.NAME, "2026-05-15", 15.0, "YF:^VIX")
    dbmod.upsert_indicator(conn, hy_ind.NAME, "2026-05-15", 6.0, "FRED:HY")
    out = rs.compute_score(conn, _REGISTRY)
    assert "波动率" in out["breakdown"]
    assert "信用" in out["breakdown"]
    assert out["breakdown"]["波动率"]["weight"] == 12.0
    assert out["breakdown"]["信用"]["weight"] == 20.0
    assert out["breakdown"]["波动率"]["indicators"][0]["level"] == "GREEN"


def test_classify_total_thresholds():
    assert rs._classify_total(0) == "GREEN"
    assert rs._classify_total(24.9) == "GREEN"
    assert rs._classify_total(25.0) == "YELLOW"
    assert rs._classify_total(50.0) == "YELLOW"
    assert rs._classify_total(64.9) == "YELLOW"
    assert rs._classify_total(65.0) == "RED"
    assert rs._classify_total(100.0) == "RED"


def test_run_and_store_writes_row(conn):
    dbmod.upsert_indicator(conn, vix_ind.NAME, "2026-05-15", 15.0, "YF:^VIX")
    rs.run_and_store(conn, _REGISTRY)
    latest = rs.get_latest_risk_score(conn)
    assert latest is not None
    assert latest["score"] == 0.0
    assert latest["level"] == "GREEN"
    assert "breakdown" in latest


def test_get_latest_returns_none_on_empty(tmp_path):
    p = tmp_path / "x.sqlite"
    with dbmod.open_db(p) as c:
        assert rs.get_latest_risk_score(c) is None


def test_run_and_store_overwrites_today(conn):
    dbmod.upsert_indicator(conn, vix_ind.NAME, "2026-05-15", 15.0, "YF:^VIX")
    rs.run_and_store(conn, _REGISTRY)
    # 改一下数据再跑
    dbmod.upsert_indicator(conn, vix_ind.NAME, "2026-05-15", 35.0, "YF:^VIX")  # RED
    rs.run_and_store(conn, _REGISTRY)
    latest = rs.get_latest_risk_score(conn)
    assert latest["level"] == "RED"
