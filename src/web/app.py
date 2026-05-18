"""Flask Web 应用：薄渲染层。

只做：从 store 读数据 → 算颜色 → 渲染模板。
不做：拉数、算阈值（阈值用 indicators 模块的常量）。

注册新指标的方式：在 _INDICATOR_REGISTRY 加一行（name, classify_fn, label）。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

from flask import Flask, abort, jsonify, render_template, request

from src.compute import briefing as bf
from src.compute import risk_score as rs
from src.compute.indicators import china_10y as china_10y_ind
from src.compute.indicators import china_fx_reserves as china_fx_ind
from src.compute.indicators import dxy as dxy_ind
from src.compute.indicators import fra_ois as fra_ois_ind
from src.compute.indicators import hy_oas as hyoas_ind
from src.compute.indicators import ig_oas as igoas_ind
from src.compute.indicators import jp_10y as jp10y_ind
from src.compute.indicators import on_rrp as on_rrp_ind
from src.compute.indicators import put_call_equity as put_call_equity_ind
from src.compute.indicators import put_call_index as put_call_index_ind
from src.compute.indicators import put_call_total as put_call_ind
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
from src.compute.thresholds import Level
from src.store import db as dbmod
from src.store import history_db as hdbmod
from src.utils.config import load_settings
from src.utils.logger import get_logger
from src.web.acceleration import compute_acceleration
from src.web.charts import build_indicator_chart_html
from src.web.comparisons import build_comparisons
from src.web.events import detect_indicator_events, merge_events
from src.web.hedge_calibration import calibrate_threshold, split_risk_vs_hedge
from src.web.heatmap import build_heatmap_html, build_risk_timeline_html
from src.web.scenarios import evaluate_scenarios
from src.web.source_links import source_url as derive_source_url
from src.web.sparkline import build_sparkline_svg
from src.web.zscore import compute_zscore

log = get_logger(__name__)

# 模板目录在项目根 templates/，不是 src/web/templates/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATE_DIR = _PROJECT_ROOT / "templates"


# ── 指标注册表 ────────────────────────────────────────────────
# 加一个新指标，只需在这里加一行（含 group 字段做分组）
# group 取值约定：曲线 / 信用 / 流动性 / 波动率 / 估值（待加）
#
# source_url：可选。指标"数据源"对应的官方页面 URL（点击 source 列跳转用）。
# 大多数指标可由 src/web/source_links.py 从 source 字符串自动推导（FRED:/YF: 等）；
# 派生指标（多源比值/差值，如 VIX 期限结构）需在这里手填权威页 URL。
#
# threshold_low / threshold_high / direction：iter 39 加，sparkline 阈值带需要。
# 直接引用 indicator 模块常量，避免与模块定义重复。
_INDICATOR_REGISTRY: List[Dict[str, Any]] = [
    # 波动率维度
    {
        "name": vix_ind.NAME,
        "label": "VIX 恐慌指数",
        "classify": vix_ind.classify_value,
        "group": "波动率",
        "threshold_low": vix_ind.THRESHOLD_LOW,
        "threshold_high": vix_ind.THRESHOLD_HIGH,
        "direction": vix_ind.DIRECTION,
        # source = FRED:VIXCLS，自动推导 → 不写 source_url
    },
    {
        "name": vts_ind.NAME,
        "label": "VIX 期限结构（VIX/VIX3M）",
        "classify": vts_ind.classify_value,
        "group": "波动率",
        "threshold_low": vts_ind.THRESHOLD_LOW,
        "threshold_high": vts_ind.THRESHOLD_HIGH,
        "direction": vts_ind.DIRECTION,
        # 派生指标：VIX/VIX3M 比值，没有单一官方页 → 链到 CBOE VIX term structure 介绍页
        "source_url": "https://www.cboe.com/tradable_products/vix/vix_options/specifications/",
    },
    {
        "name": vix9d_ind.NAME,
        "label": "VIX9D 短端恐慌",
        "classify": vix9d_ind.classify_value,
        "group": "波动率",
        "threshold_low": vix9d_ind.THRESHOLD_LOW,
        "threshold_high": vix9d_ind.THRESHOLD_HIGH,
        "direction": vix9d_ind.DIRECTION,
    },
    {
        "name": vix1y_ind.NAME,
        "label": "VIX1Y 长端恐慌",
        "classify": vix1y_ind.classify_value,
        "group": "波动率",
        "threshold_low": vix1y_ind.THRESHOLD_LOW,
        "threshold_high": vix1y_ind.THRESHOLD_HIGH,
        "direction": vix1y_ind.DIRECTION,
    },
    {
        "name": vvix_ind.NAME,
        "label": "VVIX 恐慌之恐慌",
        "classify": vvix_ind.classify_value,
        "group": "波动率",
        "threshold_low": vvix_ind.THRESHOLD_LOW,
        "threshold_high": vvix_ind.THRESHOLD_HIGH,
        "direction": vvix_ind.DIRECTION,
    },
    {
        "name": skew_ind.NAME,
        "label": "SKEW 黑天鹅定价",
        "classify": skew_ind.classify_value,
        "group": "波动率",
        "threshold_low": skew_ind.THRESHOLD_LOW,
        "threshold_high": skew_ind.THRESHOLD_HIGH,
        "direction": skew_ind.DIRECTION,
    },
    # 期权情绪维度（iter 62:Put/Call 从波动率拆出）
    {
        "name": put_call_ind.NAME,
        "label": "CBOE Total Put/Call",
        "classify": put_call_ind.classify_value,
        "group": "期权情绪",
        "threshold_low": put_call_ind.THRESHOLD_LOW,
        "threshold_high": put_call_ind.THRESHOLD_HIGH,
        "direction": put_call_ind.DIRECTION,
    },
    {
        "name": put_call_index_ind.NAME,
        "label": "CBOE Index Put/Call",
        "classify": put_call_index_ind.classify_value,
        "group": "期权情绪",
        "threshold_low": put_call_index_ind.THRESHOLD_LOW,
        "threshold_high": put_call_index_ind.THRESHOLD_HIGH,
        "direction": put_call_index_ind.DIRECTION,
    },
    {
        "name": put_call_equity_ind.NAME,
        "label": "CBOE Equity Put/Call",
        "classify": put_call_equity_ind.classify_value,
        "group": "期权情绪",
        "threshold_low": put_call_equity_ind.THRESHOLD_LOW,
        "threshold_high": put_call_equity_ind.THRESHOLD_HIGH,
        "direction": put_call_equity_ind.DIRECTION,
    },
    # 曲线维度
    {
        "name": yc_ind.NAME,
        "label": "10Y-2Y 收益率曲线",
        "classify": yc_ind.classify_value,
        "group": "曲线",
        "threshold_low": yc_ind.THRESHOLD_LOW,
        "threshold_high": yc_ind.THRESHOLD_HIGH,
        "direction": yc_ind.DIRECTION,
    },
    {
        "name": yc3m_ind.NAME,
        "label": "10Y-3M 收益率曲线",
        "classify": yc3m_ind.classify_value,
        "group": "曲线",
        "threshold_low": yc3m_ind.THRESHOLD_LOW,
        "threshold_high": yc3m_ind.THRESHOLD_HIGH,
        "direction": yc3m_ind.DIRECTION,
    },
    # 信用维度
    {
        "name": hyoas_ind.NAME,
        "label": "HY OAS 高收益债利差",
        "classify": hyoas_ind.classify_value,
        "group": "信用",
        "threshold_low": hyoas_ind.THRESHOLD_LOW,
        "threshold_high": hyoas_ind.THRESHOLD_HIGH,
        "direction": hyoas_ind.DIRECTION,
    },
    {
        "name": igoas_ind.NAME,
        "label": "IG OAS 投资级利差",
        "classify": igoas_ind.classify_value,
        "group": "信用",
        "threshold_low": igoas_ind.THRESHOLD_LOW,
        "threshold_high": igoas_ind.THRESHOLD_HIGH,
        "direction": igoas_ind.DIRECTION,
    },
    # 流动性维度
    {
        "name": sofr_ind.NAME,
        "label": "SOFR-IORB 流动性",
        "classify": sofr_ind.classify_value,
        "group": "流动性",
        "threshold_low": sofr_ind.THRESHOLD_LOW,
        "threshold_high": sofr_ind.THRESHOLD_HIGH,
        "direction": sofr_ind.DIRECTION,
        # 派生指标：SOFR - IORB 利差，链 FRED SOFR 主页
        "source_url": "https://fred.stlouisfed.org/series/SOFR",
    },
    # 融资市场维度（iter 46 加，THESIS §4.3）
    {
        "name": fra_ois_ind.NAME,
        "label": "FRA-OIS 代理（3M T-Bill - SOFR）",
        "classify": fra_ois_ind.classify_value,
        "group": "流动性",
        "threshold_low": fra_ois_ind.THRESHOLD_LOW,
        "threshold_high": fra_ois_ind.THRESHOLD_HIGH,
        "direction": fra_ois_ind.DIRECTION,
        "source_url": "https://fred.stlouisfed.org/series/DGS3MO",
    },
    # 跨市场 / 日本维度
    {
        "name": usdjpy_ind.NAME,
        "label": "USDJPY 美元日元",
        "classify": usdjpy_ind.classify_value,
        "group": "跨市场",
        "threshold_low": usdjpy_ind.THRESHOLD_LOW,
        "threshold_high": usdjpy_ind.THRESHOLD_HIGH,
        "direction": usdjpy_ind.DIRECTION,
    },
    {
        "name": dxy_ind.NAME,
        "label": "DXY 美元广义指数",
        "classify": dxy_ind.classify_value,
        "group": "跨市场",
        "threshold_low": dxy_ind.THRESHOLD_LOW,
        "threshold_high": dxy_ind.THRESHOLD_HIGH,
        "direction": dxy_ind.DIRECTION,
    },
    {
        "name": jp10y_ind.NAME,
        "label": "日本 10Y 国债收益率",
        "classify": jp10y_ind.classify_value,
        "group": "跨市场",
        "threshold_low": jp10y_ind.THRESHOLD_LOW,
        "threshold_high": jp10y_ind.THRESHOLD_HIGH,
        "direction": jp10y_ind.DIRECTION,
    },
    # 政策反应维度（iter 44 加）
    {
        "name": walcl_ind.NAME,
        "label": "WALCL 联储总资产",
        "classify": walcl_ind.classify_value,
        "group": "政策",
        "threshold_low": walcl_ind.THRESHOLD_LOW,
        "threshold_high": walcl_ind.THRESHOLD_HIGH,
        "direction": walcl_ind.DIRECTION,
    },
    {
        "name": on_rrp_ind.NAME,
        "label": "ON RRP 隔夜逆回购",
        "classify": on_rrp_ind.classify_value,
        "group": "政策",
        "threshold_low": on_rrp_ind.THRESHOLD_LOW,
        "threshold_high": on_rrp_ind.THRESHOLD_HIGH,
        "direction": on_rrp_ind.DIRECTION,
    },
    {
        "name": tga_ind.NAME,
        "label": "TGA 财政部账户",
        "classify": tga_ind.classify_value,
        "group": "政策",
        "threshold_low": tga_ind.THRESHOLD_LOW,
        "threshold_high": tga_ind.THRESHOLD_HIGH,
        "direction": tga_ind.DIRECTION,
    },
    # 中国维度（iter 46 加，THESIS §4.4 三角联动）
    {
        "name": china_fx_ind.NAME,
        "label": "中国外汇储备",
        "classify": china_fx_ind.classify_value,
        "group": "中国",
        "threshold_low": china_fx_ind.THRESHOLD_LOW,
        "threshold_high": china_fx_ind.THRESHOLD_HIGH,
        "direction": china_fx_ind.DIRECTION,
    },
    {
        "name": usdcny_ind.NAME,
        "label": "USDCNY 在岸人民币",
        "classify": usdcny_ind.classify_value,
        "group": "中国",
        "threshold_low": usdcny_ind.THRESHOLD_LOW,
        "threshold_high": usdcny_ind.THRESHOLD_HIGH,
        "direction": usdcny_ind.DIRECTION,
    },
    {
        "name": china_10y_ind.NAME,
        "label": "中国 10Y 国债收益率",
        "classify": china_10y_ind.classify_value,
        "group": "中国",
        "threshold_low": china_10y_ind.THRESHOLD_LOW,
        "threshold_high": china_10y_ind.THRESHOLD_HIGH,
        "direction": china_10y_ind.DIRECTION,
    },
]

# 注册表的快速索引（O(1) 按 name 查），iter 40 加（详情页路由用）
_REGISTRY_BY_NAME: Dict[str, Dict[str, Any]] = {ind["name"]: ind for ind in _INDICATOR_REGISTRY}

# 给 registry 每条补 "source" 字段（详情页显示用），从 indicator 模块拿
for _ind in _INDICATOR_REGISTRY:
    _name = _ind["name"]
    if _name == vix_ind.NAME:
        _ind.setdefault("source", vix_ind.SOURCE)
    elif _name == vts_ind.NAME:
        _ind.setdefault("source", vts_ind.SOURCE)
    elif _name == vix9d_ind.NAME:
        _ind.setdefault("source", vix9d_ind.SOURCE)
    elif _name == vix1y_ind.NAME:
        _ind.setdefault("source", vix1y_ind.SOURCE)
    elif _name == put_call_ind.NAME:
        _ind.setdefault("source", put_call_ind.SOURCE)
    elif _name == put_call_index_ind.NAME:
        _ind.setdefault("source", put_call_index_ind.SOURCE)
    elif _name == put_call_equity_ind.NAME:
        _ind.setdefault("source", put_call_equity_ind.SOURCE)
    elif _name == yc_ind.NAME:
        _ind.setdefault("source", yc_ind.SOURCE)
    elif _name == yc3m_ind.NAME:
        _ind.setdefault("source", yc3m_ind.SOURCE)
    elif _name == hyoas_ind.NAME:
        _ind.setdefault("source", hyoas_ind.SOURCE)
    elif _name == igoas_ind.NAME:
        _ind.setdefault("source", igoas_ind.SOURCE)
    elif _name == sofr_ind.NAME:
        _ind.setdefault("source", sofr_ind.SOURCE)
    elif _name == usdjpy_ind.NAME:
        _ind.setdefault("source", usdjpy_ind.SOURCE)
    elif _name == dxy_ind.NAME:
        _ind.setdefault("source", dxy_ind.SOURCE)
    elif _name == jp10y_ind.NAME:
        _ind.setdefault("source", jp10y_ind.SOURCE)
    elif _name == walcl_ind.NAME:
        _ind.setdefault("source", walcl_ind.SOURCE)
    elif _name == on_rrp_ind.NAME:
        _ind.setdefault("source", on_rrp_ind.SOURCE)
    elif _name == tga_ind.NAME:
        _ind.setdefault("source", tga_ind.SOURCE)
    elif _name == vvix_ind.NAME:
        _ind.setdefault("source", vvix_ind.SOURCE)
    elif _name == skew_ind.NAME:
        _ind.setdefault("source", skew_ind.SOURCE)
    elif _name == fra_ois_ind.NAME:
        _ind.setdefault("source", fra_ois_ind.SOURCE)
    elif _name == china_fx_ind.NAME:
        _ind.setdefault("source", china_fx_ind.SOURCE)
    elif _name == usdcny_ind.NAME:
        _ind.setdefault("source", usdcny_ind.SOURCE)
    elif _name == china_10y_ind.NAME:
        _ind.setdefault("source", china_10y_ind.SOURCE)


# 分组展示顺序（左到右、上到下；用户视角通常先看波动率再看信用再看曲线再看流动性）
_GROUP_ORDER = ["波动率", "期权情绪", "信用", "曲线", "流动性", "政策", "跨市场", "中国", "估值"]


# Level → 颜色（Tailwind 风格的色值，inline style 用）
_LEVEL_COLORS = {
    Level.GREEN: "#22c55e",
    Level.YELLOW: "#eab308",
    Level.RED: "#ef4444",
}


def _fetch_history_pairs(
    main_conn,
    name: str,
    days: int = 90,
    history_db_path=None,
) -> "tuple[List[str], List[float]]":
    """取最近 N 天历史 (dates, values) 两个等长 list。

    优先 history cache DB（5 年回填），少于 10 个点走主 DB 兜底。

    入参：
        main_conn: 主 DB 连接
        name: 指标 name
        days: 取最近多少天
        history_db_path: 可选 cache DB 路径
    返回：
        (dates_iso, values) 等长 list，按 date 升序；无数据返 ([], [])
    """
    today = datetime.now(tz=timezone.utc).date()
    today_iso = today.strftime("%Y-%m-%d")
    start_iso = (today - timedelta(days=days)).strftime("%Y-%m-%d")

    dates: List[str] = []
    values: List[float] = []

    # 优先 history cache DB
    try:
        with hdbmod.open_history_db(history_db_path) as hconn:
            hist_rows = hdbmod.get_series_range(hconn, name, start=start_iso, end=today_iso)
            dates = [str(r["date"]) for r in hist_rows]
            values = [float(r["value"]) for r in hist_rows]
    except Exception as e:  # noqa: BLE001
        log.warning("history pairs: history_db 取 %s 失败 (%s)，走主 DB 兜底", name, e)

    # 兜底：主 DB
    if len(values) < 10:
        main_rows = dbmod.get_series(main_conn, name, days=days)
        dates = [str(r["date"]) for r in main_rows]
        values = [float(r["value"]) for r in main_rows]

    return dates, values


def _fetch_sparkline_values(
    main_conn,
    name: str,
    days: int = 90,
    history_db_path=None,
) -> List[float]:
    """取最近 N 天 values（sparkline 不需 dates）。复用 _fetch_history_pairs。"""
    _, values = _fetch_history_pairs(main_conn, name, days=days, history_db_path=history_db_path)
    return values


def _fetch_sparkline_dates(
    main_conn,
    name: str,
    days: int = 90,
    history_db_path=None,
) -> List[str]:
    """取最近 N 天 dates（详情页配合 values 给 plotly x 轴）。"""
    dates, _ = _fetch_history_pairs(main_conn, name, days=days, history_db_path=history_db_path)
    return dates


def _build_rows(conn, history_db_path=None) -> List[Dict[str, Any]]:
    """从 DB 拉每个已注册指标的最新值，组装渲染行（含 group / source_url / sparkline_svg / comparisons）。"""
    rows: List[Dict[str, Any]] = []
    for ind in _INDICATOR_REGISTRY:
        latest = dbmod.get_latest(conn, ind["name"])
        # source_url：registry 手填优先，没填走自动推导（FRED:/YF: 等前缀）
        registry_url = ind.get("source_url")
        # sparkline + comparisons 共用 history pairs
        spark_dates, spark_values = _fetch_history_pairs(
            conn, ind["name"], days=120, history_db_path=history_db_path
        )
        sparkline_svg = build_sparkline_svg(
            values=spark_values[-90:] if len(spark_values) > 90 else spark_values,  # sparkline 仅展示最近 90
            threshold_low=ind.get("threshold_low"),
            threshold_high=ind.get("threshold_high"),
            direction=ind.get("direction", "up"),
        )

        # 同环比对比（7d / 30d / 90d）
        today_d = None
        if latest is not None and latest.get("date"):
            try:
                today_d = datetime.strptime(str(latest["date"])[:10], "%Y-%m-%d").date()
            except ValueError:
                today_d = None
        try:
            comparisons = build_comparisons(
                dates=spark_dates,
                values=spark_values,
                today_value=latest["value"] if latest else None,
                today_date=today_d,
                direction=ind.get("direction", "up"),
                lookbacks=(7, 30, 90),
            )
        except Exception as e:  # noqa: BLE001 — 防御性
            log.warning("comparisons 计算 %s 失败: %s", ind["name"], e)
            comparisons = {7: {}, 30: {}, 90: {}}

        # Z-score（长期分布）：取 5 年历史（约 1825 天），不够回退到现有 spark_values
        zscore_info: Dict[str, Any] = {"z": None, "percentile": None, "extreme": None, "n": 0}
        try:
            _, long_values = _fetch_history_pairs(
                conn, ind["name"], days=1825, history_db_path=history_db_path
            )
            if long_values:
                zscore_info = compute_zscore(
                    history_values=long_values,
                    current_value=latest["value"] if latest else None,
                    direction=ind.get("direction", "up"),
                )
        except Exception as e:  # noqa: BLE001
            log.warning("zscore 计算 %s 失败: %s", ind["name"], e)

        # 加速度（短窗 5 / 长窗 20）：用 spark_values 现成的 120 天即够
        try:
            accel_info = compute_acceleration(
                values=spark_values,
                direction=ind.get("direction", "up"),
                short_window=5,
                long_window=20,
            )
        except Exception as e:  # noqa: BLE001
            log.warning("acceleration 计算 %s 失败: %s", ind["name"], e)
            accel_info = {"short_slope": None, "long_slope": None, "ratio": None, "accelerating": None}

        if latest is None:
            rows.append({
                "name": ind["name"],
                "label": ind["label"],
                "group": ind.get("group", "其他"),
                "value": None,
                "level": None,
                "color": "#9ca3af",  # gray
                "date": None,
                "source": None,
                "source_url": registry_url,  # 即使无数据也保留外链供查阅
                "ingested_at": None,
                "sparkline_svg": sparkline_svg,
                "comparisons": comparisons,
                "zscore": zscore_info,
                "acceleration": accel_info,
            })
            continue
        level = ind["classify"](latest["value"])
        url = registry_url or derive_source_url(latest["source"])
        rows.append({
            "name": ind["name"],
            "label": ind["label"],
            "group": ind.get("group", "其他"),
            "value": latest["value"],
            "level": level.value,
            "color": _LEVEL_COLORS.get(level, "#9ca3af"),
            "date": latest["date"],
            "source": latest["source"],
            "source_url": url,
            "ingested_at": latest["ingested_at"],
            "sparkline_svg": sparkline_svg,
            "comparisons": comparisons,
            "zscore": zscore_info,
            "acceleration": accel_info,
        })
    return rows


def _group_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把 rows 按 group 聚合，并算每组的"最重等级"用于 group header 颜色。

    返回结构：[{group, header_color, header_level, rows: [...]}, ...]
    顺序按 _GROUP_ORDER；不在表中的 group 排尾。
    """
    by_group: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        by_group.setdefault(r["group"], []).append(r)

    # group 的整体等级 = 该组内最严重的 level（RED > YELLOW > GREEN > 无）
    severity = {"RED": 3, "YELLOW": 2, "GREEN": 1, None: 0}

    ordered: List[Dict[str, Any]] = []
    seen = set()
    for g in _GROUP_ORDER:
        if g not in by_group:
            continue
        seen.add(g)
        grp_rows = by_group[g]
        worst = max(grp_rows, key=lambda r: severity.get(r["level"], 0))
        ordered.append({
            "group": g,
            "header_level": worst["level"],
            "header_color": worst["color"],
            "rows": grp_rows,
        })
    # 兜底：未在 _GROUP_ORDER 的组追加到末尾
    for g, grp_rows in by_group.items():
        if g in seen:
            continue
        worst = max(grp_rows, key=lambda r: severity.get(r["level"], 0))
        ordered.append({
            "group": g,
            "header_level": worst["level"],
            "header_color": worst["color"],
            "rows": grp_rows,
        })
    return ordered


