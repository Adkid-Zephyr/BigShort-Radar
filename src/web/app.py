"""Flask Web 应用：薄渲染层。

只做：从 store 读数据 → 算颜色 → 渲染模板。
不做：拉数、算阈值（阈值用 indicators 模块的常量）。

注册新指标的方式：在 _INDICATOR_REGISTRY 加一行（name, classify_fn, label）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List

from flask import Flask, render_template

from src.compute import briefing as bf
from src.compute import risk_score as rs
from src.compute.indicators import dxy as dxy_ind
from src.compute.indicators import hy_oas as hyoas_ind
from src.compute.indicators import ig_oas as igoas_ind
from src.compute.indicators import jp_10y as jp10y_ind
from src.compute.indicators import sofr_iorb as sofr_ind
from src.compute.indicators import usdjpy as usdjpy_ind
from src.compute.indicators import vix as vix_ind
from src.compute.indicators import vix_term_structure as vts_ind
from src.compute.indicators import yield_curve as yc_ind
from src.compute.indicators import yield_curve_10y3m as yc3m_ind
from src.compute.thresholds import Level
from src.store import db as dbmod
from src.utils.config import load_settings
from src.utils.logger import get_logger

log = get_logger(__name__)

# 模板目录在项目根 templates/，不是 src/web/templates/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATE_DIR = _PROJECT_ROOT / "templates"


# ── 指标注册表 ────────────────────────────────────────────────
# 加一个新指标，只需在这里加一行（含 group 字段做分组）
# group 取值约定：曲线 / 信用 / 流动性 / 波动率 / 估值（待加）
_INDICATOR_REGISTRY: List[Dict[str, Any]] = [
    # 波动率维度
    {
        "name": vix_ind.NAME,
        "label": "VIX 恐慌指数",
        "classify": vix_ind.classify_value,
        "group": "波动率",
    },
    {
        "name": vts_ind.NAME,
        "label": "VIX 期限结构（VIX/VIX3M）",
        "classify": vts_ind.classify_value,
        "group": "波动率",
    },
    # 曲线维度
    {
        "name": yc_ind.NAME,
        "label": "10Y-2Y 收益率曲线",
        "classify": yc_ind.classify_value,
        "group": "曲线",
    },
    {
        "name": yc3m_ind.NAME,
        "label": "10Y-3M 收益率曲线",
        "classify": yc3m_ind.classify_value,
        "group": "曲线",
    },
    # 信用维度
    {
        "name": hyoas_ind.NAME,
        "label": "HY OAS 高收益债利差",
        "classify": hyoas_ind.classify_value,
        "group": "信用",
    },
    {
        "name": igoas_ind.NAME,
        "label": "IG OAS 投资级利差",
        "classify": igoas_ind.classify_value,
        "group": "信用",
    },
    # 流动性维度
    {
        "name": sofr_ind.NAME,
        "label": "SOFR-IORB 流动性",
        "classify": sofr_ind.classify_value,
        "group": "流动性",
    },
    # 跨市场 / 日本维度
    {
        "name": usdjpy_ind.NAME,
        "label": "USDJPY 美元日元",
        "classify": usdjpy_ind.classify_value,
        "group": "跨市场",
    },
    {
        "name": dxy_ind.NAME,
        "label": "DXY 美元广义指数",
        "classify": dxy_ind.classify_value,
        "group": "跨市场",
    },
    {
        "name": jp10y_ind.NAME,
        "label": "日本 10Y 国债收益率",
        "classify": jp10y_ind.classify_value,
        "group": "跨市场",
    },
]

# 分组展示顺序（左到右、上到下；用户视角通常先看波动率再看信用再看曲线再看流动性）
_GROUP_ORDER = ["波动率", "信用", "曲线", "流动性", "跨市场", "估值"]


# Level → 颜色（Tailwind 风格的色值，inline style 用）
_LEVEL_COLORS = {
    Level.GREEN: "#22c55e",
    Level.YELLOW: "#eab308",
    Level.RED: "#ef4444",
}


def _build_rows(conn) -> List[Dict[str, Any]]:
    """从 DB 拉每个已注册指标的最新值，组装渲染行（含 group）。"""
    rows: List[Dict[str, Any]] = []
    for ind in _INDICATOR_REGISTRY:
        latest = dbmod.get_latest(conn, ind["name"])
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
                "ingested_at": None,
            })
            continue
        level = ind["classify"](latest["value"])
        rows.append({
            "name": ind["name"],
            "label": ind["label"],
            "group": ind.get("group", "其他"),
            "value": latest["value"],
            "level": level.value,
            "color": _LEVEL_COLORS.get(level, "#9ca3af"),
            "date": latest["date"],
            "source": latest["source"],
            "ingested_at": latest["ingested_at"],
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


def create_app(db_path=None) -> Flask:
    """工厂函数：创建 Flask 应用。

    入参：
        db_path: 可选，覆盖默认 DB 路径（测试用）
    返回：
        Flask 应用实例
    """
    settings = load_settings()
    app = Flask(__name__, template_folder=str(_TEMPLATE_DIR))
    app.config["DB_PATH"] = db_path if db_path is not None else settings.db_path

    @app.route("/")
    def index():
        target = app.config["DB_PATH"]
        with dbmod.open_db(target) as conn:
            rows = _build_rows(conn)
            briefing = bf.get_latest_briefing(conn)
            risk = rs.get_latest_risk_score(conn)
        groups = _group_rows(rows)
        return render_template(
            "index.html",
            rows=rows, groups=groups,
            briefing=briefing, risk=risk,
            level_colors={k.value: v for k, v in _LEVEL_COLORS.items()},
        )

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}

    return app


if __name__ == "__main__":  # pragma: no cover
    settings = load_settings()
    create_app().run(
        host="127.0.0.1",
        port=settings.flask_port,
        debug=settings.flask_debug,
    )
