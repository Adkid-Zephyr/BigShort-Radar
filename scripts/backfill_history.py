"""一次性历史回填脚本：拉过去 N 年所有指标的历史序列到 historical_cache.sqlite。

用途：
    sparkline / Z-score / 加速度 / 历史回测 都需要"按指标查 N 年 series"。
    主 DB 只存每日最新一条，从 iter 21 开始攒，历史不够用。
    本脚本一次性把 5 年（默认）历史塞进独立 cache DB。

设计原则：
    - 不动主 DB（独立 cache DB 路径见 src/store/history_db.py::HISTORY_DB_PATH）
    - idempotent：重复跑不重复写（按 (name, date) UNIQUE）
    - 失败一条不影响其他（试 try/except 隔离每个 indicator）
    - 派生指标（含 `/` 或 `,` 的 source 字符串）跳过 + INFO 日志

用法：
    .venv/bin/python -m scripts.backfill_history                # 默认拉过去 5 年
    .venv/bin/python -m scripts.backfill_history --start 2010-01-01
    .venv/bin/python -m scripts.backfill_history --only vix     # 只拉一条

日志写 logs/app.log + stdout。
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from typing import List, NamedTuple, Optional

from src.compute.indicators import china_10y as china_10y_ind
from src.compute.indicators import china_fx_reserves as china_fx_ind
from src.compute.indicators import dxy as dxy_ind
from src.compute.indicators import fra_ois as fra_ois_ind
from src.compute.indicators import hy_oas as hyoas_ind
from src.compute.indicators import ig_oas as igoas_ind
from src.compute.indicators import jp_10y as jp10y_ind
from src.compute.indicators import on_rrp as on_rrp_ind
from src.compute.indicators import skew as skew_ind
from src.compute.indicators import sofr_iorb as sofr_ind
from src.compute.indicators import tga as tga_ind
from src.compute.indicators import usdcny as usdcny_ind
from src.compute.indicators import usdjpy as usdjpy_ind
from src.compute.indicators import vix as vix_ind
from src.compute.indicators import vix1y as vix1y_ind
from src.compute.indicators import vix9d as vix9d_ind
from src.compute.indicators import vix_term_structure as vts_ind
from src.compute.indicators import vvix as vvix_ind
from src.compute.indicators import walcl as walcl_ind
from src.compute.indicators import yield_curve as yc_ind
from src.compute.indicators import yield_curve_10y3m as yc3m_ind
from src.fetch import history_fetcher as hf
from src.store import history_db as hdb
from src.utils.logger import get_logger

log = get_logger("backfill_history")


class Target(NamedTuple):
    """一条要回填的指标：name + source 字符串。"""
    name: str
    source: str


# 注册所有要回填的指标。只放有原生历史源的（FRED/YF），派生指标在脚本里跳过
TARGETS: List[Target] = [
    Target(name=vix_ind.NAME, source=vix_ind.SOURCE),
    Target(name=yc_ind.NAME, source=yc_ind.SOURCE),
    Target(name=yc3m_ind.NAME, source=yc3m_ind.SOURCE),
    Target(name=hyoas_ind.NAME, source=hyoas_ind.SOURCE),
    Target(name=igoas_ind.NAME, source=igoas_ind.SOURCE),
    Target(name=vts_ind.NAME, source=vts_ind.SOURCE),
    Target(name=vix9d_ind.NAME, source=vix9d_ind.SOURCE),
    Target(name=vix1y_ind.NAME, source=vix1y_ind.SOURCE),
    Target(name=sofr_ind.NAME, source=sofr_ind.SOURCE),   # 派生（FRED:SOFR-IORB），脚本里跳过
    Target(name=usdjpy_ind.NAME, source=usdjpy_ind.SOURCE),
    Target(name=dxy_ind.NAME, source=dxy_ind.SOURCE),
    Target(name=jp10y_ind.NAME, source=jp10y_ind.SOURCE),
    Target(name=walcl_ind.NAME, source=walcl_ind.SOURCE),
    Target(name=on_rrp_ind.NAME, source=on_rrp_ind.SOURCE),
    Target(name=tga_ind.NAME, source=tga_ind.SOURCE),
    Target(name=vvix_ind.NAME, source=vvix_ind.SOURCE),
    Target(name=skew_ind.NAME, source=skew_ind.SOURCE),
    Target(name=fra_ois_ind.NAME, source=fra_ois_ind.SOURCE),  # 派生 FRED:DGS3MO-SOFR 跳过
    Target(name=china_fx_ind.NAME, source=china_fx_ind.SOURCE),
    Target(name=usdcny_ind.NAME, source=usdcny_ind.SOURCE),
    Target(name=china_10y_ind.NAME, source=china_10y_ind.SOURCE),
]

# 仅回测用扩展（iter 52 / iter 57）：走 --backtest 标志才纳入
BACKTEST_EXTRA_TARGETS: List[Target] = [
    Target(name="vix_fred", source="FRED:VIXCLS"),
    Target(name="ted_spread", source="FRED:TEDRATE"),  # 替代 LIBOR-OIS（USD3MTD156N 已停发）
    # iter 57:派生指标(vix_term_structure / sofr_iorb / fra_ois)的底层成分,
    # 让 src/backtest/derived.py 能现场算出派生值,消除三窗口 100% missing
    Target(name="vix3m", source="YF:^VIX3M"),     # vts = vix / vix3m
    Target(name="sofr_raw", source="FRED:SOFR"),  # sofr_iorb / fra_ois 共用
    Target(name="iorb_raw", source="FRED:IORB"),  # sofr_iorb 用
    Target(name="dgs3mo", source="FRED:DGS3MO"),  # fra_ois 用
]


def _is_derived(source: str) -> bool:
    """判断 source 是否是派生（多源合成或纯计算结果）。

    识别规则：
      - 含 `/` → 比值/除法派生（如 YF:^VIX/^VIX3M）
      - 含 `,` → 多源逗号分隔
      - 含 `-` 且前缀是 FRED → 减法派生（如 FRED:SOFR-IORB；FRED 真实 series id 不含 `-`）
    """
    prefix, _, ident = source.partition(":")
    if "/" in ident or "," in ident:
        return True
    if prefix.upper() == "FRED" and "-" in ident:
        return True
    return False


def _default_start(years: int = 5) -> str:
    """默认起始日：今天往前 N 年。"""
    d = date.today() - timedelta(days=int(years * 365.25))
    return d.strftime("%Y-%m-%d")


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="一次性回填历史数据到 cache DB")
    p.add_argument("--start", default=None, help="起始日 YYYY-MM-DD（默认今天往前 5 年）")
    p.add_argument("--end", default=None, help="结束日 YYYY-MM-DD（默认到今天）")
    p.add_argument("--years", type=int, default=5, help="回填年数（默认 5），仅当 --start 缺省时生效")
    p.add_argument("--only", default=None, help="只回填某条指标（NAME 完整匹配），便于调试")
    p.add_argument(
        "--backtest", action="store_true",
        help="纳入回测用扩展指标（vix_fred / libor_ois）。配合 --start 2006-01-01 拉长历史",
    )
    return p.parse_args(argv)


def run_one(target: Target, start: str, end: Optional[str], conn) -> int:
    """回填单条指标，返回入库行数（派生 / 失败均返 0）。

    入参：
        target: Target(name, source)
        start: ISO 起始日
        end: ISO 结束日 / None
        conn: history cache DB 连接
    返回：
        入库行数；派生跳过返 0；失败返 0
    """
    if _is_derived(target.source):
        log.info("[%s] 派生指标 source=%s，跳过历史回填（sparkline 走主 DB 累积）", target.name, target.source)
        return 0

    log.info("[%s] 开始回填 source=%s 区间 %s..%s", target.name, target.source, start, end or "now")
    try:
        series = hf.fetch_history(target.source, start=start, end=end)
    except Exception as e:  # noqa: BLE001 — 防御性兜底，底层 fetcher 已 try/except 但万一漏了
        log.error("[%s] fetch_history 异常: %s", target.name, e)
        return 0

    if series is None:
        log.warning("[%s] fetch_history 返回 None，跳过", target.name)
        return 0

    try:
        n = hdb.bulk_upsert(conn, name=target.name, source=target.source, series=series)
    except Exception as e:  # noqa: BLE001
        log.error("[%s] bulk_upsert 异常: %s", target.name, e)
        return 0

    log.info("[%s] 入库 %d 条", target.name, n)
    return n


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(list(argv) if argv is not None else sys.argv[1:])
    start = args.start or _default_start(args.years)
    end = args.end

    # iter 52: --backtest 标志纳入 vix_fred / libor_ois
    base_targets = TARGETS + (BACKTEST_EXTRA_TARGETS if args.backtest else [])
    targets = base_targets
    if args.only:
        targets = [t for t in base_targets if t.name == args.only]
        if not targets:
            log.error("--only %s 没匹配到任何 target，可选：%s",
                      args.only, [t.name for t in base_targets])
            return 2

    total = 0
    failures = 0
    with hdb.open_history_db() as conn:
        for t in targets:
            try:
                total += run_one(t, start=start, end=end, conn=conn)
            except Exception as e:  # noqa: BLE001
                log.error("[%s] 整体失败: %s", t.name, e)
                failures += 1

    log.info("回填完成：targets=%d 入库总计=%d failures=%d", len(targets), total, failures)
    return 0 if failures == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
