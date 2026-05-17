"""回测引擎：按窗口逐日跑出综合分序列。

用法（CLI）：
    .venv/bin/python -m src.backtest.engine --start 2019-09-01 --end 2020-12-31
    .venv/bin/python -m src.backtest.engine --start 2008-08-01 --end 2008-12-31 --out data/backtest_results/lehman_2008.csv

输出 CSV 列：date / score / level / missing_count / 各指标 value
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.backtest.registry import BACKTEST_INDICATORS
from src.backtest.score import compute_score_for_date
from src.store import history_db as hdbmod
from src.utils.logger import get_logger

log = get_logger("backtest_engine")


def _iter_dates(start: str, end: str, step_days: int = 1) -> List[str]:
    s = datetime.strptime(start, "%Y-%m-%d").date()
    e = datetime.strptime(end, "%Y-%m-%d").date()
    if e < s:
        return []
    out: List[str] = []
    d = s
    while d <= e:
        out.append(d.strftime("%Y-%m-%d"))
        d = d + timedelta(days=step_days)
    return out


def backtest_window(
    start_date: str,
    end_date: str,
    registry: Optional[List[Dict[str, Any]]] = None,
    history_db_path: Optional[Path] = None,
    step_days: int = 1,
    forward_fill_days: int = 10,
) -> List[Dict[str, Any]]:
    """对 [start_date, end_date] 逐日跑综合分。

    入参：
        start_date, end_date: ISO YYYY-MM-DD
        registry: 默认 BACKTEST_INDICATORS（含 vix_fred + libor_ois）
        history_db_path: 可选 cache DB 路径
        step_days: 间隔，1=每日，7=每周
        forward_fill_days: 单条指标向前填充天数
    返回：
        list[dict]，每条含 {date, score, level, breakdown, missing}
    """
    reg = registry if registry is not None else BACKTEST_INDICATORS
    out: List[Dict[str, Any]] = []
    dates = _iter_dates(start_date, end_date, step_days)
    if not dates:
        return out
    with hdbmod.open_history_db(history_db_path) as conn:
        for d in dates:
            try:
                r = compute_score_for_date(conn, d, reg, forward_fill_days=forward_fill_days)
                out.append(r)
            except Exception as e:  # noqa: BLE001 — 单日失败不阻塞整窗口
                log.warning("backtest %s 失败：%s", d, e)
                continue
    return out


def write_csv(results: List[Dict[str, Any]], path: Path, registry: Optional[List[Dict[str, Any]]] = None) -> None:
    """把 backtest_window 输出写 CSV。"""
    reg = registry if registry is not None else BACKTEST_INDICATORS
    indicator_names = [ind["name"] for ind in reg]
    fieldnames = ["date", "score", "level", "missing_count"] + indicator_names

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            row: Dict[str, Any] = {
                "date": r.get("date", ""),
                "score": r.get("score", ""),
                "level": r.get("level", ""),
                "missing_count": len(r.get("missing", [])),
            }
            # 把每条指标的实际值打平到列里
            value_by_name: Dict[str, Any] = {}
            for group_data in r.get("breakdown", {}).values():
                for ind in group_data.get("indicators", []):
                    value_by_name[ind["name"]] = ind.get("value", "")
            for nm in indicator_names:
                row[nm] = value_by_name.get(nm, "")
            writer.writerow(row)


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="历史回测引擎：逐日跑综合分")
    p.add_argument("--start", required=True, help="起始日 YYYY-MM-DD")
    p.add_argument("--end", required=True, help="结束日 YYYY-MM-DD")
    p.add_argument("--step", type=int, default=1, help="日间隔，默认 1")
    p.add_argument("--ff", type=int, default=10, help="forward-fill 天数")
    p.add_argument("--out", default=None, help="输出 CSV 路径（缺省打印汇总）")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(list(argv) if argv is not None else sys.argv[1:])
    log.info("backtest_window %s ~ %s step=%d ff=%d", args.start, args.end, args.step, args.ff)
    results = backtest_window(args.start, args.end, step_days=args.step, forward_fill_days=args.ff)
    log.info("共 %d 个日期点", len(results))
    if not results:
        log.warning("无结果，请检查 cache DB 是否含该窗口数据")
        return 1

    # 简单摘要
    scores = [r["score"] for r in results if isinstance(r.get("score"), (int, float))]
    if scores:
        levels = [r["level"] for r in results]
        red_days = levels.count("RED")
        yellow_days = levels.count("YELLOW")
        green_days = levels.count("GREEN")
        log.info(
            "score min=%.1f max=%.1f mean=%.1f | GREEN %d / YELLOW %d / RED %d 天",
            min(scores), max(scores), sum(scores) / len(scores),
            green_days, yellow_days, red_days,
        )

    if args.out:
        out_path = Path(args.out)
        write_csv(results, out_path)
        log.info("CSV 写入：%s（%d 行）", out_path, len(results))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
