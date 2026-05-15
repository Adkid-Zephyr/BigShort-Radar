"""briefing 模块测试：snapshot 组装 + 入库 + run_and_store。"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from src.compute import briefing as bf
from src.compute.indicators import vix as vix_ind
from src.store import db as dbmod
from src.utils.config import Settings


def _settings(key="testkey"):
    return Settings(
        fred_api_key=None,
        tz="Asia/Shanghai",
        flask_port=5050,
        flask_debug=False,
        db_path=Path("/tmp/x.sqlite"),
        logs_dir=Path("/tmp"),
        project_root=Path("/tmp"),
        llm_api_key=key,
        llm_base_url="https://api.example.com/v1",
        llm_model="qwen-plus",
    )


@pytest.fixture()
def conn(tmp_path):
    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as c:
        # 预置 VIX 当前 + 7 天前数据
        dbmod.upsert_indicator(c, vix_ind.NAME, "2026-05-15", 17.5, "YF:^VIX")
        dbmod.upsert_indicator(c, vix_ind.NAME, "2026-05-08", 14.0, "YF:^VIX")
        yield c


_REGISTRY = [
    {
        "name": vix_ind.NAME,
        "label": "VIX 恐慌指数",
        "classify": vix_ind.classify_value,
        "group": "波动率",
    },
]


# ── snapshot ─────────────────────────────────────────────────
def test_build_snapshot_contains_label_and_value(conn):
    text = bf.build_snapshot(conn, _REGISTRY)
    assert "VIX 恐慌指数" in text
    assert "17.500" in text or "17.500（" in text
    assert "GREEN" in text  # 17.5 < 20 是 GREEN


def test_build_snapshot_handles_no_data(tmp_path):
    p = tmp_path / "empty.sqlite"
    with dbmod.open_db(p) as c:
        text = bf.build_snapshot(c, _REGISTRY)
        assert "无数据" in text


# ── briefings 表 CRUD ────────────────────────────────────────
def test_upsert_and_get_latest_briefing(conn):
    bf.upsert_briefing(conn, "2026-05-15", "今日核心读数：略", model="qwen-plus")
    row = bf.get_latest_briefing(conn)
    assert row is not None
    assert row["date"] == "2026-05-15"
    assert "今日核心" in row["content"]
    assert row["model"] == "qwen-plus"


def test_upsert_briefing_overwrites(conn):
    bf.upsert_briefing(conn, "2026-05-15", "旧版本", model="qwen-plus")
    bf.upsert_briefing(conn, "2026-05-15", "新版本", model="qwen-max")
    row = bf.get_latest_briefing(conn)
    assert row["content"] == "新版本"
    assert row["model"] == "qwen-max"


def test_get_latest_picks_newest_date(conn):
    bf.upsert_briefing(conn, "2026-05-13", "旧")
    bf.upsert_briefing(conn, "2026-05-15", "新")
    bf.upsert_briefing(conn, "2026-05-14", "中")
    row = bf.get_latest_briefing(conn)
    assert row["date"] == "2026-05-15"


def test_get_latest_returns_none_on_empty(tmp_path):
    p = tmp_path / "empty.sqlite"
    with dbmod.open_db(p) as c:
        assert bf.get_latest_briefing(c) is None


# ── run_and_store（mock LLM） ────────────────────────────────
def _install_fake_requests(monkeypatch, content="今日核心读数：略。"):
    fake = types.ModuleType("requests")

    class FakeResp:
        status_code = 200
        text = ""

        def json(self):
            return {"choices": [{"message": {"content": content}}]}

    def post(url, headers=None, json=None, timeout=None):
        return FakeResp()

    fake.post = post  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "requests", fake)


def test_run_and_store_writes_briefing(conn, monkeypatch):
    _install_fake_requests(monkeypatch, content="今日 VIX 17.5 GREEN。")
    text = bf.run_and_store(conn, _REGISTRY, settings=_settings())
    assert text is not None
    row = bf.get_latest_briefing(conn)
    assert row is not None
    assert "VIX" in row["content"]


def test_run_and_store_returns_none_when_llm_fails(conn, monkeypatch):
    # 模拟 LLM 报错
    def fake_chat(*a, **kw):
        return None

    monkeypatch.setattr(bf.llm_client, "chat", fake_chat)
    text = bf.run_and_store(conn, _REGISTRY, settings=_settings())
    assert text is None
    assert bf.get_latest_briefing(conn) is None
