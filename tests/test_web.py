"""web/app.py 测试：用 Flask test_client，DB 走临时文件。"""
from __future__ import annotations

import pytest

from src.compute.indicators import vix as vix_ind
from src.store import db as dbmod
from src.web.app import create_app


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