def create_app(db_path=None, history_db_path=None) -> Flask:
    """工厂函数：创建 Flask 应用。

    入参：
        db_path: 可选，覆盖默认主 DB 路径（测试用）
        history_db_path: 可选，覆盖历史 cache DB 路径（测试用）
    返回：
        Flask 应用实例
    """
    settings = load_settings()
    app = Flask(__name__, template_folder=str(_TEMPLATE_DIR))
    app.config["DB_PATH"] = db_path if db_path is not None else settings.db_path
    app.config["HISTORY_DB_PATH"] = history_db_path  # None = 走 hdbmod 默认

    @app.route("/")
    def index():
        target = app.config["DB_PATH"]
        hist_target = app.config.get("HISTORY_DB_PATH")
        with dbmod.open_db(target) as conn:
            rows = _build_rows(conn, history_db_path=hist_target)
            briefing = bf.get_latest_briefing(conn)
            risk = rs.get_latest_risk_score(conn)
            # 评估 5 剧本
            indicator_states = {}
            for ind in _INDICATOR_REGISTRY:
                latest = dbmod.get_latest(conn, ind["name"])
                indicator_states[ind["name"]] = {
                    "latest": latest,
                    "classify": ind["classify"],
                }
        scenarios = evaluate_scenarios(indicator_states)
        groups = _group_rows(rows)
        return render_template(
            "index.html",
            rows=rows, groups=groups,
            briefing=briefing, risk=risk,
            scenarios=scenarios,
            level_colors={k.value: v for k, v in _LEVEL_COLORS.items()},
            active_page="index",
        )

    @app.route("/indicator/<name>")
    def indicator_detail(name: str):
        """指标详情页：5 年 plotly 大图 + 元信息 + 阈值带。"""
        ind = _REGISTRY_BY_NAME.get(name)
        if ind is None:
            abort(404)

        target = app.config["DB_PATH"]
        hist_target = app.config.get("HISTORY_DB_PATH")

        # 取尽可能多的历史数据：cache DB（5 年回填）+ 主 DB 兜底
        # 详情页要全量，days=None 拿全部；这里 days=2000 (~5.5 年) 上限
        days_window = 2000
        with dbmod.open_db(target) as main_conn:
            spark_values = _fetch_sparkline_values(
                main_conn, name, days=days_window, history_db_path=hist_target
            )
            # 取对应日期：与 _fetch_sparkline_values 同源，但要保留日期信息
            dates = _fetch_sparkline_dates(
                main_conn, name, days=days_window, history_db_path=hist_target
            )
            latest = dbmod.get_latest(main_conn, name)

        # 长度对齐（防御）
        if len(dates) != len(spark_values):
            dates = dates[: len(spark_values)]
            spark_values = spark_values[: len(dates)]

        # 当前等级与颜色
        level = None
        color = "#9ca3af"
        if latest is not None:
            lv = ind["classify"](latest["value"])
            level = lv.value
            color = _LEVEL_COLORS.get(lv, "#9ca3af")

        # source URL
        registry_url = ind.get("source_url")
        derived_url = derive_source_url(latest["source"]) if latest else derive_source_url(ind.get("source"))
        source_url = registry_url or derived_url

        # plotly 大图
        chart_html = build_indicator_chart_html(
            name=ind["name"],
            label=ind["label"],
            dates=dates,
            values=spark_values,
            threshold_low=ind.get("threshold_low"),
            threshold_high=ind.get("threshold_high"),
            direction=ind.get("direction", "up"),
        )

        return render_template(
            "indicator_detail.html",
            ind=ind,
            level=level,
            color=color,
            latest_value=latest["value"] if latest else None,
            latest_date=latest["date"] if latest else None,
            source_url=source_url,
            chart_html=chart_html,
            point_count=len(spark_values),
            active_page="index",  # 详情页归入"指标"栏目
        )

    @app.route("/events")
    def events():
        """异常事件流页（视角 F）：扫所有指标过去 30 天的翻档/突破/突变事件。"""
        target = app.config["DB_PATH"]
        hist_target = app.config.get("HISTORY_DB_PATH")
        per_indicator = []
        with dbmod.open_db(target) as conn:
            for ind in _INDICATOR_REGISTRY:
                # 取 60 天历史以保证 30 天窗口前面也有"前一日"做翻档对比
                dates, values = _fetch_history_pairs(
                    conn, ind["name"], days=60, history_db_path=hist_target
                )
                if len(values) < 2:
                    continue
                evs = detect_indicator_events(
                    name=ind["name"],
                    label=ind["label"],
                    group=ind.get("group", "其他"),
                    dates=dates,
                    values=values,
                    threshold_low=ind.get("threshold_low"),
                    threshold_high=ind.get("threshold_high"),
                    direction=ind.get("direction", "up"),
                    lookback_days=30,
                )
                per_indicator.append(evs)
        events = merge_events(per_indicator)
        return render_template("events.html", events=events, active_page="events")

    @app.route("/heatmap")
    def heatmap():
        """风险矩阵热力图（视角 D）：横轴日期 × 纵轴指标，按 level 着色。"""
        target = app.config["DB_PATH"]
        hist_target = app.config.get("HISTORY_DB_PATH")
        indicator_data = []
        with dbmod.open_db(target) as conn:
            for ind in _INDICATOR_REGISTRY:
                dates, values = _fetch_history_pairs(
                    conn, ind["name"], days=90, history_db_path=hist_target
                )
                if len(values) < 2:
                    continue
                indicator_data.append({
                    "name": ind["name"],
                    "label": ind["label"],
                    "dates": dates,
                    "values": values,
                    "threshold_low": ind.get("threshold_low"),
                    "threshold_high": ind.get("threshold_high"),
                    "direction": ind.get("direction", "up"),
                })
        chart_html = build_heatmap_html(indicator_data, height=600)
        return render_template("heatmap.html", chart_html=chart_html, active_page="heatmap")

    @app.route("/timeline")
    def timeline():
        """综合温度计 2 年时间线（视角 E）：风险分历史走势 + 三档背景。"""
        target = app.config["DB_PATH"]
        with dbmod.open_db(target) as conn:
            history = rs.get_risk_series(conn, days=730)  # 约 2 年
            latest = rs.get_latest_risk_score(conn)
        dates = [r["date"] for r in history]
        scores = [float(r["score"]) for r in history]
        chart_html = build_risk_timeline_html(dates, scores, height=460)
        return render_template(
            "timeline.html",
            chart_html=chart_html,
            latest_risk=latest,
            point_count=len(history),
            active_page="timeline",
        )

    @app.route("/hedge")
    def hedge():
        """政策对冲对比页（视角 I）：风险面 vs 对冲面并排。"""
        target = app.config["DB_PATH"]
        hist_target = app.config.get("HISTORY_DB_PATH")
        with dbmod.open_db(target) as conn:
            rows = _build_rows(conn, history_db_path=hist_target)
        split = split_risk_vs_hedge(rows)
        return render_template(
            "hedge.html",
            risk_rows=split["risk"],
            hedge_rows=split["hedge"],
            active_page="hedge",
        )

    @app.route("/calibration")
    def calibration():
        """阈值校准面板（视角 J）：每条指标历史三档分布 + 过敏感/过迟钝判定。"""
        target = app.config["DB_PATH"]
        hist_target = app.config.get("HISTORY_DB_PATH")
        results = []
        with dbmod.open_db(target) as conn:
            for ind in _INDICATOR_REGISTRY:
                _, values = _fetch_history_pairs(
                    conn, ind["name"], days=1825, history_db_path=hist_target
                )
                cal = calibrate_threshold(
                    values=values,
                    threshold_low=ind.get("threshold_low"),
                    threshold_high=ind.get("threshold_high"),
                    direction=ind.get("direction", "up"),
                )
                cal["name"] = ind["name"]
                cal["label"] = ind["label"]
                results.append(cal)
        # 按 verdict 排序：too_sensitive 优先 → too_dull → ok → no_data
        order = {"too_sensitive": 0, "too_dull": 1, "ok": 2, "no_data": 3}
        results.sort(key=lambda c: order.get(c["verdict"], 4))
        return render_template(
            "calibration.html",
            calibrations=results,
            active_page="calibration",
        )

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.route("/api/chat", methods=["POST"])
    def api_chat():
        """对话接口：用户问题 + 当前指标快照 + 综合分 → LLM → JSON 返回。

        请求 body：
            {"messages": [{"role":"user","content":"..."}, ...]}
            或 {"message": "..."}
        响应：
            {"reply": "...", "model": "qwen3-coder-plus"} 或 {"error": "..."}
        """
        from src.fetch import llm_client
        from src.utils.config import load_settings

        try:
            data = request.get_json(silent=True) or {}
        except Exception:
            data = {}

        # 兼容两种入参
        msgs_in = data.get("messages")
        if not msgs_in and data.get("message"):
            msgs_in = [{"role": "user", "content": data["message"]}]
        if not msgs_in:
            return jsonify({"error": "缺少 message 或 messages 字段"}), 400

        # 拼系统 prompt + 当前快照
        target = app.config["DB_PATH"]
        with dbmod.open_db(target) as conn:
            snapshot = bf.build_snapshot(conn, _INDICATOR_REGISTRY)

        system_prompt = (
            "你是 Finance Radar 的市场风险助手。用户正在监控一份本地金融指标仪表盘。\n"
            "回答必须基于下面给出的指标快照（含当前值、等级、7 天前对比、综合温度计分），不要编造历史价位与外部新闻。\n"
            "若用户问的指标不在快照里，直接说『该指标不在当前监控范围』。\n"
            "回答简洁、客观、第三人称、中文，必要时引用快照里的具体数字。\n\n"
            f"=== 当前指标快照 ===\n{snapshot}\n=== 快照结束 ==="
        )
        messages = [{"role": "system", "content": system_prompt}] + list(msgs_in)

        s = load_settings()
        out = llm_client.chat(messages, settings=s, temperature=0.3)
        if out is None:
            return jsonify({"error": "LLM 调用失败（检查 .env DASHSCOPE_API_KEY 与网络）"}), 502
        return jsonify({"reply": out, "model": s.llm_model or ""})

    return app


if __name__ == "__main__":  # pragma: no cover
    settings = load_settings()
    create_app().run(
        host="127.0.0.1",
        port=settings.flask_port,
        debug=settings.flask_debug,
    )
