"""每日数据抓取脚本。

跑一遍所有已注册 fetcher，把最新数据写入 SQLite。
建议挂 launchd 每天美东 16:30 触发（P4）。

用法：
    .venv/bin/python -m scripts.daily_fetch              # 默认从 2020-01-01 拉到今天
    .venv/bin/python -m scripts.daily_fetch --start 2024-01-01

日志写 logs/app.log + stdout。失败的 fetcher 不影响其他。
"""
from __future__ import annotations

import argparse
import sys
from typing import Callable, List, NamedTuple

from src.compute.indicators import vix as vix_ind
from src.compute.indicators import yield_curve as yc_ind
from src.compute.indicators import yield_curve_10y3m as yc3m_ind
from src.store import db as dbmod
from src.utils.logger import get_logger

log = get_logger("daily_fetch")


class Fetcher(NamedTuple):
    name: str
    run: Callable[..., int]  # (conn, start) -> 入库条数


# 已实现的 fetcher 注册（FRED 系列等用户给 key 后再加）
FETCHERS: List[Fetcher] = [
    Fetcher(name="vix", run=vix_ind.fetch_and_store),
    Fetcher(name="yield_curve_10y2y", run=yc_ind.fetch_and_store),
    Fetcher(name="yield_curve_10y3m", run=yc3m_ind.fetch_and_store),
]


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="跑一遍所有 fetcher 并入库")
    p.add_argument("--start", default="2020-01-01", help="拉取起始日期 YYYY-MM-DD")
    p.add_argument("--end", default=None, help="拉取结束日期 YYYY-MM-DD（默认到今天）")
    return p.parse_args(argv)


def run(start: str, end=None) -> int:
    """跑所有 fetcher。返回失败数（0 表示全成功）。"""
    failed = 0
    with dbmod.open_db() as conn:
        for f in FETCHERS:
            try:
                n = f.run(conn, start=start, end=end)
                log.info("[%s] 入库 %d 条", f.name, n)
            except Exception as e:  # 单个 fetcher 失败不影响其他
                log.exception("[%s] 失败：%s", f.name, e)
                failed += 1
    log.info("daily_fetch 结束：%d 个 fetcher，%d 失败", len(FETCHERS), failed)
    return failed


def main(argv=None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    return run(start=args.start, end=args.end)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
