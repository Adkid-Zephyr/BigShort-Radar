"""tests for src/web/heatmap.py + /heatmap /timeline 路由."""
from __future__ import annotations

import pytest

from src.compute.thresholds import Level
from src.web.heatmap import _level_to_int, build_heatmap_html, build_risk_timeline_html


def test_level_to_int():
    assert _level_to_int(Level.GREEN) == 0
    assert _level_to_int(Level.YELLOW) == 1
    assert _level_to_int(Level.RED) == 2
    assert _level_to_int(None) == -1


def test_heatmap_empty_returns_placeholder():
    out = build_heatmap_html([])
    assert "无数据" in out


def test_heatmap_renders_plotly():
    inds = [
        {
            "name": "vix", "label": "VIX",
            "dates": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "values": [18.0, 22.0, 35.0],
            "threshold_low": 20.0, "threshold_high": 30.0, "direction": "up",
        },
        {
            "name": "yc", "label": "10Y-2Y",
            "dates": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "values": [0.7, 0.3, -0.2],
            "threshold_low": 0.0, "threshold_high": 0.5, "direction": "down",
        },
    ]
    out = build_heatmap_html(inds)
    assert "plotly" in out.lower()
    assert "heatmap_main" in out


def test_heatmap_handles_nan_and_missing():
    inds = [
        {
            "name": "x", "label": "X",
            "dates": ["2024-01-01", "2024-01-02"],
            "values": [float("nan"), 5.0],
            "threshold_low": 1.0, "threshold_high": 10.0, "direction": "up",
        }
    ]
    out = build_heatmap_html(inds)
    # NaN 被处理为 -1 / 灰色，仍能渲染
    assert "plotly" in out.lower() or "无数据" in out


def test_timeline_empty():
    out = build_risk_timeline_html([], [])
    assert "数据不足" in out


def test_timeline_single_point():
    out = build_risk_timeline_html(["2024-01-01"], [50.0])
    assert "累积中" in out


def test_timeline_renders_plotly():
    dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
    scores = [20.0, 35.0, 70.0]
    out = build_risk_timeline_html(dates, scores)
    assert "plotly" in out.lower()
    assert "timeline_main" in out


# ── 路由 e2e ─────────────────────────────────────────────────

@pytest.fixture()
def db_path(tmp_path):
    """带数据的临时主 DB。"""
    from src.compute.indicators import vix as vix_ind
    from src.store import db as dbmod
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as conn:
        for d, v in [("2026-05-10", 18.0), ("2026-05-12", 22.0), ("2026-05-14", 35.0)]:
            dbmod.upsert_indicator(conn, vix_ind.NAME, d, v, "YF:^VIX")
    return p


@pytest.fixture()
def history_db_path(tmp_path):
    return tmp_path / "history_cache.sqlite"


@pytest.fixture()
def client(db_path, history_db_path):
    from src.web.app import create_app
    app = create_app(db_path=db_path, history_db_path=history_db_path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_heatmap_route_200(client):
    resp = client.get("/heatmap")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "热力图" in body or "矩阵" in body
    assert "page-nav" in body


def test_timeline_route_200(client):
    resp = client.get("/timeline")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "时间线" in body or "温度计" in body
    assert "page-nav" in body


def test_dashboard_nav_links(client):
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert 'href="/heatmap"' in body
    assert 'href="/timeline"' in body
