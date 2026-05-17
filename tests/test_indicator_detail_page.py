"""tests for /indicator/<name> route."""
from __future__ import annotations

import pytest

from src.compute.indicators import vix as vix_ind
from src.store import db as dbmod
from src.web.app import create_app


@pytest.fixture()
def db_path(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as conn:
        # 写多条 VIX 数据避免详情页 placeholder
        for i, (d, v) in enumerate([
            ("2026-05-10", 18.0),
            ("2026-05-11", 19.0),
            ("2026-05-12", 20.0),
            ("2026-05-13", 21.0),
            ("2026-05-14", 22.0),
        ]):
            dbmod.upsert_indicator(conn, vix_ind.NAME, d, v, "YF:^VIX")
    return p


@pytest.fixture()
def history_db_path(tmp_path):
    return tmp_path / "history_cache.sqlite"


@pytest.fixture()
def client(db_path, history_db_path):
    app = create_app(db_path=db_path, history_db_path=history_db_path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── 路由基础 ────────────────────────────────────────────────

def test_detail_page_200_for_valid_indicator(client):
    resp = client.get("/indicator/vix")
    assert resp.status_code == 200


def test_detail_page_404_for_unknown_indicator(client):
    resp = client.get("/indicator/nonexistent_xyz")
    assert resp.status_code == 404


def test_detail_page_renders_label(client):
    resp = client.get("/indicator/vix")
    body = resp.get_data(as_text=True)
    assert "VIX 恐慌指数" in body


def test_detail_page_renders_breadcrumb(client):
    resp = client.get("/indicator/vix")
    body = resp.get_data(as_text=True)
    # 面包屑回到 dashboard
    assert "返回 dashboard" in body
    assert 'href="/"' in body


def test_detail_page_renders_meta_dl(client):
    resp = client.get("/indicator/vix")
    body = resp.get_data(as_text=True)
    assert "detail-meta" in body
    assert "当前值" in body
    assert "更新日期" in body
    assert "阈值" in body
    assert "方向" in body
    assert "数据源" in body


def test_detail_page_renders_plotly_or_placeholder(client):
    """5 个数据点 < charts 模块 2 点门槛，但 cache DB 空 → 主 DB 5 点 → plotly 渲染。"""
    resp = client.get("/indicator/vix")
    body = resp.get_data(as_text=True)
    # 应该能画图（5 个点 ≥ 2，过 charts 门槛）
    assert "plotly" in body.lower() or "chart-placeholder" in body


def test_detail_page_threshold_text(client):
    """阈值显示在 dl 里，应见 GREEN < 20 / YELLOW 20-30 / RED > 30 (VIX up direction)."""
    resp = client.get("/indicator/vix")
    body = resp.get_data(as_text=True)
    assert "GREEN" in body
    assert "YELLOW" in body
    assert "RED" in body


def test_detail_page_source_url(client):
    """VIX 走自动推导 → yahoo finance %5EVIX。"""
    resp = client.get("/indicator/vix")
    body = resp.get_data(as_text=True)
    assert "finance.yahoo.com/quote/%5EVIX" in body


# ── 路由列出现在主页 ──────────────────────────────────────────

def test_dashboard_sparkline_links_to_detail(client):
    """主 dashboard 的 sparkline 应包成 <a href="/indicator/<name>">。"""
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert 'href="/indicator/vix"' in body
    assert "spark-link" in body


def test_dashboard_has_nav(client):
    """主页应渲染顶部 nav 条。"""
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert "page-nav" in body
    # nav 含"指标"为 current 状态
    assert 'class="current"' in body or 'current' in body
    # 含未来栏目占位（disabled）
    assert "事件" in body
    assert "热力图" in body


def test_detail_page_has_nav(client):
    """详情页也应有 nav。"""
    resp = client.get("/indicator/vix")
    body = resp.get_data(as_text=True)
    assert "page-nav" in body
