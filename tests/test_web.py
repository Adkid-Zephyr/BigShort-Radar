"""web/app.py 测试：用 Flask test_client，DB 走临时文件。"""
from __future__ import annotations

import pytest

from src.compute.indicators import hy_oas as hy_ind
from src.compute.indicators import vix as vix_ind
from src.store import db as dbmod
from src.web.app import _GROUP_ORDER, create_app


@pytest.fixture()
def db_path(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as conn:
        # 预置一条 VIX 黄区数据
        dbmod.upsert_indicator(conn, vix_ind.NAME, "2026-05-15", 25.0, "YF:^VIX")
    return p


@pytest.fixture()
def client(db_path):
    app = create_app(db_path=db_path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_healthz_ok(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json == {"status": "ok"}


def test_index_renders_with_data(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Finance Radar" in body
    assert "VIX" in body  # label
    assert "25.00" in body  # 格式化后的值
    assert "YELLOW" in body
    assert "2026-05-15" in body
    assert "YF:^VIX" in body


def test_index_empty_when_no_data(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p):
        pass  # 只建 schema，不写数据
    app = create_app(db_path=p)
    app.config["TESTING"] = True
    with app.test_client() as c:
        resp = c.get("/")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "暂无数据" in body


def test_index_red_level_color(client, db_path):
    # 改写一条 RED 区数据
    with dbmod.open_db(db_path) as conn:
        dbmod.upsert_indicator(conn, vix_ind.NAME, "2026-05-15", 38.0, "YF:^VIX")
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert "RED" in body
    assert "38.00" in body


# ── 分组（iter 26） ──────────────────────────────────────────
def test_index_renders_group_headers(client):
    """页面应当有"波动率/信用/曲线/流动性"分组标题。"""
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    for g in ["波动率", "信用", "曲线", "流动性"]:
        assert g in body, f"分组 {g} 未渲染"


def test_group_order_matches_constant():
    assert _GROUP_ORDER[:4] == ["波动率", "信用", "曲线", "流动性"]


def test_group_header_uses_worst_level(db_path):
    """组内最严等级应当冒到组 header（HY OAS 在信用组，写一条 RED）。"""
    with dbmod.open_db(db_path) as conn:
        dbmod.upsert_indicator(conn, hy_ind.NAME, "2026-05-15", 10.0, "FRED:BAMLH0A0HYM2")
    app = create_app(db_path=db_path)
    with app.test_client() as c:
        resp = c.get("/")
        body = resp.get_data(as_text=True)
        # 信用组里有 RED，组 header 应显示"最严：RED"
        # 简单断言：页面里"最严：RED"出现至少一次
        assert "最严：RED" in body
