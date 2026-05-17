"""每日数据抓取脚本。

跑一遍所有已注册 fetcher，把最新数据写入 SQLite。
建议挂 launchd 每天美东 16:30 触发（P4）。

用法：
    .venv/bin/python -m scripts.daily_fetch              # 默认从 2020-01-01 拉到今天
    .venv/bin/python -m scripts.daily_fetch --start 2024-01-01
    .venv/bin/python -m scripts.daily_fetch --no-briefing  # 跳过 LLM 简报

日志写 logs/app.log + stdout。失败的 fetcher 不影响其他。
跑完后自动调用 LLM 生成"今日风险简报"（缺 LLM 配置时静默跳过）。
"""
from __future__ import annotations

import argparse
import sys
from typing import Callable, List, NamedTuple

from src.compute import briefing as bf
from src.compute import risk_score as rs
from src.compute.indicators import dxy as dxy_ind
from src.compute.indicators import hy_oas as hyoas_ind
from src.compute.indicators import ig_oas as igoas_ind
from src.compute.indicators import jp_10y as jp10y_ind
from src.compute.indicators import on_rrp as on_rrp_ind
from src.compute.indicators import skew as skew_ind
from src.compute.indicators import sofr_iorb as sofr_ind
from src.compute.indicators import tga as tga_ind
from src.compute.indicators import usdjpy as usdjpy_ind
from src.compute.indicators import vix as vix_ind
from src.compute.indicators import vix_term_structure as vts_ind
from src.compute.indicators import vvix as vvix_ind
from src.compute.indicators import walcl as walcl_ind
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
    Fetcher(name="hy_oas", run=hyoas_ind.fetch_and_store),
    Fetcher(name="ig_oas", run=igoas_ind.fetch_and_store),
    Fetcher(name="vix_term_structure", run=vts_ind.fetch_and_store),
    Fetcher(name="sofr_iorb", run=sofr_ind.fetch_and_store),
    Fetcher(name="usdjpy", run=usdjpy_ind.fetch_and_store),
    Fetcher(name="dxy_broad", run=dxy_ind.fetch_and_store),
    Fetcher(name="jp_10y", run=jp10y_ind.fetch_and_store),
    Fetcher(name="walcl", run=walcl_ind.fetch_and_store),
    Fetcher(name="on_rrp", run=on_rrp_ind.fetch_and_store),
    Fetcher(name="tga", run=tga_ind.fetch_and_store),
    Fetcher(name="vvix", run=vvix_ind.fetch_and_store),
    Fetcher(name="skew", run=skew_ind.fetch_and_store),
]


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="跑一遍所有 fetcher 并入库")
    p.add_argument("--start", default="2020-01-01", help="拉取起始日期 YYYY-MM-DD")
    p.add_argument("--end", default=None, help="拉取结束日期 YYYY-MM-DD（默认到今天）")
    p.add_argument("--no-briefing", action="store_true", help="跳过 LLM 简报生成")
    return p.parse_args(argv)


# 简报生成需要 web/app.py 同款 registry，提取到这里避免循环依赖
def _briefing_registry():
    return [
        {"name": vix_ind.NAME, "label": "VIX 恐慌指数",
         "classify": vix_ind.classify_value, "group": "波动率"},
        {"name": vts_ind.NAME, "label": "VIX 期限结构（VIX/VIX3M）",
         "classify": vts_ind.classify_value, "group": "波动率"},
        {"name": yc_ind.NAME, "label": "10Y-2Y 收益率曲线",
         "classify": yc_ind.classify_value, "group": "曲线"},
        {"name": yc3m_ind.NAME, "label": "10Y-3M 收益率曲线",
         "classify": yc3m_ind.classify_value, "group": "曲线"},
        {"name": hyoas_ind.NAME, "label": "HY OAS 高收益债利差",
         "classify": hyoas_ind.classify_value, "group": "信用"},
        {"name": igoas_ind.NAME, "label": "IG OAS 投资级利差",
         "classify": igoas_ind.classify_value, "group": "信用"},
        {"name": sofr_ind.NAME, "label": "SOFR-IORB 流动性",
         "classify": sofr_ind.classify_value, "group": "流动性"},
        {"name": usdjpy_ind.NAME, "label": "USDJPY 美元日元",
         "classify": usdjpy_ind.classify_value, "group": "跨市场"},
        {"name": dxy_ind.NAME, "label": "DXY 美元广义指数",
         "classify": dxy_ind.classify_value, "group": "跨市场"},
        {"name": jp10y_ind.NAME, "label": "日本 10Y 国债收益率",
         "classify": jp10y_ind.classify_value, "group": "跨市场"},
        {"name": walcl_ind.NAME, "label": "WALCL 联储总资产",
         "classify": walcl_ind.classify_value, "group": "政策"},
        {"name": on_rrp_ind.NAME, "label": "ON RRP 隔夜逆回购",
         "classify": on_rrp_ind.classify_value, "group": "政策"},
        {"name": tga_ind.NAME, "label": "TGA 财政部账户",
         "classify": tga_ind.classify_value, "group": "政策"},
        {"name": vvix_ind.NAME, "label": "VVIX 恐慌之恐慌",
         "classify": vvix_ind.classify_value, "group": "波动率"},
        {"name": skew_ind.NAME, "label": "SKEW 黑天鹅定价",
         "classify": skew_ind.classify_value, "group": "波动率"},
    ]


def run(start: str, end=None, do_briefing: bool = True) -> int:
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
        log.info("daily_fetch 抓取结束：%d 个 fetcher，%d 失败", len(FETCHERS), failed)

        # 算综合风险分（永远先算，不依赖 LLM）
        try:
            score_result = rs.run_and_store(conn, _briefing_registry())
            log.info("综合风险分 score=%.2f level=%s（缺失 %d 条）",
                     score_result["score"], score_result["level"], len(score_result["missing"]))
        except Exception as e:
            log.exception("综合风险分计算异常（不影响主流程）：%s", e)

        if do_briefing:
            try:
                text = bf.run_and_store(conn, _briefing_registry())
                if text:
                    log.info("简报生成成功：%d 字", len(text))
                else:
                    log.info("简报跳过或失败（LLM 未配置或调用失败）")
            except Exception as e:
                log.exception("简报生成异常（不影响主流程）：%s", e)
    return failed


def main(argv=None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    return run(start=args.start, end=args.end, do_briefing=not args.no_briefing)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
