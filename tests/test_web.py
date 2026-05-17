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
def history_db_path(tmp_path):
    """空的临时 history cache DB，避免污染测试用本机真实 cache。"""
    return tmp_path / "history_cache.sqlite"


@pytest.fixture()
def client(db_path, history_db_path):
    app = create_app(db_path=db_path, history_db_path=history_db_path)
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


def test_index_renders_source_as_external_link(client):
    """source 列应该是可点击的官方页外链（VIX → yahoo finance），新页签打开。"""
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    # ^VIX 被 url-encode 成 %5EVIX
    assert "https://finance.yahoo.com/quote/%5EVIX" in body
    # target=_blank + rel noopener 防止新页可改 window.opener
    assert 'target="_blank"' in body
    assert "noopener" in body
    # CSS class 标识
    assert "source-link" in body


def test_index_renders_sparkline_column(client):
    """每行应有 sparkline SVG（即使数据不足也是占位 SVG）。"""
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    # 表头加了"90 天"列
    assert ">90 天<" in body
    # SVG 标记存在（占位或正常都有）
    assert "<svg" in body
    # spark-cell CSS class 标识
    assert "spark-cell" in body


def test_sparkline_placeholder_when_no_history(client):
    """tmp_path 主 DB 只有 1 条 VIX 数据，cache DB 为空，应显示"积累中"占位。"""
    resp = client.get("/")
    body = resp.get_data(as_text=True)
    assert "积累中" in body


def test_index_empty_when_no_data(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p):
        pass  # 只建 schema，不写数据
    hist_p = tmp_path / "history_cache.sqlite"  # 空 cache，避免读真实本机 cache
    app = create_app(db_path=p, history_db_path=hist_p)
    app.config["TESTING"] = True
    with app.test_client() as c:
        resp = c.get("/")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "暂无数据" in body
        # 即使无数据，VIX 期限结构（registry 手填 source_url）应该露出"查源"链接
        assert "cboe.com" in body
        assert "查源" in body


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


def test_group_header_uses_worst_level(db_path, history_db_path):
    """组内最严等级应当冒到组 header（HY OAS 在信用组，写一条 RED）。"""
    with dbmod.open_db(db_path) as conn:
        dbmod.upsert_indicator(conn, hy_ind.NAME, "2026-05-15", 10.0, "FRED:BAMLH0A0HYM2")
    app = create_app(db_path=db_path, history_db_path=history_db_path)
    with app.test_client() as c:
        resp = c.get("/")
        body = resp.get_data(as_text=True)
        # 信用组里有 RED，组 header 应显示"最严：RED"
        # 简单断言：页面里"最严：RED"出现至少一次
        assert "最严：RED" in body


# ── /api/chat（iter 30） ─────────────────────────────────────
def test_chat_returns_400_when_no_message(client):
    resp = client.post("/api/chat", json={})
    assert resp.status_code == 400
    assert "缺少" in resp.json.get("error", "")


def test_chat_calls_llm_and_returns_reply(client, monkeypatch):
    from src.fetch import llm_client
    captured = {}

    def fake_chat(messages, settings=None, model=None, temperature=0.3, timeout_sec=60):
        captured["messages"] = messages
        return "AI 回答内容"

    monkeypatch.setattr(llm_client, "chat", fake_chat)
    resp = client.post("/api/chat", json={"message": "现在最危险的是哪条？"})
    assert resp.status_code == 200
    assert resp.json["reply"] == "AI 回答内容"
    # 系统 prompt 必须含快照
    assert any("指标快照" in m["content"] for m in captured["messages"] if m["role"] == "system")


def test_chat_returns_502_when_llm_fails(client, monkeypatch):
    from src.fetch import llm_client
    monkeypatch.setattr(llm_client, "chat",
                        lambda messages, **kw: None)
    resp = client.post("/api/chat", json={"message": "x"})
    assert resp.status_code == 502
    assert "失败" in resp.json["error"]


def test_chat_renders_widget_in_html(client):
    body = client.get("/").get_data(as_text=True)
    # chatbot 浮窗 UI 应渲染
    assert "chat-toggle" in body
    assert "chat-panel" in body
    assert "/api/chat" in body
