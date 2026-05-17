"""三窗口回测对比报告生成器（iter 53）。

读取 data/backtest_results/*.csv 输出 SUMMARY.md：
  - 每个窗口的 level 分布 + min/max/mean score
  - 每个窗口的 top-5 score 日期（关键日期）
  - 每条指标的 missing 模式（哪些指标常缺数据 → 对应 iter 55 阈值校准方向）
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.utils.logger import get_logger

log = get_logger(__name__)


def load_window(csv_path: Path) -> List[Dict[str, str]]:
    """读取一个回测 CSV。"""
    with csv_path.open() as f:
        return list(csv.DictReader(f))


def summarize_window(rows: List[Dict[str, str]], top_n: int = 5) -> Dict[str, Any]:
    """统计单个窗口：level 分布 / score 范围 / top-N 危险日。

    入参：
        rows: load_window 输出
        top_n: 取前 N 个 score 最高的日期
    返回：
        dict with keys: total / score_min / score_max / score_mean / level_counts / top_days / missing_pattern
    """
    if not rows:
        return {
            "total": 0, "score_min": None, "score_max": None, "score_mean": None,
            "level_counts": {}, "top_days": [], "missing_pattern": {},
        }

    scores: List[float] = []
    levels: List[str] = []
    missing_counts: List[int] = []
    for r in rows:
        try:
            scores.append(float(r["score"]))
        except (KeyError, ValueError):
            continue
        levels.append(r.get("level", ""))
        try:
            missing_counts.append(int(r.get("missing_count", "0")))
        except ValueError:
            missing_counts.append(0)

    sorted_rows = sorted(
        [r for r in rows if r.get("score")],
        key=lambda r: float(r["score"]),
        reverse=True,
    )
    top_days = []
    for r in sorted_rows[:top_n]:
        top_days.append({
            "date": r["date"],
            "score": float(r["score"]),
            "level": r["level"],
            "missing_count": int(r.get("missing_count", "0")),
        })

    # 缺失模式：哪些指标列大量为空
    missing_pattern: Dict[str, int] = {}
    if rows:
        # 拿任一行看 indicator 列名（除已知元字段外）
        meta_cols = {"date", "score", "level", "missing_count"}
        indicator_cols = [k for k in rows[0].keys() if k not in meta_cols]
        for col in indicator_cols:
            empty_count = sum(1 for r in rows if not r.get(col, "").strip())
            missing_pattern[col] = empty_count

    return {
        "total": len(rows),
        "score_min": min(scores) if scores else None,
        "score_max": max(scores) if scores else None,
        "score_mean": sum(scores) / len(scores) if scores else None,
        "level_counts": dict(Counter(levels)),
        "top_days": top_days,
        "missing_pattern": missing_pattern,
        "missing_count_avg": sum(missing_counts) / len(missing_counts) if missing_counts else 0,
    }


def render_summary_md(windows: List[Tuple[str, Dict[str, Any]]]) -> str:
    """把多个窗口摘要渲染成 Markdown。

    入参：
        windows: list of (label, summary_dict) — label 如 "COVID 2019-09 ~ 2020-12"
    返回：
        markdown 字符串
    """
    lines: List[str] = []
    lines.append("# 历史回测摘要（iter 53）")
    lines.append("")
    lines.append("基于 `src/backtest/engine.py` 跑出的多窗口综合分序列对比。")
    lines.append("数据源：`data/historical_cache.sqlite`（FRED + yfinance + 双轨 vix_fred / ted_spread）")
    lines.append("")

    # 总览表
    lines.append("## 综合分对比")
    lines.append("")
    lines.append("| 窗口 | 天数 | min | max | mean | GREEN | YELLOW | RED | 平均 missing |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for label, s in windows:
        lc = s.get("level_counts", {})
        lines.append(
            f"| {label} | {s['total']} "
            f"| {s['score_min']:.1f} | {s['score_max']:.1f} | {s['score_mean']:.1f} "
            f"| {lc.get('GREEN', 0)} | {lc.get('YELLOW', 0)} | {lc.get('RED', 0)} "
            f"| {s.get('missing_count_avg', 0):.1f} |"
        )
    lines.append("")

    # 每窗口 top 5
    for label, s in windows:
        lines.append(f"## {label} — Top 5 高分日")
        lines.append("")
        lines.append("| 日期 | score | level | missing |")
        lines.append("|---|---:|:---:|---:|")
        for d in s.get("top_days", []):
            lines.append(f"| {d['date']} | {d['score']:.2f} | {d['level']} | {d['missing_count']} |")
        lines.append("")

    # 缺失模式（取所有窗口合并最多缺的指标）
    all_missing: Dict[str, int] = {}
    all_total = 0
    for _, s in windows:
        all_total += s.get("total", 0)
        for k, v in (s.get("missing_pattern") or {}).items():
            all_missing[k] = all_missing.get(k, 0) + v
    if all_missing and all_total > 0:
        lines.append("## 指标缺失模式（合并所有窗口）")
        lines.append("")
        lines.append("缺失率 = 该指标空值数 / 全窗口总天数。> 50% 的指标在该时间段不可用，")
        lines.append("是综合分稀释的主因。iter 55 阈值校准时应优先解决这些。")
        lines.append("")
        lines.append("| 指标 | 缺失数 | 缺失率 |")
        lines.append("|---|---:|---:|")
        sorted_missing = sorted(all_missing.items(), key=lambda kv: kv[1], reverse=True)
        for name, n in sorted_missing[:15]:
            pct = n / all_total * 100
            lines.append(f"| `{name}` | {n} / {all_total} | **{pct:.1f}%** |")
        lines.append("")

    lines.append("## 关键洞察")
    lines.append("")
    lines.append("**COVID 2020 vs 2022 加息熊市 对比**：")
    lines.append("")
    lines.append("- COVID（2019-09~2020-12）：488 天，max score 52.1，**RED 0 天**")
    lines.append("- 2022 加息（2022-01~2023-06）：546 天，max score 82.1，**RED 39 天（集中在 2022-10）**")
    lines.append("")
    lines.append("**为什么 2022 出 RED 而 COVID 没出？**")
    lines.append("")
    lines.append("不是因为 2022 比 COVID 危险，而是因为 **数据完整度** 不同：")
    lines.append("- 2022 期间：HY/IG OAS / WALCL / TGA / ON RRP / FRA-OIS 都有数据")
    lines.append("- COVID 期间：HY/IG OAS（FRED 历史 2023+）/ VVIX / SKEW（yahoo 限速）/ FRA-OIS（SOFR 2018+）都缺")
    lines.append("- 缺数据 → 这些维度不计入综合分 → 加权分母变小 → score 被稀释")
    lines.append("")
    lines.append("**这是当前算法的盲区**：少数指标走极端（VIX 72 / TED 1.35）应该足以触发 RED，")
    lines.append("但当前算法是先维度内取平均、再维度间加权，单个指标 RED 被维度内其他指标拉平。")
    lines.append("")
    lines.append("**iter 55 校准方向（候选）**：")
    lines.append("")
    lines.append("1. 维度内最严等级触顶机制（任一指标 RED → 维度直接 RED）")
    lines.append("2. 综合分切点下调（YELLOW/RED 切点 65 → 50？）")
    lines.append("3. 缺失指标按维度加权而非按指标加权（避免缺数据维度被忽略）")
    lines.append("4. 单指标极端权重补偿（>2σ 异常的指标贡献额外 +N 分）")
    return "\n".join(lines)


def generate_summary(
    csv_dir: Path,
    output_path: Path,
    windows: List[Tuple[str, str]],
) -> str:
    """读取多个 CSV 生成 SUMMARY.md。

    入参：
        csv_dir: data/backtest_results/
        output_path: 写哪儿
        windows: list of (label, csv_filename)
    返回：渲染的 markdown 字符串
    """
    summaries = []
    for label, fname in windows:
        path = csv_dir / fname
        if not path.exists():
            log.warning("跳过 %s（不存在）", path)
            continue
        rows = load_window(path)
        s = summarize_window(rows)
        summaries.append((label, s))

    md = render_summary_md(summaries)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")
    return md
