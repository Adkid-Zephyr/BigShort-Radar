"""tests for src/backtest/report.py — 三窗口对比 SUMMARY 生成."""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.backtest.report import (
    generate_summary,
    load_window,
    render_summary_md,
    summarize_window,
)


def _write_csv(path: Path, rows: list) -> None:
    """写一个带 indicator 列的回测 CSV。"""
    fieldnames = ["date", "score", "level", "missing_count", "vix_fred", "hy_oas", "yield_curve_10y2y"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ── load_window ──────────────────────────────────────────────

def test_load_window_returns_dicts(tmp_path):
    path = tmp_path / "x.csv"
    _write_csv(path, [
        {"date": "2024-01-01", "score": "30", "level": "YELLOW", "missing_count": "2",
         "vix_fred": "22", "hy_oas": "", "yield_curve_10y2y": "0.4"},
        {"date": "2024-01-02", "score": "70", "level": "RED", "missing_count": "1",
         "vix_fred": "32", "hy_oas": "9", "yield_curve_10y2y": "-0.2"},
    ])
    rows = load_window(path)
    assert len(rows) == 2
    assert rows[0]["date"] == "2024-01-01"
    assert rows[1]["level"] == "RED"


# ── summarize_window ─────────────────────────────────────────

def test_summarize_empty():
    out = summarize_window([])
    assert out["total"] == 0
    assert out["score_min"] is None


def test_summarize_normal(tmp_path):
    rows = [
        {"date": "2024-01-01", "score": "30.0", "level": "YELLOW", "missing_count": "2",
         "vix_fred": "22", "hy_oas": "", "yield_curve_10y2y": "0.4"},
        {"date": "2024-01-02", "score": "70.0", "level": "RED", "missing_count": "1",
         "vix_fred": "32", "hy_oas": "9", "yield_curve_10y2y": "-0.2"},
        {"date": "2024-01-03", "score": "20.0", "level": "GREEN", "missing_count": "3",
         "vix_fred": "15", "hy_oas": "", "yield_curve_10y2y": "0.7"},
    ]
    s = summarize_window(rows, top_n=2)
    assert s["total"] == 3
    assert s["score_min"] == 20.0
    assert s["score_max"] == 70.0
    assert s["score_mean"] == pytest.approx(40.0)
    assert s["level_counts"]["RED"] == 1
    assert s["level_counts"]["YELLOW"] == 1
    assert s["level_counts"]["GREEN"] == 1
    assert len(s["top_days"]) == 2
    # top1 应是 score 70 的 RED 日
    assert s["top_days"][0]["score"] == 70.0


def test_summarize_missing_pattern():
    rows = [
        {"date": "2024-01-01", "score": "30.0", "level": "YELLOW", "missing_count": "2",
         "vix_fred": "22", "hy_oas": "", "yield_curve_10y2y": "0.4"},
        {"date": "2024-01-02", "score": "70.0", "level": "RED", "missing_count": "1",
         "vix_fred": "32", "hy_oas": "", "yield_curve_10y2y": "-0.2"},
    ]
    s = summarize_window(rows)
    assert s["missing_pattern"]["hy_oas"] == 2
    assert s["missing_pattern"]["vix_fred"] == 0


# ── render_summary_md ────────────────────────────────────────

def test_render_summary_md_basic():
    s = {
        "total": 3, "score_min": 20.0, "score_max": 70.0, "score_mean": 40.0,
        "level_counts": {"GREEN": 1, "YELLOW": 1, "RED": 1},
        "top_days": [{"date": "2024-01-02", "score": 70.0, "level": "RED", "missing_count": 1}],
        "missing_pattern": {"hy_oas": 2, "vix_fred": 0},
        "missing_count_avg": 2.0,
    }
    md = render_summary_md([("Test 窗口", s)])
    assert "# 历史回测摘要" in md
    assert "Test 窗口" in md
    assert "70.0" in md or "70.00" in md
    assert "2024-01-02" in md
    assert "hy_oas" in md


def test_render_summary_md_multi_windows():
    s1 = {
        "total": 100, "score_min": 10.0, "score_max": 50.0, "score_mean": 30.0,
        "level_counts": {"GREEN": 50, "YELLOW": 50, "RED": 0},
        "top_days": [], "missing_pattern": {}, "missing_count_avg": 0,
    }
    s2 = {
        "total": 200, "score_min": 30.0, "score_max": 80.0, "score_mean": 55.0,
        "level_counts": {"YELLOW": 150, "RED": 50}, "top_days": [],
        "missing_pattern": {}, "missing_count_avg": 0,
    }
    md = render_summary_md([("窗口 1", s1), ("窗口 2", s2)])
    assert "窗口 1" in md
    assert "窗口 2" in md


# ── generate_summary e2e ─────────────────────────────────────

def test_generate_summary_writes_file(tmp_path):
    csv_dir = tmp_path / "csvs"
    csv_dir.mkdir()
    _write_csv(csv_dir / "win_a.csv", [
        {"date": "2024-01-01", "score": "30", "level": "YELLOW", "missing_count": "1",
         "vix_fred": "22", "hy_oas": "5", "yield_curve_10y2y": "0.4"},
    ])
    _write_csv(csv_dir / "win_b.csv", [
        {"date": "2024-02-01", "score": "70", "level": "RED", "missing_count": "0",
         "vix_fred": "35", "hy_oas": "10", "yield_curve_10y2y": "-0.5"},
    ])

    out_path = tmp_path / "SUMMARY.md"
    md = generate_summary(
        csv_dir=csv_dir,
        output_path=out_path,
        windows=[("窗口 A", "win_a.csv"), ("窗口 B", "win_b.csv")],
    )
    assert out_path.exists()
    assert "窗口 A" in md
    assert "窗口 B" in md


def test_generate_summary_skips_missing_csv(tmp_path):
    csv_dir = tmp_path / "csvs"
    csv_dir.mkdir()
    _write_csv(csv_dir / "exists.csv", [
        {"date": "2024-01-01", "score": "30", "level": "YELLOW", "missing_count": "0",
         "vix_fred": "22", "hy_oas": "5", "yield_curve_10y2y": "0.4"},
    ])
    out_path = tmp_path / "SUMMARY.md"
    md = generate_summary(
        csv_dir=csv_dir, output_path=out_path,
        windows=[("有", "exists.csv"), ("无", "nonexistent.csv")],
    )
    assert "有" in md
    # 不存在的窗口跳过，不抛
    assert out_path.exists()
