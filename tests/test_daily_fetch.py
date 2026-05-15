"""daily_fetch 脚本测试：mock fetcher，确保编排逻辑正确。"""
from __future__ import annotations

from typing import List

import pytest

from scripts import daily_fetch
from src.store import db as dbmod


def test_parse_args_defaults():
    ns = daily_fetch.parse_args([])
    assert ns.start == "2020-01-01"
    assert ns.end is None


def test_parse_args_custom():
    ns = daily_fetch.parse_args(["--start", "2024-01-01", "--end", "2024-12-31"])
    assert ns.start == "2024-01-01"
    assert ns.end == "2024-12-31"


def test_run_calls_each_fetcher(monkeypatch, tmp_path):
    """run() 应调用每个 fetcher，并返回 0（无失败）。"""
    # 1. 把 DB 路径切到 tmp
    monkeypatch.setattr(daily_fetch.dbmod, "DB_PATH", tmp_path / "radar.sqlite")

    calls: List[str] = []

    def fake_vix(conn, start, end=None):
        calls.append(f"vix:{start}")
        return 5

    fake = daily_fetch.Fetcher(name="vix", run=fake_vix)
    monkeypatch.setattr(daily_fetch, "FETCHERS", [fake])

    failed = daily_fetch.run(start="2026-01-01")
    assert failed == 0
    assert calls == ["vix:2026-01-01"]


def test_run_isolates_fetcher_failures(monkeypatch, tmp_path):
    """单个 fetcher 抛异常，不影响其他，且 failed 计数 +1。"""
    monkeypatch.setattr(daily_fetch.dbmod, "DB_PATH", tmp_path / "radar.sqlite")

    def boom(conn, start, end=None):
        raise RuntimeError("network down")

    def ok(conn, start, end=None):
        return 3

    monkeypatch.setattr(daily_fetch, "FETCHERS", [
        daily_fetch.Fetcher(name="bad", run=boom),
        daily_fetch.Fetcher(name="good", run=ok),
    ])

    failed = daily_fetch.run(start="2026-01-01")
    assert failed == 1


def test_main_returns_int_exit_code(monkeypatch, tmp_path):
    monkeypatch.setattr(daily_fetch.dbmod, "DB_PATH", tmp_path / "radar.sqlite")
    monkeypatch.setattr(daily_fetch, "FETCHERS", [])
    code = daily_fetch.main(["--start", "2026-01-01"])
    assert code == 0
