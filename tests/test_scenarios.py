"""tests for src/web/scenarios.py — 5 剧本检测器."""
from __future__ import annotations

import pytest

from src.compute.thresholds import Level
from src.web.scenarios import SCENARIOS, _is_red, _is_yellow_or_red, _val, evaluate_scenarios


# ── helpers ──────────────────────────────────────────────────

def test_val_normal():
    assert _val({"value": 18.5}) == 18.5


def test_val_none():
    assert _val(None) is None


def test_val_invalid():
    assert _val({"value": "abc"}) is None


def test_is_red_with_classify_returns_red():
    def classify(v): return Level.RED
    assert _is_red({"value": 50}, classify) is True


def test_is_red_with_classify_returns_yellow():
    def classify(v): return Level.YELLOW
    assert _is_red({"value": 25}, classify) is False


def test_is_yellow_or_red():
    def classify(v): return Level.YELLOW
    assert _is_yellow_or_red({"value": 25}, classify) is True

    def classify_g(v): return Level.GREEN
    assert _is_yellow_or_red({"value": 5}, classify_g) is False


def test_no_classify_no_match():
    assert _is_red({"value": 50}, None) is False
    assert _is_yellow_or_red({"value": 50}, None) is False


# ── evaluate_scenarios ───────────────────────────────────────

def _make_state(value: float, level: Level):
    """构造 indicator_states 单条入口。"""
    return {
        "latest": {"value": value},
        "classify": lambda v, _lv=level: _lv,
    }


def test_all_quiet_when_no_indicators():
    out = evaluate_scenarios({})
    assert len(out) == len(SCENARIOS)
    assert all(s["level"] == "quiet" for s in out)


def test_dollar_squeeze_active_when_3_of_4():
    """剧本 A 4 条规则中 3 条触发就 active。"""
    states = {
        "dxy_broad": _make_state(130, Level.RED),
        "usdjpy": _make_state(165, Level.RED),
        "sofr_iorb": _make_state(0.20, Level.YELLOW),
        # on_rrp 缺
    }
    out = evaluate_scenarios(states)
    a = next(s for s in out if s["id"] == "A_dollar_squeeze")
    assert a["matched"] == 3
    assert a["active"] is True
    assert a["level"] == "active"


def test_dollar_squeeze_watch_when_2_of_4():
    states = {
        "dxy_broad": _make_state(130, Level.RED),
        "usdjpy": _make_state(165, Level.RED),
    }
    out = evaluate_scenarios(states)
    a = next(s for s in out if s["id"] == "A_dollar_squeeze")
    assert a["matched"] == 2
    assert a["active"] is False  # min_match=3，不到
    assert a["level"] == "watch"


def test_credit_lag_needs_both():
    """E 剧本 min_match=2，HY+IG 都要 ≥YELLOW 才 active。"""
    states_only_one = {
        "hy_oas": _make_state(7.0, Level.YELLOW),
    }
    out = evaluate_scenarios(states_only_one)
    e = next(s for s in out if s["id"] == "E_credit_lag")
    assert e["matched"] == 1
    assert e["active"] is False

    states_both = {
        "hy_oas": _make_state(7.0, Level.YELLOW),
        "ig_oas": _make_state(2.0, Level.YELLOW),
    }
    out = evaluate_scenarios(states_both)
    e = next(s for s in out if s["id"] == "E_credit_lag")
    assert e["matched"] == 2
    assert e["active"] is True


def test_hits_listed():
    states = {
        "dxy_broad": _make_state(130, Level.RED),
        "usdjpy": _make_state(165, Level.RED),
    }
    out = evaluate_scenarios(states)
    a = next(s for s in out if s["id"] == "A_dollar_squeeze")
    assert "dxy_broad" in a["hits"]
    assert "usdjpy" in a["hits"]


def test_all_5_scenarios_returned():
    out = evaluate_scenarios({})
    ids = {s["id"] for s in out}
    assert "A_dollar_squeeze" in ids
    assert "B_basis_blow" in ids
    assert "C_japan_carry" in ids
    assert "D_ai_bubble" in ids
    assert "E_credit_lag" in ids


def test_thesis_ref_present():
    out = evaluate_scenarios({})
    for s in out:
        assert "THESIS" in s["thesis_ref"]


# ── Web e2e ──────────────────────────────────────────────────

def test_dashboard_renders_scenarios(tmp_path):
    """主 dashboard 应渲染 5 个剧本卡片。"""
    from src.compute.indicators import vix as vix_ind
    from src.store import db as dbmod
    from src.web.app import create_app

    p = tmp_path / "radar.sqlite"
    with dbmod.open_db(p) as conn:
        dbmod.upsert_indicator(conn, vix_ind.NAME, "2026-05-15", 25.0, "YF:^VIX")
    hist_p = tmp_path / "h.sqlite"
    app = create_app(db_path=p, history_db_path=hist_p)
    with app.test_client() as c:
        resp = c.get("/")
        body = resp.get_data(as_text=True)
        assert "scenario-card" in body
        assert "美元荒" in body
        assert "信用 + 估值滞后崩" in body or "信用" in body
